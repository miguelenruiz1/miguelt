"""Product cost history — one record per PO line received."""
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.entity import Product
    from app.db.models.supplier import Supplier


class ProductCostHistory(Base):
    __tablename__ = "product_cost_history"

    id:                     Mapped[str]     = mapped_column(String(36), primary_key=True)
    tenant_id:              Mapped[str]     = mapped_column(String(255), nullable=False)
    product_id:             Mapped[str]     = mapped_column(
        String(36), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False
    )
    variant_id:             Mapped[str | None] = mapped_column(
        String(36), ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True
    )
    purchase_order_id:      Mapped[str]     = mapped_column(
        String(36), ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False
    )
    purchase_order_line_id: Mapped[str]     = mapped_column(
        String(36), ForeignKey("purchase_order_lines.id", ondelete="CASCADE"), nullable=False
    )
    supplier_id:            Mapped[str]     = mapped_column(
        String(36), ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False
    )
    supplier_name:          Mapped[str]     = mapped_column(String(255), nullable=False)

    uom_purchased:          Mapped[str]     = mapped_column(String(20), nullable=False)
    qty_purchased:          Mapped[Decimal] = mapped_column(Numeric(15, 6), nullable=False)
    qty_in_base_uom:        Mapped[Decimal] = mapped_column(Numeric(15, 6), nullable=False)
    unit_cost_purchased:    Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    unit_cost_base_uom:     Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    total_cost:             Mapped[Decimal] = mapped_column(Numeric(16, 6), nullable=False)

    market_note:            Mapped[str | None] = mapped_column(Text, nullable=True)
    received_at:            Mapped[DateTime]   = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    product:  Mapped[Product]       = relationship("Product")
    supplier: Mapped[Supplier]      = relationship("Supplier")

    __table_args__ = (
        Index("ix_cost_history_tenant_product_date", "tenant_id", "product_id", "received_at"),
        Index("ix_cost_history_supplier", "supplier_id"),
        Index("ix_cost_history_product_tenant", "product_id", "tenant_id"),
    )
