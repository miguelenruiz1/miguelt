"""Supplier schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.domain.schemas.base import OrmBase


class SupplierCreate(BaseModel):
    name: str = Field(..., max_length=255)
    code: str = Field(..., max_length=50)
    supplier_type_id: str | None = None
    contact_name: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    address: dict[str, Any] | None = None
    payment_terms_days: int = 30
    lead_time_days: int = 7
    is_active: bool = True
    notes: str | None = Field(default=None, max_length=2000)
    custom_attributes: dict[str, Any] = {}
    origin_plot_id: str | None = Field(default=None, max_length=36)
    origin_plot_code: str | None = Field(default=None, max_length=64)


class SupplierUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    code: str | None = Field(default=None, max_length=50)
    supplier_type_id: str | None = None
    contact_name: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    address: dict[str, Any] | None = None
    payment_terms_days: int | None = None
    lead_time_days: int | None = None
    is_active: bool | None = None
    notes: str | None = Field(default=None, max_length=2000)
    custom_attributes: dict[str, Any] | None = None
    origin_plot_id: str | None = Field(default=None, max_length=36)
    origin_plot_code: str | None = Field(default=None, max_length=64)


class SupplierOut(OrmBase):
    id: str
    tenant_id: str
    name: str
    code: str
    supplier_type_id: str | None
    contact_name: str | None
    email: str | None
    phone: str | None
    address: dict[str, Any] | None
    payment_terms_days: int
    lead_time_days: int
    is_active: bool
    notes: str | None
    custom_attributes: dict[str, Any]
    origin_plot_id: str | None = None
    origin_plot_code: str | None = None
    created_by: str | None = None
    updated_by: str | None = None
    created_at: datetime
    updated_at: datetime


class PaginatedSuppliers(BaseModel):
    items: list[SupplierOut]
    total: int
    offset: int
    limit: int
