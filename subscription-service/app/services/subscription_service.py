"""Business logic for subscription management."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.db.models import (
    BillingCycle, EventType, Invoice, InvoiceStatus,
    Subscription, SubscriptionStatus,
)
from app.repositories.event_repo import EventRepository
from app.repositories.invoice_repo import InvoiceRepository
from app.repositories.plan_repo import PlanRepository
from app.repositories.subscription_repo import SubscriptionRepository


class SubscriptionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = SubscriptionRepository(db)
        self.plan_repo = PlanRepository(db)
        self.invoice_repo = InvoiceRepository(db)
        self.event_repo = EventRepository(db)

    async def get_or_create(self, tenant_id: str, plan_slug: str) -> Subscription:
        """Idempotent: returns existing subscription or creates one on the given plan."""
        existing = await self.repo.get_by_tenant(tenant_id)
        if existing:
            return existing
        return await self.create({"tenant_id": tenant_id, "plan_slug": plan_slug})

    async def create(self, data: dict) -> Subscription:
        tenant_id = data["tenant_id"]
        plan_slug = data.get("plan_slug", "free")
        billing_cycle = data.get("billing_cycle", BillingCycle.monthly)

        existing = await self.repo.get_by_tenant(tenant_id)
        if existing:
            raise ConflictError(f"Tenant {tenant_id!r} already has a subscription")

        plan = await self.plan_repo.get_by_slug(plan_slug)
        if not plan:
            raise NotFoundError(f"Plan {plan_slug!r} not found")

        now = datetime.now(timezone.utc)
        period_end = now + timedelta(days=30)

        sub = await self.repo.create({
            "tenant_id": tenant_id,
            "plan_id": plan.id,
            "status": SubscriptionStatus.active,
            "billing_cycle": billing_cycle,
            "current_period_start": now,
            "current_period_end": period_end,
            "notes": data.get("notes"),
        })

        await self.event_repo.create(
            subscription_id=sub.id,
            tenant_id=tenant_id,
            event_type=EventType.created,
            data={"plan_slug": plan_slug},
            performed_by=data.get("performed_by"),
        )
        return sub

    async def get(self, tenant_id: str) -> Subscription:
        sub = await self.repo.get_by_tenant(tenant_id)
        if not sub:
            raise NotFoundError(f"No subscription found for tenant {tenant_id!r}")
        return sub

    async def list(
        self,
        status: str | None = None,
        plan_id: str | None = None,
        tenant_id: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[Subscription], int]:
        return await self.repo.list(
            status=status,
            plan_id=plan_id,
            tenant_id=tenant_id,
            offset=offset,
            limit=limit,
        )

    async def upgrade(self, tenant_id: str, plan_slug: str, performed_by: str | None = None) -> Subscription:
        sub = await self.get(tenant_id)
        old_plan = sub.plan
        plan = await self.plan_repo.get_by_slug(plan_slug)
        if not plan:
            raise NotFoundError(f"Plan {plan_slug!r} not found")

        sub = await self.repo.update(sub, {"plan_id": plan.id, "status": SubscriptionStatus.active})
        await self.event_repo.create(
            subscription_id=sub.id,
            tenant_id=tenant_id,
            event_type=EventType.plan_changed,
            data={"from": old_plan.slug if old_plan else None, "to": plan_slug},
            performed_by=performed_by,
        )
        return sub

    async def cancel(
        self,
        tenant_id: str,
        reason: str | None = None,
        performed_by: str | None = None,
    ) -> None:
        sub = await self.get(tenant_id)
        if sub.status == SubscriptionStatus.canceled:
            raise ValidationError("Subscription is already canceled")
        now = datetime.now(timezone.utc)
        await self.repo.update(sub, {
            "status": SubscriptionStatus.canceled,
            "canceled_at": now,
            "cancellation_reason": reason,
        })
        await self.event_repo.create(
            subscription_id=sub.id,
            tenant_id=tenant_id,
            event_type=EventType.canceled,
            data={"reason": reason},
            performed_by=performed_by,
        )

    async def reactivate(self, tenant_id: str, performed_by: str | None = None) -> Subscription:
        sub = await self.get(tenant_id)
        if sub.status == SubscriptionStatus.active:
            raise ValidationError("Subscription is already active")
        now = datetime.now(timezone.utc)
        sub = await self.repo.update(sub, {
            "status": SubscriptionStatus.active,
            "canceled_at": None,
            "cancellation_reason": None,
            "current_period_start": now,
            "current_period_end": now + timedelta(days=30),
        })
        await self.event_repo.create(
            subscription_id=sub.id,
            tenant_id=tenant_id,
            event_type=EventType.reactivated,
            performed_by=performed_by,
        )
        return sub

    async def generate_invoice(
        self,
        tenant_id: str,
        performed_by: str | None = None,
    ) -> Invoice:
        sub = await self.get(tenant_id)
        invoice_number = await self.invoice_repo.next_invoice_number()
        amount = sub.plan.price_monthly if sub.plan else Decimal("0")

        invoice = await self.invoice_repo.create({
            "subscription_id": sub.id,
            "tenant_id": tenant_id,
            "invoice_number": invoice_number,
            "status": InvoiceStatus.open,
            "amount": amount,
            "currency": sub.plan.currency if sub.plan else "USD",
            "period_start": sub.current_period_start,
            "period_end": sub.current_period_end,
            "line_items": [
                {
                    "description": f"{sub.plan.name} plan — {sub.billing_cycle}",
                    "quantity": 1,
                    "unit_price": float(amount),
                    "amount": float(amount),
                }
            ],
        })

        await self.event_repo.create(
            subscription_id=sub.id,
            tenant_id=tenant_id,
            event_type=EventType.invoice_generated,
            data={"invoice_number": invoice_number, "amount": float(amount)},
            performed_by=performed_by,
        )
        return invoice

    async def mark_invoice_paid(
        self,
        tenant_id: str,
        invoice_id: str,
        performed_by: str | None = None,
    ) -> Invoice:
        sub = await self.get(tenant_id)
        invoice = await self.invoice_repo.get_by_id(invoice_id)
        if not invoice or invoice.subscription_id != sub.id:
            raise NotFoundError(f"Invoice {invoice_id!r} not found")
        if invoice.status == InvoiceStatus.paid:
            raise ValidationError("Invoice is already paid")

        invoice = await self.invoice_repo.update(invoice, {
            "status": InvoiceStatus.paid,
            "paid_at": datetime.now(timezone.utc),
        })

        await self.event_repo.create(
            subscription_id=sub.id,
            tenant_id=tenant_id,
            event_type=EventType.payment_received,
            data={"invoice_number": invoice.invoice_number, "amount": float(invoice.amount)},
            performed_by=performed_by,
        )
        return invoice

    async def get_events(self, tenant_id: str) -> list:
        sub = await self.get(tenant_id)
        return await self.event_repo.list_by_subscription(sub.id)

    async def get_invoices(self, tenant_id: str) -> list[Invoice]:
        sub = await self.get(tenant_id)
        return await self.invoice_repo.list_by_subscription(sub.id)
