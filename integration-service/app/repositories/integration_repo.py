"""Repository for IntegrationConfig, SyncJob, SyncLog, WebhookLog."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import IntegrationConfig, SyncJob, SyncLog, WebhookLog


class IntegrationConfigRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_for_tenant(self, tenant_id: str) -> list[IntegrationConfig]:
        q = select(IntegrationConfig).where(IntegrationConfig.tenant_id == tenant_id).order_by(IntegrationConfig.provider_slug)
        return list((await self.db.execute(q)).scalars().all())

    async def get(self, config_id: str, tenant_id: str) -> IntegrationConfig | None:
        return (await self.db.execute(
            select(IntegrationConfig).where(
                IntegrationConfig.id == config_id,
                IntegrationConfig.tenant_id == tenant_id,
            )
        )).scalar_one_or_none()

    async def get_by_provider(self, tenant_id: str, provider_slug: str) -> IntegrationConfig | None:
        return (await self.db.execute(
            select(IntegrationConfig).where(
                IntegrationConfig.tenant_id == tenant_id,
                IntegrationConfig.provider_slug == provider_slug,
            )
        )).scalar_one_or_none()

    async def upsert(self, data: dict) -> IntegrationConfig:
        existing = await self.get_by_provider(data["tenant_id"], data["provider_slug"])
        if existing:
            for k, v in data.items():
                if k not in ("id", "tenant_id", "provider_slug"):
                    setattr(existing, k, v)
            await self.db.flush()
            await self.db.refresh(existing)
            return existing
        config = IntegrationConfig(id=str(uuid.uuid4()), **data)
        self.db.add(config)
        await self.db.flush()
        await self.db.refresh(config)
        return config

    async def delete(self, config: IntegrationConfig) -> None:
        self.db.delete(config)
        await self.db.flush()


class SyncJobRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(
        self, tenant_id: str, provider_slug: str | None = None,
        status: str | None = None, offset: int = 0, limit: int = 50,
    ) -> tuple[list[SyncJob], int]:
        q = select(SyncJob).where(SyncJob.tenant_id == tenant_id)
        if provider_slug:
            q = q.where(SyncJob.provider_slug == provider_slug)
        if status:
            q = q.where(SyncJob.status == status)
        total = (await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
        q = q.order_by(SyncJob.created_at.desc()).offset(offset).limit(limit)
        return list((await self.db.execute(q)).scalars().all()), total

    async def get(self, job_id: str) -> SyncJob | None:
        return (await self.db.execute(select(SyncJob).where(SyncJob.id == job_id))).scalar_one_or_none()

    async def create(self, data: dict) -> SyncJob:
        job = SyncJob(id=str(uuid.uuid4()), **data)
        self.db.add(job)
        await self.db.flush()
        await self.db.refresh(job)
        return job

    async def update(self, job: SyncJob, data: dict) -> SyncJob:
        for k, v in data.items():
            setattr(job, k, v)
        await self.db.flush()
        await self.db.refresh(job)
        return job


class SyncLogRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_by_job(self, job_id: str, offset: int = 0, limit: int = 100) -> list[SyncLog]:
        q = (
            select(SyncLog).where(SyncLog.sync_job_id == job_id)
            .order_by(SyncLog.created_at).offset(offset).limit(limit)
        )
        return list((await self.db.execute(q)).scalars().all())

    async def create(self, data: dict) -> SyncLog:
        log = SyncLog(id=str(uuid.uuid4()), **data)
        self.db.add(log)
        await self.db.flush()
        return log


class WebhookLogRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(
        self, tenant_id: str | None = None, provider_slug: str | None = None,
        offset: int = 0, limit: int = 50,
    ) -> tuple[list[WebhookLog], int]:
        q = select(WebhookLog)
        if tenant_id:
            q = q.where(WebhookLog.tenant_id == tenant_id)
        if provider_slug:
            q = q.where(WebhookLog.provider_slug == provider_slug)
        total = (await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
        q = q.order_by(WebhookLog.created_at.desc()).offset(offset).limit(limit)
        return list((await self.db.execute(q)).scalars().all()), total

    async def create(self, data: dict) -> WebhookLog:
        log = WebhookLog(id=str(uuid.uuid4()), **data)
        self.db.add(log)
        await self.db.flush()
        return log

    async def update(self, log: WebhookLog, data: dict) -> WebhookLog:
        for k, v in data.items():
            setattr(log, k, v)
        await self.db.flush()
        return log
