"""Repository for Warehouse CRUD."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Warehouse
from app.db.models.production import ProductionRun


class WarehouseRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(
        self, tenant_id: str, is_active: bool | None = None,
        offset: int = 0, limit: int = 50,
    ) -> tuple[list[Warehouse], int]:
        base = select(Warehouse).where(Warehouse.tenant_id == tenant_id)
        if is_active is not None:
            base = base.where(Warehouse.is_active == is_active)

        count_q = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        q = base.order_by(Warehouse.name).offset(offset).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def get_by_id(self, warehouse_id: str, tenant_id: str) -> Warehouse | None:
        result = await self.db.execute(
            select(Warehouse).where(
                Warehouse.id == warehouse_id,
                Warehouse.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str, tenant_id: str) -> Warehouse | None:
        result = await self.db.execute(
            select(Warehouse).where(
                Warehouse.code == code,
                Warehouse.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_default(self, tenant_id: str) -> Warehouse | None:
        result = await self.db.execute(
            select(Warehouse).where(
                Warehouse.tenant_id == tenant_id,
                Warehouse.is_default == True,  # noqa: E712
                Warehouse.is_active == True,   # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def _demote_other_defaults(self, tenant_id: str, exclude_id: str | None = None) -> None:
        """Ensure only one warehouse per tenant has is_default=True.

        Called whenever a warehouse is created or updated with is_default=True.
        """
        from sqlalchemy import update as sa_update
        stmt = sa_update(Warehouse).where(
            Warehouse.tenant_id == tenant_id,
            Warehouse.is_default == True,  # noqa: E712
        ).values(is_default=False)
        if exclude_id is not None:
            stmt = stmt.where(Warehouse.id != exclude_id)
        await self.db.execute(stmt)

    async def create(self, data: dict) -> Warehouse:
        # Enforce single default per tenant
        if data.get("is_default") and data.get("tenant_id"):
            await self._demote_other_defaults(data["tenant_id"])
        wh = Warehouse(id=str(uuid.uuid4()), **data)
        self.db.add(wh)
        await self.db.flush()
        await self.db.refresh(wh)
        return wh

    async def update(self, wh: Warehouse, data: dict) -> Warehouse:
        # If this update marks the warehouse as default, demote any other
        # default for the same tenant first.
        if data.get("is_default") is True:
            await self._demote_other_defaults(wh.tenant_id, exclude_id=wh.id)
        for k, v in data.items():
            setattr(wh, k, v)
        await self.db.flush()
        await self.db.refresh(wh)
        return wh

    async def count_active_production_runs(self, warehouse_id: str, tenant_id: str) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(ProductionRun).where(
                ProductionRun.tenant_id == tenant_id,
                ProductionRun.warehouse_id == warehouse_id,
                ProductionRun.status != "completed",
            )
        )
        return result.scalar_one()

    async def soft_delete(self, wh: Warehouse) -> None:
        wh.is_active = False
        await self.db.flush()
