"""Repository for ComplianceCertificate CRUD."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.certificate import ComplianceCertificate


class CertificateRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(
        self,
        tenant_id: uuid.UUID,
        framework_slug: str | None = None,
        status: str | None = None,
        year: int | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[ComplianceCertificate], int]:
        q = select(ComplianceCertificate).where(ComplianceCertificate.tenant_id == tenant_id)
        if framework_slug is not None:
            q = q.where(ComplianceCertificate.framework_slug == framework_slug)
        if status is not None:
            q = q.where(ComplianceCertificate.status == status)
        if year is not None:
            q = q.where(func.extract("year", ComplianceCertificate.valid_from) == year)

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        q = q.order_by(ComplianceCertificate.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def get_by_id(self, certificate_id: uuid.UUID) -> ComplianceCertificate | None:
        result = await self.db.execute(
            select(ComplianceCertificate).where(ComplianceCertificate.id == certificate_id)
        )
        return result.scalar_one_or_none()

    async def get_by_record(
        self,
        record_id: uuid.UUID,
        status: str | None = None,
    ) -> ComplianceCertificate | None:
        q = select(ComplianceCertificate).where(ComplianceCertificate.record_id == record_id)
        if status is not None:
            q = q.where(ComplianceCertificate.status == status)
        else:
            q = q.where(ComplianceCertificate.status == "active")
        q = q.order_by(ComplianceCertificate.created_at.desc())
        result = await self.db.execute(q)
        return result.scalar_one_or_none()

    async def get_by_number(self, certificate_number: str) -> ComplianceCertificate | None:
        result = await self.db.execute(
            select(ComplianceCertificate).where(
                ComplianceCertificate.certificate_number == certificate_number
            )
        )
        return result.scalar_one_or_none()

    async def get_next_number(self, year: int) -> str:
        count_q = select(func.count()).select_from(
            select(ComplianceCertificate)
            .where(
                ComplianceCertificate.certificate_number.like(f"TL-{year}-%")
            )
            .subquery()
        )
        count = (await self.db.execute(count_q)).scalar_one()
        seq = count + 1
        return f"TL-{year}-{seq:06d}"

    async def create(self, tenant_id: uuid.UUID, **kwargs) -> ComplianceCertificate:
        cert = ComplianceCertificate(id=uuid.uuid4(), tenant_id=tenant_id, **kwargs)
        self.db.add(cert)
        await self.db.flush()
        await self.db.refresh(cert)
        return cert

    async def update(self, cert: ComplianceCertificate, **kwargs) -> ComplianceCertificate:
        for k, v in kwargs.items():
            if v is not None:
                setattr(cert, k, v)
        cert.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(cert)
        return cert

    async def supersede_existing(self, record_id: uuid.UUID) -> None:
        stmt = (
            update(ComplianceCertificate)
            .where(
                ComplianceCertificate.record_id == record_id,
                ComplianceCertificate.status == "active",
            )
            .values(
                status="superseded",
                updated_at=datetime.now(timezone.utc),
            )
        )
        await self.db.execute(stmt)
        await self.db.flush()
