"""Unified Business Partner schemas."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.domain.schemas.base import OrmBase
from app.utils.nit import is_valid_nit


# Matches 6-10 digits with optional single-digit DV (e.g. "900123456" or "900123456-7").
# Mirrors front-trace/src/pages/inventory/PartnerDetailPage.tsx:237 so frontend and
# backend accept/reject the same inputs.
_NIT_RE = re.compile(r"^\d{6,10}(-\d)?$")


def _validate_tax_id(v: str | None) -> str | None:
    if v is None or v == "":
        return v
    cleaned = v.replace(".", "").replace(" ", "").strip()
    if not _NIT_RE.match(cleaned):
        raise ValueError("NIT inválido (formato: 900123456-7)")
    # DV check only when user provided the check digit.
    if "-" in cleaned and not is_valid_nit(cleaned):
        raise ValueError("Dígito verificador NIT incorrecto")
    return cleaned


class PartnerCreate(BaseModel):
    name: str = Field(..., max_length=255)
    code: str = Field(..., max_length=50)
    is_supplier: bool = False
    is_customer: bool = False
    supplier_type_id: str | None = None
    customer_type_id: str | None = None
    tax_id: str | None = Field(None, max_length=50)
    contact_name: str | None = Field(None, max_length=255)
    email: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)
    address: dict[str, Any] | None = None
    shipping_address: dict[str, Any] | None = None
    credit_limit: int = 0
    discount_percent: int = 0
    lead_time_days: int = 7
    payment_terms_days: int = 30
    is_active: bool = True
    notes: str | None = None
    custom_attributes: dict[str, Any] = {}

    @field_validator("tax_id")
    @classmethod
    def _check_tax_id(cls, v: str | None) -> str | None:
        return _validate_tax_id(v)


class PartnerUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    code: str | None = Field(None, max_length=50)
    is_supplier: bool | None = None
    is_customer: bool | None = None
    supplier_type_id: str | None = None
    customer_type_id: str | None = None
    tax_id: str | None = Field(None, max_length=50)
    # DIAN: 1 = Responsable IVA, 2 = No responsable IVA
    tax_regime: int | None = None

    @field_validator("tax_id")
    @classmethod
    def _check_tax_id(cls, v: str | None) -> str | None:
        return _validate_tax_id(v)
    contact_name: str | None = Field(None, max_length=255)
    email: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)
    address: dict[str, Any] | None = None
    shipping_address: dict[str, Any] | None = None
    credit_limit: int | None = None
    discount_percent: int | None = None
    lead_time_days: int | None = None
    payment_terms_days: int | None = None
    is_active: bool | None = None
    notes: str | None = None
    custom_attributes: dict[str, Any] | None = None


class PartnerOut(OrmBase):
    id: str
    tenant_id: str
    name: str
    code: str
    is_supplier: bool
    is_customer: bool
    supplier_type_id: str | None = None
    customer_type_id: str | None = None
    tax_id: str | None = None
    tax_regime: int | None = None
    contact_name: str | None = None
    email: str | None = None
    phone: str | None = None
    address: dict[str, Any] | None = None
    shipping_address: dict[str, Any] | None = None
    credit_limit: int = 0
    discount_percent: int = 0
    lead_time_days: int = 7
    payment_terms_days: int = 30
    is_active: bool = True
    notes: str | None = None
    custom_attributes: dict[str, Any] = {}
    created_by: str | None = None
    updated_by: str | None = None
    created_at: datetime
    updated_at: datetime


class PaginatedPartners(BaseModel):
    items: list[PartnerOut]
    total: int
    offset: int
    limit: int
