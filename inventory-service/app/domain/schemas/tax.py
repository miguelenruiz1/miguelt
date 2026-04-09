"""Pydantic schemas for tax categories, rates and line taxes."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.domain.schemas.base import OrmBase


# ── Tax categories ─────────────────────────────────────────────────────────

TaxBehavior = Literal["addition", "withholding"]
TaxBaseKind = Literal["subtotal", "subtotal_with_other_additions"]


class TaxCategoryCreate(BaseModel):
    slug: str = Field(..., min_length=1, max_length=50, pattern=r"^[a-z0-9_-]+$")
    name: str = Field(..., min_length=1, max_length=100)
    behavior: TaxBehavior
    base_kind: TaxBaseKind = "subtotal"
    description: str | None = Field(None, max_length=2000)
    color: str | None = Field(None, max_length=20)
    sort_order: int = 0


class TaxCategoryUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    behavior: TaxBehavior | None = None
    base_kind: TaxBaseKind | None = None
    description: str | None = Field(None, max_length=2000)
    color: str | None = Field(None, max_length=20)
    sort_order: int | None = None
    is_active: bool | None = None


class TaxCategoryOut(OrmBase):
    id: str
    tenant_id: str
    slug: str
    name: str
    behavior: TaxBehavior
    base_kind: TaxBaseKind
    description: str | None = None
    color: str | None = None
    sort_order: int
    is_system: bool
    is_active: bool
    rate_count: int = 0
    created_at: datetime | None = None


# ── Tax rates ──────────────────────────────────────────────────────────────


class TaxRateCreate(BaseModel):
    """Create a tax rate. Either category_id or category_slug must be provided.

    `tax_type` is kept as legacy fallback — if neither category field is set
    and tax_type is, the service tries to look up an existing category by slug.
    """
    name: str = Field(..., min_length=1, max_length=100)
    rate: Decimal = Field(..., ge=0, le=1)
    category_id: str | None = None
    category_slug: str | None = None
    tax_type: str | None = None  # legacy
    is_default: bool = False
    dian_code: str | None = Field(None, max_length=20)
    description: str | None = Field(None, max_length=255)


class TaxRateUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)
    rate: Decimal | None = Field(None, ge=0, le=1)
    category_id: str | None = None
    is_default: bool | None = None
    is_active: bool | None = None
    dian_code: str | None = Field(None, max_length=20)
    description: str | None = Field(None, max_length=255)


class TaxRateOut(OrmBase):
    id: str
    tenant_id: str
    name: str
    tax_type: str
    category_id: str | None = None
    category: TaxCategoryOut | None = None
    rate: Decimal
    is_default: bool
    is_active: bool
    dian_code: str | None = None
    description: str | None = None
    created_at: datetime | None = None


class TaxRateSummary(BaseModel):
    """Legacy summary used by old endpoints. Kept for backwards compat."""
    default_iva: TaxRateOut | None = None
    available_iva: list[TaxRateOut] = []
    available_retention: list[TaxRateOut] = []


# ── Sales-order line taxes (multi-stack) ───────────────────────────────────


class LineTaxIn(BaseModel):
    """Tax to apply to a sales order line. Sent by the frontend when creating
    or updating a line — the service will compute base_amount and tax_amount.
    """
    tax_rate_id: str


class LineTaxOut(OrmBase):
    id: str
    tax_rate_id: str
    rate_pct: Decimal
    base_amount: Decimal
    tax_amount: Decimal
    behavior: TaxBehavior
    rate_name: str | None = None
    category_name: str | None = None
    category_slug: str | None = None
