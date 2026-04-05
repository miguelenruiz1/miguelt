"""Customer-specific negotiated prices."""
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean, Date, DateTime, ForeignKey, Index, Numeric, String, Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.customer import Customer
    from app.db.models.entity import Product
    from app.db.models.variant import ProductVariant


class CustomerPrice(Base):
    __tablename__ = "customer_prices"

    id:            Mapped[str]              = mapped_column(String(36), primary_key=True)
    tenant_id:     Mapped[str]              = mapped_column(String(255), nullable=False)
    customer_id:   Mapped[str]              = mapped_column(String(36), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    product_id:    Mapped[str]              = mapped_column(String(36), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)
    variant_id:    Mapped[str | None]       = mapped_column(String(36), ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=True)
    price:         Mapped[Decimal]          = mapped_column(Numeric(18, 4), nullable=False)
    min_quantity:  Mapped[Decimal]          = mapped_column(Numeric(18, 4), nullable=False, server_default="1")
    currency:      Mapped[str]              = mapped_column(String(3), nullable=False, server_default="COP")
    valid_from:    Mapped[Date]             = mapped_column(Date, nullable=False)
    valid_to:      Mapped[Date | None]      = mapped_column(Date, nullable=True)
    reason:        Mapped[str | None]       = mapped_column(String(255), nullable=True)
    is_active:     Mapped[bool]             = mapped_column(Boolean, nullable=False, server_default="true")
    created_by:    Mapped[str]              = mapped_column(String(100), nullable=False)
    created_at:    Mapped[DateTime]         = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:    Mapped[DateTime]         = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    customer: Mapped[Customer]             = relationship("Customer")
    product:  Mapped[Product]              = relationship("Product")
    variant:  Mapped[ProductVariant | None] = relationship("ProductVariant")

    __table_args__ = (
        Index("ix_customer_price_lookup", "tenant_id", "customer_id", "product_id", "is_active"),
        Index("ix_customer_price_validity", "valid_from", "valid_to"),
    )


class CustomerPriceHistory(Base):
    __tablename__ = "customer_price_history"

    id:                Mapped[str]              = mapped_column(String(36), primary_key=True)
    tenant_id:         Mapped[str]              = mapped_column(String(255), nullable=False)
    customer_price_id: Mapped[str]              = mapped_column(String(36), ForeignKey("customer_prices.id", ondelete="CASCADE"), nullable=False)
    customer_id:       Mapped[str]              = mapped_column(String(36), nullable=False)
    product_id:        Mapped[str]              = mapped_column(String(36), nullable=False)
    old_price:         Mapped[Decimal | None]   = mapped_column(Numeric(18, 4), nullable=True)
    new_price:         Mapped[Decimal]          = mapped_column(Numeric(18, 4), nullable=False)
    changed_by:        Mapped[str]              = mapped_column(String(100), nullable=False)
    changed_by_name:   Mapped[str | None]       = mapped_column(String(200), nullable=True)
    reason:            Mapped[str | None]       = mapped_column(String(255), nullable=True)
    changed_at:        Mapped[DateTime]         = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_price_history_customer_product", "customer_id", "product_id"),
    )
