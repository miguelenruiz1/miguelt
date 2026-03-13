"""Tax rate models for Colombian tax system (IVA, retention, ICA)."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean, DateTime, Index, Numeric, String, Text,
    UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TaxRate(Base):
    __tablename__ = "tax_rates"

    id:          Mapped[str]            = mapped_column(String(36), primary_key=True)
    tenant_id:   Mapped[str]            = mapped_column(String(255), nullable=False)
    name:        Mapped[str]            = mapped_column(String(100), nullable=False)
    tax_type:    Mapped[str]            = mapped_column(String(20), nullable=False)
    rate:        Mapped[Decimal]        = mapped_column(Numeric(5, 4), nullable=False)
    is_default:  Mapped[bool]           = mapped_column(Boolean, nullable=False, server_default="false")
    is_active:   Mapped[bool]           = mapped_column(Boolean, nullable=False, server_default="true")
    dian_code:   Mapped[str | None]     = mapped_column(String(20), nullable=True)
    description: Mapped[str | None]     = mapped_column(String(255), nullable=True)
    created_at:  Mapped[datetime]       = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_tax_rate_name"),
        Index("ix_tax_rate_tenant", "tenant_id", "tax_type", "is_active"),
    )
