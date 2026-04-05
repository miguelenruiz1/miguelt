"""Product variant models — attribute groups (size, color, etc.) and SKU variants."""
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text,
    UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.entity import Product


class VariantAttribute(Base):
    """Defines an attribute axis — e.g. 'Size', 'Color'."""
    __tablename__ = "variant_attributes"

    id:          Mapped[str]        = mapped_column(String(36), primary_key=True)
    tenant_id:   Mapped[str]        = mapped_column(String(255), nullable=False)
    name:        Mapped[str]        = mapped_column(String(100), nullable=False)
    slug:        Mapped[str]        = mapped_column(String(100), nullable=False)
    sort_order:  Mapped[int]        = mapped_column(Integer, nullable=False, server_default="0")
    is_active:   Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="true")
    created_at:  Mapped[DateTime]   = mapped_column(DateTime(timezone=True), server_default=func.now())

    options: Mapped[list[VariantAttributeOption]] = relationship(
        "VariantAttributeOption", back_populates="attribute", cascade="all, delete-orphan",
        order_by="VariantAttributeOption.sort_order",
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_variant_attr_tenant_slug"),
        Index("ix_variant_attributes_tenant_id", "tenant_id"),
    )


class VariantAttributeOption(Base):
    """A value within an attribute axis — e.g. 'Red', 'XL'."""
    __tablename__ = "variant_attribute_options"

    id:           Mapped[str]        = mapped_column(String(36), primary_key=True)
    tenant_id:    Mapped[str]        = mapped_column(String(255), nullable=False, index=True)
    attribute_id: Mapped[str]        = mapped_column(
        String(36), ForeignKey("variant_attributes.id", ondelete="CASCADE"), nullable=False
    )
    value:        Mapped[str]        = mapped_column(String(100), nullable=False)
    color_hex:    Mapped[str | None] = mapped_column(String(7), nullable=True)
    sort_order:   Mapped[int]        = mapped_column(Integer, nullable=False, server_default="0")
    is_active:    Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="true")

    attribute: Mapped[VariantAttribute] = relationship("VariantAttribute", back_populates="options")

    __table_args__ = (
        UniqueConstraint("attribute_id", "value", name="uq_variant_option_attr_value"),
    )


class ProductVariant(Base):
    """A concrete SKU variant of a parent product — e.g. 'T-Shirt Red XL'."""
    __tablename__ = "product_variants"

    id:              Mapped[str]            = mapped_column(String(36), primary_key=True)
    tenant_id:       Mapped[str]            = mapped_column(String(255), nullable=False)
    parent_id:       Mapped[str]            = mapped_column(
        String(36), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False
    )
    sku:             Mapped[str]            = mapped_column(String(100), nullable=False)
    barcode:         Mapped[str | None]     = mapped_column(String(100), nullable=True)
    name:            Mapped[str]            = mapped_column(String(255), nullable=False)
    cost_price:      Mapped[Decimal]        = mapped_column(Numeric(18, 4), nullable=False, server_default="0")
    sale_price:      Mapped[Decimal]        = mapped_column(Numeric(18, 4), nullable=False, server_default="0")
    weight:          Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    is_active:       Mapped[bool]           = mapped_column(Boolean, nullable=False, server_default="true")
    option_values:   Mapped[dict]           = mapped_column(JSONB, nullable=False, server_default="{}")
    images:          Mapped[list]           = mapped_column(JSONB, nullable=False, server_default="[]")
    created_at:      Mapped[DateTime]       = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:      Mapped[DateTime]       = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    parent: Mapped[Product] = relationship("Product")

    __table_args__ = (
        UniqueConstraint("tenant_id", "sku", name="uq_variant_tenant_sku"),
        Index("ix_product_variants_tenant_id", "tenant_id"),
        Index("ix_product_variants_parent_id", "parent_id"),
    )
