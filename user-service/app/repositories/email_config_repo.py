"""Email configuration repository."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EmailConfig


class EmailConfigRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_tenant(self, tenant_id: str) -> EmailConfig | None:
        result = await self.db.execute(
            select(EmailConfig).where(EmailConfig.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def upsert(self, tenant_id: str, **kwargs) -> EmailConfig:
        config = await self.get_by_tenant(tenant_id)
        if config:
            for k, v in kwargs.items():
                setattr(config, k, v)
            config.updated_at = datetime.now(timezone.utc)
        else:
            config = EmailConfig(tenant_id=tenant_id, **kwargs)
            self.db.add(config)
        await self.db.flush()
        await self.db.refresh(config)
        return config
