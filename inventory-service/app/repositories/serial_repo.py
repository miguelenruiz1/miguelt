"""Repository for EntitySerial CRUD."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EntitySerial


class SerialRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(
        self,
        tenant_id: str,
        entity_id: str | None = None,
        status_id: str | None = None,
        warehouse_id: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[EntitySerial], int]:
        q = select(EntitySerial).where(EntitySerial.tenant_id == tenant_id)
        if entity_id:
            q = q.where(EntitySerial.entity_id == entity_id)
        if status_id:
            q = q.where(EntitySerial.status_id == status_id)
        if warehouse_id:
            q = q.where(EntitySerial.warehouse_id == warehouse_id)
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar_one()
        q = q.order_by(EntitySerial.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def get(self, tenant_id: str, serial_id: str) -> EntitySerial | None:
        result = await self.db.execute(
            select(EntitySerial).where(
                EntitySerial.tenant_id == tenant_id, EntitySerial.id == serial_id
            )
        )
        return result.scalar_one_or_none()

    async def create(self, tenant_id: str, data: dict) -> EntitySerial:
        obj = EntitySerial(id=str(uuid.uuid4()), tenant_id=tenant_id, **data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update(self, obj: EntitySerial, data: dict) -> EntitySerial:
        for k, v in data.items():
            if v is not None:
                setattr(obj, k, v)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete(self, obj: EntitySerial) -> None:
        await self.db.delete(obj)
        await self.db.flush()
