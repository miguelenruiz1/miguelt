"""Repository for StockAlert."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import StockAlert


class AlertRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(
        self,
        tenant_id: str,
        is_resolved: bool | None = None,
        alert_type: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[StockAlert], int]:
        q = select(StockAlert).where(StockAlert.tenant_id == tenant_id)
        if is_resolved is not None:
            q = q.where(StockAlert.is_resolved == is_resolved)
        if alert_type:
            q = q.where(StockAlert.alert_type == alert_type)
        total = (await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
        q = q.order_by(StockAlert.created_at.desc()).offset(offset).limit(limit)
        return list((await self.db.execute(q)).scalars().all()), total

    async def create(self, data: dict) -> StockAlert:
        obj = StockAlert(id=str(uuid.uuid4()), **data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def mark_read(self, alert_id: str, tenant_id: str) -> StockAlert | None:
        result = await self.db.execute(
            select(StockAlert).where(StockAlert.id == alert_id, StockAlert.tenant_id == tenant_id)
        )
        alert = result.scalar_one_or_none()
        if alert:
            alert.is_read = True
            await self.db.flush()
        return alert

    async def resolve(self, alert_id: str, tenant_id: str) -> StockAlert | None:
        result = await self.db.execute(
            select(StockAlert).where(StockAlert.id == alert_id, StockAlert.tenant_id == tenant_id)
        )
        alert = result.scalar_one_or_none()
        if alert:
            alert.is_resolved = True
            alert.resolved_at = datetime.now(timezone.utc)
            await self.db.flush()
        return alert

    async def get_expiry_alert(
        self, tenant_id: str, batch_id: str, alert_type: str,
    ) -> StockAlert | None:
        """Find an existing unresolved expiry alert for a specific batch."""
        result = await self.db.execute(
            select(StockAlert).where(
                StockAlert.tenant_id == tenant_id,
                StockAlert.batch_id == batch_id,
                StockAlert.alert_type == alert_type,
                StockAlert.is_resolved == False,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def count_unread(self, tenant_id: str) -> int:
        return (await self.db.execute(
            select(func.count()).where(
                StockAlert.tenant_id == tenant_id,
                StockAlert.is_read == False,  # noqa: E712
                StockAlert.is_resolved == False,  # noqa: E712
            )
        )).scalar_one()
