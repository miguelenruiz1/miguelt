"""Service for dynamic movement types, warehouse types, locations, serial statuses,
event types, event severities, event statuses."""
from __future__ import annotations

import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.repositories.event_repo import (
    EventSeverityRepository,
    EventStatusRepository,
    EventTypeRepository,
)
from app.repositories.location_repo import LocationRepository
from app.repositories.movement_type_repo import MovementTypeRepository
from app.repositories.warehouse_type_repo import WarehouseTypeRepository

# Reuse serial status repo via config_repo pattern
from app.db.models import SerialStatus
import uuid
from sqlalchemy import select


def _slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "-", slug)
    return slug[:150]


class DynamicConfigService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.mt_repo = MovementTypeRepository(db)
        self.wt_repo = WarehouseTypeRepository(db)
        self.loc_repo = LocationRepository(db)
        self.et_repo = EventTypeRepository(db)
        self.es_repo = EventSeverityRepository(db)
        self.est_repo = EventStatusRepository(db)

    # ── Movement Types ──────────────────────────────────────────────────────

    async def list_movement_types(self, tenant_id: str, offset: int = 0, limit: int = 100):
        return await self.mt_repo.list(tenant_id, offset=offset, limit=limit)

    async def create_movement_type(self, tenant_id: str, data: dict):
        if not data.get("slug"):
            data["slug"] = _slugify(data["name"])
        existing = await self.mt_repo.get_by_slug(tenant_id, data["slug"])
        if existing:
            raise ConflictError(f"Ya existe un tipo de movimiento con slug '{data['slug']}'")
        return await self.mt_repo.create(tenant_id, data)

    async def update_movement_type(self, tenant_id: str, type_id: str, data: dict):
        obj = await self.mt_repo.get(tenant_id, type_id)
        if not obj:
            raise NotFoundError("Tipo de movimiento no encontrado")
        if obj.is_system:
            raise ValidationError("No se puede editar un tipo de movimiento del sistema")
        return await self.mt_repo.update(obj, {k: v for k, v in data.items() if v is not None})

    async def delete_movement_type(self, tenant_id: str, type_id: str) -> None:
        obj = await self.mt_repo.get(tenant_id, type_id)
        if not obj:
            raise NotFoundError("Tipo de movimiento no encontrado")
        if obj.is_system:
            raise ValidationError("No se puede eliminar un tipo de movimiento del sistema")
        await self.mt_repo.delete(obj)

    # ── Warehouse Types ─────────────────────────────────────────────────────

    async def list_warehouse_types(self, tenant_id: str, offset: int = 0, limit: int = 100):
        return await self.wt_repo.list(tenant_id, offset=offset, limit=limit)

    async def create_warehouse_type(self, tenant_id: str, data: dict):
        if not data.get("slug"):
            data["slug"] = _slugify(data["name"])
        existing = await self.wt_repo.get_by_slug(tenant_id, data["slug"]) if hasattr(self.wt_repo, "get_by_slug") else None
        if existing:
            raise ConflictError(f"Ya existe un tipo de bodega con slug '{data['slug']}'")
        from sqlalchemy.exc import IntegrityError
        try:
            async with self.db.begin_nested():
                return await self.wt_repo.create(tenant_id, data)
        except IntegrityError:
            raise ConflictError(f"Ya existe un tipo de bodega con slug '{data['slug']}'")

    async def update_warehouse_type(self, tenant_id: str, type_id: str, data: dict):
        obj = await self.wt_repo.get(tenant_id, type_id)
        if not obj:
            raise NotFoundError("Tipo de bodega no encontrado")
        if obj.is_system:
            raise ValidationError("No se puede editar un tipo de bodega del sistema")
        return await self.wt_repo.update(obj, {k: v for k, v in data.items() if v is not None})

    async def delete_warehouse_type(self, tenant_id: str, type_id: str) -> None:
        obj = await self.wt_repo.get(tenant_id, type_id)
        if not obj:
            raise NotFoundError("Tipo de bodega no encontrado")
        if obj.is_system:
            raise ValidationError("No se puede eliminar un tipo de bodega del sistema")
        await self.wt_repo.delete(obj)

    # ── Locations ───────────────────────────────────────────────────────────

    async def list_locations(self, tenant_id: str, warehouse_id: str | None = None, offset: int = 0, limit: int = 100):
        return await self.loc_repo.list(tenant_id, warehouse_id, offset=offset, limit=limit)

    async def create_location(self, tenant_id: str, data: dict):
        return await self.loc_repo.create(tenant_id, data)

    async def update_location(self, tenant_id: str, location_id: str, data: dict):
        obj = await self.loc_repo.get(tenant_id, location_id)
        if not obj:
            raise NotFoundError("Ubicación no encontrada")
        return await self.loc_repo.update(obj, {k: v for k, v in data.items() if v is not None})

    async def delete_location(self, tenant_id: str, location_id: str) -> None:
        obj = await self.loc_repo.get(tenant_id, location_id)
        if not obj:
            raise NotFoundError("Ubicación no encontrada")
        await self.loc_repo.delete(obj)

    # ── Event Types ─────────────────────────────────────────────────────────

    async def list_event_types(self, tenant_id: str, offset: int = 0, limit: int = 100):
        return await self.et_repo.list(tenant_id, offset=offset, limit=limit)

    async def create_event_type(self, tenant_id: str, data: dict):
        if not data.get("slug"):
            data["slug"] = _slugify(data["name"])
        return await self.et_repo.create(tenant_id, data)

    async def update_event_type(self, tenant_id: str, type_id: str, data: dict):
        obj = await self.et_repo.get(tenant_id, type_id)
        if not obj:
            raise NotFoundError("Tipo de evento no encontrado")
        return await self.et_repo.update(obj, {k: v for k, v in data.items() if v is not None})

    async def delete_event_type(self, tenant_id: str, type_id: str) -> None:
        obj = await self.et_repo.get(tenant_id, type_id)
        if not obj:
            raise NotFoundError("Tipo de evento no encontrado")
        await self.et_repo.delete(obj)

    # ── Event Severities ────────────────────────────────────────────────────

    async def list_event_severities(self, tenant_id: str, offset: int = 0, limit: int = 100):
        return await self.es_repo.list(tenant_id, offset=offset, limit=limit)

    async def create_event_severity(self, tenant_id: str, data: dict):
        if not data.get("slug"):
            data["slug"] = _slugify(data["name"])
        return await self.es_repo.create(tenant_id, data)

    async def update_event_severity(self, tenant_id: str, sev_id: str, data: dict):
        obj = await self.es_repo.get(tenant_id, sev_id)
        if not obj:
            raise NotFoundError("Severidad no encontrada")
        return await self.es_repo.update(obj, {k: v for k, v in data.items() if v is not None})

    async def delete_event_severity(self, tenant_id: str, sev_id: str) -> None:
        obj = await self.es_repo.get(tenant_id, sev_id)
        if not obj:
            raise NotFoundError("Severidad no encontrada")
        await self.es_repo.delete(obj)

    # ── Event Statuses ──────────────────────────────────────────────────────

    async def list_event_statuses(self, tenant_id: str, offset: int = 0, limit: int = 100):
        return await self.est_repo.list(tenant_id, offset=offset, limit=limit)

    async def create_event_status(self, tenant_id: str, data: dict):
        if not data.get("slug"):
            data["slug"] = _slugify(data["name"])
        return await self.est_repo.create(tenant_id, data)

    async def update_event_status(self, tenant_id: str, status_id: str, data: dict):
        obj = await self.est_repo.get(tenant_id, status_id)
        if not obj:
            raise NotFoundError("Estado de evento no encontrado")
        return await self.est_repo.update(obj, {k: v for k, v in data.items() if v is not None})

    async def delete_event_status(self, tenant_id: str, status_id: str) -> None:
        obj = await self.est_repo.get(tenant_id, status_id)
        if not obj:
            raise NotFoundError("Estado de evento no encontrado")
        await self.est_repo.delete(obj)

    # ── Serial Statuses ─────────────────────────────────────────────────────

    async def list_serial_statuses(self, tenant_id: str, offset: int = 0, limit: int = 100):
        from sqlalchemy import func
        base = select(SerialStatus).where(SerialStatus.tenant_id == tenant_id)
        total = (await self.db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
        result = await self.db.execute(base.order_by(SerialStatus.name).offset(offset).limit(limit))
        return list(result.scalars().all()), total

    async def create_serial_status(self, tenant_id: str, data: dict):
        if not data.get("slug"):
            data["slug"] = _slugify(data["name"])
        obj = SerialStatus(id=str(uuid.uuid4()), tenant_id=tenant_id, **data)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update_serial_status(self, tenant_id: str, status_id: str, data: dict):
        result = await self.db.execute(
            select(SerialStatus).where(SerialStatus.tenant_id == tenant_id, SerialStatus.id == status_id)
        )
        obj = result.scalar_one_or_none()
        if not obj:
            raise NotFoundError("Estado de serial no encontrado")
        for k, v in data.items():
            if v is not None:
                setattr(obj, k, v)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete_serial_status(self, tenant_id: str, status_id: str) -> None:
        result = await self.db.execute(
            select(SerialStatus).where(SerialStatus.tenant_id == tenant_id, SerialStatus.id == status_id)
        )
        obj = result.scalar_one_or_none()
        if not obj:
            raise NotFoundError("Estado de serial no encontrado")
        self.db.delete(obj)
        await self.db.flush()
