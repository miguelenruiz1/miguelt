"""PurchaseOrder schemas."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.db.models.enums import POStatus
from app.domain.schemas.base import OrmBase


class POLineCreate(BaseModel):
    product_id: str
    variant_id: str | None = None
    qty_ordered: Decimal = Field(..., gt=0)
    uom: str = "primary"
    unit_cost: Decimal = Field(..., ge=0)
    location_id: str | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @property
    def line_total(self) -> Decimal:
        return self.qty_ordered * self.unit_cost


class POCreate(BaseModel):
    supplier_id: str
    warehouse_id: str | None = None
    expected_date: date | None = None
    notes: str | None = Field(default=None, max_length=2000)
    lines: list[POLineCreate] = []


class POUpdate(BaseModel):
    supplier_id: str | None = None
    warehouse_id: str | None = None
    expected_date: date | None = None
    notes: str | None = Field(default=None, max_length=2000)


class POLineOut(OrmBase):
    id: str
    po_id: str
    product_id: str
    variant_id: str | None = None
    qty_ordered: Decimal
    qty_received: Decimal
    unit_cost: Decimal
    line_total: Decimal
    location_id: str | None = None
    notes: str | None


class POOut(OrmBase):
    id: str
    tenant_id: str
    po_number: str
    supplier_id: str
    status: POStatus
    warehouse_id: str | None
    expected_date: date | None
    received_date: date | None
    is_auto_generated: bool = False
    reorder_trigger_stock: float | None = None
    notes: str | None
    is_consolidated: bool = False
    consolidated_from_ids: list[str] | None = None
    consolidated_at: datetime | None = None
    consolidated_by: str | None = None
    parent_consolidated_id: str | None = None
    created_by: str | None
    updated_by: str | None = None
    created_at: datetime
    updated_at: datetime
    lines: list[POLineOut] = []


class PaginatedPOs(BaseModel):
    items: list[POOut]
    total: int
    offset: int
    limit: int


class LineReceiptIn(BaseModel):
    line_id: str
    qty_received: Decimal = Field(..., gt=0)
    uom: str = "primary"


class ReceivePOIn(BaseModel):
    lines: list[LineReceiptIn]


class ConsolidateRequest(BaseModel):
    po_ids: list[str] = Field(..., min_length=2)


class ConsolidationCandidate(BaseModel):
    supplier_id: str
    supplier_name: str
    po_count: int
    total_amount: float
    pos: list[POOut]


class ConsolidationResult(BaseModel):
    consolidated_po: POOut
    original_pos: list[POOut]
    lines_merged: int
    message: str


class ConsolidationInfo(BaseModel):
    type: str  # "consolidated" | "original" | "none"
    consolidated_po: POOut | None = None
    original_pos: list[POOut] | None = None
    consolidated_at: datetime | None = None
    consolidated_by: str | None = None
