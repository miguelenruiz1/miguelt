"""Repository for EntityBatch CRUD."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EntityBatch


class BatchRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(
        self,
        tenant_id: str,
        entity_id: str | None = None,
        is_active: bool | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[EntityBatch], int]:
        q = select(EntityBatch).where(EntityBatch.tenant_id == tenant_id)
        if entity_id:
            q = q.where(EntityBatch.entity_id == entity_id)
        if is_active is not None:
            q = q.where(EntityBatch.is_active == is_active)
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar_one()
        q = q.order_by(EntityBatch.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def get(self, tenant_id: str, batch_id: str) -> EntityBatch | None:
        result = await self.db.execute(
            select(EntityBatch).where(
                EntityBatch.tenant_id == tenant_id, EntityBatch.id == batch_id
            )
        )
        return result.scalar_one_or_none()

    async def create(self, tenant_id: str, data: dict) -> EntityBatch:
        obj = EntityBatch(id=str(uuid.uuid4()), tenant_id=tenant_id, **data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update(self, obj: EntityBatch, data: dict) -> EntityBatch:
        for k, v in data.items():
            if v is not None:
                setattr(obj, k, v)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def count_expiring(self, tenant_id: str, days: int = 30) -> int:
        """Count active batches with expiration_date within the next N days."""
        now = datetime.now(timezone.utc)
        cutoff = now + timedelta(days=days)
        result = await self.db.execute(
            select(func.count()).where(
                EntityBatch.tenant_id == tenant_id,
                EntityBatch.is_active == True,  # noqa: E712
                EntityBatch.expiration_date != None,  # noqa: E711
                EntityBatch.expiration_date >= now.date(),
                EntityBatch.expiration_date <= cutoff.date(),
            )
        )
        return result.scalar_one()

    async def product_has_active_batches(self, tenant_id: str, entity_id: str) -> bool:
        """Check if a product has any active batches (used to decide FEFO dispatch)."""
        result = await self.db.execute(
            select(func.count()).where(
                EntityBatch.tenant_id == tenant_id,
                EntityBatch.entity_id == entity_id,
                EntityBatch.is_active == True,  # noqa: E712
            )
        )
        return result.scalar_one() > 0

    async def get_expiring_soon(
        self,
        tenant_id: str,
        days: int = 30,
        warehouse_id: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[EntityBatch], int]:
        """Return active batches expiring within the next N days."""
        now = datetime.now(timezone.utc)
        cutoff = now + timedelta(days=days)
        q = select(EntityBatch).where(
            EntityBatch.tenant_id == tenant_id,
            EntityBatch.is_active == True,  # noqa: E712
            EntityBatch.expiration_date != None,  # noqa: E711
            EntityBatch.expiration_date >= now.date(),
            EntityBatch.expiration_date <= cutoff.date(),
        )
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar_one()
        q = q.order_by(EntityBatch.expiration_date.asc()).offset(offset).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def soft_delete(self, obj: EntityBatch) -> None:
        obj.is_active = False
        await self.db.flush()
