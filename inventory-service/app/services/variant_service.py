"""Business logic for product variants and variant attributes."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.repositories.product_repo import ProductRepository
from app.repositories.variant_repo import (
    ProductVariantRepository, VariantAttributeOptionRepository, VariantAttributeRepository,
)


class VariantService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.attr_repo = VariantAttributeRepository(db)
        self.option_repo = VariantAttributeOptionRepository(db)
        self.variant_repo = ProductVariantRepository(db)
        self.product_repo = ProductRepository(db)

    # ── Attributes ──────────────────────────────────────────────────
    async def list_attributes(self, tenant_id: str):
        return await self.attr_repo.list(tenant_id)

    async def create_attribute(self, tenant_id: str, data: dict, options: list[dict] | None = None):
        data["tenant_id"] = tenant_id
        attr = await self.attr_repo.create(data)
        if options:
            for opt in options:
                opt["attribute_id"] = attr.id
                await self.option_repo.create(opt)
            attr = await self.attr_repo._reload(attr.id, tenant_id)
        return attr

    async def update_attribute(self, attr_id: str, tenant_id: str, data: dict):
        obj = await self.attr_repo.get_by_id(attr_id, tenant_id)
        if not obj:
            raise NotFoundError("Variant attribute not found")
        return await self.attr_repo.update(obj, data)

    async def delete_attribute(self, attr_id: str, tenant_id: str):
        obj = await self.attr_repo.get_by_id(attr_id, tenant_id)
        if not obj:
            raise NotFoundError("Variant attribute not found")
        await self.attr_repo.delete(obj)

    # ── Options ─────────────────────────────────────────────────────
    async def add_option(self, attr_id: str, tenant_id: str, data: dict):
        attr = await self.attr_repo.get_by_id(attr_id, tenant_id)
        if not attr:
            raise NotFoundError("Variant attribute not found")
        data["attribute_id"] = attr_id
        return await self.option_repo.create(data)

    async def update_option(self, option_id: str, data: dict, tenant_id: str | None = None):
        obj = await self.option_repo.get_by_id(option_id, tenant_id)
        if not obj:
            raise NotFoundError("Variant option not found")
        return await self.option_repo.update(obj, data)

    async def delete_option(self, option_id: str, tenant_id: str | None = None):
        obj = await self.option_repo.get_by_id(option_id, tenant_id)
        if not obj:
            raise NotFoundError("Variant option not found")
        await self.option_repo.delete(obj)

    # ── Product Variants ────────────────────────────────────────────
    async def list_variants(self, tenant_id: str, **kwargs):
        return await self.variant_repo.list(tenant_id, **kwargs)

    async def list_variants_for_product(self, parent_id: str, tenant_id: str):
        product = await self.product_repo.get_by_id(parent_id, tenant_id)
        if not product:
            raise NotFoundError("Parent product not found")
        return await self.variant_repo.list_by_parent(parent_id, tenant_id)

    async def get_variant(self, vid: str, tenant_id: str):
        v = await self.variant_repo.get_by_id(vid, tenant_id)
        if not v:
            raise NotFoundError("Product variant not found")
        return v

    async def create_variant(self, tenant_id: str, data: dict):
        product = await self.product_repo.get_by_id(data["parent_id"], tenant_id)
        if not product:
            raise NotFoundError("Parent product not found")
        data["tenant_id"] = tenant_id
        return await self.variant_repo.create(data)

    async def update_variant(self, vid: str, tenant_id: str, data: dict):
        obj = await self.variant_repo.get_by_id(vid, tenant_id)
        if not obj:
            raise NotFoundError("Product variant not found")
        return await self.variant_repo.update(obj, data)

    async def delete_variant(self, vid: str, tenant_id: str):
        obj = await self.variant_repo.get_by_id(vid, tenant_id)
        if not obj:
            raise NotFoundError("Product variant not found")
        await self.variant_repo.delete(obj)
