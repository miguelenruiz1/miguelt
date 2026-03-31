"""ComplianceRiskAssessment — EUDR Art. 10-11 formal risk assessment."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Date, ForeignKey, Index, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


class ComplianceRiskAssessment(Base):
    __tablename__ = "compliance_risk_assessments"
    __table_args__ = (
        UniqueConstraint("tenant_id", "record_id", name="uq_risk_tenant_record"),
        Index("ix_risk_tenant", "tenant_id"),
        Index("ix_risk_record", "record_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("compliance_records.id", ondelete="CASCADE"), nullable=False
    )
    assessed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    assessed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    # Step 1: Country risk (Art. 29)
    country_risk_level: Mapped[str | None] = mapped_column(Text, nullable=True)
    country_risk_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    country_benchmarking_source: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Step 2: Supply chain risk
    supply_chain_risk_level: Mapped[str | None] = mapped_column(Text, nullable=True)
    supply_chain_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    supplier_verification_status: Mapped[str] = mapped_column(Text, nullable=False, default="not_started")
    traceability_confidence: Mapped[str] = mapped_column(Text, nullable=False, default="none")

    # Step 3: Regional / product risk
    regional_risk_level: Mapped[str | None] = mapped_column(Text, nullable=True)
    deforestation_prevalence: Mapped[str | None] = mapped_column(Text, nullable=True)
    indigenous_rights_risk: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    corruption_index_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Mitigation measures (Art. 11)
    mitigation_measures: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    additional_info_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    independent_audit_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Conclusion
    overall_risk_level: Mapped[str | None] = mapped_column(Text, nullable=True)
    conclusion: Mapped[str | None] = mapped_column(Text, nullable=True)
    conclusion_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(Text, nullable=False, default="draft")
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)
