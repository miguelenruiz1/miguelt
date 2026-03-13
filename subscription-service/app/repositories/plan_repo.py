"""Repository for Plan CRUD operations."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Plan


class PlanRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_active(self) -> list[Plan]:
        result = await self.db.execute(
            select(Plan)
            .where(Plan.is_archived == False)  # noqa: E712
            .order_by(Plan.sort_order, Plan.name)
        )
        return list(result.scalars().all())

    async def list_all(self) -> list[Plan]:
        result = await self.db.execute(
            select(Plan).order_by(Plan.sort_order, Plan.name)
        )
        return list(result.scalars().all())

    async def get_by_id(self, plan_id: str) -> Plan | None:
        result = await self.db.execute(select(Plan).where(Plan.id == plan_id))
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Plan | None:
        result = await self.db.execute(select(Plan).where(Plan.slug == slug))
        return result.scalar_one_or_none()

    async def create(self, data: dict) -> Plan:
        plan = Plan(id=str(uuid.uuid4()), **data)
        self.db.add(plan)
        await self.db.flush()
        await self.db.refresh(plan)
        return plan

    async def update(self, plan: Plan, data: dict) -> Plan:
        for k, v in data.items():
            setattr(plan, k, v)
        plan.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(plan)
        return plan

    async def archive(self, plan: Plan) -> Plan:
        plan.is_archived = True
        plan.is_active = False
        plan.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return plan
