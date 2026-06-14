"""WM putaway / removal / packaging schemas."""
from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.domain.schemas.base import OrmBase

RemovalStrategy = Literal["fifo", "fefo", "lifo", "fixed_bin"]


class PutawayRuleCreate(BaseModel):
    warehouse_id: str
    match_product_id: str | None = None
    match_category_id: str | None = None
    match_commodity: str | None = None
    dest_storage_type_id: str | None = None
    dest_storage_section_id: str | None = None
    priority: int = 100
    is_active: bool = True


class PutawayRuleOut(OrmBase):
    id: str
    tenant_id: str
    warehouse_id: str
    match_product_id: str | None = None
    match_category_id: str | None = None
    match_commodity: str | None = None
    dest_storage_type_id: str | None = None
    dest_storage_section_id: str | None = None
    priority: int
    is_active: bool


class PackageTypeCreate(BaseModel):
    code: str = Field(..., max_length=30)
    name: str = Field(..., max_length=150)
    max_weight_kg: Decimal | None = None
    length_cm: Decimal | None = None
    width_cm: Decimal | None = None
    height_cm: Decimal | None = None
    is_active: bool = True


class PackageTypeOut(OrmBase):
    id: str
    tenant_id: str
    code: str
    name: str
    max_weight_kg: Decimal | None = None
    length_cm: Decimal | None = None
    width_cm: Decimal | None = None
    height_cm: Decimal | None = None
    is_active: bool


class PutawayProposeIn(BaseModel):
    warehouse_id: str
    product_id: str
    quantity: Decimal = Field(Decimal("1"), gt=0)


class PutawayProposeOut(BaseModel):
    location_id: str | None = None
    code: str | None = None
    storage_type_id: str | None = None
    reason: str


class RemovalPlanIn(BaseModel):
    warehouse_id: str
    product_id: str
    quantity: Decimal = Field(..., gt=0)
    strategy: RemovalStrategy | None = None   # defaults per storage/product; fallback fefo


class RemovalAllocation(BaseModel):
    batch_id: str | None = None
    batch_number: str | None = None
    expiration_date: str | None = None
    qty: Decimal


class RemovalPlanOut(BaseModel):
    strategy: str
    requested_qty: Decimal
    allocated_qty: Decimal
    shortfall: Decimal
    allocations: list[RemovalAllocation]
