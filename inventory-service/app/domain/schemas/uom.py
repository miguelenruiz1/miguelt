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
