"""Warehouse and WarehouseLocation schemas."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.db.models.enums import WarehouseType
from app.domain.schemas.base import OrmBase


class WarehouseCreate(BaseModel):
    name: str = Field(..., max_length=150)
    code: str = Field(..., max_length=50)
    type: WarehouseType = WarehouseType.main
    warehouse_type_id: str | None = None
    address: dict[str, Any] | None = None
    is_active: bool = True
    is_default: bool = False
    cost_per_sqm: float | None = None
    total_area_sqm: float | None = None
    max_stock_capacity: int | None = None


class WarehouseUpdate(BaseModel):
    name: str | None = Field(None, max_length=150)
    code: str | None = Field(None, max_length=50)
    type: WarehouseType | None = None
    warehouse_type_id: str | None = None
    address: dict[str, Any] | None = None
    is_active: bool | None = None
    is_default: bool | None = None
    cost_per_sqm: float | None = None
    total_area_sqm: float | None = None
    max_stock_capacity: int | None = None


class WarehouseOut(OrmBase):
    id: str
    tenant_id: str
    name: str
    code: str
    type: WarehouseType
    warehouse_type_id: str | None = None
    address: dict[str, Any] | None
    is_active: bool
    is_default: bool
    cost_per_sqm: float | None = None
    total_area_sqm: float | None = None
    max_stock_capacity: int | None = None
    created_by: str | None = None
    updated_by: str | None = None


# ─── Location ───────────────────────────────────────────────────────────────

class LocationCreate(BaseModel):
    warehouse_id: str
    parent_location_id: str | None = None
    name: str = Field(..., max_length=150)
    code: str = Field(..., max_length=50)
    description: str | None = None
    location_type: str = "bin"
    is_active: bool = True
    sort_order: int = 0


class LocationUpdate(BaseModel):
    parent_location_id: str | None = None
    name: str | None = Field(None, max_length=150)
    code: str | None = Field(None, max_length=50)
    description: str | None = None
    location_type: str | None = None
    is_active: bool | None = None
    sort_order: int | None = None


class LocationOut(OrmBase):
    id: str
    tenant_id: str
    warehouse_id: str
    parent_location_id: str | None
    name: str
    code: str
    description: str | None
    location_type: str
    is_active: bool
    sort_order: int
