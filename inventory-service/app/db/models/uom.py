"""Unit of Measure models."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UnitOfMeasure(Base):
    __tablename__ = "units_of_measure"

    id:        Mapped[str]  = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str]  = mapped_column(String(255), nullable=False)
    name:      Mapped[str]  = mapped_column(String(100), nullable=False)
    symbol:    Mapped[str]  = mapped_column(String(20), nullable=False)
    category:  Mapped[str]  = mapped_column(String(50), nullable=False)
    is_base:   Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "symbol", name="uq_uom_tenant_symbol"),
        Index("ix_uom_tenant_id", "tenant_id"),
    )


class UoMConversion(Base):
    __tablename__ = "uom_conversions"

    id:          Mapped[str]     = mapped_column(String(36), primary_key=True)
    tenant_id:   Mapped[str]     = mapped_column(String(255), nullable=False)
    from_uom_id: Mapped[str]     = mapped_column(
        String(36), ForeignKey("units_of_measure.id", ondelete="CASCADE"), nullable=False
    )
    to_uom_id:   Mapped[str]     = mapped_column(
        String(36), ForeignKey("units_of_measure.id", ondelete="CASCADE"), nullable=False
    )
    factor:      Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    is_active:   Mapped[bool]    = mapped_column(Boolean, nullable=False, server_default="true")

    from_uom: Mapped[UnitOfMeasure] = relationship("UnitOfMeasure", foreign_keys=[from_uom_id])
    to_uom:   Mapped[UnitOfMeasure] = relationship("UnitOfMeasure", foreign_keys=[to_uom_id])

    __table_args__ = (
        UniqueConstraint("tenant_id", "from_uom_id", "to_uom_id", name="uq_uom_conv_tenant_from_to"),
        Index("ix_uom_conv_tenant_id", "tenant_id"),
    )
