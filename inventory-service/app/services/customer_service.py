"""Business logic for customers and customer types."""
from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.repositories.customer_repo import CustomerRepository, CustomerTypeRepository


class CustomerService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = CustomerRepository(db)
        self.type_repo = CustomerTypeRepository(db)

    # ── Customer Types ──────────────────────────────────────────────
    async def list_types(self, tenant_id: str, offset: int = 0, limit: int = 100):
        return await self.type_repo.list(tenant_id, offset=offset, limit=limit)

    async def create_type(self, tenant_id: str, data: dict):
        data["tenant_id"] = tenant_id
        try:
            async with self.db.begin_nested():
                return await self.type_repo.create(data)
        except IntegrityError:
            slug_or_name = data.get("slug") or data.get("name") or ""
            raise ConflictError(f"Ya existe un tipo de cliente '{slug_or_name}'")

    async def update_type(self, type_id: str, tenant_id: str, data: dict):
        obj = await self.type_repo.get_by_id(type_id, tenant_id)
        if not obj:
            raise NotFoundError("Customer type not found")
        return await self.type_repo.update(obj, data)

    async def delete_type(self, type_id: str, tenant_id: str):
        obj = await self.type_repo.get_by_id(type_id, tenant_id)
        if not obj:
            raise NotFoundError("Customer type not found")
        await self.type_repo.delete(obj)

    # ── Customers ───────────────────────────────────────────────────
    async def list_customers(self, tenant_id: str, **kwargs):
        return await self.repo.list(tenant_id, **kwargs)

    async def get_customer(self, cid: str, tenant_id: str):
        c = await self.repo.get_by_id(cid, tenant_id)
        if not c:
            raise NotFoundError("Customer not found")
        return c

    async def create_customer(self, tenant_id: str, data: dict):
        existing = await self.repo.get_by_code(data["code"], tenant_id)
        if existing:
            raise ConflictError(f"Ya existe un cliente con código '{data['code']}'")
        data["tenant_id"] = tenant_id
        try:
            async with self.db.begin_nested():
                return await self.repo.create(data)
        except IntegrityError:
            raise ConflictError(f"Ya existe un cliente con código '{data['code']}'")

    async def update_customer(self, cid: str, tenant_id: str, data: dict):
        obj = await self.repo.get_by_id(cid, tenant_id)
        if not obj:
            raise NotFoundError("Customer not found")
        return await self.repo.update(obj, data)

    async def delete_customer(self, cid: str, tenant_id: str):
        obj = await self.repo.get_by_id(cid, tenant_id)
        if not obj:
            raise NotFoundError("Customer not found")
        await self.repo.delete(obj)

