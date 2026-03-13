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
    reorder_trigger_stock: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    notes:         Mapped[str | None]  = mapped_column(Text, nullable=True)

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
    qty_ordered:  Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    qty_received: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, server_default="0")
    unit_cost:    Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    line_total:   Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    location_id:  Mapped[str | None] = mapped_column(
        String(36), ForeignKey("warehouse_locations.id", ondelete="SET NULL"), nullable=True
    )
    notes:        Mapped[str | None] = mapped_column(Text, nullable=True)

    po:      Mapped[PurchaseOrder] = relationship("PurchaseOrder", back_populates="lines")
    product: Mapped[Product]       = relationship("Product")
    variant: Mapped[ProductVariant | None] = relationship("ProductVariant")
