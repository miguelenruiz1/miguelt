"""Business logic for serial number tracking."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.repositories.serial_repo import SerialRepository


class SerialService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = SerialRepository(db)

    async def list(
        self,
        tenant_id: str,
        entity_id: str | None = None,
        status_id: str | None = None,
        warehouse_id: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ):
        return await self.repo.list(tenant_id, entity_id, status_id, warehouse_id, offset, limit)

    async def get(self, tenant_id: str, serial_id: str):
        obj = await self.repo.get(tenant_id, serial_id)
        if not obj:
            raise NotFoundError("Serial no encontrado")
        return obj

    async def create(self, tenant_id: str, data: dict):
        # Remap 'metadata' key to avoid collision with SQLAlchemy mapped column
        if "metadata" in data:
            data["metadata_"] = data.pop("metadata")
        return await self.repo.create(tenant_id, data)

    async def update(self, tenant_id: str, serial_id: str, data: dict):
        obj = await self.repo.get(tenant_id, serial_id)
        if not obj:
            raise NotFoundError("Serial no encontrado")
        if "metadata" in data:
            data["metadata_"] = data.pop("metadata")
        return await self.repo.update(obj, {k: v for k, v in data.items() if v is not None})

    async def delete(self, tenant_id: str, serial_id: str) -> None:
        obj = await self.get(tenant_id, serial_id)
        await self.repo.delete(obj)
