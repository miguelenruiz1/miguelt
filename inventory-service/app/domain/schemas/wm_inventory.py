"""WM inventory / stock-state schemas."""
from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

from app.domain.schemas.base import OrmBase

StockType = Literal["available", "quality", "blocked", "consignment"]


class BinBlockIn(BaseModel):
    blocked_inbound: bool = True
    blocked_outbound: bool = True
    block_reason: str | None = None


class SetStockStateIn(BaseModel):
    stock_type: StockType


class StockStatusBucket(BaseModel):
    stock_type: str
    quants: int
    total_qty: Decimal


class StockStatusOut(BaseModel):
    warehouse_id: str
    buckets: list[StockStatusBucket]


class ERIOut(BaseModel):
    warehouse_id: str
    items_counted: int
    items_accurate: int
    eri_pct: float
    value_accuracy_pct: float | None = None
    target_pct: float = 98.0


class LocationStateOut(OrmBase):
    id: str
    code: str
    blocked_inbound: bool
    blocked_outbound: bool
    block_reason: str | None = None
