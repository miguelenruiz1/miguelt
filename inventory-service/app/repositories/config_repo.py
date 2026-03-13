"""Repositories for tenant-level configuration: product types, order types, custom fields."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    CustomMovementField, CustomProductField, CustomSupplierField, CustomWarehouseField,
    OrderType, ProductType, SupplierType,
)


class ProductTypeRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(self, tenant_id: str, offset: int = 0, limit: int = 100) -> tuple[list[ProductType], int]:
        base = select(ProductType).where(ProductType.tenant_id == tenant_id)
        total = (await self.db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
        result = await self.db.execute(base.order_by(ProductType.name).offset(offset).limit(limit))
        return list(result.scalars().all()), total

    async def get(self, tenant_id: str, type_id: str) -> ProductType | None:
        result = await self.db.execute(
            select(ProductType).where(
                ProductType.tenant_id == tenant_id,
                ProductType.id == type_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, tenant_id: str, data: dict) -> ProductType:
        obj = ProductType(id=str(uuid.uuid4()), tenant_id=tenant_id, **data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update(self, obj: ProductType, data: dict) -> ProductType:
        for key, val in data.items():
            if val is not None:
                setattr(obj, key, val)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete(self, obj: ProductType) -> None:
        self.db.delete(obj)
        await self.db.flush()


class OrderTypeRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(self, tenant_id: str, offset: int = 0, limit: int = 100) -> tuple[list[OrderType], int]:
        base = select(OrderType).where(OrderType.tenant_id == tenant_id)
        total = (await self.db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
        result = await self.db.execute(base.order_by(OrderType.name).offset(offset).limit(limit))
        return list(result.scalars().all()), total

    async def get(self, tenant_id: str, type_id: str) -> OrderType | None:
        result = await self.db.execute(
            select(OrderType).where(
                OrderType.tenant_id == tenant_id,
                OrderType.id == type_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, tenant_id: str, data: dict) -> OrderType:
        obj = OrderType(id=str(uuid.uuid4()), tenant_id=tenant_id, **data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update(self, obj: OrderType, data: dict) -> OrderType:
        for key, val in data.items():
            if val is not None:
                setattr(obj, key, val)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete(self, obj: OrderType) -> None:
        self.db.delete(obj)
        await self.db.flush()


class CustomFieldRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(
        self, tenant_id: str, *, product_type_id: str | None = None,
        offset: int = 0, limit: int = 100,
    ) -> tuple[list[CustomProductField], int]:
        base = select(CustomProductField).where(CustomProductField.tenant_id == tenant_id)
        if product_type_id is not None:
            base = base.where(CustomProductField.product_type_id == product_type_id)
        total = (await self.db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
        result = await self.db.execute(
            base.order_by(CustomProductField.sort_order, CustomProductField.label).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total

    async def get(self, tenant_id: str, field_id: str) -> CustomProductField | None:
        result = await self.db.execute(
            select(CustomProductField).where(
                CustomProductField.tenant_id == tenant_id,
                CustomProductField.id == field_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, tenant_id: str, data: dict) -> CustomProductField:
        obj = CustomProductField(id=str(uuid.uuid4()), tenant_id=tenant_id, **data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update(self, obj: CustomProductField, data: dict) -> CustomProductField:
        for key, val in data.items():
            if val is not None:
                setattr(obj, key, val)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete(self, obj: CustomProductField) -> None:
        self.db.delete(obj)
        await self.db.flush()


class SupplierTypeRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(self, tenant_id: str, offset: int = 0, limit: int = 100) -> tuple[list[SupplierType], int]:
        base = select(SupplierType).where(SupplierType.tenant_id == tenant_id)
        total = (await self.db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
        result = await self.db.execute(base.order_by(SupplierType.name).offset(offset).limit(limit))
        return list(result.scalars().all()), total

    async def get(self, tenant_id: str, type_id: str) -> SupplierType | None:
        result = await self.db.execute(
            select(SupplierType).where(
                SupplierType.tenant_id == tenant_id,
                SupplierType.id == type_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, tenant_id: str, data: dict) -> SupplierType:
        obj = SupplierType(id=str(uuid.uuid4()), tenant_id=tenant_id, **data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update(self, obj: SupplierType, data: dict) -> SupplierType:
        for key, val in data.items():
            if val is not None:
                setattr(obj, key, val)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete(self, obj: SupplierType) -> None:
        self.db.delete(obj)
        await self.db.flush()


class CustomSupplierFieldRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(
        self, tenant_id: str, *, supplier_type_id: str | None = None,
        offset: int = 0, limit: int = 100,
    ) -> tuple[list[CustomSupplierField], int]:
        base = select(CustomSupplierField).where(CustomSupplierField.tenant_id == tenant_id)
        if supplier_type_id is not None:
            base = base.where(CustomSupplierField.supplier_type_id == supplier_type_id)
        total = (await self.db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
        result = await self.db.execute(
            base.order_by(CustomSupplierField.sort_order, CustomSupplierField.label).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total

    async def get(self, tenant_id: str, field_id: str) -> CustomSupplierField | None:
        result = await self.db.execute(
            select(CustomSupplierField).where(
                CustomSupplierField.tenant_id == tenant_id,
                CustomSupplierField.id == field_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, tenant_id: str, data: dict) -> CustomSupplierField:
        obj = CustomSupplierField(id=str(uuid.uuid4()), tenant_id=tenant_id, **data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update(self, obj: CustomSupplierField, data: dict) -> CustomSupplierField:
        for key, val in data.items():
            if val is not None:
                setattr(obj, key, val)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete(self, obj: CustomSupplierField) -> None:
        self.db.delete(obj)
        await self.db.flush()


class CustomWarehouseFieldRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(
        self, tenant_id: str, *, warehouse_type_id: str | None = None,
        offset: int = 0, limit: int = 100,
    ) -> tuple[list[CustomWarehouseField], int]:
        base = select(CustomWarehouseField).where(CustomWarehouseField.tenant_id == tenant_id)
        if warehouse_type_id is not None:
            base = base.where(CustomWarehouseField.warehouse_type_id == warehouse_type_id)
        total = (await self.db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
        result = await self.db.execute(
            base.order_by(CustomWarehouseField.sort_order, CustomWarehouseField.label).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total

    async def get(self, tenant_id: str, field_id: str) -> CustomWarehouseField | None:
        result = await self.db.execute(
            select(CustomWarehouseField).where(
                CustomWarehouseField.tenant_id == tenant_id,
                CustomWarehouseField.id == field_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, tenant_id: str, data: dict) -> CustomWarehouseField:
        obj = CustomWarehouseField(id=str(uuid.uuid4()), tenant_id=tenant_id, **data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update(self, obj: CustomWarehouseField, data: dict) -> CustomWarehouseField:
        for key, val in data.items():
            if val is not None:
                setattr(obj, key, val)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete(self, obj: CustomWarehouseField) -> None:
        self.db.delete(obj)
        await self.db.flush()


class CustomMovementFieldRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(
        self, tenant_id: str, *, movement_type_id: str | None = None,
        offset: int = 0, limit: int = 100,
    ) -> tuple[list[CustomMovementField], int]:
        base = select(CustomMovementField).where(CustomMovementField.tenant_id == tenant_id)
        if movement_type_id is not None:
            base = base.where(CustomMovementField.movement_type_id == movement_type_id)
        total = (await self.db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
        result = await self.db.execute(
            base.order_by(CustomMovementField.sort_order, CustomMovementField.label).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total

    async def get(self, tenant_id: str, field_id: str) -> CustomMovementField | None:
        result = await self.db.execute(
            select(CustomMovementField).where(
                CustomMovementField.tenant_id == tenant_id,
                CustomMovementField.id == field_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, tenant_id: str, data: dict) -> CustomMovementField:
        obj = CustomMovementField(id=str(uuid.uuid4()), tenant_id=tenant_id, **data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update(self, obj: CustomMovementField, data: dict) -> CustomMovementField:
        for key, val in data.items():
            if val is not None:
                setattr(obj, key, val)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete(self, obj: CustomMovementField) -> None:
        self.db.delete(obj)
        await self.db.flush()
