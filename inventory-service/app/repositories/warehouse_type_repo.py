"""Repository for DynamicWarehouseType CRUD."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DynamicWarehouseType


class WarehouseTypeRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(self, tenant_id: str, offset: int = 0, limit: int = 100) -> tuple[list[DynamicWarehouseType], int]:
        base = select(DynamicWarehouseType).where(DynamicWarehouseType.tenant_id == tenant_id)
        total = (await self.db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
        result = await self.db.execute(
            base.order_by(DynamicWarehouseType.sort_order, DynamicWarehouseType.name).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total

    async def get(self, tenant_id: str, type_id: str) -> DynamicWarehouseType | None:
        result = await self.db.execute(
            select(DynamicWarehouseType).where(
                DynamicWarehouseType.tenant_id == tenant_id,
                DynamicWarehouseType.id == type_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, tenant_id: str, data: dict) -> DynamicWarehouseType:
        obj = DynamicWarehouseType(id=str(uuid.uuid4()), tenant_id=tenant_id, **data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update(self, obj: DynamicWarehouseType, data: dict) -> DynamicWarehouseType:
        for key, val in data.items():
            if val is not None:
                setattr(obj, key, val)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete(self, obj: DynamicWarehouseType) -> None:
        self.db.delete(obj)
        await self.db.flush()
