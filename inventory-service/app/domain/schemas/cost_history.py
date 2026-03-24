"""Cost history schemas."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.domain.schemas.base import OrmBase


class ProductCostHistoryOut(OrmBase):
    id: str
    tenant_id: str
    product_id: str
    variant_id: str | None = None
    purchase_order_id: str
    purchase_order_line_id: str
    supplier_id: str
    supplier_name: str
    uom_purchased: str
    qty_purchased: Decimal
    qty_in_base_uom: Decimal
    unit_cost_purchased: Decimal
    unit_cost_base_uom: Decimal
    total_cost: Decimal
    market_note: str | None = None
    received_at: datetime


class PaginatedCostHistory(BaseModel):
    items: list[ProductCostHistoryOut]
    total: int
