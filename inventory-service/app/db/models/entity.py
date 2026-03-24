"""Entity (Product) model."""
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
    from app.db.models.category import Category
    from app.db.models.config import ProductType
    from app.db.models.stock import StockLevel, StockMovement
    from app.db.models.supplier import Supplier


class Product(Base):
    __tablename__ = "entities"

    id:               Mapped[str]        = mapped_column(String(36), primary_key=True)
    tenant_id:        Mapped[str]        = mapped_column(String(255), nullable=False)
    sku:              Mapped[str]        = mapped_column(String(100), nullable=False)
    barcode:          Mapped[str | None] = mapped_column(String(100), nullable=True)
    name:             Mapped[str]        = mapped_column(String(255), nullable=False)
    description:      Mapped[str | None] = mapped_column(Text, nullable=True)
    unit_of_measure:  Mapped[str]        = mapped_column(String(50), nullable=False, server_default="un")
    is_active:        Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="true")
    track_batches:    Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="false")
    min_stock_level:  Mapped[int]        = mapped_column(Integer, nullable=False, server_default="0")
    reorder_point:    Mapped[int]        = mapped_column(Integer, nullable=False, server_default="0")
    reorder_quantity: Mapped[int]        = mapped_column(Integer, nullable=False, server_default="1")
    preferred_supplier_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True
    )
    auto_reorder:     Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="false")
    valuation_method: Mapped[str]        = mapped_column(String(20), nullable=False, server_default="weighted_average")

    # ── Dynamic pricing ──────────────────────────────────────────────────
    margin_target:          Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    margin_minimum:         Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    margin_cost_method:     Mapped[str]            = mapped_column(String(20), nullable=False, server_default="last_purchase")
    last_purchase_cost:     Mapped[Decimal | None] = mapped_column(Numeric(14, 6), nullable=True)
    last_purchase_date:     Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_purchase_supplier: Mapped[str | None]     = mapped_column(String(255), nullable=True)
    suggested_sale_price:   Mapped[Decimal | None] = mapped_column(Numeric(14, 6), nullable=True)
    minimum_sale_price:     Mapped[Decimal | None] = mapped_column(Numeric(14, 6), nullable=True)
    preferred_currency:     Mapped[str]            = mapped_column(String(3), nullable=False, server_default="COP")

    product_type_id:  Mapped[str | None] = mapped_column(
        String(36), ForeignKey("product_types.id", ondelete="SET NULL"), nullable=True
    )
    category_id:      Mapped[str | None] = mapped_column(
        String(36), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    tax_rate_id:      Mapped[str | None] = mapped_column(
        String(36), ForeignKey("tax_rates.id", ondelete="SET NULL"), nullable=True
    )
    is_tax_exempt:    Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="false")
    retention_rate:   Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    images:           Mapped[list]       = mapped_column(JSONB, nullable=False, server_default="[]")
    attributes:       Mapped[dict]       = mapped_column(JSONB, nullable=False, server_default="{}")
    created_at:       Mapped[DateTime]   = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by:       Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_by:       Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_at:       Mapped[DateTime]   = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    category:           Mapped[Category | None]                  = relationship("Category")
    product_type:       Mapped[ProductType | None]              = relationship("ProductType", back_populates="products")
    preferred_supplier: Mapped[Supplier | None]                = relationship("Supplier", foreign_keys=[preferred_supplier_id])
    stock_levels:       Mapped[list[StockLevel]]               = relationship("StockLevel", back_populates="product")
    movements:        Mapped[list[StockMovement]]             = relationship("StockMovement", back_populates="product")
    __table_args__ = (
        UniqueConstraint("tenant_id", "sku", name="uq_product_tenant_sku"),
        Index("ix_entities_tenant_id", "tenant_id"),
    )
