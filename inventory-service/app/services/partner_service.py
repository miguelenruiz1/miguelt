"""Business Partner service — unified supplier + customer logic."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, ValidationError
from app.db.models.partner import BusinessPartner
from app.repositories.partner_repo import PartnerRepository


class PartnerService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = PartnerRepository(db)

    async def list(
        self,
        tenant_id: str,
        is_supplier: bool | None = None,
        is_customer: bool | None = None,
        is_active: bool | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[BusinessPartner], int]:
        return await self.repo.list(
            tenant_id, is_supplier=is_supplier, is_customer=is_customer,
            is_active=is_active, search=search, offset=offset, limit=limit,
        )

    async def get(self, partner_id: str, tenant_id: str) -> BusinessPartner:
        p = await self.repo.get_by_id(partner_id, tenant_id)
        if not p:
            raise NotFoundError(f"Partner {partner_id!r} not found")
        return p

    async def create(self, tenant_id: str, data: dict) -> BusinessPartner:
        if not data.get("is_supplier") and not data.get("is_customer"):
            raise ValidationError("Partner must be at least supplier or customer")
        existing = await self.repo.get_by_code(data["code"], tenant_id)
        if existing:
            raise ValidationError(f"Code {data['code']!r} already in use")
        data["tenant_id"] = tenant_id
        return await self.repo.create(data)

    async def update(self, partner_id: str, tenant_id: str, data: dict) -> BusinessPartner:
        partner = await self.get(partner_id, tenant_id)
        if "code" in data and data["code"] != partner.code:
            existing = await self.repo.get_by_code(data["code"], tenant_id)
            if existing:
                raise ValidationError(f"Code {data['code']!r} already in use")
        return await self.repo.update(partner, data)

    async def delete(self, partner_id: str, tenant_id: str) -> None:
        partner = await self.get(partner_id, tenant_id)
        # Soft delete — set is_active=false
        await self.repo.update(partner, {"is_active": False})
