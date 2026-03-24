"""Repository for ComplianceRecord CRUD."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.record import ComplianceRecord


class RecordRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(
        self,
        tenant_id: uuid.UUID,
        framework_slug: str | None = None,
        asset_id: uuid.UUID | None = None,
        status: str | None = None,
        commodity_type: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[ComplianceRecord], int]:
        q = select(ComplianceRecord).where(ComplianceRecord.tenant_id == tenant_id)
        if framework_slug is not None:
            q = q.where(ComplianceRecord.framework_slug == framework_slug)
        if asset_id is not None:
            q = q.where(ComplianceRecord.asset_id == asset_id)
        if status is not None:
            q = q.where(ComplianceRecord.compliance_status == status)
        if commodity_type is not None:
            q = q.where(ComplianceRecord.commodity_type == commodity_type)

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        q = q.order_by(ComplianceRecord.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def get_by_id(self, record_id: uuid.UUID) -> ComplianceRecord | None:
        result = await self.db.execute(
            select(ComplianceRecord).where(ComplianceRecord.id == record_id)
        )
        return result.scalar_one_or_none()

    async def get_by_asset_framework(
        self,
        tenant_id: uuid.UUID,
        asset_id: uuid.UUID,
        framework_id: uuid.UUID,
    ) -> ComplianceRecord | None:
        result = await self.db.execute(
            select(ComplianceRecord).where(
                ComplianceRecord.tenant_id == tenant_id,
                ComplianceRecord.asset_id == asset_id,
                ComplianceRecord.framework_id == framework_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_asset(
        self, tenant_id: uuid.UUID, asset_id: uuid.UUID
    ) -> list[ComplianceRecord]:
        result = await self.db.execute(
            select(ComplianceRecord)
            .where(
                ComplianceRecord.tenant_id == tenant_id,
                ComplianceRecord.asset_id == asset_id,
            )
            .order_by(ComplianceRecord.created_at.desc())
        )
        return list(result.scalars().all())

    async def create(self, tenant_id: uuid.UUID, **kwargs) -> ComplianceRecord:
        record = ComplianceRecord(id=uuid.uuid4(), tenant_id=tenant_id, **kwargs)
        self.db.add(record)
        await self.db.flush()
        await self.db.refresh(record)
        return record

    async def update(self, record: ComplianceRecord, **kwargs) -> ComplianceRecord:
        for k, v in kwargs.items():
            if v is not None:
                setattr(record, k, v)
        record.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(record)
        return record

    async def delete(self, record: ComplianceRecord) -> None:
        await self.db.delete(record)
        await self.db.flush()
