"""Repository for Subscription CRUD operations."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Plan, Subscription, SubscriptionStatus


class SubscriptionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_tenant(self, tenant_id: str) -> Subscription | None:
        result = await self.db.execute(
            select(Subscription)
            .options(selectinload(Subscription.plan))
            .where(Subscription.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, sub_id: str) -> Subscription | None:
        result = await self.db.execute(
            select(Subscription)
            .options(selectinload(Subscription.plan))
            .where(Subscription.id == sub_id)
        )
        return result.scalar_one_or_none()

    async def create(self, data: dict) -> Subscription:
        sub = Subscription(id=str(uuid.uuid4()), **data)
        self.db.add(sub)
        await self.db.flush()
        await self.db.refresh(sub, ["plan"])
        return sub

    async def update(self, sub: Subscription, data: dict) -> Subscription:
        for k, v in data.items():
            setattr(sub, k, v)
        sub.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(sub, ["plan"])
        return sub

    async def list(
        self,
        status: str | None = None,
        plan_id: str | None = None,
        tenant_id: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[Subscription], int]:
        q = select(Subscription).options(selectinload(Subscription.plan))
        if status:
            q = q.where(Subscription.status == status)
        if plan_id:
            q = q.where(Subscription.plan_id == plan_id)
        if tenant_id:
            q = q.where(Subscription.tenant_id.ilike(f"%{tenant_id}%"))

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        q = q.order_by(Subscription.created_at.desc()).offset(offset).limit(limit)
        rows = list((await self.db.execute(q)).scalars().all())
        return rows, total

    async def count_by_status(self) -> dict[str, int]:
        result = await self.db.execute(
            select(Subscription.status, func.count(Subscription.id))
            .group_by(Subscription.status)
        )
        return {row[0]: row[1] for row in result.all()}

    async def mrr_by_plan(self) -> list[dict]:
        result = await self.db.execute(
            select(
                Plan.slug,
                Plan.name,
                Plan.price_monthly,
                func.count(Subscription.id).label("count"),
            )
            .join(Plan, Subscription.plan_id == Plan.id)
            .where(Subscription.status == SubscriptionStatus.active)
            .group_by(Plan.id, Plan.slug, Plan.name, Plan.price_monthly)
        )
        rows = []
        for r in result.all():
            price = float(r.price_monthly) if r.price_monthly and float(r.price_monthly) >= 0 else 0
            rows.append({
                "slug": r.slug,
                "name": r.name,
                "price_monthly": float(r.price_monthly) if r.price_monthly else 0,
                "count": r.count,
                "mrr": price * r.count,
            })
        return rows
