"""Repository for EventTypeConfig CRUD."""
from __future__ import annotations

import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EventTypeConfig


class EventTypeConfigRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def list(
        self,
        tenant_id: uuid.UUID,
        active_only: bool = True,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[list[EventTypeConfig], int]:
        q = select(EventTypeConfig).where(EventTypeConfig.tenant_id == tenant_id)
        if active_only:
            q = q.where(EventTypeConfig.is_active.is_(True))
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self._db.execute(count_q)).scalar() or 0
        q = q.order_by(EventTypeConfig.sort_order, EventTypeConfig.name)
        q = q.offset(offset).limit(limit)
        rows = (await self._db.execute(q)).scalars().all()
        return list(rows), total

    async def get_by_id(self, config_id: uuid.UUID) -> EventTypeConfig | None:
        return await self._db.get(EventTypeConfig, config_id)

    async def get_by_slug(
        self, tenant_id: uuid.UUID, slug: str
    ) -> EventTypeConfig | None:
        q = select(EventTypeConfig).where(
            EventTypeConfig.tenant_id == tenant_id,
            EventTypeConfig.slug == slug,
        )
        return (await self._db.execute(q)).scalar_one_or_none()

    async def create(self, tenant_id: uuid.UUID, **kwargs) -> EventTypeConfig:
        row = EventTypeConfig(tenant_id=tenant_id, **kwargs)
        self._db.add(row)
        await self._db.flush()
        return row

    async def update(
        self, config: EventTypeConfig, **kwargs
    ) -> EventTypeConfig:
        for k, v in kwargs.items():
            if v is not None:
                setattr(config, k, v)
        await self._db.flush()
        return config

    async def delete(self, config: EventTypeConfig) -> None:
        await self._db.delete(config)
        await self._db.flush()
