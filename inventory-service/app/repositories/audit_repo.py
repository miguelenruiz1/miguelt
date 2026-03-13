"""Repository for inventory audit logs."""
from __future__ import annotations

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.audit import InventoryAuditLog


class InventoryAuditRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        *,
        tenant_id: str,
        user_id: str,
        user_email: str | None = None,
        user_name: str | None = None,
        action: str,
        description: str | None = None,
        resource_type: str,
        resource_id: str,
        old_data: dict | None = None,
        new_data: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> InventoryAuditLog:
        log = InventoryAuditLog(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            user_id=user_id,
            user_email=user_email,
            user_name=user_name,
            action=action,
            description=description,
            resource_type=resource_type,
            resource_id=resource_id,
            old_data=old_data,
            new_data=new_data,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(log)
        await self.db.flush()
        return log

    async def list(
        self,
        tenant_id: str,
        *,
        action: str | None = None,
        user_id: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        offset: int = 0,
        limit: int = 25,
    ) -> tuple[list[InventoryAuditLog], int]:
        q = select(InventoryAuditLog).where(InventoryAuditLog.tenant_id == tenant_id)

        if action:
            like = f"%{action}%"
            q = q.where(
                or_(
                    InventoryAuditLog.action.ilike(like),
                    InventoryAuditLog.description.ilike(like),
                )
            )
        if user_id:
            q = q.where(InventoryAuditLog.user_id == user_id)
        if resource_type:
            q = q.where(InventoryAuditLog.resource_type == resource_type)
        if resource_id:
            q = q.where(InventoryAuditLog.resource_id == resource_id)
        if date_from:
            q = q.where(InventoryAuditLog.created_at >= date_from)
        if date_to:
            q = q.where(InventoryAuditLog.created_at <= date_to)

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        q = q.order_by(InventoryAuditLog.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def entity_timeline(
        self,
        tenant_id: str,
        resource_type: str,
        resource_id: str,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[InventoryAuditLog], int]:
        q = (
            select(InventoryAuditLog)
            .where(
                InventoryAuditLog.tenant_id == tenant_id,
                InventoryAuditLog.resource_type == resource_type,
                InventoryAuditLog.resource_id == resource_id,
            )
        )

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        q = q.order_by(InventoryAuditLog.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total
