"""WM movement-order schemas (internal bin->bin; not freight)."""
from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.domain.schemas.base import OrmBase

Direction = Literal["inbound", "outbound", "internal"]


# ─── Operation Types ──────────────────────────────────────────────────────────

class OperationTypeCreate(BaseModel):
    warehouse_id: str | None = None
    code: str = Field(..., max_length=10)
    name: str = Field(..., max_length=150)
    direction: Direction
    movement_type: str | None = None
    source_zone: str | None = None
    dest_zone: str | None = None
    requires_qa: bool = False
    is_active: bool = True


class OperationTypeUpdate(BaseModel):
    name: str | None = Field(None, max_length=150)
    direction: Direction | None = None
    movement_type: str | None = None
    source_zone: str | None = None
    dest_zone: str | None = None
    requires_qa: bool | None = None
    is_active: bool | None = None


class OperationTypeOut(OrmBase):
    id: str
    tenant_id: str
    warehouse_id: str | None = None
    code: str
    name: str
    direction: str
    movement_type: str | None = None
    source_zone: str | None = None
    dest_zone: str | None = None
    requires_qa: bool
    is_active: bool


# ─── Movement Order (SAP transfer order) ──────────────────────────────────────

class MovementOrderLineCreate(BaseModel):
    product_id: str
    batch_id: str | None = None
    variant_id: str | None = None
    quantity: Decimal = Field(..., gt=0)
    uom: str = "primary"
    source_location_id: str | None = None
    dest_location_id: str | None = None


class MovementOrderCreate(BaseModel):
    warehouse_id: str
    operation_type_id: str | None = None
    requirement_id: str | None = None
    source_doc_type: str | None = None
    source_doc_id: str | None = None
    notes: str | None = None
    lines: list[MovementOrderLineCreate] = Field(..., min_length=1)


class MovementOrderLineOut(OrmBase):
    id: str
    line_no: int
    product_id: str
    batch_id: str | None = None
    variant_id: str | None = None
    quantity: Decimal
    uom: str
    source_location_id: str | None = None
    dest_location_id: str | None = None
    source_confirmed: bool
    dest_confirmed: bool
    confirmed_qty: Decimal | None = None
    status: str


class MovementOrderOut(OrmBase):
    id: str
    tenant_id: str
    warehouse_id: str
    to_number: str
    operation_type_id: str | None = None
    requirement_id: str | None = None
    status: str
    source_doc_type: str | None = None
    source_doc_id: str | None = None
    notes: str | None = None
    created_by: str | None = None
    lines: list[MovementOrderLineOut] = []


class ConfirmLineIn(BaseModel):
    """Confirm a movement-order line: source (pick) and/or dest (putaway)."""
    confirm_source: bool = True
    confirm_dest: bool = True
    source_location_id: str | None = None   # override bin at confirm time
    dest_location_id: str | None = None
    confirmed_qty: Decimal | None = None
