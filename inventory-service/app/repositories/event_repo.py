"""Repository for inventory events and event config tables."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    EventImpact, EventSeverity, EventStatus, EventStatusLog, EventType, InventoryEvent,
)


class EventTypeRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(self, tenant_id: str, offset: int = 0, limit: int = 100) -> tuple[list[EventType], int]:
        base = select(EventType).where(EventType.tenant_id == tenant_id)
        total = (await self.db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
        result = await self.db.execute(base.order_by(EventType.name).offset(offset).limit(limit))
        return list(result.scalars().all()), total

    async def get(self, tenant_id: str, type_id: str) -> EventType | None:
        result = await self.db.execute(
            select(EventType).where(EventType.tenant_id == tenant_id, EventType.id == type_id)
        )
        return result.scalar_one_or_none()

    async def create(self, tenant_id: str, data: dict) -> EventType:
        obj = EventType(id=str(uuid.uuid4()), tenant_id=tenant_id, **data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update(self, obj: EventType, data: dict) -> EventType:
        for k, v in data.items():
            if v is not None:
                setattr(obj, k, v)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete(self, obj: EventType) -> None:
        await self.db.delete(obj)
        await self.db.flush()


class EventSeverityRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(self, tenant_id: str, offset: int = 0, limit: int = 100) -> tuple[list[EventSeverity], int]:
        base = select(EventSeverity).where(EventSeverity.tenant_id == tenant_id)
        total = (await self.db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
        result = await self.db.execute(base.order_by(EventSeverity.weight).offset(offset).limit(limit))
        return list(result.scalars().all()), total

    async def get(self, tenant_id: str, sev_id: str) -> EventSeverity | None:
        result = await self.db.execute(
            select(EventSeverity).where(EventSeverity.tenant_id == tenant_id, EventSeverity.id == sev_id)
        )
        return result.scalar_one_or_none()

    async def create(self, tenant_id: str, data: dict) -> EventSeverity:
        obj = EventSeverity(id=str(uuid.uuid4()), tenant_id=tenant_id, **data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update(self, obj: EventSeverity, data: dict) -> EventSeverity:
        for k, v in data.items():
            if v is not None:
                setattr(obj, k, v)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete(self, obj: EventSeverity) -> None:
        await self.db.delete(obj)
        await self.db.flush()


class EventStatusRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(self, tenant_id: str, offset: int = 0, limit: int = 100) -> tuple[list[EventStatus], int]:
        base = select(EventStatus).where(EventStatus.tenant_id == tenant_id)
        total = (await self.db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
        result = await self.db.execute(base.order_by(EventStatus.sort_order).offset(offset).limit(limit))
        return list(result.scalars().all()), total

    async def get(self, tenant_id: str, status_id: str) -> EventStatus | None:
        result = await self.db.execute(
            select(EventStatus).where(EventStatus.tenant_id == tenant_id, EventStatus.id == status_id)
        )
        return result.scalar_one_or_none()

    async def create(self, tenant_id: str, data: dict) -> EventStatus:
        obj = EventStatus(id=str(uuid.uuid4()), tenant_id=tenant_id, **data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update(self, obj: EventStatus, data: dict) -> EventStatus:
        for k, v in data.items():
            if v is not None:
                setattr(obj, k, v)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete(self, obj: EventStatus) -> None:
        await self.db.delete(obj)
        await self.db.flush()


class InventoryEventRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(
        self,
        tenant_id: str,
        event_type_id: str | None = None,
        severity_id: str | None = None,
        status_id: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[InventoryEvent], int]:
        q = select(InventoryEvent).where(InventoryEvent.tenant_id == tenant_id)
        if event_type_id:
            q = q.where(InventoryEvent.event_type_id == event_type_id)
        if severity_id:
            q = q.where(InventoryEvent.severity_id == severity_id)
        if status_id:
            q = q.where(InventoryEvent.status_id == status_id)
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar_one()
        q = (
            q.options(selectinload(InventoryEvent.impacts), selectinload(InventoryEvent.status_logs))
            .order_by(InventoryEvent.occurred_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(q)
        return list(result.scalars().unique().all()), total

    async def get(self, tenant_id: str, event_id: str) -> InventoryEvent | None:
        result = await self.db.execute(
            select(InventoryEvent)
            .options(selectinload(InventoryEvent.impacts), selectinload(InventoryEvent.status_logs))
            .where(InventoryEvent.tenant_id == tenant_id, InventoryEvent.id == event_id)
        )
        return result.scalar_one_or_none()

    async def create(self, data: dict) -> InventoryEvent:
        obj = InventoryEvent(id=str(uuid.uuid4()), **data)
        self.db.add(obj)
        await self.db.flush()
        # Full re-fetch to get server defaults + relationships
        result = await self.db.execute(
            select(InventoryEvent)
            .options(selectinload(InventoryEvent.impacts), selectinload(InventoryEvent.status_logs))
            .where(InventoryEvent.id == obj.id)
        )
        return result.scalar_one()

    async def update(self, obj: InventoryEvent, data: dict) -> InventoryEvent:
        for k, v in data.items():
            if v is not None:
                setattr(obj, k, v)
        await self.db.flush()
        # Full re-fetch to get server-side updated_at + all relationships
        result = await self.db.execute(
            select(InventoryEvent)
            .options(selectinload(InventoryEvent.impacts), selectinload(InventoryEvent.status_logs))
            .where(InventoryEvent.id == obj.id)
        )
        return result.scalar_one()

    async def count_by_severity(self, tenant_id: str) -> list[dict]:
        """Count open events (non-final status) grouped by severity name."""
        q = (
            select(
                EventSeverity.name.label("severity"),
                func.count(InventoryEvent.id).label("count"),
            )
            .join(EventSeverity, InventoryEvent.severity_id == EventSeverity.id)
            .join(EventStatus, InventoryEvent.status_id == EventStatus.id)
            .where(
                InventoryEvent.tenant_id == tenant_id,
                EventStatus.is_final == False,  # noqa: E712
            )
            .group_by(EventSeverity.name)
            .order_by(func.count(InventoryEvent.id).desc())
        )
        result = await self.db.execute(q)
        return [{"severity": row.severity, "count": row.count} for row in result.fetchall()]

    async def count_by_type(self, tenant_id: str) -> list[dict]:
        """Count open events grouped by event type name + color."""
        q = (
            select(
                EventType.name.label("type_name"),
                EventType.color.label("color"),
                func.count(InventoryEvent.id).label("count"),
            )
            .join(EventType, InventoryEvent.event_type_id == EventType.id)
            .join(EventStatus, InventoryEvent.status_id == EventStatus.id)
            .where(
                InventoryEvent.tenant_id == tenant_id,
                EventStatus.is_final == False,  # noqa: E712
            )
            .group_by(EventType.name, EventType.color)
            .order_by(func.count(InventoryEvent.id).desc())
        )
        result = await self.db.execute(q)
        return [{"type_name": row.type_name, "color": row.color, "count": row.count} for row in result.fetchall()]

    async def create_status_log(self, data: dict) -> EventStatusLog:
        obj = EventStatusLog(id=str(uuid.uuid4()), **data)
        self.db.add(obj)
        await self.db.flush()
        return obj

    async def create_impact(self, data: dict) -> EventImpact:
        obj = EventImpact(id=str(uuid.uuid4()), **data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj
