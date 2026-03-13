"""Configuration type schemas (ProductType, OrderType, CustomFields, etc.)."""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.domain.schemas.base import FieldType, OrmBase


# ─── DynamicMovementType ────────────────────────────────────────────────────

class MovementTypeCreate(BaseModel):
    name: str = Field(..., max_length=150)
    slug: str | None = Field(None, max_length=150)
    description: str | None = None
    direction: str = "in"
    affects_cost: bool = True
    requires_reference: bool = False
    color: str | None = "#3b82f6"
    is_active: bool = True
    sort_order: int = 0


class MovementTypeUpdate(BaseModel):
    name: str | None = Field(None, max_length=150)
    description: str | None = None
    direction: str | None = None
    affects_cost: bool | None = None
    requires_reference: bool | None = None
    color: str | None = None
    is_active: bool | None = None
    sort_order: int | None = None


class MovementTypeOut(OrmBase):
    id: str
    tenant_id: str
    name: str
    slug: str
    description: str | None
    direction: str
    affects_cost: bool
    requires_reference: bool
    color: str | None
    is_active: bool
    is_system: bool
    sort_order: int


# ─── DynamicWarehouseType ───────────────────────────────────────────────────

class WarehouseTypeCreate(BaseModel):
    name: str = Field(..., max_length=150)
    slug: str | None = Field(None, max_length=150)
    description: str | None = None
    color: str | None = "#f59e0b"
    is_active: bool = True
    sort_order: int = 0


class WarehouseTypeUpdate(BaseModel):
    name: str | None = Field(None, max_length=150)
    description: str | None = None
    color: str | None = None
    is_active: bool | None = None
    sort_order: int | None = None


class WarehouseTypeOut(OrmBase):
    id: str
    tenant_id: str
    name: str
    slug: str
    description: str | None
    color: str | None
    is_active: bool
    is_system: bool
    sort_order: int


# ─── ProductType ─────────────────────────────────────────────────────────────

class ProductTypeCreate(BaseModel):
    name: str = Field(..., max_length=150)
    slug: str | None = Field(None, max_length=150)
    description: str | None = None
    color: str | None = "#6366f1"
    is_active: bool = True
    tracks_serials: bool = False
    tracks_batches: bool = False
    requires_qc: bool = False
    entry_rule_location_id: str | None = None
    dispatch_rule: str = "fifo"
    rotation_target_months: int | None = None
    default_category_id: str | None = None


class ProductTypeUpdate(BaseModel):
    name: str | None = Field(None, max_length=150)
    description: str | None = None
    color: str | None = None
    is_active: bool | None = None
    tracks_serials: bool | None = None
    tracks_batches: bool | None = None
    requires_qc: bool | None = None
    entry_rule_location_id: str | None = None
    dispatch_rule: str | None = None
    rotation_target_months: int | None = None
    default_category_id: str | None = None


class ProductTypeOut(OrmBase):
    id: str
    tenant_id: str
    name: str
    slug: str
    description: str | None
    color: str | None
    is_active: bool
    tracks_serials: bool
    tracks_batches: bool
    requires_qc: bool = False
    entry_rule_location_id: str | None = None
    dispatch_rule: str = "fifo"
    rotation_target_months: int | None = None
    default_category_id: str | None = None


# ─── OrderType ───────────────────────────────────────────────────────────────

class OrderTypeCreate(BaseModel):
    name: str = Field(..., max_length=150)
    slug: str | None = Field(None, max_length=150)
    description: str | None = None
    color: str | None = "#10b981"
    is_active: bool = True


class OrderTypeUpdate(BaseModel):
    name: str | None = Field(None, max_length=150)
    description: str | None = None
    color: str | None = None
    is_active: bool | None = None


class OrderTypeOut(OrmBase):
    id: str
    tenant_id: str
    name: str
    slug: str
    description: str | None
    color: str | None
    is_active: bool


# ─── CustomProductField ─────────────────────────────────────────────────────

class CustomFieldCreate(BaseModel):
    label: str = Field(..., max_length=150)
    field_key: str = Field(..., max_length=100)
    field_type: FieldType = "text"
    options: list[str] | None = None
    required: bool = False
    sort_order: int = 0
    is_active: bool = True
    product_type_id: str | None = None


class CustomFieldUpdate(BaseModel):
    label: str | None = Field(None, max_length=150)
    field_type: FieldType | None = None
    options: list[str] | None = None
    required: bool | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class CustomFieldOut(OrmBase):
    id: str
    tenant_id: str
    product_type_id: str | None
    label: str
    field_key: str
    field_type: str
    options: list[str] | None
    required: bool
    sort_order: int
    is_active: bool


# ─── SupplierType ────────────────────────────────────────────────────────────

class SupplierTypeCreate(BaseModel):
    name: str = Field(..., max_length=150)
    slug: str | None = Field(None, max_length=150)
    description: str | None = None
    color: str | None = "#f59e0b"
    is_active: bool = True


class SupplierTypeUpdate(BaseModel):
    name: str | None = Field(None, max_length=150)
    description: str | None = None
    color: str | None = None
    is_active: bool | None = None


class SupplierTypeOut(OrmBase):
    id: str
    tenant_id: str
    name: str
    slug: str
    description: str | None
    color: str | None
    is_active: bool


# ─── CustomSupplierField ────────────────────────────────────────────────────

class CustomSupplierFieldCreate(BaseModel):
    label: str = Field(..., max_length=150)
    field_key: str = Field(..., max_length=100)
    field_type: FieldType = "text"
    options: list[str] | None = None
    required: bool = False
    sort_order: int = 0
    is_active: bool = True
    supplier_type_id: str | None = None


class CustomSupplierFieldUpdate(BaseModel):
    label: str | None = Field(None, max_length=150)
    field_type: FieldType | None = None
    options: list[str] | None = None
    required: bool | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class CustomSupplierFieldOut(OrmBase):
    id: str
    tenant_id: str
    supplier_type_id: str | None
    label: str
    field_key: str
    field_type: str
    options: list[str] | None
    required: bool
    sort_order: int
    is_active: bool


# ─── CustomWarehouseField ──────────────────────────────────────────────────

class CustomWarehouseFieldCreate(BaseModel):
    label: str = Field(..., max_length=150)
    field_key: str = Field(..., max_length=100)
    field_type: FieldType = "text"
    options: list[str] | None = None
    required: bool = False
    sort_order: int = 0
    is_active: bool = True
    warehouse_type_id: str | None = None


class CustomWarehouseFieldUpdate(BaseModel):
    label: str | None = Field(None, max_length=150)
    field_type: FieldType | None = None
    options: list[str] | None = None
    required: bool | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class CustomWarehouseFieldOut(OrmBase):
    id: str
    tenant_id: str
    warehouse_type_id: str | None
    label: str
    field_key: str
    field_type: str
    options: list[str] | None
    required: bool
    sort_order: int
    is_active: bool


# ─── CustomMovementField ──────────────────────────────────────────────────

class CustomMovementFieldCreate(BaseModel):
    label: str = Field(..., max_length=150)
    field_key: str = Field(..., max_length=100)
    field_type: FieldType = "text"
    options: list[str] | None = None
    required: bool = False
    sort_order: int = 0
    is_active: bool = True
    movement_type_id: str | None = None


class CustomMovementFieldUpdate(BaseModel):
    label: str | None = Field(None, max_length=150)
    field_type: FieldType | None = None
    options: list[str] | None = None
    required: bool | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class CustomMovementFieldOut(OrmBase):
    id: str
    tenant_id: str
    movement_type_id: str | None
    label: str
    field_key: str
    field_type: str
    options: list[str] | None
    required: bool
    sort_order: int
    is_active: bool


# ─── SerialStatus ───────────────────────────────────────────────────────────

class SerialStatusCreate(BaseModel):
    name: str = Field(..., max_length=150)
    slug: str | None = Field(None, max_length=150)
    description: str | None = None
    color: str | None = "#3b82f6"
    is_active: bool = True


class SerialStatusUpdate(BaseModel):
    name: str | None = Field(None, max_length=150)
    description: str | None = None
    color: str | None = None
    is_active: bool | None = None


class SerialStatusOut(OrmBase):
    id: str
    tenant_id: str
    name: str
    slug: str
    description: str | None
    color: str | None
    is_active: bool


# ─── EventType config ───────────────────────────────────────────────────────

class EventTypeCreate(BaseModel):
    name: str = Field(..., max_length=150)
    slug: str | None = Field(None, max_length=150)
    description: str | None = None
    auto_generate_movement_type_id: str | None = None
    color: str | None = "#ef4444"
    icon: str | None = None
    is_active: bool = True


class EventTypeUpdate(BaseModel):
    name: str | None = Field(None, max_length=150)
    description: str | None = None
    auto_generate_movement_type_id: str | None = None
    color: str | None = None
    icon: str | None = None
    is_active: bool | None = None


class EventTypeOut(OrmBase):
    id: str
    tenant_id: str
    name: str
    slug: str
    description: str | None
    auto_generate_movement_type_id: str | None
    color: str | None
    icon: str | None
    is_active: bool


# ─── EventSeverity config ──────────────────────────────────────────────────

class EventSeverityCreate(BaseModel):
    name: str = Field(..., max_length=150)
    slug: str | None = Field(None, max_length=150)
    weight: int = 1
    color: str | None = "#f59e0b"
    is_active: bool = True


class EventSeverityUpdate(BaseModel):
    name: str | None = Field(None, max_length=150)
    weight: int | None = None
    color: str | None = None
    is_active: bool | None = None


class EventSeverityOut(OrmBase):
    id: str
    tenant_id: str
    name: str
    slug: str
    weight: int
    color: str | None
    is_active: bool


# ─── EventStatus config ────────────────────────────────────────────────────

class EventStatusCreate(BaseModel):
    name: str = Field(..., max_length=150)
    slug: str | None = Field(None, max_length=150)
    is_final: bool = False
    color: str | None = "#6b7280"
    sort_order: int = 0
    is_active: bool = True


class EventStatusUpdate(BaseModel):
    name: str | None = Field(None, max_length=150)
    is_final: bool | None = None
    color: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class EventStatusOut(OrmBase):
    id: str
    tenant_id: str
    name: str
    slug: str
    is_final: bool
    color: str | None
    sort_order: int
    is_active: bool
