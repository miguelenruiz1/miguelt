"""Repository for ComplianceFramework queries."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.framework import ComplianceFramework


class FrameworkRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(
        self,
        target_market: str | None = None,
        commodity: str | None = None,
        active_only: bool = True,
    ) -> tuple[list[ComplianceFramework], int]:
        q = select(ComplianceFramework)
        if active_only:
            q = q.where(ComplianceFramework.is_active.is_(True))
        if target_market is not None:
            q = q.where(ComplianceFramework.target_markets.any(target_market))
        if commodity is not None:
            q = q.where(ComplianceFramework.applicable_commodities.any(commodity))

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        q = q.order_by(ComplianceFramework.name)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def get_by_id(self, framework_id: uuid.UUID) -> ComplianceFramework | None:
        result = await self.db.execute(
            select(ComplianceFramework).where(ComplianceFramework.id == framework_id)
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> ComplianceFramework | None:
        result = await self.db.execute(
            select(ComplianceFramework).where(ComplianceFramework.slug == slug)
        )
        return result.scalar_one_or_none()
