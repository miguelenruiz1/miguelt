"""Production v2 — BOM/Recipe, production runs, emissions, receipts, cost layers."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.domain.schemas.base import OrmBase


# ─── Recipe / BOM ────────────────────────────────────────────────────────────

class RecipeComponentCreate(BaseModel):
    component_entity_id: str
    quantity_required: Decimal = Field(..., gt=0)
    notes: str | None = None
    issue_method: str = "manual"
    scrap_percentage: Decimal = Decimal("0")
    lead_time_offset_days: int = 0


class RecipeCreate(BaseModel):
    name: str = Field(..., max_length=255)
    output_entity_id: str
    output_quantity: Decimal = Field(Decimal("1"), gt=0)
    description: str | None = None
    is_active: bool = True
    bom_type: str = "production"
    standard_cost: Decimal = Decimal("0")
    planned_production_size: int = 1
    version: str = "v1"
    is_default: bool = True
    components: list[RecipeComponentCreate] = []


class RecipeUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    output_entity_id: str | None = None
    output_quantity: Decimal | None = None
    description: str | None = None
    is_active: bool | None = None
    bom_type: str | None = None
    standard_cost: Decimal | None = None
    planned_production_size: int | None = None
    version: str | None = None
    is_default: bool | None = None
    components: list[RecipeComponentCreate] | None = None


class RecipeComponentOut(OrmBase):
    id: str
    recipe_id: str
    component_entity_id: str
    quantity_required: Decimal
    notes: str | None
    issue_method: str = "manual"
    scrap_percentage: Decimal = Decimal("0")
    lead_time_offset_days: int = 0


class RecipeOut(OrmBase):
    id: str
    tenant_id: str
    name: str
    output_entity_id: str
    output_quantity: Decimal
    description: str | None
    is_active: bool
    bom_type: str = "production"
    standard_cost: Decimal = Decimal("0")
    planned_production_size: int = 1
    version: str = "v1"
    is_default: bool = True
    created_by: str | None = None
    updated_by: str | None = None
    created_at: datetime
    components: list[RecipeComponentOut] = []
    resources: list[RecipeResourceOut] = []


# ─── Resources / Work Centers ────────────────────────────────────────────────

class ProductionResourceCreate(BaseModel):
    name: str = Field(..., max_length=255)
    resource_type: str = "labor"
    cost_per_hour: Decimal = Decimal("0")
    cost_per_unit: Decimal = Decimal("0")
    capacity_hours_per_day: Decimal = Decimal("8")
    efficiency_pct: Decimal = Decimal("100")
    shifts_per_day: int = 1
    available_hours_override: Decimal | None = None
    notes: str | None = None


class ProductionResourceUpdate(BaseModel):
    name: str | None = None
    resource_type: str | None = None
    cost_per_hour: Decimal | None = None
    cost_per_unit: Decimal | None = None
    capacity_hours_per_day: Decimal | None = None
    efficiency_pct: Decimal | None = None
    shifts_per_day: int | None = None
    available_hours_override: Decimal | None = None
    is_active: bool | None = None
    notes: str | None = None


class ProductionResourceOut(OrmBase):
    id: str
    tenant_id: str
    name: str
    resource_type: str
    cost_per_hour: Decimal
    cost_per_unit: Decimal
    capacity_hours_per_day: Decimal
    efficiency_pct: Decimal
    shifts_per_day: int
    available_hours_override: Decimal | None = None
    is_active: bool
    notes: str | None = None
    created_at: datetime


class RecipeResourceCreate(BaseModel):
    resource_id: str
    hours_per_unit: Decimal = Field(..., gt=0)
    setup_time_hours: Decimal = Decimal("0")
    notes: str | None = None


class RecipeResourceOut(OrmBase):
    id: str
    recipe_id: str
    resource_id: str
    hours_per_unit: Decimal
    setup_time_hours: Decimal
    notes: str | None = None


class RunResourceCostOut(OrmBase):
    id: str
    production_run_id: str
    resource_id: str
    planned_hours: Decimal
    actual_hours: Decimal | None = None
    cost_per_hour: Decimal
    total_cost: Decimal


# ─── MRP ─────────────────────────────────────────────────────────────────────

class MRPRequest(BaseModel):
    recipe_id: str
    quantity: Decimal = Field(..., gt=0)
    warehouse_id: str
    consider_reserved: bool = True
    auto_create_po: bool = False
    supplier_id: str | None = None
    expected_date: str | None = None


class MRPLine(BaseModel):
    component_entity_id: str
    component_name: str | None = None
    required_qty: Decimal
    available_qty: Decimal
    shortage: Decimal
    suggested_order_qty: Decimal
    preferred_supplier_id: str | None = None
    lead_time_offset_days: int = 0
    estimated_unit_cost: Decimal = Decimal("0")
    action: str = "buy"  # "buy" or "make"
    sub_recipe_id: str | None = None  # if action=make, which recipe to use
    sub_recipe_name: str | None = None


class MRPResult(BaseModel):
    recipe_id: str
    recipe_name: str
    output_quantity: Decimal
    lines: list[MRPLine]
    total_estimated_cost: Decimal = Decimal("0")
    purchase_orders_created: list[str] = []
    make_suggestions: list[MRPLine] = []  # sub-assemblies to produce


# ─── Capacity ────────────────────────────────────────────────────────────────

class CapacityLine(BaseModel):
    resource_id: str
    resource_name: str
    required_hours: Decimal
    available_hours: Decimal
    committed_hours: Decimal
    utilization_pct: Decimal
    has_capacity: bool


class CapacityResult(BaseModel):
    lines: list[CapacityLine]
    all_have_capacity: bool


# ─── Production Run ──────────────────────────────────────────────────────────

class ProductionRunCreate(BaseModel):
    recipe_id: str
    warehouse_id: str
    output_warehouse_id: str | None = None
    multiplier: Decimal = Field(Decimal("1"), gt=0)
    notes: str | None = None
    order_type: str = "standard"
    priority: int = Field(50, ge=0, le=100)
    planned_start_date: datetime | None = None
    planned_end_date: datetime | None = None
    linked_sales_order_id: str | None = None
    linked_customer_id: str | None = None


class ProductionRunUpdate(BaseModel):
    notes: str | None = None
    priority: int | None = Field(None, ge=0, le=100)
    planned_start_date: datetime | None = None
    planned_end_date: datetime | None = None
    output_warehouse_id: str | None = None
    linked_sales_order_id: str | None = None
    linked_customer_id: str | None = None
    multiplier: Decimal | None = None


class ProductionRunReject(BaseModel):
    rejection_notes: str = Field(..., min_length=1, max_length=2000)


class ProductionRunOut(OrmBase):
    id: str
    tenant_id: str
    recipe_id: str
    run_number: str
    warehouse_id: str
    output_warehouse_id: str | None = None
    multiplier: Decimal
    status: str
    order_type: str = "standard"
    priority: int = 50
    planned_start_date: datetime | None = None
    planned_end_date: datetime | None = None
    actual_start_date: datetime | None = None
    actual_end_date: datetime | None = None
    actual_output_quantity: Decimal | None = None
    total_component_cost: Decimal | None = None
    total_production_cost: Decimal | None = None
    unit_production_cost: Decimal | None = None
    variance_amount: Decimal | None = None
    total_resource_cost: Decimal | None = None
    linked_sales_order_id: str | None = None
    linked_customer_id: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    performed_by: str | None = None
    updated_by: str | None = None
    notes: str | None = None
    approved_by: str | None = None
    approved_at: datetime | None = None
    rejection_notes: str | None = None
    created_at: datetime


class PaginatedProductionRuns(BaseModel):
    items: list[ProductionRunOut]
    total: int
    offset: int
    limit: int


# ─── Emission (Material Issue) ───────────────────────────────────────────────

class EmissionLineCreate(BaseModel):
    component_entity_id: str
    actual_quantity: Decimal = Field(..., gt=0)
    batch_id: str | None = None
    warehouse_id: str | None = None


class EmissionCreate(BaseModel):
    emission_date: datetime | None = None
    warehouse_id: str | None = None
    notes: str | None = None
    lines: list[EmissionLineCreate] | None = None  # None = auto from BOM


class EmissionLineOut(OrmBase):
    id: str
    emission_id: str
    component_entity_id: str
    planned_quantity: Decimal
    actual_quantity: Decimal
    unit_cost: Decimal
    total_cost: Decimal
    batch_id: str | None = None
    warehouse_id: str | None = None
    variance_quantity: Decimal


class EmissionOut(OrmBase):
    id: str
    tenant_id: str
    production_run_id: str
    emission_number: str
    status: str
    emission_date: datetime
    warehouse_id: str | None = None
    notes: str | None = None
    performed_by: str | None = None
    created_at: datetime
    lines: list[EmissionLineOut] = []


# ─── Receipt (Finished Goods) ────────────────────────────────────────────────

class ReceiptLineCreate(BaseModel):
    received_quantity: Decimal = Field(..., gt=0)
    batch_id: str | None = None
    is_complete: bool = True


class ReceiptCreate(BaseModel):
    receipt_date: datetime | None = None
    output_warehouse_id: str | None = None
    notes: str | None = None
    lines: list[ReceiptLineCreate] | None = None  # None = auto planned qty


class ReceiptLineOut(OrmBase):
    id: str
    receipt_id: str
    entity_id: str
    planned_quantity: Decimal
    received_quantity: Decimal
    unit_cost: Decimal
    total_cost: Decimal
    batch_id: str | None = None
    is_complete: bool


class ReceiptOut(OrmBase):
    id: str
    tenant_id: str
    production_run_id: str
    receipt_number: str
    status: str
    receipt_date: datetime
    output_warehouse_id: str | None = None
    notes: str | None = None
    performed_by: str | None = None
    created_at: datetime
    lines: list[ReceiptLineOut] = []


# ─── Stock Layer ─────────────────────────────────────────────────────────────

class StockLayerOut(OrmBase):
    id: str
    tenant_id: str
    entity_id: str
    warehouse_id: str
    movement_id: str | None
    quantity_initial: Decimal
    quantity_remaining: Decimal
    unit_cost: Decimal
    batch_id: str | None
    created_at: datetime
