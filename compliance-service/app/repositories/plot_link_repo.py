"""Repository for CompliancePlotLink CRUD."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plot_link import CompliancePlotLink


class PlotLinkRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_for_record(
        self, record_id: uuid.UUID
    ) -> list[CompliancePlotLink]:
        result = await self.db.execute(
            select(CompliancePlotLink).where(
                CompliancePlotLink.record_id == record_id
            )
        )
        return list(result.scalars().all())

    async def get(
        self, record_id: uuid.UUID, plot_id: uuid.UUID
    ) -> CompliancePlotLink | None:
        result = await self.db.execute(
            select(CompliancePlotLink).where(
                CompliancePlotLink.record_id == record_id,
                CompliancePlotLink.plot_id == plot_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, tenant_id: uuid.UUID, **kwargs) -> CompliancePlotLink:
        link = CompliancePlotLink(id=uuid.uuid4(), tenant_id=tenant_id, **kwargs)
        self.db.add(link)
        await self.db.flush()
        await self.db.refresh(link)
        return link

    async def delete(self, link: CompliancePlotLink) -> None:
        await self.db.delete(link)
        await self.db.flush()

    async def count_for_record(self, record_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count()).where(CompliancePlotLink.record_id == record_id)
        )
        return result.scalar_one()
