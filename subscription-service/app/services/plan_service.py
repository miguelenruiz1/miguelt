"""Business logic for plan management."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.db.models import Plan, Subscription, SubscriptionStatus
from app.repositories.plan_repo import PlanRepository


class PlanService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = PlanRepository(db)

    async def list_plans(self, include_archived: bool = False) -> list[Plan]:
        if include_archived:
            return await self.repo.list_all()
        return await self.repo.list_active()

    async def get_plan(self, plan_id: str) -> Plan:
        plan = await self.repo.get_by_id(plan_id)
        if not plan:
            raise NotFoundError(f"Plan {plan_id!r} not found")
        return plan

    async def create_plan(self, data: dict) -> Plan:
        existing = await self.repo.get_by_slug(data["slug"])
        if existing:
            raise ConflictError(f"Plan with slug {data['slug']!r} already exists")
        return await self.repo.create(data)

    async def update_plan(self, plan_id: str, data: dict) -> Plan:
        plan = await self.get_plan(plan_id)
        if "slug" in data and data["slug"] != plan.slug:
            existing = await self.repo.get_by_slug(data["slug"])
            if existing:
                raise ConflictError(f"Plan with slug {data['slug']!r} already exists")
        return await self.repo.update(plan, data)

    async def archive_plan(self, plan_id: str) -> None:
        plan = await self.get_plan(plan_id)
        active_count_result = await self.db.execute(
            select(func.count())
            .select_from(Subscription)
            .where(
                Subscription.plan_id == plan_id,
                Subscription.status == SubscriptionStatus.active,
            )
        )
        active_count = active_count_result.scalar_one()
        if active_count > 0:
            raise ConflictError(
                f"Cannot archive plan {plan.name!r}: {active_count} active subscription(s) exist"
            )
        await self.repo.archive(plan)
