"""Repository for TenantModuleActivation CRUD operations."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TenantModuleActivation


class ModuleRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, tenant_id: str, slug: str) -> TenantModuleActivation | None:
        result = await self.db.execute(
            select(TenantModuleActivation).where(
                TenantModuleActivation.tenant_id == tenant_id,
                TenantModuleActivation.module_slug == slug,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_tenant(self, tenant_id: str) -> list[TenantModuleActivation]:
        result = await self.db.execute(
            select(TenantModuleActivation)
            .where(TenantModuleActivation.tenant_id == tenant_id)
            .order_by(TenantModuleActivation.module_slug)
        )
        return list(result.scalars().all())

    async def activate(
        self,
        tenant_id: str,
        slug: str,
        performed_by: str | None = None,
    ) -> TenantModuleActivation:
        """Upsert an activation record (insert or reactivate)."""
        existing = await self.get(tenant_id, slug)
        now = datetime.now(timezone.utc)
        if existing:
            existing.is_active = True
            existing.activated_at = now
            existing.activated_by = performed_by
            existing.deactivated_at = None
            existing.deactivated_by = None
            await self.db.flush()
            await self.db.refresh(existing)
            return existing

        record = TenantModuleActivation(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            module_slug=slug,
            is_active=True,
            activated_at=now,
            activated_by=performed_by,
        )
        self.db.add(record)
        await self.db.flush()
        await self.db.refresh(record)
        return record

    async def deactivate(
        self,
        tenant_id: str,
        slug: str,
        performed_by: str | None = None,
    ) -> TenantModuleActivation | None:
        existing = await self.get(tenant_id, slug)
        if not existing:
            return None
        existing.is_active = False
        existing.deactivated_at = datetime.now(timezone.utc)
        existing.deactivated_by = performed_by
        await self.db.flush()
        await self.db.refresh(existing)
        return existing
