"""WM material-master schemas (SAP Gestión de almacenes 1 & 2)."""
from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

from app.domain.schemas.base import OrmBase

RemovalStrategy = Literal["fifo", "fefo", "lifo", "fixed_bin"]
PutawayStrategy = Literal["manual", "fixed_bin", "next_empty", "by_section"]


class ProductWMDataIn(BaseModel):
    removal_strategy: RemovalStrategy = "fifo"
    putaway_strategy: PutawayStrategy = "manual"
    fixed_bin_id: str | None = None
    picking_storage_type_id: str | None = None
    wm_uom: str | None = None
    lot_managed: bool = False
    serial_managed: bool = False
    hazmat: bool = False
    gs1_enabled: bool = False
    storage_unit_type_id: str | None = None
    units_per_storage_unit: Decimal | None = None
    max_qty_per_bin: Decimal | None = None


class ProductWMDataOut(OrmBase):
    id: str
    tenant_id: str
    product_id: str
    warehouse_id: str
    removal_strategy: str
    putaway_strategy: str
    fixed_bin_id: str | None = None
    picking_storage_type_id: str | None = None
    wm_uom: str | None = None
    lot_managed: bool
    serial_managed: bool
    hazmat: bool
    gs1_enabled: bool
    storage_unit_type_id: str | None = None
    units_per_storage_unit: Decimal | None = None
    max_qty_per_bin: Decimal | None = None
