"""Schemas for sales orders."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import InstanceState
from pydantic import BaseModel, Field, model_validator

from app.domain.schemas.base import OrmBase


def _loaded_rel(obj: Any, attr: str) -> Any | None:
    """Return a relationship value ONLY if already loaded (no lazy load).

    Uses SQLAlchemy's instance state to check the dict directly,
    avoiding descriptor __get__ which would trigger a greenlet-unsafe lazy load.
    """
    state: InstanceState | None = getattr(obj, "_sa_instance_state", None)
    if state is None:
        # Not an ORM object — fall back to getattr
        return getattr(obj, attr, None)
    return state.dict.get(attr)


class SOLineCreate(BaseModel):
    product_id: str
    variant_id: str | None = None
    warehouse_id: str | None = None
    qty_ordered: float
    uom: str = "primary"
    unit_price: float | None = None
    discount_pct: float = 0.0
    tax_rate: float = 0.0
    notes: str | None = Field(default=None, max_length=2000)


class SOLineOut(OrmBase):
    id: str
    order_id: str
    product_id: str
    product_name: str | None = None
    product_sku: str | None = None
    variant_id: str | None = None
    batch_id: str | None = None
    warehouse_id: str | None = None
    warehouse_name: str | None = None
    qty_ordered: float
    qty_shipped: float
    original_quantity: float | None = None
    unit_price: float
    original_unit_price: float | None = None
    discount_pct: float
    discount_amount: float = 0.0
    line_subtotal: float = 0.0
    tax_rate: float
    tax_rate_id: str | None = None
    tax_rate_pct: float | None = None
    tax_amount: float = 0.0
    retention_pct: float | None = None
    retention_amount: float = 0.0
    line_total_with_tax: float = 0.0
    line_total: float
    notes: str | None = None
    backorder_line_id: str | None = None
    price_source: str | None = None
    customer_price_id: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _resolve_product(cls, data: Any) -> Any:
        product = _loaded_rel(data, "product")
        if product is not None:
            if not getattr(data, "product_name", None):
                data.product_name = product.name
            if not getattr(data, "product_sku", None):
                data.product_sku = product.sku
        warehouse = _loaded_rel(data, "warehouse")
        if warehouse is not None:
            if not getattr(data, "warehouse_name", None):
                data.warehouse_name = warehouse.name
        return data


class SOCreate(BaseModel):
    customer_id: str
    warehouse_id: str | None = None
    shipping_address: dict | None = None
    expected_date: datetime | None = None
    currency: str = Field(default="USD", max_length=3)
    discount_pct: float = 0.0
    discount_reason: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=2000)
    lines: list[SOLineCreate]


class SOUpdate(BaseModel):
    warehouse_id: str | None = None
    shipping_address: dict | None = None
    expected_date: datetime | None = None
    discount_pct: float | None = None
    discount_reason: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=2000)


class LineShipment(BaseModel):
    line_id: str
    qty_shipped: float
    uom: str = "primary"


class ShippingInfo(BaseModel):
    """Shipping details captured at dispatch time."""
    recipient_name: str | None = None
    recipient_phone: str | None = None
    recipient_email: str | None = None
    recipient_document: str | None = None
    address_line: str | None = None
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None
    country: str | None = None
    shipping_method: str | None = None
    carrier: str | None = None
    tracking_number: str | None = None
    photo_url: str | None = None
    shipping_notes: str | None = None


class ShipRequest(BaseModel):
    line_shipments: list[LineShipment] | None = None
    shipping_info: ShippingInfo | None = None


class SOOut(OrmBase):
    id: str
    tenant_id: str
    order_number: str
    customer_id: str
    customer_name: str | None = None
    status: str
    warehouse_id: str | None = None
    warehouse_name: str | None = None
    shipping_address: dict | None = None
    expected_date: datetime | None = None
    confirmed_at: datetime | None = None
    shipped_date: datetime | None = None
    delivered_date: datetime | None = None
    subtotal: float
    tax_amount: float
    discount_pct: float = 0.0
    discount_amount: float
    discount_reason: str | None = None
    total: float
    total_retention: float = 0.0
    total_with_tax: float = 0.0
    total_payable: float = 0.0
    currency: str
    notes: str | None = None
    shipping_info: dict | None = None
    cufe: str | None = None
    invoice_number: str | None = None
    invoice_pdf_url: str | None = None
    invoice_status: str | None = None
    invoice_remote_id: str | None = None
    invoice_provider: str | None = None
    credit_note_cufe: str | None = None
    credit_note_number: str | None = None
    credit_note_remote_id: str | None = None
    credit_note_status: str | None = None
    returned_at: datetime | None = None
    remission_number: str | None = None
    remission_generated_at: datetime | None = None
    approval_required: bool = False
    approved_by: str | None = None
    approved_at: datetime | None = None
    rejected_by: str | None = None
    rejected_at: datetime | None = None
    rejection_reason: str | None = None
    approval_requested_at: datetime | None = None
    is_backorder: bool = False
    parent_so_id: str | None = None
    backorder_number: int = 0
    backorder_ids: list[str] = []
    lines: list[SOLineOut] = []
    created_at: datetime | None = None
    created_by: str | None = None
    updated_at: datetime | None = None
    updated_by: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _resolve_relations(cls, data: Any) -> Any:
        customer = _loaded_rel(data, "customer")
        if customer is not None:
            if not getattr(data, "customer_name", None):
                data.customer_name = customer.name
        warehouse = _loaded_rel(data, "warehouse")
        if warehouse is not None:
            if not getattr(data, "warehouse_name", None):
                data.warehouse_name = warehouse.name
        # Extract shipping_info from extra_data JSONB
        meta = getattr(data, "extra_data", None)
        if isinstance(meta, dict) and "shipping_info" in meta:
            if not getattr(data, "shipping_info", None):
                data.shipping_info = meta["shipping_info"]
        # Resolve backorder IDs from relationship
        backorders = _loaded_rel(data, "backorders")
        if backorders and not getattr(data, "backorder_ids", None):
            data.backorder_ids = [bo.id for bo in backorders]
        return data


class PaginatedSOs(BaseModel):
    items: list[SOOut]
    total: int
    offset: int
    limit: int


class StockCheckLine(BaseModel):
    line_id: str
    product_name: str
    warehouse_name: str
    required: float
    available: float
    sufficient: bool


class StockCheckResult(BaseModel):
    ready_to_ship: bool
    lines: list[StockCheckLine]


class LineWarehouseUpdate(BaseModel):
    warehouse_id: str


class SODiscountUpdate(BaseModel):
    discount_pct: float
    discount_reason: str | None = None


class BackorderLinePreview(BaseModel):
    product_name: str
    product_sku: str | None = None
    warehouse_name: str | None = None
    qty_ordered: float
    qty_confirmable: float
    qty_backordered: float


class BackorderPreview(BaseModel):
    """Returned when confirm detects insufficient stock and creates a backorder."""
    has_backorder: bool = False
    lines: list[BackorderLinePreview] = []


class ConfirmWithBackorderOut(BaseModel):
    """Response from confirm endpoint when a backorder is auto-created."""
    order: SOOut
    backorder: SOOut | None = None
    split_preview: BackorderPreview


class StockReservationOut(OrmBase):
    id: str
    sales_order_id: str
    sales_order_line_id: str
    product_id: str
    product_name: str | None = None
    product_sku: str | None = None
    variant_id: str | None = None
    warehouse_id: str
    warehouse_name: str | None = None
    quantity: float
    status: str
    reserved_at: datetime | None = None
    released_at: datetime | None = None
    released_reason: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _resolve_names(cls, data: Any) -> Any:
        product = _loaded_rel(data, "product")
        if product is not None:
            if not getattr(data, "product_name", None):
                data.product_name = product.name
            if not getattr(data, "product_sku", None):
                data.product_sku = product.sku
        warehouse = _loaded_rel(data, "warehouse")
        if warehouse is not None:
            if not getattr(data, "warehouse_name", None):
                data.warehouse_name = warehouse.name
        return data


class SOApprovalLogOut(BaseModel):
    id: str
    tenant_id: str
    sales_order_id: str
    action: str
    performed_by: str
    performed_by_name: str | None = None
    reason: str | None = None
    so_total_at_action: float
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class RejectRequest(BaseModel):
    reason: str


class ApprovalThresholdUpdate(BaseModel):
    threshold: float | None = None


class ApprovalThresholdOut(BaseModel):
    tenant_id: str
    so_approval_threshold: float | None = None
