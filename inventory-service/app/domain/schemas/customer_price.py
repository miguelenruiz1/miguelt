"""Schemas for customer special pricing."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, model_validator
from sqlalchemy.orm import InstanceState

from app.domain.schemas.base import OrmBase


def _loaded_rel(obj: Any, attr: str) -> Any | None:
    state: InstanceState | None = getattr(obj, "_sa_instance_state", None)
    if state is None:
        return getattr(obj, attr, None)
    return state.dict.get(attr)


class CustomerPriceCreate(BaseModel):
    customer_id: str
    product_id: str
    variant_id: str | None = None
    price: float
    min_quantity: float = 1.0
    currency: str = "COP"
    valid_from: date | None = None
    valid_to: date | None = None
    reason: str | None = None


class CustomerPriceHistoryOut(OrmBase):
    id: str
    tenant_id: str
    customer_price_id: str
    customer_id: str
    product_id: str
    old_price: float | None = None
    new_price: float
    changed_by: str
    changed_by_name: str | None = None
    reason: str | None = None
    changed_at: datetime | None = None


class CustomerPriceOut(OrmBase):
    id: str
    tenant_id: str
    customer_id: str
    product_id: str
    variant_id: str | None = None
    price: float
    min_quantity: float
    currency: str
    valid_from: date
    valid_to: date | None = None
    reason: str | None = None
    is_active: bool
    created_by: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    customer_name: str | None = None
    product_name: str | None = None
    product_sku: str | None = None
    variant_name: str | None = None
    variant_sku: str | None = None
    base_price: float | None = None

    @model_validator(mode="before")
    @classmethod
    def _resolve_relations(cls, data: Any) -> Any:
        customer = _loaded_rel(data, "customer")
        if customer is not None:
            if not getattr(data, "customer_name", None):
                data.customer_name = customer.name
        product = _loaded_rel(data, "product")
        if product is not None:
            if not getattr(data, "product_name", None):
                data.product_name = product.name
            if not getattr(data, "product_sku", None):
                data.product_sku = product.sku
        variant = _loaded_rel(data, "variant")
        if variant is not None:
            if not getattr(data, "variant_name", None):
                data.variant_name = getattr(variant, "name", None) or getattr(variant, "sku", None)
            if not getattr(data, "variant_sku", None):
                data.variant_sku = getattr(variant, "sku", None)
            # Use variant sale_price as base price when available
            variant_sale = getattr(variant, "sale_price", None)
            if variant_sale and float(variant_sale) > 0:
                data.base_price = float(variant_sale)
        # Fallback: product suggested_sale_price as base price
        if not getattr(data, "base_price", None) and product is not None:
            suggested = getattr(product, "suggested_sale_price", None)
            if suggested and float(suggested) > 0:
                data.base_price = float(suggested)
        return data


class CustomerPriceDetailOut(CustomerPriceOut):
    history: list[CustomerPriceHistoryOut] = []


class PriceLookupRequest(BaseModel):
    customer_id: str
    product_id: str
    quantity: float = 1.0
    variant_id: str | None = None


class PriceLookupResponse(BaseModel):
    price: float
    original_price: float | None = None
    source: str
    customer_price_id: str | None = None
    valid_to: str | None = None
    reason: str | None = None


class CustomerPriceMetrics(BaseModel):
    active_count: int
    expiring_soon: int
    customers_with_prices: int
