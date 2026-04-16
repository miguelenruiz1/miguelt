"""Repository for LicenseKey operations."""
from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import LicenseKey, LicenseStatus


def _generate_key() -> str:
    """Generate TRACE-XXXXXXXX-XXXXXXXX-XXXXXXXX-XXXXXXXX license key.

    32 hex chars = 128 bits of entropy — industry-standard minimum for secrets
    that grant recurring access. The older 64-bit format (token_hex(2) × 4)
    was auditor-flagged as brute-force feasible at scale.
    """
    def segment() -> str:
        return secrets.token_hex(4).upper()
    return f"TRACE-{segment()}-{segment()}-{segment()}-{segment()}"


class LicenseRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, data: dict) -> LicenseKey:
        if "key" not in data or not data["key"]:
            data["key"] = _generate_key()
        lic = LicenseKey(id=str(uuid.uuid4()), **data)
        self.db.add(lic)
        await self.db.flush()
        await self.db.refresh(lic)
        return lic

    async def get_by_id(
        self, lic_id: str, tenant_id: str | None = None
    ) -> LicenseKey | None:
        """Optional tenant filter — defense in depth.
        Service layer also enforces it (license_service.get/revoke)."""
        q = select(LicenseKey).where(LicenseKey.id == lic_id)
        if tenant_id is not None:
            q = q.where(LicenseKey.tenant_id == tenant_id)
        result = await self.db.execute(q)
        return result.scalar_one_or_none()

    async def get_by_key(self, key: str) -> LicenseKey | None:
        result = await self.db.execute(
            select(LicenseKey).where(LicenseKey.key == key)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        tenant_id: str | None = None,
        status: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[LicenseKey]:
        q = select(LicenseKey)
        if tenant_id:
            q = q.where(LicenseKey.tenant_id.ilike(f"%{tenant_id}%"))
        if status:
            q = q.where(LicenseKey.status == status)
        q = q.order_by(LicenseKey.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def revoke(self, lic: LicenseKey, revoked_by: str | None = None) -> LicenseKey:
        lic.status = LicenseStatus.revoked
        lic.revoked_at = datetime.now(timezone.utc)
        lic.revoked_by = revoked_by
        lic.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return lic
