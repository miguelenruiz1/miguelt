"""Service for tenant-level inventory configuration."""
from __future__ import annotations

import re

from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.db.models import Product
from app.repositories.config_repo import (
    CustomFieldRepository,
    CustomMovementFieldRepository,
    CustomSupplierFieldRepository,
    CustomWarehouseFieldRepository,
    OrderTypeRepository,
    ProductTypeRepository,
    SupplierTypeRepository,
)


def _slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "-", slug)
    return slug[:150]


class ConfigService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.pt_repo = ProductTypeRepository(db)
        self.ot_repo = OrderTypeRepository(db)
        self.cf_repo = CustomFieldRepository(db)
        self.st_repo = SupplierTypeRepository(db)
        self.csf_repo = CustomSupplierFieldRepository(db)
        self.cwf_repo = CustomWarehouseFieldRepository(db)
        self.cmf_repo = CustomMovementFieldRepository(db)

    # ── Product Types ──────────────────────────────────────────────────────────

    async def list_product_types(self, tenant_id: str, offset: int = 0, limit: int = 100):
        return await self.pt_repo.list(tenant_id, offset=offset, limit=limit)

    async def create_product_type(self, tenant_id: str, data: dict):
        if not data.get("slug"):
            data["slug"] = _slugify(data["name"])
        try:
            async with self.db.begin_nested():
                return await self.pt_repo.create(tenant_id, data)
        except IntegrityError:
            raise ConflictError(f"Ya existe un tipo de producto con slug '{data['slug']}'")

    async def update_product_type(self, tenant_id: str, type_id: str, data: dict):
        obj = await self.pt_repo.get(tenant_id, type_id)
        if not obj:
            raise NotFoundError("Tipo de producto no encontrado")
        return await self.pt_repo.update(obj, {k: v for k, v in data.items() if v is not None})

    async def delete_product_type(self, tenant_id: str, type_id: str) -> None:
        obj = await self.pt_repo.get(tenant_id, type_id)
        if not obj:
            raise NotFoundError("Tipo de producto no encontrado")
        product_count = (await self.db.execute(
            select(func.count()).where(
                Product.tenant_id == tenant_id,
                Product.product_type_id == type_id,
                Product.is_active == True,  # noqa: E712
            )
        )).scalar_one()
        if product_count:
            raise ValidationError(
                f"No se puede eliminar: el tipo tiene {product_count} producto(s) asociado(s)"
            )
        await self.pt_repo.delete(obj)

    # ── Order Types ────────────────────────────────────────────────────────────

    async def list_order_types(self, tenant_id: str, offset: int = 0, limit: int = 100):
        return await self.ot_repo.list(tenant_id, offset=offset, limit=limit)

    async def create_order_type(self, tenant_id: str, data: dict):
        if not data.get("slug"):
            data["slug"] = _slugify(data["name"])
        try:
            async with self.db.begin_nested():
                return await self.ot_repo.create(tenant_id, data)
        except IntegrityError:
            raise ConflictError(f"Ya existe un tipo de orden con slug '{data['slug']}'")

    async def update_order_type(self, tenant_id: str, type_id: str, data: dict):
        obj = await self.ot_repo.get(tenant_id, type_id)
        if not obj:
            raise NotFoundError("Tipo de orden no encontrado")
        return await self.ot_repo.update(obj, {k: v for k, v in data.items() if v is not None})

    async def delete_order_type(self, tenant_id: str, type_id: str) -> None:
        obj = await self.ot_repo.get(tenant_id, type_id)
        if not obj:
            raise NotFoundError("Tipo de orden no encontrado")
        await self.ot_repo.delete(obj)

    # ── Custom Product Fields ──────────────────────────────────────────────────

    async def list_custom_fields(
        self, tenant_id: str, *, product_type_id: str | None = None,
        offset: int = 0, limit: int = 100,
    ):
        return await self.cf_repo.list(tenant_id, product_type_id=product_type_id, offset=offset, limit=limit)

    async def create_custom_field(self, tenant_id: str, data: dict):
        # Check for duplicate field_key within the same product_type scope
        pt_id = data.get("product_type_id")
        existing, _ = await self.cf_repo.list(tenant_id, product_type_id=pt_id)
        if any(f.field_key == data["field_key"] for f in existing):
            raise ConflictError(f"Ya existe un campo con key '{data['field_key']}'")
        return await self.cf_repo.create(tenant_id, data)

    async def update_custom_field(self, tenant_id: str, field_id: str, data: dict):
        obj = await self.cf_repo.get(tenant_id, field_id)
        if not obj:
            raise NotFoundError("Campo personalizado no encontrado")
        return await self.cf_repo.update(obj, {k: v for k, v in data.items() if v is not None})

    async def delete_custom_field(self, tenant_id: str, field_id: str) -> None:
        obj = await self.cf_repo.get(tenant_id, field_id)
        if not obj:
            raise NotFoundError("Campo personalizado no encontrado")
        await self.cf_repo.delete(obj)

    # ── Supplier Types ─────────────────────────────────────────────────────────

    async def list_supplier_types(self, tenant_id: str, offset: int = 0, limit: int = 100):
        return await self.st_repo.list(tenant_id, offset=offset, limit=limit)

    async def create_supplier_type(self, tenant_id: str, data: dict):
        if not data.get("slug"):
            data["slug"] = _slugify(data["name"])
        try:
            async with self.db.begin_nested():
                return await self.st_repo.create(tenant_id, data)
        except IntegrityError:
            raise ConflictError(f"Ya existe un tipo de proveedor con slug '{data['slug']}'")

    async def update_supplier_type(self, tenant_id: str, type_id: str, data: dict):
        obj = await self.st_repo.get(tenant_id, type_id)
        if not obj:
            raise NotFoundError("Tipo de proveedor no encontrado")
        return await self.st_repo.update(obj, {k: v for k, v in data.items() if v is not None})

    async def delete_supplier_type(self, tenant_id: str, type_id: str) -> None:
        obj = await self.st_repo.get(tenant_id, type_id)
        if not obj:
            raise NotFoundError("Tipo de proveedor no encontrado")
        await self.st_repo.delete(obj)

    # ── Custom Supplier Fields ─────────────────────────────────────────────────

    async def list_supplier_fields(
        self, tenant_id: str, *, supplier_type_id: str | None = None,
        offset: int = 0, limit: int = 100,
    ):
        return await self.csf_repo.list(tenant_id, supplier_type_id=supplier_type_id, offset=offset, limit=limit)

    async def create_supplier_field(self, tenant_id: str, data: dict):
        st_id = data.get("supplier_type_id")
        existing, _ = await self.csf_repo.list(tenant_id, supplier_type_id=st_id)
        if any(f.field_key == data["field_key"] for f in existing):
            raise ConflictError(f"Ya existe un campo con key '{data['field_key']}'")
        return await self.csf_repo.create(tenant_id, data)

    async def update_supplier_field(self, tenant_id: str, field_id: str, data: dict):
        obj = await self.csf_repo.get(tenant_id, field_id)
        if not obj:
            raise NotFoundError("Campo de proveedor no encontrado")
        return await self.csf_repo.update(obj, {k: v for k, v in data.items() if v is not None})

    async def delete_supplier_field(self, tenant_id: str, field_id: str) -> None:
        obj = await self.csf_repo.get(tenant_id, field_id)
        if not obj:
            raise NotFoundError("Campo de proveedor no encontrado")
        await self.csf_repo.delete(obj)

    # ── Custom Warehouse Fields ────────────────────────────────────────────────

    async def list_warehouse_fields(
        self, tenant_id: str, *, warehouse_type_id: str | None = None,
        offset: int = 0, limit: int = 100,
    ):
        return await self.cwf_repo.list(tenant_id, warehouse_type_id=warehouse_type_id, offset=offset, limit=limit)

    async def create_warehouse_field(self, tenant_id: str, data: dict):
        wt_id = data.get("warehouse_type_id")
        existing, _ = await self.cwf_repo.list(tenant_id, warehouse_type_id=wt_id)
        if any(f.field_key == data["field_key"] for f in existing):
            raise ConflictError(f"Ya existe un campo con key '{data['field_key']}'")
        return await self.cwf_repo.create(tenant_id, data)

    async def update_warehouse_field(self, tenant_id: str, field_id: str, data: dict):
        obj = await self.cwf_repo.get(tenant_id, field_id)
        if not obj:
            raise NotFoundError("Campo de bodega no encontrado")
        return await self.cwf_repo.update(obj, {k: v for k, v in data.items() if v is not None})

    async def delete_warehouse_field(self, tenant_id: str, field_id: str) -> None:
        obj = await self.cwf_repo.get(tenant_id, field_id)
        if not obj:
            raise NotFoundError("Campo de bodega no encontrado")
        await self.cwf_repo.delete(obj)

    # ── Custom Movement Fields ─────────────────────────────────────────────────

    async def list_movement_fields(
        self, tenant_id: str, *, movement_type_id: str | None = None,
        offset: int = 0, limit: int = 100,
    ):
        return await self.cmf_repo.list(tenant_id, movement_type_id=movement_type_id, offset=offset, limit=limit)

    async def create_movement_field(self, tenant_id: str, data: dict):
        mt_id = data.get("movement_type_id")
        existing, _ = await self.cmf_repo.list(tenant_id, movement_type_id=mt_id)
        if any(f.field_key == data["field_key"] for f in existing):
            raise ConflictError(f"Ya existe un campo con key '{data['field_key']}'")
        return await self.cmf_repo.create(tenant_id, data)

    async def update_movement_field(self, tenant_id: str, field_id: str, data: dict):
        obj = await self.cmf_repo.get(tenant_id, field_id)
        if not obj:
            raise NotFoundError("Campo de movimiento no encontrado")
        return await self.cmf_repo.update(obj, {k: v for k, v in data.items() if v is not None})

    async def delete_movement_field(self, tenant_id: str, field_id: str) -> None:
        obj = await self.cmf_repo.get(tenant_id, field_id)
        if not obj:
            raise NotFoundError("Campo de movimiento no encontrado")
        await self.cmf_repo.delete(obj)
