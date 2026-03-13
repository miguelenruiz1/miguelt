"""Schemas for customers, customer types, and price lists."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.schemas.base import OrmBase


# ── Customer Types ──────────────────────────────────────────────────
class CustomerTypeCreate(BaseModel):
    name: str
    slug: str
    description: str | None = None
    color: str = "#6366f1"
    is_active: bool = True


class CustomerTypeUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    description: str | None = None
    color: str | None = None
    is_active: bool | None = None


class CustomerTypeOut(OrmBase):
    id: str
    tenant_id: str
    name: str
    slug: str
    description: str | None = None
    color: str
    is_active: bool
    created_at: datetime | None = None


# ── Customers ───────────────────────────────────────────────────────
class CustomerCreate(BaseModel):
    name: str = Field(..., max_length=255)
    code: str = Field(..., max_length=50)
    customer_type_id: str | None = None
    tax_id: str | None = Field(default=None, max_length=50)
    contact_name: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    address: dict | None = None
    shipping_address: dict | None = None
    payment_terms_days: int = 30
    credit_limit: int = 0
    discount_percent: int = 0
    is_active: bool = True
    notes: str | None = Field(default=None, max_length=2000)
    custom_attributes: dict = {}


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    code: str | None = Field(default=None, max_length=50)
    customer_type_id: str | None = None
    tax_id: str | None = Field(default=None, max_length=50)
    contact_name: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    address: dict | None = None
    shipping_address: dict | None = None
    payment_terms_days: int | None = None
    credit_limit: int | None = None
    discount_percent: int | None = None
    is_active: bool | None = None
    notes: str | None = Field(default=None, max_length=2000)
    custom_attributes: dict | None = None


class CustomerOut(OrmBase):
    id: str
    tenant_id: str
    name: str
    code: str
    customer_type_id: str | None = None
    tax_id: str | None = None
    contact_name: str | None = None
    email: str | None = None
    phone: str | None = None
    address: dict | None = None
    shipping_address: dict | None = None
    payment_terms_days: int
    credit_limit: int
    discount_percent: int
    is_active: bool
    notes: str | None = None
    custom_attributes: dict = {}
    created_by: str | None = None
    updated_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class PaginatedCustomers(BaseModel):
    items: list[CustomerOut]
    total: int
    offset: int
    limit: int
