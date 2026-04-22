"""Repository for PaymentGatewayConfig CRUD operations."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PaymentGatewayConfig


class PaymentGatewayRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_for_tenant(self, tenant_id: str) -> list[PaymentGatewayConfig]:
        result = await self.db.execute(
            select(PaymentGatewayConfig)
            .where(PaymentGatewayConfig.tenant_id == tenant_id)
            .order_by(PaymentGatewayConfig.gateway_slug)
        )
        return list(result.scalars().all())

    async def get(self, tenant_id: str, slug: str) -> PaymentGatewayConfig | None:
        result = await self.db.execute(
            select(PaymentGatewayConfig)
            .where(
                PaymentGatewayConfig.tenant_id == tenant_id,
                PaymentGatewayConfig.gateway_slug == slug,
            )
        )
        return result.scalar_one_or_none()

    async def upsert(
        self,
        tenant_id: str,
        slug: str,
        display_name: str,
        credentials: dict,
    ) -> PaymentGatewayConfig:
        existing = await self.get(tenant_id, slug)
        now = datetime.now(timezone.utc)
        if existing:
            existing.credentials = credentials
            existing.display_name = display_name
            existing.updated_at = now
            await self.db.flush()
            await self.db.refresh(existing)
            return existing
        config = PaymentGatewayConfig(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            gateway_slug=slug,
            display_name=display_name,
            credentials=credentials,
            is_active=False,
        )
        self.db.add(config)
        await self.db.flush()
        await self.db.refresh(config)
        return config

    async def set_active(self, tenant_id: str, slug: str) -> PaymentGatewayConfig:
        """Set the given gateway as active and deactivate all others for the tenant."""
        now = datetime.now(timezone.utc)
        # Deactivate all
        await self.db.execute(
            update(PaymentGatewayConfig)
            .where(PaymentGatewayConfig.tenant_id == tenant_id)
            .values(is_active=False, updated_at=now)
        )
        # Activate target
        result = await self.db.execute(
            select(PaymentGatewayConfig)
            .where(
                PaymentGatewayConfig.tenant_id == tenant_id,
                PaymentGatewayConfig.gateway_slug == slug,
            )
        )
        config = result.scalar_one_or_none()
        if config is None:
            raise ValueError(f"Gateway '{slug}' not configured for tenant '{tenant_id}'")
        config.is_active = True
        config.updated_at = now
        await self.db.flush()
        await self.db.refresh(config)
        return config

    async def delete(self, tenant_id: str, slug: str) -> bool:
        config = await self.get(tenant_id, slug)
        if config is None:
            return False
        await self.db.delete(config)
        await self.db.flush()
        return True
