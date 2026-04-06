"""Repository for VariantAttribute, VariantAttributeOption, ProductVariant."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import VariantAttribute, VariantAttributeOption, ProductVariant


class VariantAttributeRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(self, tenant_id: str) -> list[VariantAttribute]:
        q = (
            select(VariantAttribute)
            .options(selectinload(VariantAttribute.options))
            .where(VariantAttribute.tenant_id == tenant_id)
            .order_by(VariantAttribute.sort_order, VariantAttribute.name)
        )
        return list((await self.db.execute(q)).scalars().unique().all())

    async def get_by_id(self, attr_id: str, tenant_id: str) -> VariantAttribute | None:
        return (await self.db.execute(
            select(VariantAttribute)
            .options(selectinload(VariantAttribute.options))
            .where(VariantAttribute.id == attr_id, VariantAttribute.tenant_id == tenant_id)
        )).scalar_one_or_none()

    async def _reload(self, attr_id: str, tenant_id: str) -> VariantAttribute:
        return (await self.db.execute(
            select(VariantAttribute)
            .options(selectinload(VariantAttribute.options))
            .where(VariantAttribute.id == attr_id, VariantAttribute.tenant_id == tenant_id)
        )).scalar_one()

    async def create(self, data: dict) -> VariantAttribute:
        obj = VariantAttribute(id=str(uuid.uuid4()), **data)
        self.db.add(obj)
        await self.db.flush()
        return await self._reload(obj.id, obj.tenant_id)

    async def update(self, obj: VariantAttribute, data: dict) -> VariantAttribute:
        for k, v in data.items():
            setattr(obj, k, v)
        await self.db.flush()
        return await self._reload(obj.id, obj.tenant_id)

    async def delete(self, obj: VariantAttribute) -> None:
        await self.db.delete(obj)
        await self.db.flush()


class VariantAttributeOptionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, data: dict) -> VariantAttributeOption:
        obj = VariantAttributeOption(id=str(uuid.uuid4()), **data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update(self, obj: VariantAttributeOption, data: dict) -> VariantAttributeOption:
        for k, v in data.items():
            setattr(obj, k, v)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete(self, obj: VariantAttributeOption) -> None:
        await self.db.delete(obj)
        await self.db.flush()

    async def get_by_id(self, opt_id: str, tenant_id: str) -> VariantAttributeOption | None:
        """tenant_id is REQUIRED — no silent default to prevent cross-tenant reads."""
        q = (
            select(VariantAttributeOption)
            .where(VariantAttributeOption.id == opt_id)
            .join(VariantAttribute, VariantAttributeOption.attribute_id == VariantAttribute.id)
            .where(VariantAttribute.tenant_id == tenant_id)
        )
        return (await self.db.execute(q)).scalar_one_or_none()


class ProductVariantRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_by_parent(self, parent_id: str, tenant_id: str) -> list[ProductVariant]:
        q = (
            select(ProductVariant)
            .where(ProductVariant.parent_id == parent_id, ProductVariant.tenant_id == tenant_id)
            .order_by(ProductVariant.sku)
        )
        return list((await self.db.execute(q)).scalars().all())

    async def list(
        self, tenant_id: str, parent_id: str | None = None, search: str | None = None,
        offset: int = 0, limit: int = 50,
    ) -> tuple[list[ProductVariant], int]:
        q = select(ProductVariant).where(ProductVariant.tenant_id == tenant_id)
        if parent_id:
            q = q.where(ProductVariant.parent_id == parent_id)
        if search:
            pat = f"%{search}%"
            q = q.where(ProductVariant.name.ilike(pat) | ProductVariant.sku.ilike(pat))
        total = (await self.db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
        q = q.order_by(ProductVariant.sku).offset(offset).limit(limit)
        return list((await self.db.execute(q)).scalars().all()), total

    async def get_by_id(self, vid: str, tenant_id: str) -> ProductVariant | None:
        return (await self.db.execute(
            select(ProductVariant).where(ProductVariant.id == vid, ProductVariant.tenant_id == tenant_id)
        )).scalar_one_or_none()

    async def create(self, data: dict) -> ProductVariant:
        obj = ProductVariant(id=str(uuid.uuid4()), **data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update(self, obj: ProductVariant, data: dict) -> ProductVariant:
        for k, v in data.items():
            setattr(obj, k, v)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete(self, obj: ProductVariant) -> None:
        await self.db.delete(obj)
        await self.db.flush()
