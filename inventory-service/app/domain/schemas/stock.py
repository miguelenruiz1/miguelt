"""Stock level and movement schemas."""
from __future__ import annotations

from typing import Any
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.db.models.enums import MovementType
from app.domain.schemas.base import OrmBase


class StockProductSummary(OrmBase):
    """Lightweight product info embedded in stock level responses."""
    id: str
    sku: str
    name: str
    barcode: str | None = None
    product_type_id: str | None = None
    unit_of_measure: str = "und"
    reorder_point: int = 0


class StockLevelOut(OrmBase):
    id: str
    tenant_id: str
    product_id: str
    warehouse_id: str
    location_id: str | None = None
    location_name: str | None = None
    batch_id: str | None = None
    variant_id: str | None = None
    qty_on_hand: Decimal
    qty_reserved: Decimal
    qty_available: float | None = None  # Computed: qty_on_hand - qty_reserved
    qty_in_transit: Decimal = Decimal("0")
    qc_status: str | None = None
    reorder_point: int
    max_stock: int
    last_count_at: datetime | None
    updated_at: datetime
    product: StockProductSummary | None = None

    @model_validator(mode="before")
    @classmethod
    def _resolve_location(cls, data: Any) -> Any:
        from app.db.models.warehouse import WarehouseLocation
        loc = getattr(data, "location", None)
        if loc is not None and isinstance(loc, WarehouseLocation):
            if not getattr(data, "location_name", None):
                data.location_name = loc.name
        return data


class ReceiveStockIn(BaseModel):
    product_id: str
    warehouse_id: str
    quantity: Decimal = Field(..., gt=0)
    uom: str = "primary"
    unit_cost: Decimal | None = None
    reference: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=2000)
    batch_number: str | None = Field(default=None, max_length=100)
    variant_id: str | None = None
    location_id: str | None = None


class IssueStockIn(BaseModel):
    product_id: str
    warehouse_id: str
    quantity: Decimal = Field(..., gt=0)
    uom: str = "primary"
    reference: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=2000)
    variant_id: str | None = None


class TransferStockIn(BaseModel):
    product_id: str
    from_warehouse_id: str
    to_warehouse_id: str
    quantity: Decimal = Field(..., gt=0)
    uom: str = "primary"
    notes: str | None = Field(default=None, max_length=2000)
    variant_id: str | None = None
    from_location_id: str | None = None
    to_location_id: str | None = None


class AdjustStockIn(BaseModel):
    product_id: str
    warehouse_id: str
    new_qty: Decimal = Field(..., ge=0)
    reason: str | None = Field(default=None, max_length=500)
    variant_id: str | None = None


class ReturnStockIn(BaseModel):
    product_id: str
    warehouse_id: str
    quantity: Decimal = Field(..., gt=0)
    uom: str = "primary"
    unit_cost: Decimal | None = None
    reference: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=2000)
    variant_id: str | None = None


class AdjustInStockIn(BaseModel):
    product_id: str
    warehouse_id: str
    quantity: Decimal = Field(..., gt=0)
    uom: str = "primary"
    unit_cost: Decimal | None = None
    reason: str | None = Field(default=None, max_length=500)
    variant_id: str | None = None


class AdjustOutStockIn(BaseModel):
    product_id: str
    warehouse_id: str
    quantity: Decimal = Field(..., gt=0)
    uom: str = "primary"
    reason: str | None = Field(default=None, max_length=500)
    variant_id: str | None = None


class WasteStockIn(BaseModel):
    product_id: str
    warehouse_id: str
    quantity: Decimal = Field(..., gt=0)
    reason: str | None = Field(default=None, max_length=500)
    variant_id: str | None = None


class AssignLocationIn(BaseModel):
    location_id: str | None = None


class QCActionIn(BaseModel):
    product_id: str
    warehouse_id: str
    batch_id: str | None = None
    variant_id: str | None = None
    notes: str | None = Field(default=None, max_length=2000)


class StockMovementOut(OrmBase):
    id: str
    tenant_id: str
    movement_type: MovementType
    movement_type_id: str | None = None
    product_id: str
    variant_id: str | None = None
    batch_id: str | None = None
    from_warehouse_id: str | None
    to_warehouse_id: str | None
    quantity: Decimal
    original_qty: Decimal | None = None
    uom: str = "primary"
    unit_cost: Decimal | None
    reference: str | None
    notes: str | None
    batch_number: str | None
    performed_by: str | None
    event_id: str | None = None
    status: str = "completed"
    completed_at: datetime | None = None
    created_at: datetime


class PaginatedStockLevels(BaseModel):
    items: list[StockLevelOut]
    total: int
    offset: int
    limit: int


class PaginatedMovements(BaseModel):
    items: list[StockMovementOut]
    total: int
    offset: int
    limit: int
