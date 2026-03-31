"""ComplianceRecord — compliance data for an asset against a framework."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Index, Numeric, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


class ComplianceRecord(Base):
    __tablename__ = "compliance_records"
    __table_args__ = (
        UniqueConstraint("tenant_id", "asset_id", "framework_id", name="uq_record_asset_framework"),
        Index("ix_records_tenant", "tenant_id"),
        Index("ix_records_asset", "asset_id"),
        Index("ix_records_framework", "framework_id"),
        Index("ix_records_status", "compliance_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    framework_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("compliance_frameworks.id", ondelete="RESTRICT"), nullable=False
    )
    framework_slug: Mapped[str] = mapped_column(Text, nullable=False)

    # Product identification (EUDR Art. 9.1.a, 9.1.b)
    hs_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    commodity_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    product_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    scientific_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    quantity_kg: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    quantity_unit: Mapped[str] = mapped_column(Text, nullable=False, default="kg")
    country_of_production: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Production period (EUDR Art. 9.1.d)
    production_period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    production_period_end: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Supply chain (EUDR Art. 9.1.e, 9.1.f)
    supplier_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    supplier_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    supplier_email: Mapped[str | None] = mapped_column(Text, nullable=True)
    buyer_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    buyer_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    buyer_email: Mapped[str | None] = mapped_column(Text, nullable=True)

    # EU export specific
    operator_eori: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Activity type (Annex II #2: import, domestic_production, export)
    activity_type: Mapped[str] = mapped_column(Text, nullable=False, default="export")

    # Declarations (EUDR Art. 9.1.g, 9.1.h)
    deforestation_free_declaration: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    legal_compliance_declaration: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Document hashes
    legal_cert_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    deforestation_evidence_hash: Mapped[str | None] = mapped_column(Text, nullable=True)

    # DDS / equivalent declaration
    declaration_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    declaration_submission_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    declaration_status: Mapped[str] = mapped_column(Text, nullable=False, default="not_required")
    declaration_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Status
    compliance_status: Mapped[str] = mapped_column(Text, nullable=False, default="incomplete")
    last_validated_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    validation_result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    missing_fields: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # Signatory (Annex II #10: name, role, date of the person signing)
    signatory_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    signatory_role: Mapped[str | None] = mapped_column(Text, nullable=True)
    signatory_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Prior DDS references (Annex II #8: for derived products)
    prior_dds_references: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # Retention
    documents_retention_until: Mapped[date | None] = mapped_column(Date, nullable=True)

    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)
