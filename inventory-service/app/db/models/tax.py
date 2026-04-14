"""Tax models — administrable categories + multi-stack line taxes.

Architecture:
- TaxCategory: tenant-managed catalog of tax kinds (IVA, IRPF, ICMS, IPI, ...).
  Each category declares a `behavior` ('addition' adds to total, 'withholding'
  subtracts from payable) and a `base_kind` ('subtotal' or
  'subtotal_with_other_additions' for cumulative taxes like Brazil's IPI).
- TaxRate: a specific percentage under a category. e.g. category="IVA" might
  have rates 19%, 5%, 0%.
- SalesOrderLineTax: applied tax on a specific SO line. N rows per line,
  enabling multi-stack taxation (Brazil ICMS+IPI+PIS+COFINS+ISS, etc).
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text,
    UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.sales_order import SalesOrderLine


class TaxCategory(Base):
    __tablename__ = "tax_categories"

    id:           Mapped[str]            = mapped_column(String(36), primary_key=True)
    tenant_id:    Mapped[str]            = mapped_column(String(255), nullable=False)
    slug:         Mapped[str]            = mapped_column(String(50), nullable=False)
    name:         Mapped[str]            = mapped_column(String(100), nullable=False)
    # 'addition' (suma al total) | 'withholding' (resta del pagar)
    behavior:     Mapped[str]            = mapped_column(String(20), nullable=False)
    # 'subtotal' (default) | 'subtotal_with_other_additions' (Brazil IPI)
    base_kind:    Mapped[str]            = mapped_column(String(40), nullable=False, server_default="subtotal")
    description:  Mapped[str | None]     = mapped_column(Text, nullable=True)
    color:        Mapped[str | None]     = mapped_column(String(20), nullable=True)
    sort_order:   Mapped[int]            = mapped_column(Integer, nullable=False, server_default="0")
    is_system:    Mapped[bool]           = mapped_column(Boolean, nullable=False, server_default="false")
    is_active:    Mapped[bool]           = mapped_column(Boolean, nullable=False, server_default="true")
    created_at:   Mapped[datetime]       = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at:   Mapped[datetime]       = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    rates: Mapped[list["TaxRate"]] = relationship("TaxRate", back_populates="category")

    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_tax_category_tenant_slug"),
        Index("ix_tax_category_tenant", "tenant_id", "is_active"),
    )


class TaxRate(Base):
    __tablename__ = "tax_rates"

    id:          Mapped[str]            = mapped_column(String(36), primary_key=True)
    tenant_id:   Mapped[str]            = mapped_column(String(255), nullable=False)
    name:        Mapped[str]            = mapped_column(String(100), nullable=False)
    # Legacy column — kept for backwards compatibility. Prefer category_id.
    tax_type:    Mapped[str]            = mapped_column(String(20), nullable=False)
    category_id: Mapped[str | None]     = mapped_column(
        String(36), ForeignKey("tax_categories.id", ondelete="RESTRICT"), nullable=True
    )
    rate:        Mapped[Decimal]        = mapped_column(Numeric(5, 4), nullable=False)
    is_default:  Mapped[bool]           = mapped_column(Boolean, nullable=False, server_default="false")
    is_active:   Mapped[bool]           = mapped_column(Boolean, nullable=False, server_default="true")
    dian_code:   Mapped[str | None]     = mapped_column(String(20), nullable=True)
    description: Mapped[str | None]     = mapped_column(String(255), nullable=True)
    created_at:  Mapped[datetime]       = mapped_column(DateTime(timezone=True), server_default=func.now())

    category: Mapped[TaxCategory | None] = relationship("TaxCategory", back_populates="rates")

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_tax_rate_name"),
        Index("ix_tax_rate_tenant", "tenant_id", "tax_type", "is_active"),
        Index("ix_tax_rate_category", "tenant_id", "category_id", "is_active"),
    )


class SalesOrderLineTax(Base):
    """One row per tax applied to a sales order line.

    Enables multi-stack taxation (Brazil ICMS+IPI+PIS+COFINS+ISS, etc).
    Legacy single-tax lines were backfilled into this table by migration 082.
    """
    __tablename__ = "sales_order_line_taxes"

    id:          Mapped[str]     = mapped_column(String(36), primary_key=True)
    tenant_id:   Mapped[str]     = mapped_column(String(255), nullable=False)
    line_id:     Mapped[str]     = mapped_column(
        String(36), ForeignKey("sales_order_lines.id", ondelete="CASCADE"), nullable=False
    )
    tax_rate_id: Mapped[str]     = mapped_column(
        String(36), ForeignKey("tax_rates.id", ondelete="RESTRICT"), nullable=False
    )
    rate_pct:    Mapped[Decimal] = mapped_column(Numeric(7, 6), nullable=False)
    base_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    tax_amount:  Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    behavior:    Mapped[str]     = mapped_column(String(20), nullable=False)  # snapshot
    created_at:  Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    line: Mapped["SalesOrderLine"] = relationship("SalesOrderLine", back_populates="line_taxes")
    rate: Mapped[TaxRate]          = relationship("TaxRate")

    __table_args__ = (
        Index("ix_sol_taxes_line", "line_id"),
        Index("ix_sol_taxes_tenant", "tenant_id"),
    )
