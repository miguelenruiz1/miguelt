"""Schemas for stock alerts."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.domain.schemas.base import OrmBase


class StockAlertOut(OrmBase):
    id: str
    tenant_id: str
    product_id: str
    warehouse_id: str | None = None
    batch_id: str | None = None
    alert_type: str
    message: str
    current_qty: int
    threshold_qty: int
    is_read: bool
    is_resolved: bool
    created_at: datetime | None = None
    resolved_at: datetime | None = None
    # Enriched fields (populated by service, not stored in DB)
    product_name: str | None = None
    product_sku: str | None = None
    warehouse_name: str | None = None
    uom: str | None = None


class PaginatedAlerts(BaseModel):
    items: list[StockAlertOut]
    total: int
    offset: int
    limit: int


class KardexEntry(BaseModel):
    movement_id: str
    date: str | None
    type: str
    reference: str | None
    quantity: float
    unit_cost: float
    balance: float
    value: float | None
