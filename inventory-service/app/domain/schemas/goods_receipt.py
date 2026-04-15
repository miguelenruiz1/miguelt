"""Goods Receipt Note (GRN) schemas."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.domain.schemas.base import OrmBase


class GRNLineCreate(BaseModel):
    po_line_id: str
    qty_received: Decimal = Field(..., gt=0)
    batch_number: str | None = None
    discrepancy_reason: str | None = None
    notes: str | None = None


class GRNCreate(BaseModel):
    receipt_date: date
    notes: str | None = None
    attachments: list[dict] | None = None
    lines: list[GRNLineCreate] = Field(..., min_length=1)


class GRNLineOut(OrmBase):
    id: str
    po_line_id: str
    product_id: str
    qty_expected: Decimal
    qty_received: Decimal
    qty_discrepancy: Decimal
    batch_number: str | None = None
    discrepancy_reason: str | None = None
    notes: str | None = None


class GRNOut(OrmBase):
    id: str
    tenant_id: str
    grn_number: str
    purchase_order_id: str
    receipt_date: date
    received_by: str | None = None
    notes: str | None = None
    has_discrepancy: bool
    attachments: list[dict] | None = None
    created_at: datetime
    lines: list[GRNLineOut] = []
