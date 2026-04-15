"""Business logic for linking batches to compliance plots (cross-DB lineage)."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.db.models.tracking import BatchPlotOrigin, EntityBatch


class BatchOriginService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _ensure_batch(self, tenant_id: str, batch_id: str) -> EntityBatch:
        batch = (
            await self.db.execute(
                select(EntityBatch).where(
                    EntityBatch.tenant_id == tenant_id,
                    EntityBatch.id == batch_id,
                )
            )
        ).scalar_one_or_none()
        if batch is None:
            raise NotFoundError(f"Lote '{batch_id}' no encontrado")
        return batch

    async def create(
        self,
        tenant_id: str,
        batch_id: str,
        data: dict,
    ) -> BatchPlotOrigin:
        await self._ensure_batch(tenant_id, batch_id)
        row = BatchPlotOrigin(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            batch_id=batch_id,
            plot_id=data["plot_id"],
            plot_code=data.get("plot_code"),
            origin_quantity_kg=data["origin_quantity_kg"],
        )
        self.db.add(row)
        await self.db.flush()
        await self.db.refresh(row)
        return row

    async def list_for_batch(self, tenant_id: str, batch_id: str) -> list[BatchPlotOrigin]:
        await self._ensure_batch(tenant_id, batch_id)
        rows = (
            await self.db.execute(
                select(BatchPlotOrigin)
                .where(
                    BatchPlotOrigin.tenant_id == tenant_id,
                    BatchPlotOrigin.batch_id == batch_id,
                )
                .order_by(BatchPlotOrigin.created_at.asc())
            )
        ).scalars().all()
        return list(rows)
