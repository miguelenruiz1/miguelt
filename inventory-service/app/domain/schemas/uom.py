"""UoM schemas."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.domain.schemas.base import OrmBase


class UoMCreate(BaseModel):
    name: str = Field(..., max_length=100)
    symbol: str = Field(..., max_length=20)
    category: str = Field(..., max_length=50)
    is_base: bool = False


class UoMOut(OrmBase):
    id: str
    tenant_id: str
    name: str
    symbol: str
    category: str
    is_base: bool
    is_active: bool
    created_at: datetime


class UoMConversionCreate(BaseModel):
    from_uom_id: str
    to_uom_id: str
    factor: Decimal = Field(..., gt=0)


class UoMConversionOut(OrmBase):
    id: str
    tenant_id: str
    from_uom_id: str
    to_uom_id: str
    factor: Decimal
    is_active: bool


class ConvertRequest(BaseModel):
    quantity: Decimal
    from_uom: str
    to_uom: str


class ConvertResponse(BaseModel):
    quantity: Decimal
    from_uom: str
    to_uom: str
    result: Decimal
    factor: Decimal


class CategoryBaseChoice(BaseModel):
    category: str
    base_symbol: str


class SetupRequest(BaseModel):
    bases: list[CategoryBaseChoice]


class SetupResponse(BaseModel):
    created: int
    categories_set_up: list[str]
    skipped: list[str] = []


class ChangeBaseRequest(BaseModel):
    new_base_id: str


class ChangeBaseResponse(BaseModel):
    old_base: str
    new_base: str
    pivot: str
    affected: dict[str, int]


class StandardCategory(BaseModel):
    """Catalog entry returned to the frontend so the wizard can render options."""
    category: str
    label: str
    options: list[dict]  # [{symbol, name, suggested_default: bool}]
