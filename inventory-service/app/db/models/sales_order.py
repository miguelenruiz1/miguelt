"""Sales Order models — the sell/dispatch side of inventory."""
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean, DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, Text,
    UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import SalesOrderStatus

if TYPE_CHECKING:
    from app.db.models.customer import Customer
    from app.db.models.entity import Product
    from app.db.models.tracking import EntityBatch
    from app.db.models.variant import ProductVariant
    from app.db.models.warehouse import Warehouse
    from app.db.models.tax import SalesOrderLineTax


class SalesOrder(Base):
    __tablename__ = "sales_orders"

    id:               Mapped[str]              = mapped_column(String(36), primary_key=True)
    tenant_id:        Mapped[str]              = mapped_column(String(255), nullable=False)
    order_number:     Mapped[str]              = mapped_column(String(50), nullable=False)
    customer_id:      Mapped[str]              = mapped_column(
        String(36), ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False
    )
    status:           Mapped[SalesOrderStatus] = mapped_column(
        Enum(SalesOrderStatus, native_enum=False), nullable=False, server_default="draft"
    )
    warehouse_id:     Mapped[str | None]       = mapped_column(
        String(36), ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True
    )
    shipping_address: Mapped[dict | None]      = mapped_column(JSONB, nullable=True)
    expected_date:    Mapped[DateTime | None]   = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_at:     Mapped[DateTime | None]   = mapped_column(DateTime(timezone=True), nullable=True)
    shipped_date:     Mapped[DateTime | None]   = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_date:   Mapped[DateTime | None]   = mapped_column(DateTime(timezone=True), nullable=True)
    subtotal:         Mapped[Decimal]           = mapped_column(Numeric(18, 2), nullable=False, server_default="0")
    tax_amount:       Mapped[Decimal]           = mapped_column(Numeric(18, 2), nullable=False, server_default="0")
    discount_pct:     Mapped[Decimal]           = mapped_column(Numeric(5, 2), nullable=False, server_default="0")
    discount_amount:  Mapped[Decimal]           = mapped_column(Numeric(18, 2), nullable=False, server_default="0")
    discount_reason:  Mapped[str | None]       = mapped_column(String(255), nullable=True)
    total:            Mapped[Decimal]           = mapped_column(Numeric(18, 2), nullable=False, server_default="0")
    total_retention:  Mapped[Decimal]           = mapped_column(Numeric(18, 2), nullable=False, server_default="0")
    total_with_tax:   Mapped[Decimal]           = mapped_column(Numeric(18, 2), nullable=False, server_default="0")
    total_payable:    Mapped[Decimal]           = mapped_column(Numeric(18, 2), nullable=False, server_default="0")
    currency:         Mapped[str]              = mapped_column(String(3), nullable=False, server_default="COP")
    # Export / international (added in migration 065 as raw columns; mapped now for API exposure).
    exchange_rate:       Mapped[Decimal | None] = mapped_column(Numeric(14, 6), nullable=True)
    incoterm:            Mapped[str | None]    = mapped_column(String(10), nullable=True)
    origin_country:      Mapped[str | None]    = mapped_column(String(3), nullable=True)
    destination_country: Mapped[str | None]    = mapped_column(String(3), nullable=True)
    is_international:    Mapped[bool]          = mapped_column(Boolean, nullable=False, server_default="false")
    payment_form:     Mapped[int]              = mapped_column(Integer, nullable=False, server_default="1")  # 1=Contado, 2=Crédito
    payment_method:   Mapped[int]              = mapped_column(Integer, nullable=False, server_default="10")  # 10=Efectivo
    notes:            Mapped[str | None]       = mapped_column(Text, nullable=True)
    extra_data:       Mapped[dict]             = mapped_column("extra_data", JSONB, nullable=False, server_default="{}")

    created_at:       Mapped[DateTime]         = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by:       Mapped[str | None]       = mapped_column(String(255), nullable=True)
    updated_at:       Mapped[DateTime]         = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    updated_by:       Mapped[str | None]       = mapped_column(String(255), nullable=True)

    # Electronic invoicing (DIAN)
    cufe:              Mapped[str | None]       = mapped_column(String(255), nullable=True)
    invoice_number:    Mapped[str | None]       = mapped_column(String(50), nullable=True)
    invoice_pdf_url:   Mapped[str | None]       = mapped_column(String(500), nullable=True)
    invoice_status:    Mapped[str | None]       = mapped_column(String(50), nullable=True)
    invoice_remote_id: Mapped[str | None]       = mapped_column(String(255), nullable=True)
    invoice_provider:  Mapped[str | None]       = mapped_column(String(50), nullable=True)

    # Credit note (DIAN — issued on return)
    credit_note_cufe:      Mapped[str | None]   = mapped_column(String(255), nullable=True)
    credit_note_number:    Mapped[str | None]   = mapped_column(String(50), nullable=True)
    credit_note_remote_id: Mapped[str | None]   = mapped_column(String(255), nullable=True)
    credit_note_status:    Mapped[str | None]    = mapped_column(String(50), nullable=True)
    returned_at:           Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Debit note (DIAN — issued for price adjustments)
    debit_note_cufe:       Mapped[str | None]   = mapped_column(String(255), nullable=True)
    debit_note_number:     Mapped[str | None]   = mapped_column(String(50), nullable=True)
    debit_note_remote_id:  Mapped[str | None]   = mapped_column(String(255), nullable=True)
    debit_note_status:     Mapped[str | None]   = mapped_column(String(50), nullable=True)
    debit_note_reason:     Mapped[str | None]   = mapped_column(Text, nullable=True)
    debit_note_amount:     Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)

    # Backorder support
    is_backorder:     Mapped[bool]             = mapped_column(Boolean, nullable=False, server_default="false")
    parent_so_id:     Mapped[str | None]       = mapped_column(
        String(36), ForeignKey("sales_orders.id", ondelete="SET NULL"), nullable=True
    )
    backorder_number: Mapped[int]              = mapped_column(Integer, nullable=False, server_default="0")

    # Remission (delivery note)
    remission_number:       Mapped[str | None]       = mapped_column(String(50), nullable=True)
    remission_generated_at: Mapped[DateTime | None]   = mapped_column(DateTime(timezone=True), nullable=True)

    # Approval workflow
    approval_required:      Mapped[bool]             = mapped_column(Boolean, nullable=False, server_default="false")
    approved_by:            Mapped[str | None]       = mapped_column(String(100), nullable=True)
    approved_at:            Mapped[DateTime | None]   = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_by:            Mapped[str | None]       = mapped_column(String(100), nullable=True)
    rejected_at:            Mapped[DateTime | None]   = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason:       Mapped[str | None]       = mapped_column(String(500), nullable=True)
    approval_requested_at:  Mapped[DateTime | None]   = mapped_column(DateTime(timezone=True), nullable=True)

    customer:  Mapped[Customer]              = relationship("Customer")
    warehouse: Mapped[Warehouse | None]      = relationship("Warehouse", foreign_keys=[warehouse_id])
    lines:     Mapped[list[SalesOrderLine]]  = relationship(
        "SalesOrderLine", back_populates="order", cascade="all, delete-orphan"
    )
    parent_so: Mapped[SalesOrder | None]     = relationship(
        "SalesOrder", remote_side="SalesOrder.id", foreign_keys=[parent_so_id],
        back_populates="backorders",
    )
    backorders: Mapped[list[SalesOrder]]     = relationship(
        "SalesOrder", back_populates="parent_so", foreign_keys="SalesOrder.parent_so_id",
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "order_number", name="uq_sales_order_tenant_number"),
        Index("ix_sales_orders_tenant_id", "tenant_id"),
        Index("ix_sales_orders_customer_id", "customer_id"),
        Index("ix_sales_orders_status", "status"),
        Index("ix_sales_orders_tenant_status", "tenant_id", "status"),
        Index("ix_sales_orders_parent_so_id", "parent_so_id"),
    )


class SalesOrderLine(Base):
    __tablename__ = "sales_order_lines"

    id:            Mapped[str]     = mapped_column(String(36), primary_key=True)
    tenant_id:     Mapped[str]     = mapped_column(String(255), nullable=False, index=True)
    order_id:      Mapped[str]     = mapped_column(
        String(36), ForeignKey("sales_orders.id", ondelete="CASCADE"), nullable=False
    )
    product_id:    Mapped[str]     = mapped_column(
        String(36), ForeignKey("entities.id", ondelete="RESTRICT"), nullable=False
    )
    variant_id:    Mapped[str | None] = mapped_column(
        String(36), ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True
    )
    batch_id:      Mapped[str | None] = mapped_column(
        String(36), ForeignKey("entity_batches.id", ondelete="SET NULL"), nullable=True, index=True
    )
    warehouse_id:  Mapped[str | None] = mapped_column(
        String(36), ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True
    )
    qty_ordered:       Mapped[Decimal]        = mapped_column(Numeric(18, 4), nullable=False)
    qty_shipped:       Mapped[Decimal]        = mapped_column(Numeric(18, 4), nullable=False, server_default="0")
    original_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    unit_price:        Mapped[Decimal]        = mapped_column(Numeric(18, 4), nullable=False)
    original_unit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    discount_pct:      Mapped[Decimal]        = mapped_column(Numeric(5, 2), nullable=False, server_default="0")
    discount_amount:   Mapped[Decimal]        = mapped_column(Numeric(18, 4), nullable=False, server_default="0")
    line_subtotal:     Mapped[Decimal]        = mapped_column(Numeric(18, 4), nullable=False, server_default="0")
    tax_rate:          Mapped[Decimal]        = mapped_column(Numeric(5, 2), nullable=False, server_default="0")
    tax_rate_id:       Mapped[str | None]     = mapped_column(
        String(36), ForeignKey("tax_rates.id", ondelete="SET NULL"), nullable=True
    )
    tax_rate_pct:      Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    tax_amount:        Mapped[Decimal]        = mapped_column(Numeric(14, 4), nullable=False, server_default="0")
    retention_pct:     Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    retention_amount:  Mapped[Decimal]        = mapped_column(Numeric(14, 4), nullable=False, server_default="0")
    line_total_with_tax: Mapped[Decimal]      = mapped_column(Numeric(14, 4), nullable=False, server_default="0")
    line_total:        Mapped[Decimal]        = mapped_column(Numeric(18, 2), nullable=False, server_default="0")
    notes:             Mapped[str | None]     = mapped_column(Text, nullable=True)
    uom:               Mapped[str | None]     = mapped_column(String(20), nullable=True)
    qty_in_base_uom:   Mapped[Decimal | None] = mapped_column(Numeric(15, 6), nullable=True)
    margin_pct:        Mapped[Decimal | None] = mapped_column(Numeric(7, 4), nullable=True)
    backorder_line_id: Mapped[str | None]     = mapped_column(
        String(36), ForeignKey("sales_order_lines.id", ondelete="SET NULL"), nullable=True
    )
    price_source:      Mapped[str | None]     = mapped_column(String(20), nullable=True)
    customer_price_id: Mapped[str | None]     = mapped_column(
        String(36), ForeignKey("customer_prices.id", ondelete="SET NULL"), nullable=True
    )

    order:     Mapped[SalesOrder]          = relationship("SalesOrder", back_populates="lines")
    product:   Mapped[Product]             = relationship("Product")
    variant:   Mapped[ProductVariant | None] = relationship("ProductVariant")
    batch:     Mapped[EntityBatch | None]  = relationship("EntityBatch", lazy="noload")
    warehouse: Mapped[Warehouse | None]    = relationship("Warehouse", lazy="joined")
    line_taxes: Mapped[list["SalesOrderLineTax"]] = relationship(
        "SalesOrderLineTax", back_populates="line", cascade="all, delete-orphan", lazy="selectin",
    )

    __table_args__ = (
        Index("ix_sales_order_lines_order_id", "order_id"),
    )


class SOApprovalLog(Base):
    __tablename__ = "so_approval_logs"

    id:                 Mapped[str]              = mapped_column(String(36), primary_key=True)
    tenant_id:          Mapped[str]              = mapped_column(String(255), nullable=False)
    sales_order_id:     Mapped[str]              = mapped_column(
        String(36), ForeignKey("sales_orders.id", ondelete="CASCADE"), nullable=False
    )
    action:             Mapped[str]              = mapped_column(String(20), nullable=False)
    performed_by:       Mapped[str]              = mapped_column(String(100), nullable=False)
    performed_by_name:  Mapped[str | None]       = mapped_column(String(200), nullable=True)
    reason:             Mapped[str | None]       = mapped_column(String(500), nullable=True)
    so_total_at_action: Mapped[Decimal]          = mapped_column(Numeric(18, 2), nullable=False, server_default="0")
    created_at:         Mapped[DateTime]         = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_approval_log_so", "sales_order_id"),
    )


class TenantInventoryConfig(Base):
    __tablename__ = "tenant_inventory_configs"

    id:                     Mapped[str]              = mapped_column(String(36), primary_key=True)
    tenant_id:              Mapped[str]              = mapped_column(String(255), nullable=False, unique=True)
    so_approval_threshold:  Mapped[Decimal | None]   = mapped_column(Numeric(18, 2), nullable=True)
    margin_target_global:         Mapped[Decimal]    = mapped_column(Numeric(5, 2), nullable=False, server_default="35.00")
    margin_minimum_global:        Mapped[Decimal]    = mapped_column(Numeric(5, 2), nullable=False, server_default="20.00")
    margin_cost_method_global:    Mapped[str]        = mapped_column(String(20), nullable=False, server_default="last_purchase")
    below_minimum_requires_auth:  Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="true")

    # ── Feature toggles ──────────────────────────────────────────────────
    feature_lotes:           Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    feature_seriales:        Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    feature_variantes:       Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    feature_conteo:          Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    feature_escaner:         Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    feature_picking:         Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    feature_eventos:         Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    feature_kardex:          Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    feature_precios:         Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    feature_aprobaciones:    Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    created_at:             Mapped[DateTime]         = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:             Mapped[DateTime]         = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
