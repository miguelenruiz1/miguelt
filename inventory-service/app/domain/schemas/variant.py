"""Schemas for product variants and variant attributes."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.domain.schemas.base import OrmBase


# ── Variant Attributes ──────────────────────────────────────────────
class VariantOptionIn(BaseModel):
    value: str
    color_hex: str | None = None
    sort_order: int = 0
    is_active: bool = True


class VariantOptionOut(OrmBase):
    id: str
    attribute_id: str
    value: str
    color_hex: str | None = None
    sort_order: int
    is_active: bool


class VariantAttributeCreate(BaseModel):
    name: str
    slug: str
    sort_order: int = 0
    is_active: bool = True
    options: list[VariantOptionIn] | None = None


class VariantAttributeUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class VariantAttributeOut(OrmBase):
    id: str
    tenant_id: str
    name: str
    slug: str
    sort_order: int
    is_active: bool
    options: list[VariantOptionOut] = []
    created_at: datetime | None = None


# ── Product Variants ────────────────────────────────────────────────
class ProductVariantCreate(BaseModel):
    parent_id: str
    sku: str
    barcode: str | None = None
    name: str
    cost_price: float = 0
    sale_price: float = 0
    weight: float | None = None
    is_active: bool = True
    option_values: dict = {}
    images: list = []


class ProductVariantUpdate(BaseModel):
    sku: str | None = None
    barcode: str | None = None
    name: str | None = None
    cost_price: float | None = None
    sale_price: float | None = None
    weight: float | None = None
    is_active: bool | None = None
    option_values: dict | None = None
    images: list | None = None


class ProductVariantOut(OrmBase):
    id: str
    tenant_id: str
    parent_id: str
    sku: str
    barcode: str | None = None
    name: str
    cost_price: float
    sale_price: float
    weight: float | None = None
    is_active: bool
    option_values: dict = {}
    images: list = []
    created_at: datetime | None = None
    updated_at: datetime | None = None


class PaginatedVariants(BaseModel):
    items: list[ProductVariantOut]
    total: int
    offset: int
    limit: int
