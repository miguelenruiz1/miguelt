"""PurchaseOrder and PurchaseOrderLine models."""
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean, Date, DateTime, ForeignKey, Index, Numeric, String, Text,
    UniqueConstraint, func,
)
from sqlalchemy import Enum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import POStatus

if TYPE_CHECKING:
    from app.db.models.config import OrderType
    from app.db.models.entity import Product
    from app.db.models.supplier import Supplier
    from app.db.models.variant import ProductVariant
    from app.db.models.warehouse import Warehouse


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id:            Mapped[str]      = mapped_column(String(36), primary_key=True)
    tenant_id:     Mapped[str]      = mapped_column(String(255), nullable=False)
    po_number:     Mapped[str]      = mapped_column(String(50), nullable=False)
    supplier_id:   Mapped[str]      = mapped_column(
        String(36), ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False
    )
    status:        Mapped[POStatus] = mapped_column(
        Enum(POStatus, native_enum=False), nullable=False, server_default="draft"
    )
    warehouse_id:  Mapped[str | None] = mapped_column(
        String(36), ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True
    )
    order_type_id: Mapped[str | None]   = mapped_column(
        String(36), ForeignKey("order_types.id", ondelete="SET NULL"), nullable=True
    )
    expected_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    received_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    is_auto_generated:   Mapped[bool]        = mapped_column(Boolean, nullable=False, server_default="false")
    reorder_trigger_stock: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    notes:         Mapped[str | None]  = mapped_column(Text, nullable=True)
    attachments:   Mapped[list | None] = mapped_column(JSONB, nullable=True, server_default="[]")

    # Approval workflow
    approval_required:  Mapped[bool]            = mapped_column(Boolean, nullable=False, server_default="false")
    approved_by:        Mapped[str | None]      = mapped_column(String(255), nullable=True)
    approved_at:        Mapped[DateTime | None]  = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_reason:    Mapped[str | None]      = mapped_column(Text, nullable=True)
    rejected_by:        Mapped[str | None]      = mapped_column(String(255), nullable=True)
    rejected_at:        Mapped[DateTime | None]  = mapped_column(DateTime(timezone=True), nullable=True)

    # Send/Confirm tracking
    sent_at:            Mapped[DateTime | None]  = mapped_column(DateTime(timezone=True), nullable=True)
    sent_by:            Mapped[str | None]      = mapped_column(String(255), nullable=True)
    confirmed_at:       Mapped[DateTime | None]  = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_by:       Mapped[str | None]      = mapped_column(String(255), nullable=True)

    # Supplier invoice data (filled on receipt)
    supplier_invoice_number: Mapped[str | None]  = mapped_column(String(100), nullable=True)
    supplier_invoice_date:   Mapped[Date | None]  = mapped_column(Date, nullable=True)
    supplier_invoice_total:  Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    payment_terms:           Mapped[str | None]  = mapped_column(String(50), nullable=True)
    payment_due_date:        Mapped[Date | None]  = mapped_column(Date, nullable=True)
    related_sales_order_id:  Mapped[str | None]  = mapped_column(
        String(36), ForeignKey("sales_orders.id", ondelete="SET NULL"), nullable=True
    )

    # Consolidation
    is_consolidated:        Mapped[bool]             = mapped_column(Boolean, nullable=False, server_default="false")
    consolidated_from_ids:  Mapped[dict | None]      = mapped_column(JSONB, nullable=True)
    consolidated_at:        Mapped[DateTime | None]   = mapped_column(DateTime(timezone=True), nullable=True)
    consolidated_by:        Mapped[str | None]       = mapped_column(String(100), nullable=True)
    parent_consolidated_id: Mapped[str | None]       = mapped_column(
        String(36), ForeignKey("purchase_orders.id", ondelete="SET NULL"), nullable=True
    )

    created_by:    Mapped[str | None]  = mapped_column(String(255), nullable=True)
    updated_by:    Mapped[str | None]  = mapped_column(String(255), nullable=True)
    created_at:    Mapped[DateTime]    = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:    Mapped[DateTime]    = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    supplier:   Mapped[Supplier]               = relationship("Supplier", back_populates="purchase_orders")
    order_type: Mapped[OrderType | None]       = relationship("OrderType", back_populates="purchase_orders")
    lines:      Mapped[list[PurchaseOrderLine]] = relationship(
        "PurchaseOrderLine", back_populates="po", cascade="all, delete-orphan"
    )
    consolidated_parent: Mapped[PurchaseOrder | None] = relationship(
        "PurchaseOrder", remote_side="PurchaseOrder.id", foreign_keys=[parent_consolidated_id],
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "po_number", name="uq_po_tenant_number"),
        Index("ix_purchase_orders_tenant_id", "tenant_id"),
        Index("ix_purchase_orders_supplier_id", "supplier_id"),
        Index("ix_purchase_orders_status", "status"),
        Index("ix_purchase_orders_tenant_status", "tenant_id", "status"),
    )


class PurchaseOrderLine(Base):
    __tablename__ = "purchase_order_lines"

    id:           Mapped[str]     = mapped_column(String(36), primary_key=True)
    tenant_id:    Mapped[str]     = mapped_column(String(255), nullable=False, index=True)
    po_id:        Mapped[str]     = mapped_column(
        String(36), ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False
    )
    product_id:   Mapped[str]     = mapped_column(
        String(36), ForeignKey("entities.id", ondelete="RESTRICT"), nullable=False
    )
    variant_id:   Mapped[str | None] = mapped_column(
        String(36), ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True
    )
    qty_ordered:  Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    qty_received: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, server_default="0")
    unit_cost:    Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    line_total:   Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    location_id:  Mapped[str | None] = mapped_column(
        String(36), ForeignKey("warehouse_locations.id", ondelete="SET NULL"), nullable=True
    )
    uom:              Mapped[str | None]        = mapped_column(String(20), nullable=True)
    qty_in_base_uom:  Mapped[Decimal | None]    = mapped_column(Numeric(15, 6), nullable=True)
    notes:        Mapped[str | None] = mapped_column(Text, nullable=True)

    po:      Mapped[PurchaseOrder] = relationship("PurchaseOrder", back_populates="lines")
    product: Mapped[Product]       = relationship("Product")
    variant: Mapped[ProductVariant | None] = relationship("ProductVariant")


class POApprovalLog(Base):
    __tablename__ = "po_approval_logs"

    id:                 Mapped[str]           = mapped_column(String(36), primary_key=True)
    tenant_id:          Mapped[str]           = mapped_column(String(255), nullable=False)
    purchase_order_id:  Mapped[str]           = mapped_column(
        String(36), ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False
    )
    action:             Mapped[str]           = mapped_column(String(50), nullable=False)
    performed_by:       Mapped[str]           = mapped_column(String(255), nullable=False)
    performed_by_name:  Mapped[str | None]    = mapped_column(String(255), nullable=True)
    reason:             Mapped[str | None]    = mapped_column(Text, nullable=True)
    po_total:           Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    created_at:         Mapped[DateTime]      = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_po_approval_logs_tenant", "tenant_id"),
        Index("ix_po_approval_logs_po", "purchase_order_id"),
    )
