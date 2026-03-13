"""Stock alert models."""
from __future__ import annotations

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class StockAlert(Base):
    __tablename__ = "stock_alerts"

    id:            Mapped[str]            = mapped_column(String(36), primary_key=True)
    tenant_id:     Mapped[str]            = mapped_column(String(255), nullable=False)
    product_id:    Mapped[str]            = mapped_column(
        String(36), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False
    )
    warehouse_id:  Mapped[str | None]     = mapped_column(
        String(36), ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True
    )
    batch_id:      Mapped[str | None]     = mapped_column(
        String(36), ForeignKey("entity_batches.id", ondelete="SET NULL"), nullable=True
    )
    alert_type:    Mapped[str]            = mapped_column(String(30), nullable=False)
    message:       Mapped[str]            = mapped_column(Text, nullable=False)
    current_qty:   Mapped[int]            = mapped_column(Integer, nullable=False, server_default="0")
    threshold_qty: Mapped[int]            = mapped_column(Integer, nullable=False, server_default="0")
    is_read:       Mapped[bool]           = mapped_column(Boolean, nullable=False, server_default="false")
    is_resolved:   Mapped[bool]           = mapped_column(Boolean, nullable=False, server_default="false")
    created_at:    Mapped[DateTime]       = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at:   Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_stock_alerts_tenant_id", "tenant_id"),
        Index("ix_stock_alerts_product_id", "product_id"),
        Index("ix_stock_alerts_is_resolved", "is_resolved"),
        Index("ix_stock_alerts_batch_id", "batch_id"),
    )
