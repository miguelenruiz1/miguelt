"""Repository for DynamicMovementType CRUD."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DynamicMovementType


class MovementTypeRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(self, tenant_id: str, offset: int = 0, limit: int = 100) -> tuple[list[DynamicMovementType], int]:
        base = select(DynamicMovementType).where(DynamicMovementType.tenant_id == tenant_id)
        total = (await self.db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
        result = await self.db.execute(
            base.order_by(DynamicMovementType.sort_order, DynamicMovementType.name).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total

    async def get(self, tenant_id: str, type_id: str) -> DynamicMovementType | None:
        result = await self.db.execute(
            select(DynamicMovementType).where(
                DynamicMovementType.tenant_id == tenant_id,
                DynamicMovementType.id == type_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, tenant_id: str, slug: str) -> DynamicMovementType | None:
        result = await self.db.execute(
            select(DynamicMovementType).where(
                DynamicMovementType.tenant_id == tenant_id,
                DynamicMovementType.slug == slug,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, tenant_id: str, data: dict) -> DynamicMovementType:
        obj = DynamicMovementType(id=str(uuid.uuid4()), tenant_id=tenant_id, **data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update(self, obj: DynamicMovementType, data: dict) -> DynamicMovementType:
        for key, val in data.items():
            if val is not None:
                setattr(obj, key, val)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete(self, obj: DynamicMovementType) -> None:
        self.db.delete(obj)
        await self.db.flush()
