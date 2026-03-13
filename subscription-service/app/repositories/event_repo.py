"""Repository for SubscriptionEvent operations."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EventType, SubscriptionEvent


class EventRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        subscription_id: str,
        tenant_id: str,
        event_type: EventType,
        data: dict | None = None,
        performed_by: str | None = None,
    ) -> SubscriptionEvent:
        event = SubscriptionEvent(
            id=str(uuid.uuid4()),
            subscription_id=subscription_id,
            tenant_id=tenant_id,
            event_type=event_type,
            data=data,
            performed_by=performed_by,
        )
        self.db.add(event)
        await self.db.flush()
        return event

    async def list_by_subscription(self, subscription_id: str) -> list[SubscriptionEvent]:
        result = await self.db.execute(
            select(SubscriptionEvent)
            .where(SubscriptionEvent.subscription_id == subscription_id)
            .order_by(SubscriptionEvent.created_at.desc())
        )
        return list(result.scalars().all())
