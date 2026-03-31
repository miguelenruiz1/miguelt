"""Platform administration service — superuser-only business metrics and tenant overview."""
from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, case, literal_column, text, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.settings import get_settings

from app.db.models import (
    BillingCycle,
    EventType,
    Plan,
    Subscription,
    SubscriptionStatus,
    Invoice,
    InvoiceStatus,
    LicenseKey,
    LicenseStatus,
    SubscriptionEvent,
    TenantModuleActivation,
    PaymentGatewayConfig,
)
from app.repositories.plan_repo import PlanRepository
from app.repositories.subscription_repo import SubscriptionRepository
from app.repositories.event_repo import EventRepository
from app.repositories.invoice_repo import InvoiceRepository


class PlatformService:
    def __init__(self, db: AsyncSession, redis=None) -> None:
        self.db = db
        self.redis = redis
        self.sub_repo = SubscriptionRepository(db)
        self.plan_repo = PlanRepository(db)
        self.event_repo = EventRepository(db)
        self.invoice_repo = InvoiceRepository(db)

    # ── Dashboard KPIs ────────────────────────────────────────────────────────

    async def get_dashboard(self) -> dict:
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        prev_month_start = (month_start - timedelta(days=1)).replace(day=1)

        # Subscription counts by status
        status_counts = dict(
            (await self.db.execute(
                select(Subscription.status, func.count(Subscription.id))
                .group_by(Subscription.status)
            )).all()
        )
        active = status_counts.get(SubscriptionStatus.active, 0)
        trialing = status_counts.get(SubscriptionStatus.trialing, 0)
        past_due = status_counts.get(SubscriptionStatus.past_due, 0)
        canceled = status_counts.get(SubscriptionStatus.canceled, 0)
        expired = status_counts.get(SubscriptionStatus.expired, 0)
        total_tenants = active + trialing + past_due + canceled + expired

        # MRR
        mrr_result = await self.db.execute(
            select(func.coalesce(func.sum(Plan.price_monthly), 0))
            .join(Subscription, Subscription.plan_id == Plan.id)
            .where(
                Subscription.status == SubscriptionStatus.active,
                Plan.price_monthly > 0,
            )
        )
        mrr = float(mrr_result.scalar_one())

        # Revenue this month (paid invoices)
        rev_this_month = (await self.db.execute(
            select(func.coalesce(func.sum(Invoice.amount), 0))
            .where(Invoice.status == InvoiceStatus.paid, Invoice.paid_at >= month_start)
        )).scalar_one()

        # Revenue last month
        rev_last_month = (await self.db.execute(
            select(func.coalesce(func.sum(Invoice.amount), 0))
            .where(
                Invoice.status == InvoiceStatus.paid,
                Invoice.paid_at >= prev_month_start,
                Invoice.paid_at < month_start,
            )
        )).scalar_one()

        # New subscriptions this month
        new_this_month = (await self.db.execute(
            select(func.count(Subscription.id))
            .where(Subscription.created_at >= month_start)
        )).scalar_one()

        # Canceled this month
        canceled_this_month = (await self.db.execute(
            select(func.count(Subscription.id))
            .where(
                Subscription.canceled_at >= month_start,
                Subscription.status == SubscriptionStatus.canceled,
            )
        )).scalar_one()

        # Churn rate (canceled / (active + canceled) if any)
        churn_base = active + canceled_this_month
        churn_rate = round((canceled_this_month / churn_base * 100) if churn_base > 0 else 0, 2)

        # Active licenses
        active_licenses = (await self.db.execute(
            select(func.count(LicenseKey.id))
            .where(LicenseKey.status == LicenseStatus.active)
        )).scalar_one()

        # Active modules (distinct activations)
        active_modules = (await self.db.execute(
            select(func.count(TenantModuleActivation.id))
            .where(TenantModuleActivation.is_active.is_(True))
        )).scalar_one()

        # Plan breakdown
        plan_breakdown = []
        pb_result = await self.db.execute(
            select(
                Plan.slug,
                Plan.name,
                Plan.price_monthly,
                func.count(Subscription.id).label("count"),
            )
            .join(Subscription, Subscription.plan_id == Plan.id)
            .where(Subscription.status.in_([
                SubscriptionStatus.active,
                SubscriptionStatus.trialing,
            ]))
            .group_by(Plan.id, Plan.slug, Plan.name, Plan.price_monthly)
            .order_by(Plan.price_monthly)
        )
        for r in pb_result.all():
            price = float(r.price_monthly) if r.price_monthly and float(r.price_monthly) >= 0 else 0
            plan_breakdown.append({
                "slug": r.slug,
                "name": r.name,
                "count": r.count,
                "mrr": round(price * r.count, 2),
            })

        # Module adoption — only count tenants that have a subscription
        module_adoption = []
        ma_result = await self.db.execute(
            select(
                TenantModuleActivation.module_slug,
                func.count(TenantModuleActivation.id).label("count"),
            )
            .where(
                TenantModuleActivation.is_active.is_(True),
                TenantModuleActivation.tenant_id.in_(
                    select(Subscription.tenant_id)
                ),
            )
            .group_by(TenantModuleActivation.module_slug)
        )
        for r in ma_result.all():
            module_adoption.append({
                "slug": r.module_slug,
                "active_tenants": r.count,
            })

        return {
            "total_tenants": total_tenants,
            "active": active,
            "trialing": trialing,
            "past_due": past_due,
            "canceled": canceled,
            "expired": expired,
            "mrr": round(mrr, 2),
            "arr": round(mrr * 12, 2),
            "revenue_this_month": round(float(rev_this_month), 2),
            "revenue_last_month": round(float(rev_last_month), 2),
            "new_this_month": new_this_month,
            "canceled_this_month": canceled_this_month,
            "churn_rate": churn_rate,
            "active_licenses": active_licenses,
            "active_modules": active_modules,
            "plan_breakdown": plan_breakdown,
            "module_adoption": module_adoption,
        }

    # ── Tenant list ───────────────────────────────────────────────────────────

    async def list_tenants(
        self,
        search: str | None = None,
        status: str | None = None,
        plan_slug: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> dict:
        q = (
            select(Subscription)
            .options(selectinload(Subscription.plan))
        )

        if status:
            q = q.where(Subscription.status == status)
        if plan_slug:
            q = q.join(Plan, Subscription.plan_id == Plan.id).where(Plan.slug == plan_slug)
        if search:
            q = q.where(Subscription.tenant_id.ilike(f"%{search}%"))

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        q = q.order_by(Subscription.created_at.desc()).offset(offset).limit(limit)
        subs = list((await self.db.execute(q)).scalars().all())

        # Enrich with modules per tenant
        tenant_ids = [s.tenant_id for s in subs]
        modules_map: dict[str, list[str]] = {}
        if tenant_ids:
            mod_result = await self.db.execute(
                select(
                    TenantModuleActivation.tenant_id,
                    TenantModuleActivation.module_slug,
                )
                .where(
                    TenantModuleActivation.tenant_id.in_(tenant_ids),
                    TenantModuleActivation.is_active.is_(True),
                )
            )
            for row in mod_result.all():
                modules_map.setdefault(row.tenant_id, []).append(row.module_slug)

        # Enrich with invoice count / total revenue per tenant
        revenue_map: dict[str, dict] = {}
        if tenant_ids:
            rev_result = await self.db.execute(
                select(
                    Invoice.tenant_id,
                    func.count(Invoice.id).label("invoice_count"),
                    func.coalesce(func.sum(
                        case(
                            (Invoice.status == InvoiceStatus.paid, Invoice.amount),
                            else_=literal_column("0"),
                        )
                    ), 0).label("total_revenue"),
                )
                .where(Invoice.tenant_id.in_(tenant_ids))
                .group_by(Invoice.tenant_id)
            )
            for row in rev_result.all():
                revenue_map[row.tenant_id] = {
                    "invoice_count": row.invoice_count,
                    "total_revenue": round(float(row.total_revenue), 2),
                }

        items = []
        for sub in subs:
            items.append({
                "tenant_id": sub.tenant_id,
                "plan": {
                    "slug": sub.plan.slug,
                    "name": sub.plan.name,
                    "price_monthly": float(sub.plan.price_monthly),
                },
                "status": sub.status.value,
                "billing_cycle": sub.billing_cycle.value,
                "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
                "trial_ends_at": sub.trial_ends_at.isoformat() if sub.trial_ends_at else None,
                "canceled_at": sub.canceled_at.isoformat() if sub.canceled_at else None,
                "created_at": sub.created_at.isoformat() if sub.created_at else None,
                "active_modules": modules_map.get(sub.tenant_id, []),
                "invoice_count": revenue_map.get(sub.tenant_id, {}).get("invoice_count", 0),
                "total_revenue": revenue_map.get(sub.tenant_id, {}).get("total_revenue", 0),
            })

        return {"items": items, "total": total, "offset": offset, "limit": limit}

    # ── Tenant detail ─────────────────────────────────────────────────────────

    async def get_tenant_detail(self, tenant_id: str) -> dict | None:
        sub = (await self.db.execute(
            select(Subscription)
            .options(selectinload(Subscription.plan))
            .where(Subscription.tenant_id == tenant_id)
        )).scalar_one_or_none()

        if not sub:
            return None

        # Modules
        mods = (await self.db.execute(
            select(TenantModuleActivation)
            .where(TenantModuleActivation.tenant_id == tenant_id)
        )).scalars().all()

        # Invoices
        invoices = (await self.db.execute(
            select(Invoice)
            .where(Invoice.tenant_id == tenant_id)
            .order_by(Invoice.created_at.desc())
            .limit(20)
        )).scalars().all()

        # Licenses
        licenses = (await self.db.execute(
            select(LicenseKey)
            .where(LicenseKey.tenant_id == tenant_id)
            .order_by(LicenseKey.created_at.desc())
            .limit(20)
        )).scalars().all()

        # Events
        events = (await self.db.execute(
            select(SubscriptionEvent)
            .where(SubscriptionEvent.tenant_id == tenant_id)
            .order_by(SubscriptionEvent.created_at.desc())
            .limit(50)
        )).scalars().all()

        # Payment gateway
        gateway = (await self.db.execute(
            select(PaymentGatewayConfig)
            .where(
                PaymentGatewayConfig.tenant_id == tenant_id,
                PaymentGatewayConfig.is_active.is_(True),
            )
        )).scalar_one_or_none()

        return {
            "tenant_id": tenant_id,
            "subscription": {
                "id": sub.id,
                "status": sub.status.value,
                "billing_cycle": sub.billing_cycle.value,
                "current_period_start": sub.current_period_start.isoformat() if sub.current_period_start else None,
                "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
                "trial_ends_at": sub.trial_ends_at.isoformat() if sub.trial_ends_at else None,
                "canceled_at": sub.canceled_at.isoformat() if sub.canceled_at else None,
                "cancellation_reason": sub.cancellation_reason,
                "created_at": sub.created_at.isoformat() if sub.created_at else None,
                "plan": {
                    "slug": sub.plan.slug,
                    "name": sub.plan.name,
                    "price_monthly": float(sub.plan.price_monthly),
                    "price_annual": float(sub.plan.price_annual) if sub.plan.price_annual else None,
                    "max_users": sub.plan.max_users,
                    "max_assets": sub.plan.max_assets,
                    "max_wallets": sub.plan.max_wallets,
                    "modules": sub.plan.modules,
                },
            },
            "modules": [
                {
                    "slug": m.module_slug,
                    "is_active": m.is_active,
                    "activated_at": m.activated_at.isoformat() if m.activated_at else None,
                    "deactivated_at": m.deactivated_at.isoformat() if m.deactivated_at else None,
                }
                for m in mods
            ],
            "invoices": [
                {
                    "id": inv.id,
                    "invoice_number": inv.invoice_number,
                    "status": inv.status.value,
                    "amount": float(inv.amount),
                    "currency": inv.currency,
                    "period_start": inv.period_start.isoformat() if inv.period_start else None,
                    "period_end": inv.period_end.isoformat() if inv.period_end else None,
                    "paid_at": inv.paid_at.isoformat() if inv.paid_at else None,
                    "created_at": inv.created_at.isoformat() if inv.created_at else None,
                }
                for inv in invoices
            ],
            "licenses": [
                {
                    "id": lic.id,
                    "key": lic.key,
                    "status": lic.status.value,
                    "activations_count": lic.activations_count,
                    "max_activations": lic.max_activations,
                    "issued_at": lic.issued_at.isoformat() if lic.issued_at else None,
                    "expires_at": lic.expires_at.isoformat() if lic.expires_at else None,
                }
                for lic in licenses
            ],
            "events": [
                {
                    "id": ev.id,
                    "event_type": ev.event_type.value,
                    "data": ev.data,
                    "performed_by": ev.performed_by,
                    "created_at": ev.created_at.isoformat() if ev.created_at else None,
                }
                for ev in events
            ],
            "active_gateway": {
                "slug": gateway.gateway_slug,
                "display_name": gateway.display_name,
                "is_test_mode": gateway.is_test_mode,
            } if gateway else None,
        }

    # ── Analytics (trends) ────────────────────────────────────────────────────

    async def get_analytics(self, months: int = 6) -> dict:
        now = datetime.now(timezone.utc)

        # Monthly subscription growth (last N months)
        growth = []
        for i in range(months - 1, -1, -1):
            month_dt = now - timedelta(days=30 * i)
            month_end = month_dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if i > 0:
                label = month_end.strftime("%Y-%m")
            else:
                label = now.strftime("%Y-%m")
                month_end = now

            count = (await self.db.execute(
                select(func.count(Subscription.id))
                .where(Subscription.created_at <= month_end)
            )).scalar_one()
            growth.append({"month": label, "total_subscriptions": count})

        # Monthly revenue (last N months)
        revenue_trend = []
        for i in range(months - 1, -1, -1):
            ref = now - timedelta(days=30 * i)
            m_start = ref.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if i > 0:
                next_month = (m_start + timedelta(days=32)).replace(day=1)
            else:
                next_month = now

            rev = (await self.db.execute(
                select(func.coalesce(func.sum(Invoice.amount), 0))
                .where(
                    Invoice.status == InvoiceStatus.paid,
                    Invoice.paid_at >= m_start,
                    Invoice.paid_at < next_month,
                )
            )).scalar_one()
            revenue_trend.append({"month": m_start.strftime("%Y-%m"), "revenue": round(float(rev), 2)})

        # Status distribution
        status_dist = []
        sd_result = await self.db.execute(
            select(Subscription.status, func.count(Subscription.id))
            .group_by(Subscription.status)
        )
        for row in sd_result.all():
            status_dist.append({"status": row[0].value if hasattr(row[0], 'value') else row[0], "count": row[1]})

        # Module adoption over time (simplified: current snapshot)
        module_stats = []
        ms_result = await self.db.execute(
            select(
                TenantModuleActivation.module_slug,
                func.count(TenantModuleActivation.id).filter(
                    TenantModuleActivation.is_active.is_(True)
                ).label("active"),
                func.count(TenantModuleActivation.id).label("total"),
            )
            .group_by(TenantModuleActivation.module_slug)
        )
        for r in ms_result.all():
            module_stats.append({
                "slug": r.module_slug,
                "active": r.active,
                "total": r.total,
            })

        # Recent events
        recent_events = (await self.db.execute(
            select(SubscriptionEvent)
            .order_by(SubscriptionEvent.created_at.desc())
            .limit(20)
        )).scalars().all()

        return {
            "subscription_growth": growth,
            "revenue_trend": revenue_trend,
            "status_distribution": status_dist,
            "module_adoption": module_stats,
            "recent_events": [
                {
                    "id": e.id,
                    "tenant_id": e.tenant_id,
                    "event_type": e.event_type.value,
                    "data": e.data,
                    "performed_by": e.performed_by,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in recent_events
            ],
        }

    # ── Sales metrics ─────────────────────────────────────────────────────────

    async def get_sales_metrics(self) -> dict:
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Upcoming renewals (period end in next 30 days)
        upcoming_renewals = (await self.db.execute(
            select(Subscription)
            .options(selectinload(Subscription.plan))
            .where(
                Subscription.status == SubscriptionStatus.active,
                Subscription.current_period_end <= now + timedelta(days=30),
                Subscription.current_period_end > now,
            )
            .order_by(Subscription.current_period_end.asc())
        )).scalars().all()

        # Overdue (period ended, still active — should pay)
        overdue = (await self.db.execute(
            select(Subscription)
            .options(selectinload(Subscription.plan))
            .where(
                Subscription.status.in_([SubscriptionStatus.active, SubscriptionStatus.past_due]),
                Subscription.current_period_end < now,
            )
            .order_by(Subscription.current_period_end.asc())
        )).scalars().all()

        # Recently canceled (last 30 days)
        recently_canceled = (await self.db.execute(
            select(Subscription)
            .options(selectinload(Subscription.plan))
            .where(
                Subscription.status == SubscriptionStatus.canceled,
                Subscription.canceled_at >= month_start,
            )
            .order_by(Subscription.canceled_at.desc())
        )).scalars().all()

        # Open invoices (unpaid)
        open_invoices = (await self.db.execute(
            select(Invoice)
            .where(Invoice.status == InvoiceStatus.open)
            .order_by(Invoice.created_at.desc())
            .limit(50)
        )).scalars().all()

        # Paid this month
        paid_this_month_count = (await self.db.execute(
            select(func.count(Invoice.id))
            .where(Invoice.status == InvoiceStatus.paid, Invoice.paid_at >= month_start)
        )).scalar_one()

        total_open_amount = (await self.db.execute(
            select(func.coalesce(func.sum(Invoice.amount), 0))
            .where(Invoice.status == InvoiceStatus.open)
        )).scalar_one()

        def _sub_item(s: Subscription) -> dict:
            return {
                "tenant_id": s.tenant_id,
                "plan_name": s.plan.name if s.plan else "?",
                "plan_slug": s.plan.slug if s.plan else "?",
                "price_monthly": float(s.plan.price_monthly) if s.plan else 0,
                "status": s.status.value,
                "billing_cycle": s.billing_cycle.value,
                "current_period_end": s.current_period_end.isoformat() if s.current_period_end else None,
                "canceled_at": s.canceled_at.isoformat() if s.canceled_at else None,
                "cancellation_reason": s.cancellation_reason,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }

        return {
            "upcoming_renewals": [_sub_item(s) for s in upcoming_renewals],
            "overdue": [_sub_item(s) for s in overdue],
            "recently_canceled": [_sub_item(s) for s in recently_canceled],
            "open_invoices": [
                {
                    "id": inv.id,
                    "tenant_id": inv.tenant_id,
                    "invoice_number": inv.invoice_number,
                    "amount": float(inv.amount),
                    "currency": inv.currency,
                    "period_end": inv.period_end.isoformat() if inv.period_end else None,
                    "created_at": inv.created_at.isoformat() if inv.created_at else None,
                }
                for inv in open_invoices
            ],
            "paid_this_month_count": paid_this_month_count,
            "total_open_amount": round(float(total_open_amount), 2),
            "upcoming_renewal_count": len(upcoming_renewals),
            "overdue_count": len(overdue),
            "canceled_this_month_count": len(recently_canceled),
        }

    # ── Onboard tenant (full flow: user + subscription + modules) ──────────────

    async def onboard_tenant(
        self,
        tenant_id: str,
        company_name: str,
        admin_email: str,
        admin_password: str,
        admin_name: str,
        plan_slug: str,
        billing_cycle: str = "monthly",
        modules: list[str] | None = None,
        notes: str | None = None,
        performed_by: str | None = None,
        http_client: "httpx.AsyncClient | None" = None,
    ) -> dict:
        import httpx as _httpx
        import logging

        log = logging.getLogger("platform.onboard")
        settings = get_settings()

        # 1. Check if tenant already has a subscription
        existing = await self.sub_repo.get_by_tenant(tenant_id)
        if existing:
            raise ValueError(f"Tenant '{tenant_id}' ya tiene una suscripción activa")

        # 2. Register admin user in user-service (creates the tenant there)
        client = http_client or _httpx.AsyncClient(timeout=15.0)
        user_created = None
        try:
            resp = await client.post(
                f"{settings.USER_SERVICE_URL}/api/v1/auth/register",
                headers={"X-Tenant-Id": tenant_id, "Content-Type": "application/json"},
                json={
                    "email": admin_email,
                    "username": admin_email.split("@")[0],
                    "full_name": admin_name,
                    "password": admin_password,
                    "company": company_name,
                    "tenant_id": tenant_id,
                },
            )
            if resp.status_code == 201:
                user_created = resp.json()
                log.info("onboard_user_created tenant=%s email=%s", tenant_id, admin_email)
            elif resp.status_code == 409 or "already exists" in resp.text.lower():
                log.info("onboard_user_already_exists tenant=%s email=%s", tenant_id, admin_email)
            else:
                detail = resp.json().get("detail", resp.text) if resp.headers.get("content-type", "").startswith("application/json") else resp.text
                raise ValueError(f"Error al crear usuario admin: {detail}")
        except _httpx.RequestError as exc:
            raise ValueError(f"user-service no disponible: {exc}")

        # 3. Create subscription locally
        plan = await self.plan_repo.get_by_slug(plan_slug)
        if not plan:
            raise ValueError(f"Plan '{plan_slug}' no encontrado")

        now = datetime.now(timezone.utc)
        cycle = BillingCycle(billing_cycle) if billing_cycle in [e.value for e in BillingCycle] else BillingCycle.monthly
        period_days = 365 if cycle == BillingCycle.annual else 30

        sub = await self.sub_repo.create({
            "tenant_id": tenant_id,
            "plan_id": plan.id,
            "status": SubscriptionStatus.active,
            "billing_cycle": cycle,
            "current_period_start": now,
            "current_period_end": now + timedelta(days=period_days),
            "notes": notes,
        })

        await self.event_repo.create(
            subscription_id=sub.id,
            tenant_id=tenant_id,
            event_type=EventType.created,
            data={
                "plan_slug": plan_slug,
                "admin_email": admin_email,
                "company_name": company_name,
                "source": "platform_onboard",
            },
            performed_by=performed_by,
        )

        # 4. Activate modules
        activated = []
        for slug in (modules or []):
            existing_mod = (await self.db.execute(
                select(TenantModuleActivation)
                .where(
                    TenantModuleActivation.tenant_id == tenant_id,
                    TenantModuleActivation.module_slug == slug,
                )
            )).scalar_one_or_none()

            if existing_mod:
                if not existing_mod.is_active:
                    existing_mod.is_active = True
                    existing_mod.activated_at = now
                    existing_mod.activated_by = performed_by
                    existing_mod.deactivated_at = None
                    existing_mod.deactivated_by = None
                activated.append(slug)
            else:
                self.db.add(TenantModuleActivation(
                    id=str(uuid.uuid4()),
                    tenant_id=tenant_id,
                    module_slug=slug,
                    is_active=True,
                    activated_at=now,
                    activated_by=performed_by,
                ))
                activated.append(slug)

        await self.db.flush()
        await self.db.refresh(sub, ["plan"])

        return {
            "tenant_id": tenant_id,
            "subscription_id": sub.id,
            "plan": plan_slug,
            "billing_cycle": cycle.value,
            "period_end": sub.current_period_end.isoformat(),
            "modules_activated": activated,
            "admin_email": admin_email,
            "company_name": company_name,
            "user_created": user_created is not None,
        }

    # ── Change plan for a tenant ──────────────────────────────────────────────

    async def change_tenant_plan(
        self,
        tenant_id: str,
        plan_slug: str,
        performed_by: str | None = None,
    ) -> dict:
        sub = await self.sub_repo.get_by_tenant(tenant_id)
        if not sub:
            raise ValueError(f"No subscription for tenant {tenant_id!r}")

        old_plan = sub.plan
        new_plan = await self.plan_repo.get_by_slug(plan_slug)
        if not new_plan:
            raise ValueError(f"Plan {plan_slug!r} not found")

        sub = await self.sub_repo.update(sub, {
            "plan_id": new_plan.id,
            "status": SubscriptionStatus.active,
        })

        await self.event_repo.create(
            subscription_id=sub.id,
            tenant_id=tenant_id,
            event_type=EventType.plan_changed,
            data={"from": old_plan.slug if old_plan else None, "to": plan_slug, "source": "platform_admin"},
            performed_by=performed_by,
        )

        return {
            "tenant_id": tenant_id,
            "old_plan": old_plan.slug if old_plan else None,
            "new_plan": plan_slug,
        }

    # ── Toggle module for a tenant ────────────────────────────────────────────

    async def toggle_tenant_module(
        self,
        tenant_id: str,
        module_slug: str,
        active: bool,
        performed_by: str | None = None,
    ) -> dict:
        now = datetime.now(timezone.utc)
        existing = (await self.db.execute(
            select(TenantModuleActivation)
            .where(
                TenantModuleActivation.tenant_id == tenant_id,
                TenantModuleActivation.module_slug == module_slug,
            )
        )).scalar_one_or_none()

        if existing:
            existing.is_active = active
            if active:
                existing.activated_at = now
                existing.activated_by = performed_by
                existing.deactivated_at = None
            else:
                existing.deactivated_at = now
                existing.deactivated_by = performed_by
        else:
            self.db.add(TenantModuleActivation(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                module_slug=module_slug,
                is_active=active,
                activated_at=now if active else None,
                activated_by=performed_by if active else None,
            ))

        await self.db.flush()
        return {"tenant_id": tenant_id, "module": module_slug, "is_active": active}

    # ── Generate invoice for tenant ───────────────────────────────────────────

    async def generate_tenant_invoice(
        self,
        tenant_id: str,
        performed_by: str | None = None,
    ) -> dict:
        sub = await self.sub_repo.get_by_tenant(tenant_id)
        if not sub:
            raise ValueError(f"No subscription for tenant {tenant_id!r}")

        invoice_number = await self.invoice_repo.next_invoice_number()
        amount = sub.plan.price_monthly if sub.plan else 0

        invoice = await self.invoice_repo.create({
            "subscription_id": sub.id,
            "tenant_id": tenant_id,
            "invoice_number": invoice_number,
            "status": InvoiceStatus.open,
            "amount": amount,
            "currency": sub.plan.currency if sub.plan else "USD",
            "period_start": sub.current_period_start,
            "period_end": sub.current_period_end,
            "line_items": [{
                "description": f"{sub.plan.name} — {sub.billing_cycle.value}",
                "quantity": 1,
                "unit_price": float(amount),
                "amount": float(amount),
            }],
        })

        await self.event_repo.create(
            subscription_id=sub.id,
            tenant_id=tenant_id,
            event_type=EventType.invoice_generated,
            data={"invoice_number": invoice_number, "amount": float(amount), "source": "platform_admin"},
            performed_by=performed_by,
        )

        return {
            "id": invoice.id,
            "invoice_number": invoice_number,
            "amount": float(amount),
            "status": invoice.status.value,
        }

    # ── Cancel tenant subscription ────────────────────────────────────────────

    async def cancel_tenant_subscription(
        self,
        tenant_id: str,
        reason: str | None = None,
        performed_by: str | None = None,
    ) -> dict:
        sub = await self.sub_repo.get_by_tenant(tenant_id)
        if not sub:
            raise ValueError(f"No subscription for tenant {tenant_id!r}")

        now = datetime.now(timezone.utc)
        await self.sub_repo.update(sub, {
            "status": SubscriptionStatus.canceled,
            "canceled_at": now,
            "cancellation_reason": reason,
        })
        await self.event_repo.create(
            subscription_id=sub.id,
            tenant_id=tenant_id,
            event_type=EventType.canceled,
            data={"reason": reason, "source": "platform_admin"},
            performed_by=performed_by,
        )
        return {"tenant_id": tenant_id, "status": "canceled"}

    # ── Reactivate tenant subscription ────────────────────────────────────────

    async def reactivate_tenant_subscription(
        self,
        tenant_id: str,
        performed_by: str | None = None,
    ) -> dict:
        sub = await self.sub_repo.get_by_tenant(tenant_id)
        if not sub:
            raise ValueError(f"No subscription for tenant {tenant_id!r}")

        now = datetime.now(timezone.utc)
        await self.sub_repo.update(sub, {
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
            data={"source": "platform_admin"},
            performed_by=performed_by,
        )
        return {"tenant_id": tenant_id, "status": "active"}

    # ── Generate payment link (token-based) ───────────────────────────────────

    async def generate_payment_link(
        self,
        tenant_id: str,
        performed_by: str | None = None,
    ) -> dict:
        sub = await self.sub_repo.get_by_tenant(tenant_id)
        if not sub:
            raise ValueError(f"No subscription for tenant {tenant_id!r}")

        # Generate a unique token for this payment
        token = secrets.token_urlsafe(32)
        amount = float(sub.plan.price_monthly) if sub.plan else 0

        # Generate an invoice if there isn't an open one
        open_inv = (await self.db.execute(
            select(Invoice)
            .where(
                Invoice.tenant_id == tenant_id,
                Invoice.status == InvoiceStatus.open,
            )
            .order_by(Invoice.created_at.desc())
            .limit(1)
        )).scalar_one_or_none()

        if not open_inv:
            inv_result = await self.generate_tenant_invoice(tenant_id, performed_by)
            invoice_number = inv_result["invoice_number"]
        else:
            invoice_number = open_inv.invoice_number
            amount = float(open_inv.amount)

        # Persist token in Redis (24h TTL) so checkout can validate it
        import json
        if self.redis:
            await self.redis.set(
                f"payment_link:{token}",
                json.dumps({"tenant_id": tenant_id, "invoice_number": invoice_number, "amount": amount}),
                ex=86400,
            )

        return {
            "tenant_id": tenant_id,
            "token": token,
            "invoice_number": invoice_number,
            "amount": amount,
            "currency": sub.plan.currency if sub.plan else "USD",
            "plan_name": sub.plan.name if sub.plan else "?",
            "link": f"/checkout?token={token}&tenant={tenant_id}",
        }
