"""Goods Receipt Note (GRN) — formal document recording PO receipt with discrepancies."""
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean, Date, DateTime, ForeignKey, Index, Numeric, String, Text,
    UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.purchase_order import PurchaseOrder, PurchaseOrderLine
    from app.db.models.entity import Product


class GoodsReceipt(Base):
    __tablename__ = "goods_receipts"

    id:                Mapped[str]      = mapped_column(String(36), primary_key=True)
    tenant_id:         Mapped[str]      = mapped_column(String(255), nullable=False)
    grn_number:        Mapped[str]      = mapped_column(String(50), nullable=False)
    purchase_order_id: Mapped[str]      = mapped_column(
        String(36), ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False
    )
    receipt_date:      Mapped[Date]     = mapped_column(Date, nullable=False)
    received_by:       Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes:             Mapped[str | None] = mapped_column(Text, nullable=True)
    has_discrepancy:   Mapped[bool]     = mapped_column(Boolean, nullable=False, server_default="false")
    attachments:       Mapped[list | None] = mapped_column(JSONB, nullable=True, server_default="[]")
    created_at:        Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:        Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    purchase_order: Mapped["PurchaseOrder"] = relationship("PurchaseOrder", foreign_keys=[purchase_order_id])
    lines:          Mapped[list["GoodsReceiptLine"]] = relationship(
        "GoodsReceiptLine", back_populates="grn", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "grn_number", name="uq_grn_tenant_number"),
        Index("ix_goods_receipts_tenant_po", "tenant_id", "purchase_order_id"),
    )


class GoodsReceiptLine(Base):
    __tablename__ = "goods_receipt_lines"

    id:           Mapped[str]     = mapped_column(String(36), primary_key=True)
    tenant_id:    Mapped[str]     = mapped_column(String(255), nullable=False, index=True)
    grn_id:       Mapped[str]     = mapped_column(
        String(36), ForeignKey("goods_receipts.id", ondelete="CASCADE"), nullable=False
    )
    po_line_id:   Mapped[str]     = mapped_column(
        String(36), ForeignKey("purchase_order_lines.id", ondelete="RESTRICT"), nullable=False
    )
    product_id:   Mapped[str]     = mapped_column(
        String(36), ForeignKey("entities.id", ondelete="RESTRICT"), nullable=False
    )
    qty_expected: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    qty_received: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    qty_discrepancy: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, server_default="0")
    batch_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    discrepancy_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes:        Mapped[str | None] = mapped_column(Text, nullable=True)

    grn:     Mapped[GoodsReceipt] = relationship("GoodsReceipt", back_populates="lines")
    product: Mapped["Product"]    = relationship("Product")

    __table_args__ = (
        Index("ix_grn_lines_grn", "grn_id"),
        Index("ix_grn_lines_po_line", "po_line_id"),
    )
