"""Serial and batch tracking schemas."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from app.domain.schemas.base import OrmBase


# ─── Serial ─────────────────────────────────────────────────────────────────

class SerialCreate(BaseModel):
    entity_id: str
    serial_number: str = Field(..., max_length=255)
    status_id: str
    warehouse_id: str | None = None
    location_id: str | None = None
    batch_id: str | None = None
    notes: str | None = None
    metadata: dict[str, Any] = {}


class SerialUpdate(BaseModel):
    status_id: str | None = None
    warehouse_id: str | None = None
    location_id: str | None = None
    batch_id: str | None = None
    notes: str | None = None
    metadata: dict[str, Any] | None = None


class SerialOut(OrmBase):
    id: str
    tenant_id: str
    entity_id: str
    serial_number: str
    status_id: str
    warehouse_id: str | None
    location_id: str | None
    batch_id: str | None
    notes: str | None
    created_by: str | None = None
    updated_by: str | None = None
    created_at: datetime
    updated_at: datetime


class PaginatedSerials(BaseModel):
    items: list[SerialOut]
    total: int
    offset: int
    limit: int


# ─── Batch ──────────────────────────────────────────────────────────────────

class BatchCreate(BaseModel):
    entity_id: str
    batch_number: str = Field(..., max_length=100)
    manufacture_date: date | None = None
    expiration_date: date | None = None
    cost: Decimal | None = None
    quantity: Decimal = Decimal("0")
    notes: str | None = None
    metadata: dict[str, Any] = {}
    is_active: bool = True


class BatchUpdate(BaseModel):
    manufacture_date: date | None = None
    expiration_date: date | None = None
    cost: Decimal | None = None
    quantity: Decimal | None = None
    notes: str | None = None
    metadata: dict[str, Any] | None = None
    is_active: bool | None = None


class BatchOut(OrmBase):
    id: str
    tenant_id: str
    entity_id: str
    batch_number: str
    manufacture_date: date | None
    expiration_date: date | None
    cost: Decimal | None
    quantity: Decimal
    notes: str | None
    is_active: bool
    # Blockchain fields
    anchor_hash: str | None = None
    anchor_status: str = "none"
    anchor_tx_sig: str | None = None
    blockchain_asset_id: str | None = None
    blockchain_status: str = "none"
    created_by: str | None = None
    updated_by: str | None = None
    created_at: datetime


class PaginatedBatches(BaseModel):
    items: list[BatchOut]
    total: int
    offset: int
    limit: int


# ─── Lot Traceability ────────────────────────────────────────────────────────

class BatchDispatchEntry(BaseModel):
    movement_id: str
    movement_date: datetime | None = None
    qty: float
    sales_order_id: str | None = None
    sales_order_number: str | None = None
    customer_id: str | None = None
    customer_name: str | None = None
    warehouse_id: str | None = None
    # Blockchain proof
    anchor_hash: str | None = None
    anchor_tx_sig: str | None = None


class BlockchainProofEntry(BaseModel):
    """A single link in the on-chain proof chain."""
    event_type: str
    entity_type: str
    entity_id: str
    anchor_hash: str | None = None
    anchor_tx_sig: str | None = None
    timestamp: datetime | None = None


class TraceForwardOut(BaseModel):
    batch: BatchOut
    product_id: str
    product_name: str | None = None
    dispatches: list[BatchDispatchEntry]
    total_dispatched: float
    total_remaining: float
    # Blockchain proof chain
    blockchain_proof: list[BlockchainProofEntry] = []


class SOBatchEntry(BaseModel):
    line_id: str
    product_id: str
    product_name: str | None = None
    batch_id: str
    batch_number: str
    expiration_date: date | None = None
    qty_from_this_batch: float


class TraceBackwardOut(BaseModel):
    order_number: str
    customer_id: str
    customer_name: str | None = None
    batches_used: list[SOBatchEntry]


class BatchSearchResult(BaseModel):
    batch: BatchOut
    product_name: str | None = None
    total_received: float
    total_dispatched: float
    current_qty: float
    expiration_status: str
    sales_orders: list[dict]
