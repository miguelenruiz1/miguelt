"""Pydantic schemas for tax rates."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.domain.schemas.base import OrmBase


class TaxRateCreate(BaseModel):
    name: str = Field(..., max_length=100)
    tax_type: str = Field(..., pattern=r"^(iva|retention|ica)$")
    rate: Decimal = Field(..., ge=0, le=1)
    is_default: bool = False
    dian_code: str | None = Field(None, max_length=20)
    description: str | None = Field(None, max_length=255)


class TaxRateUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)
    rate: Decimal | None = Field(None, ge=0, le=1)
    is_default: bool | None = None
    is_active: bool | None = None
    dian_code: str | None = Field(None, max_length=20)
    description: str | None = Field(None, max_length=255)


class TaxRateOut(OrmBase):
    id: str
    tenant_id: str
    name: str
    tax_type: str
    rate: Decimal
    is_default: bool
    is_active: bool
    dian_code: str | None = None
    description: str | None = None
    created_at: datetime | None = None


class TaxRateSummary(BaseModel):
    default_iva: TaxRateOut | None = None
    available_iva: list[TaxRateOut] = []
    available_retention: list[TaxRateOut] = []
