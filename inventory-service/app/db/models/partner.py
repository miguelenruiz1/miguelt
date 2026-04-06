"""Unified Business Partner model — replaces separate Customer + Supplier tables."""
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
    from app.db.models.config import SupplierType
    from app.db.models.customer import CustomerType


class BusinessPartner(Base):
    """A person or company that can be a supplier, customer, or both."""
    __tablename__ = "business_partners"

    id:               Mapped[str]        = mapped_column(String(36), primary_key=True)
    tenant_id:        Mapped[str]        = mapped_column(String(255), nullable=False)
    name:             Mapped[str]        = mapped_column(String(255), nullable=False)
    code:             Mapped[str]        = mapped_column(String(50), nullable=False)

    # ── Roles ─────────────────────────────────────────────────────────────
    is_supplier:      Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="false")
    is_customer:      Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="false")

    # ── Type classification (optional, one per role) ──────────────────────
    supplier_type_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("supplier_types.id", ondelete="SET NULL"), nullable=True
    )
    customer_type_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("customer_types.id", ondelete="SET NULL"), nullable=True
    )

    # ── Contact info (shared) ─────────────────────────────────────────────
    tax_id:           Mapped[str | None] = mapped_column(String(50), nullable=True)
    contact_name:     Mapped[str | None] = mapped_column(String(255), nullable=True)
    email:            Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone:            Mapped[str | None] = mapped_column(String(50), nullable=True)
    address:          Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # ── DIAN fiscal fields (e-invoicing) ──────────────────────────────────
    dv:                Mapped[str | None] = mapped_column(String(1), nullable=True)
    document_type:     Mapped[str]        = mapped_column(String(10), nullable=False, server_default="CC")
    organization_type: Mapped[int]        = mapped_column(Integer, nullable=False, server_default="2")
    tax_regime:        Mapped[int]        = mapped_column(Integer, nullable=False, server_default="2")
    tax_liability:     Mapped[int]        = mapped_column(Integer, nullable=False, server_default="7")
    municipality_id:   Mapped[int]        = mapped_column(Integer, nullable=False, server_default="149")
    company_name:      Mapped[str | None] = mapped_column(String(255), nullable=True)

    # ── Customer-specific ─────────────────────────────────────────────────
    shipping_address: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Numeric so amounts in COP/USD don't lose decimals.
    credit_limit:     Mapped[Decimal]    = mapped_column(Numeric(18, 2), nullable=False, server_default="0")
    # Numeric so 12.5% etc. is preservable; CHECK constraint enforces 0..100 range.
    discount_percent: Mapped[Decimal]    = mapped_column(Numeric(5, 2), nullable=False, server_default="0")

    # ── Supplier-specific ─────────────────────────────────────────────────
    lead_time_days:   Mapped[int]        = mapped_column(Integer, nullable=False, server_default="7")

    # ── Shared ────────────────────────────────────────────────────────────
    payment_terms_days: Mapped[int]      = mapped_column(Integer, nullable=False, server_default="30")
    is_active:        Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="true")
    notes:            Mapped[str | None] = mapped_column(Text, nullable=True)
    custom_attributes: Mapped[dict]      = mapped_column(JSONB, nullable=False, server_default="{}")

    created_by:       Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_by:       Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at:       Mapped[DateTime]   = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:       Mapped[DateTime]   = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    supplier_type: Mapped[SupplierType | None] = relationship("SupplierType", foreign_keys=[supplier_type_id])
    customer_type: Mapped[CustomerType | None] = relationship("CustomerType", foreign_keys=[customer_type_id])

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_partner_tenant_code"),
        Index("ix_business_partners_tenant_id", "tenant_id"),
        Index("ix_business_partners_is_supplier", "tenant_id", "is_supplier"),
        Index("ix_business_partners_is_customer", "tenant_id", "is_customer"),
    )
