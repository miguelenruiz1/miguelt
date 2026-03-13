"""Product (Entity) schemas."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from app.domain.schemas.base import OrmBase


class ProductCreate(BaseModel):
    sku: str = Field(..., max_length=100)
    barcode: str | None = Field(None, max_length=100)
    name: str = Field(..., max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    product_type_id: str | None = None
    category_id: str | None = None
    unit_of_measure: str = Field("un", max_length=50)
    cost_price: Decimal = Decimal("0")
    sale_price: Decimal = Decimal("0")
    currency: str = Field("USD", max_length=3)
    is_active: bool = True
    track_batches: bool = False
    min_stock_level: int = 0
    reorder_point: int = 0
    reorder_quantity: int = 1
    preferred_supplier_id: str | None = None
    auto_reorder: bool = False
    tax_rate_id: str | None = None
    is_tax_exempt: bool = False
    retention_rate: Decimal | None = None
    images: list[Any] = []
    attributes: dict[str, Any] = {}


class ProductUpdate(BaseModel):
    sku: str | None = Field(None, max_length=100)
    barcode: str | None = Field(None, max_length=100)
    name: str | None = Field(None, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    product_type_id: str | None = None
    category_id: str | None = None
    unit_of_measure: str | None = Field(default=None, max_length=50)
    cost_price: Decimal | None = None
    sale_price: Decimal | None = None
    currency: str | None = Field(default=None, max_length=3)
    is_active: bool | None = None
    track_batches: bool | None = None
    min_stock_level: int | None = None
    reorder_point: int | None = None
    reorder_quantity: int | None = None
    preferred_supplier_id: str | None = None
    auto_reorder: bool | None = None
    tax_rate_id: str | None = None
    is_tax_exempt: bool | None = None
    retention_rate: Decimal | None = None
    images: list[Any] | None = None
    attributes: dict[str, Any] | None = None


class ProductOut(OrmBase):
    id: str
    tenant_id: str
    sku: str
    barcode: str | None
    name: str
    description: str | None
    product_type_id: str | None
    category_id: str | None = None
    unit_of_measure: str
    cost_price: Decimal
    sale_price: Decimal
    currency: str
    is_active: bool
    track_batches: bool
    min_stock_level: int
    reorder_point: int
    reorder_quantity: int
    preferred_supplier_id: str | None = None
    auto_reorder: bool = False
    tax_rate_id: str | None = None
    is_tax_exempt: bool = False
    retention_rate: Decimal | None = None
    images: list[Any]
    attributes: dict[str, Any]
    created_by: str | None = None
    updated_by: str | None = None
    created_at: datetime
    updated_at: datetime
    has_movements: bool = False


class PaginatedProducts(BaseModel):
    items: list[ProductOut]
    total: int
    offset: int
    limit: int
