"""Pricing schemas."""
from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel

from app.domain.schemas.cost_history import ProductCostHistoryOut


class ProductPricingOut(BaseModel):
    last_purchase_cost: float | None = None
    last_purchase_date: str | None = None
    last_purchase_supplier: str | None = None
    suggested_sale_price: float | None = None
    minimum_sale_price: float | None = None
    margin_target: float | None = None
    margin_minimum: float | None = None
    margin_cost_method: str | None = None
    current_avg_cost: float | None = None
    cost_history: list[ProductCostHistoryOut] = []


class MarginUpdateIn(BaseModel):
    margin_target: Decimal | None = None
    margin_minimum: Decimal | None = None
    margin_cost_method: str | None = None


class GlobalMarginOut(BaseModel):
    margin_target_global: float
    margin_minimum_global: float
    margin_cost_method_global: str
    below_minimum_requires_auth: bool


class GlobalMarginUpdateIn(BaseModel):
    margin_target_global: Decimal | None = None
    margin_minimum_global: Decimal | None = None
    margin_cost_method_global: str | None = None
    below_minimum_requires_auth: bool | None = None
