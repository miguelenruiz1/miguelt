"""Business logic for license key management."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.db.models import LicenseKey, LicenseStatus
from app.repositories.license_repo import LicenseRepository


class LicenseService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = LicenseRepository(db)

    async def issue(self, data: dict) -> LicenseKey:
        return await self.repo.create(data)

    async def revoke(self, lic_id: str, revoked_by: str | None = None) -> LicenseKey:
        lic = await self.repo.get_by_id(lic_id)
        if not lic:
            raise NotFoundError(f"License {lic_id!r} not found")
        if lic.status == LicenseStatus.revoked:
            raise ValidationError("License is already revoked")
        return await self.repo.revoke(lic, revoked_by=revoked_by)

    async def list(
        self,
        tenant_id: str | None = None,
        status: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[LicenseKey]:
        return await self.repo.list(
            tenant_id=tenant_id,
            status=status,
            offset=offset,
            limit=limit,
        )

    async def get(self, lic_id: str) -> LicenseKey:
        lic = await self.repo.get_by_id(lic_id)
        if not lic:
            raise NotFoundError(f"License {lic_id!r} not found")
        return lic

    async def validate(self, key: str) -> dict:
        """Public validation endpoint — no auth required."""
        lic = await self.repo.get_by_key(key)
        if not lic:
            return {"valid": False, "reason": "not_found"}
        if lic.status == LicenseStatus.revoked:
            return {"valid": False, "reason": "revoked"}
        if lic.status == LicenseStatus.expired:
            return {"valid": False, "reason": "expired"}
        now = datetime.now(timezone.utc)
        if lic.expires_at and lic.expires_at < now:
            return {"valid": False, "reason": "expired"}
        if lic.max_activations != -1 and lic.activations_count >= lic.max_activations:
            return {"valid": False, "reason": "max_activations_reached"}
        return {
            "valid": True,
            "tenant_id": lic.tenant_id,
            "features": lic.features,
            "expires_at": lic.expires_at.isoformat() if lic.expires_at else None,
        }
