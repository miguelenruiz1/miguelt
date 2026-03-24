"""Repository for TenantFrameworkActivation CRUD."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activation import TenantFrameworkActivation
from app.models.framework import ComplianceFramework


class ActivationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_for_tenant(
        self, tenant_id: uuid.UUID
    ) -> list[TenantFrameworkActivation]:
        result = await self.db.execute(
            select(TenantFrameworkActivation)
            .where(TenantFrameworkActivation.tenant_id == tenant_id)
            .order_by(TenantFrameworkActivation.activated_at.desc())
        )
        return list(result.scalars().all())

    async def get(
        self, tenant_id: uuid.UUID, framework_id: uuid.UUID
    ) -> TenantFrameworkActivation | None:
        result = await self.db.execute(
            select(TenantFrameworkActivation).where(
                TenantFrameworkActivation.tenant_id == tenant_id,
                TenantFrameworkActivation.framework_id == framework_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_slug(
        self, tenant_id: uuid.UUID, framework_slug: str
    ) -> TenantFrameworkActivation | None:
        result = await self.db.execute(
            select(TenantFrameworkActivation)
            .join(
                ComplianceFramework,
                ComplianceFramework.id == TenantFrameworkActivation.framework_id,
            )
            .where(
                TenantFrameworkActivation.tenant_id == tenant_id,
                ComplianceFramework.slug == framework_slug,
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self, tenant_id: uuid.UUID, **kwargs
    ) -> TenantFrameworkActivation:
        activation = TenantFrameworkActivation(
            id=uuid.uuid4(), tenant_id=tenant_id, **kwargs
        )
        self.db.add(activation)
        await self.db.flush()
        await self.db.refresh(activation)
        return activation

    async def update(
        self, activation: TenantFrameworkActivation, **kwargs
    ) -> TenantFrameworkActivation:
        for k, v in kwargs.items():
            if v is not None:
                setattr(activation, k, v)
        await self.db.flush()
        await self.db.refresh(activation)
        return activation

    async def delete(self, activation: TenantFrameworkActivation) -> None:
        await self.db.delete(activation)
        await self.db.flush()
