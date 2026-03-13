"""Supplier model."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.config import SupplierType
    from app.db.models.purchase_order import PurchaseOrder


class Supplier(Base):
    __tablename__ = "suppliers"

    id:                 Mapped[str]        = mapped_column(String(36), primary_key=True)
    tenant_id:          Mapped[str]        = mapped_column(String(255), nullable=False)
    name:               Mapped[str]        = mapped_column(String(255), nullable=False)
    code:               Mapped[str]        = mapped_column(String(50), nullable=False)
    supplier_type_id:   Mapped[str | None] = mapped_column(
        String(36), ForeignKey("supplier_types.id", ondelete="SET NULL"), nullable=True
    )
    contact_name:       Mapped[str | None] = mapped_column(String(255), nullable=True)
    email:              Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone:              Mapped[str | None] = mapped_column(String(50), nullable=True)
    address:            Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    payment_terms_days: Mapped[int]        = mapped_column(Integer, nullable=False, server_default="30")
    lead_time_days:     Mapped[int]        = mapped_column(Integer, nullable=False, server_default="7")
    is_active:          Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="true")
    notes:              Mapped[str | None] = mapped_column(Text, nullable=True)
    custom_attributes:  Mapped[dict]       = mapped_column(JSONB, nullable=False, server_default="{}")
    created_by:         Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_by:         Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at:         Mapped[DateTime]   = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:         Mapped[DateTime]   = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    supplier_type:   Mapped[SupplierType | None]        = relationship("SupplierType", back_populates="suppliers")
    purchase_orders: Mapped[list[PurchaseOrder]]        = relationship("PurchaseOrder", back_populates="supplier")

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_supplier_tenant_code"),
        Index("ix_suppliers_tenant_id", "tenant_id"),
    )
