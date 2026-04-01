"""Repository for WarehouseLocation CRUD."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import WarehouseLocation


class LocationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(
        self, tenant_id: str, warehouse_id: str | None = None,
        offset: int = 0, limit: int = 100,
    ) -> tuple[list[WarehouseLocation], int]:
        base = select(WarehouseLocation).where(WarehouseLocation.tenant_id == tenant_id)
        if warehouse_id:
            base = base.where(WarehouseLocation.warehouse_id == warehouse_id)

        total = (await self.db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
        q = base.order_by(WarehouseLocation.sort_order, WarehouseLocation.name).offset(offset).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def get(self, tenant_id: str, location_id: str) -> WarehouseLocation | None:
        result = await self.db.execute(
            select(WarehouseLocation).where(
                WarehouseLocation.tenant_id == tenant_id,
                WarehouseLocation.id == location_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, tenant_id: str, data: dict) -> WarehouseLocation:
        obj = WarehouseLocation(id=str(uuid.uuid4()), tenant_id=tenant_id, **data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update(self, obj: WarehouseLocation, data: dict) -> WarehouseLocation:
        for key, val in data.items():
            if val is not None:
                setattr(obj, key, val)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete(self, obj: WarehouseLocation) -> None:
        await self.db.delete(obj)
        await self.db.flush()
