"""Repositories for WM foundations: storage types & sections."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.wm import StorageSection, StorageType


class StorageTypeRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(
        self, tenant_id: str, warehouse_id: str | None = None, is_active: bool | None = None,
    ) -> list[StorageType]:
        q = select(StorageType).where(StorageType.tenant_id == tenant_id)
        if warehouse_id:
            q = q.where(StorageType.warehouse_id == warehouse_id)
        if is_active is not None:
            q = q.where(StorageType.is_active == is_active)
        q = q.order_by(StorageType.code)
        return list((await self.db.execute(q)).scalars().all())

    async def get(self, tenant_id: str, type_id: str) -> StorageType | None:
        return (await self.db.execute(
            select(StorageType).where(
                StorageType.tenant_id == tenant_id, StorageType.id == type_id,
            )
        )).scalar_one_or_none()

    async def get_by_code(self, tenant_id: str, warehouse_id: str, code: str) -> StorageType | None:
        return (await self.db.execute(
            select(StorageType).where(
                StorageType.tenant_id == tenant_id,
                StorageType.warehouse_id == warehouse_id,
                StorageType.code == code,
            )
        )).scalar_one_or_none()

    async def create(self, tenant_id: str, data: dict) -> StorageType:
        obj = StorageType(id=str(uuid.uuid4()), tenant_id=tenant_id, **data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update(self, obj: StorageType, data: dict) -> StorageType:
        for key, val in data.items():
            setattr(obj, key, val)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete(self, obj: StorageType) -> None:
        await self.db.delete(obj)
        await self.db.flush()


class StorageSectionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(self, tenant_id: str, storage_type_id: str | None = None) -> list[StorageSection]:
        q = select(StorageSection).where(StorageSection.tenant_id == tenant_id)
        if storage_type_id:
            q = q.where(StorageSection.storage_type_id == storage_type_id)
        q = q.order_by(StorageSection.sort_order, StorageSection.code)
        return list((await self.db.execute(q)).scalars().all())

    async def get(self, tenant_id: str, section_id: str) -> StorageSection | None:
        return (await self.db.execute(
            select(StorageSection).where(
                StorageSection.tenant_id == tenant_id, StorageSection.id == section_id,
            )
        )).scalar_one_or_none()

    async def get_by_code(self, tenant_id: str, storage_type_id: str, code: str) -> StorageSection | None:
        return (await self.db.execute(
            select(StorageSection).where(
                StorageSection.tenant_id == tenant_id,
                StorageSection.storage_type_id == storage_type_id,
                StorageSection.code == code,
            )
        )).scalar_one_or_none()

    async def create(self, tenant_id: str, data: dict) -> StorageSection:
        obj = StorageSection(id=str(uuid.uuid4()), tenant_id=tenant_id, **data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update(self, obj: StorageSection, data: dict) -> StorageSection:
        for key, val in data.items():
            setattr(obj, key, val)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete(self, obj: StorageSection) -> None:
        await self.db.delete(obj)
        await self.db.flush()
