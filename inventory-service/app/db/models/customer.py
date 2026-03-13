"""Customer model for sales/dispatch side of inventory."""
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


class CustomerType(Base):
    __tablename__ = "customer_types"

    id:          Mapped[str]        = mapped_column(String(36), primary_key=True)
    tenant_id:   Mapped[str]        = mapped_column(String(255), nullable=False)
    name:        Mapped[str]        = mapped_column(String(100), nullable=False)
    slug:        Mapped[str]        = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    color:       Mapped[str]        = mapped_column(String(7), nullable=False, server_default="#6366f1")
    is_active:   Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="true")
    created_at:  Mapped[DateTime]   = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by:  Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_at:  Mapped[DateTime]   = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by:  Mapped[str | None] = mapped_column(String(255), nullable=True)

    customers: Mapped[list[Customer]] = relationship("Customer", back_populates="customer_type")

    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_customer_type_tenant_slug"),
        Index("ix_customer_types_tenant_id", "tenant_id"),
    )


class Customer(Base):
    __tablename__ = "customers"

    id:                 Mapped[str]        = mapped_column(String(36), primary_key=True)
    tenant_id:          Mapped[str]        = mapped_column(String(255), nullable=False)
    name:               Mapped[str]        = mapped_column(String(255), nullable=False)
    code:               Mapped[str]        = mapped_column(String(50), nullable=False)
    customer_type_id:   Mapped[str | None] = mapped_column(
        String(36), ForeignKey("customer_types.id", ondelete="SET NULL"), nullable=True
    )
    tax_id:             Mapped[str | None] = mapped_column(String(50), nullable=True)
    contact_name:       Mapped[str | None] = mapped_column(String(255), nullable=True)
    email:              Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone:              Mapped[str | None] = mapped_column(String(50), nullable=True)
    address:            Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    shipping_address:   Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    payment_terms_days: Mapped[int]        = mapped_column(Integer, nullable=False, server_default="30")
    credit_limit:       Mapped[int]        = mapped_column(Integer, nullable=False, server_default="0")
    discount_percent:   Mapped[int]        = mapped_column(Integer, nullable=False, server_default="0")
    is_active:          Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="true")
    notes:              Mapped[str | None] = mapped_column(Text, nullable=True)
    custom_attributes:  Mapped[dict]       = mapped_column(JSONB, nullable=False, server_default="{}")
    created_by:         Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_by:         Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at:         Mapped[DateTime]   = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:         Mapped[DateTime]   = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    customer_type: Mapped[CustomerType | None] = relationship("CustomerType", back_populates="customers")

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_customer_tenant_code"),
        Index("ix_customers_tenant_id", "tenant_id"),
    )


