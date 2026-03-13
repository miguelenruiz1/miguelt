"""Schemas for cycle count operations."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.domain.schemas.base import OrmBase


# ── Request schemas ──────────────────────────────────────────────────────────

class CycleCountCreate(BaseModel):
    warehouse_id: str
    product_ids: list[str] = Field(default_factory=list, description="Empty = all products with stock")
    methodology: str | None = Field(None, description="control_group|location_audit|random_selection|diminishing_population|product_category|abc")
    assigned_counters: int = Field(1, ge=1)
    minutes_per_count: int = Field(2, ge=1)
    scheduled_date: datetime | None = None
    notes: str | None = None


class RecordCountIn(BaseModel):
    counted_qty: Decimal = Field(..., ge=0)
    notes: str | None = None


class RecountIn(BaseModel):
    recount_qty: Decimal = Field(..., ge=0)
    root_cause: str | None = None
    notes: str | None = None


# ── Response schemas ─────────────────────────────────────────────────────────

class CycleCountItemOut(OrmBase):
    id: str
    tenant_id: str
    cycle_count_id: str
    product_id: str
    product_name: str | None = None
    product_sku: str | None = None
    location_id: str | None = None
    batch_id: str | None = None
    system_qty: Decimal
    counted_qty: Decimal | None = None
    discrepancy: Decimal | None = None
    recount_qty: Decimal | None = None
    recount_discrepancy: Decimal | None = None
    root_cause: str | None = None
    counted_by: str | None = None
    counted_at: datetime | None = None
    notes: str | None = None
    movement_id: str | None = None
    created_at: datetime


class CycleCountOut(OrmBase):
    id: str
    tenant_id: str
    count_number: str
    warehouse_id: str
    warehouse_name: str | None = None
    status: str
    methodology: str | None = None
    assigned_counters: int = 1
    minutes_per_count: int = 2
    scheduled_date: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    approved_at: datetime | None = None
    approved_by: str | None = None
    created_by: str | None = None
    updated_by: str | None = None
    notes: str | None = None
    created_at: datetime
    items: list[CycleCountItemOut] = []
    ira: IRAComputeOut | None = None
    feasibility: FeasibilityOut | None = None


class PaginatedCycleCounts(BaseModel):
    items: list[CycleCountOut]
    total: int
    offset: int
    limit: int


class IRASnapshotOut(OrmBase):
    id: str
    tenant_id: str
    cycle_count_id: str
    warehouse_id: str | None = None
    total_items: int
    accurate_items: int
    ira_percentage: Decimal
    total_system_value: Decimal
    total_counted_value: Decimal
    value_accuracy: Decimal
    snapshot_date: datetime
    created_at: datetime


class IRAComputeOut(BaseModel):
    total_items: int
    accurate_items: int
    ira_percentage: float
    total_system_value: float
    total_counted_value: float
    value_accuracy: float
    counted_items: int


class FeasibilityOut(BaseModel):
    """Personnel/time feasibility calculator (per video methodology)."""
    total_items: int
    minutes_per_count: int
    assigned_counters: int
    total_minutes: float
    total_hours: float
    hours_per_counter: float
    available_hours: float = 7.0
    is_feasible: bool


class ProductDiscrepancyOut(BaseModel):
    cycle_count_id: str
    count_number: str
    warehouse_id: str
    warehouse_name: str | None = None
    counted_at: datetime | None = None
    system_qty: float
    counted_qty: float | None = None
    discrepancy: float | None = None
    root_cause: str | None = None
