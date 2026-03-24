"""Business Partner repository."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.partner import BusinessPartner


class PartnerRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

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
        q = select(BusinessPartner).where(BusinessPartner.tenant_id == tenant_id)
        cq = select(func.count()).select_from(BusinessPartner).where(BusinessPartner.tenant_id == tenant_id)

        if is_supplier is not None:
            q = q.where(BusinessPartner.is_supplier == is_supplier)
            cq = cq.where(BusinessPartner.is_supplier == is_supplier)
        if is_customer is not None:
            q = q.where(BusinessPartner.is_customer == is_customer)
            cq = cq.where(BusinessPartner.is_customer == is_customer)
        if is_active is not None:
            q = q.where(BusinessPartner.is_active == is_active)
            cq = cq.where(BusinessPartner.is_active == is_active)
        if search:
            like = f"%{search}%"
            filt = or_(
                BusinessPartner.name.ilike(like),
                BusinessPartner.code.ilike(like),
                BusinessPartner.email.ilike(like),
                BusinessPartner.contact_name.ilike(like),
            )
            q = q.where(filt)
            cq = cq.where(filt)

        total = (await self.db.execute(cq)).scalar_one()
        q = q.order_by(BusinessPartner.name).offset(offset).limit(limit)
        items = (await self.db.execute(q)).scalars().all()
        return list(items), total

    async def get_by_id(self, partner_id: str, tenant_id: str) -> BusinessPartner | None:
        result = await self.db.execute(
            select(BusinessPartner).where(
                BusinessPartner.id == partner_id,
                BusinessPartner.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str, tenant_id: str) -> BusinessPartner | None:
        result = await self.db.execute(
            select(BusinessPartner).where(
                BusinessPartner.code == code,
                BusinessPartner.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, data: dict) -> BusinessPartner:
        partner = BusinessPartner(id=str(uuid.uuid4()), **data)
        self.db.add(partner)
        await self.db.flush()
        await self.db.refresh(partner)
        return partner

    async def update(self, partner: BusinessPartner, data: dict) -> BusinessPartner:
        for k, v in data.items():
            setattr(partner, k, v)
        await self.db.flush()
        await self.db.refresh(partner)
        return partner

    async def delete(self, partner: BusinessPartner) -> None:
        await self.db.delete(partner)
        await self.db.flush()
