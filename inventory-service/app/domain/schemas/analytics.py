"""Analytics schemas."""
from __future__ import annotations

from pydantic import BaseModel


class MovementTrend(BaseModel):
    date: str
    count: int


class AnalyticsOverview(BaseModel):
    total_skus: int
    total_value: float
    low_stock_count: int
    out_of_stock_count: int
    pending_pos: int
    top_products: list[dict]
    low_stock_alerts: list[dict]
    movement_trend: list[MovementTrend] = []
    movements_by_type: list[dict] = []
    product_type_breakdown: list[dict] = []
    supplier_type_breakdown: list[dict] = []
    event_summary: list[dict] = []
    event_type_summary: list[dict] = []
    expiring_batches_count: int = 0
    production_runs_this_month: int = 0
    latest_ira: float | None = None
    pending_cycle_counts: int = 0
