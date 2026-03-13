"""Repository for Supplier CRUD."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Supplier


class SupplierRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(
        self,
        tenant_id: str,
        is_active: bool | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[Supplier], int]:
        q = select(Supplier).where(Supplier.tenant_id == tenant_id)
        if is_active is not None:
            q = q.where(Supplier.is_active == is_active)
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar_one()
        q = q.order_by(Supplier.name).offset(offset).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all()), total

    async def get_by_id(self, supplier_id: str, tenant_id: str) -> Supplier | None:
        result = await self.db.execute(
            select(Supplier).where(
                Supplier.id == supplier_id,
                Supplier.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str, tenant_id: str) -> Supplier | None:
        result = await self.db.execute(
            select(Supplier).where(
                Supplier.code == code,
                Supplier.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, data: dict) -> Supplier:
        supplier = Supplier(id=str(uuid.uuid4()), **data)
        self.db.add(supplier)
        await self.db.flush()
        await self.db.refresh(supplier)
        return supplier

    async def update(self, supplier: Supplier, data: dict) -> Supplier:
        for k, v in data.items():
            setattr(supplier, k, v)
        supplier.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(supplier)
        return supplier

    async def soft_delete(self, supplier: Supplier) -> None:
        supplier.is_active = False
        supplier.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
