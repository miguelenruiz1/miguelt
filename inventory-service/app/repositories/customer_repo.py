"""Repository for Customer + CustomerType CRUD."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Customer, CustomerType


class CustomerTypeRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(self, tenant_id: str, offset: int = 0, limit: int = 100) -> tuple[list[CustomerType], int]:
        base = select(CustomerType).where(CustomerType.tenant_id == tenant_id)
        total = (await self.db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
        q = base.order_by(CustomerType.name).offset(offset).limit(limit)
        return list((await self.db.execute(q)).scalars().all()), total

    async def get_by_id(self, type_id: str, tenant_id: str) -> CustomerType | None:
        return (await self.db.execute(
            select(CustomerType).where(CustomerType.id == type_id, CustomerType.tenant_id == tenant_id)
        )).scalar_one_or_none()

    async def create(self, data: dict) -> CustomerType:
        obj = CustomerType(id=str(uuid.uuid4()), **data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update(self, obj: CustomerType, data: dict) -> CustomerType:
        for k, v in data.items():
            setattr(obj, k, v)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete(self, obj: CustomerType) -> None:
        self.db.delete(obj)
        await self.db.flush()


class CustomerRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(
        self,
        tenant_id: str,
        customer_type_id: str | None = None,
        is_active: bool | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[Customer], int]:
        q = select(Customer).where(Customer.tenant_id == tenant_id)
        if customer_type_id:
            q = q.where(Customer.customer_type_id == customer_type_id)
        if is_active is not None:
            q = q.where(Customer.is_active == is_active)
        if search:
            pat = f"%{search}%"
            q = q.where(Customer.name.ilike(pat) | Customer.code.ilike(pat) | Customer.email.ilike(pat))
        total = (await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
        q = q.order_by(Customer.name).offset(offset).limit(limit)
        return list((await self.db.execute(q)).scalars().all()), total

    async def get_by_id(self, cid: str, tenant_id: str) -> Customer | None:
        return (await self.db.execute(
            select(Customer)
            .where(Customer.id == cid, Customer.tenant_id == tenant_id)
        )).scalar_one_or_none()

    async def get_by_code(self, code: str, tenant_id: str) -> Customer | None:
        return (await self.db.execute(
            select(Customer).where(Customer.code == code, Customer.tenant_id == tenant_id)
        )).scalar_one_or_none()

    async def create(self, data: dict) -> Customer:
        obj = Customer(id=str(uuid.uuid4()), **data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update(self, obj: Customer, data: dict) -> Customer:
        for k, v in data.items():
            setattr(obj, k, v)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete(self, obj: Customer) -> None:
        self.db.delete(obj)
        await self.db.flush()

    async def count(self, tenant_id: str) -> int:
        return (await self.db.execute(
            select(func.count()).where(Customer.tenant_id == tenant_id)
        )).scalar_one()
