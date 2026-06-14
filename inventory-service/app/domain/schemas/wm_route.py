"""WM route / step-config schemas."""
from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.domain.schemas.base import OrmBase

Flow = Literal["inbound", "outbound", "manufacture"]


class WMConfigUpdate(BaseModel):
    receive_steps: int = Field(1, ge=1, le=3)
    deliver_steps: int = Field(1, ge=1, le=3)
    manufacture_steps: int = Field(1, ge=1, le=3)


class WMConfigOut(OrmBase):
    id: str
    tenant_id: str
    warehouse_id: str
    receive_steps: int
    deliver_steps: int
    manufacture_steps: int


class RouteRuleOut(OrmBase):
    id: str
    sequence: int
    name: str
    source_zone: str
    dest_zone: str
    operation_code: str | None = None


class RouteOut(OrmBase):
    id: str
    tenant_id: str
    warehouse_id: str
    code: str
    name: str
    flow: str
    steps: int
    is_active: bool
    rules: list[RouteRuleOut] = []


class GenerateChainLine(BaseModel):
    product_id: str
    quantity: Decimal = Field(..., gt=0)
    batch_id: str | None = None
    variant_id: str | None = None
    uom: str = "primary"


class GenerateChainIn(BaseModel):
    warehouse_id: str
    flow: Flow
    source_doc_type: str | None = None
    source_doc_id: str | None = None
    lines: list[GenerateChainLine] = Field(..., min_length=1)


class GeneratedOrder(BaseModel):
    id: str
    to_number: str
    sequence: int
    step_name: str
    source_zone: str
    dest_zone: str


class GenerateChainResult(BaseModel):
    flow: str
    steps: int
    orders: list[GeneratedOrder]
