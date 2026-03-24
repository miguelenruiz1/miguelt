"""Repository for CompliancePlot CRUD."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plot import CompliancePlot


class PlotRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(
        self,
        tenant_id: uuid.UUID,
        organization_id: uuid.UUID | None = None,
        risk_level: str | None = None,
        is_active: bool | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[CompliancePlot], int]:
        q = select(CompliancePlot).where(CompliancePlot.tenant_id == tenant_id)
        if organization_id is not None:
            q = q.where(CompliancePlot.organization_id == organization_id)
        if risk_level is not None:
            q = q.where(CompliancePlot.risk_level == risk_level)
        if is_active is not None:
            q = q.where(CompliancePlot.is_active == is_active)

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        q = q.order_by(CompliancePlot.plot_code).offset(offset).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def get_by_id(self, plot_id: uuid.UUID) -> CompliancePlot | None:
        result = await self.db.execute(
            select(CompliancePlot).where(CompliancePlot.id == plot_id)
        )
        return result.scalar_one_or_none()

    async def get_by_code(
        self, tenant_id: uuid.UUID, plot_code: str
    ) -> CompliancePlot | None:
        result = await self.db.execute(
            select(CompliancePlot).where(
                CompliancePlot.tenant_id == tenant_id,
                CompliancePlot.plot_code == plot_code,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, tenant_id: uuid.UUID, **kwargs) -> CompliancePlot:
        plot = CompliancePlot(id=uuid.uuid4(), tenant_id=tenant_id, **kwargs)
        self.db.add(plot)
        await self.db.flush()
        await self.db.refresh(plot)
        return plot

    async def update(self, plot: CompliancePlot, **kwargs) -> CompliancePlot:
        for k, v in kwargs.items():
            if v is not None:
                setattr(plot, k, v)
        plot.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(plot)
        return plot

    async def delete(self, plot: CompliancePlot) -> None:
        await self.db.delete(plot)
        await self.db.flush()
