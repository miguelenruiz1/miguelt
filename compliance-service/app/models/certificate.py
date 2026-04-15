"""ComplianceCertificate — PDF certificates for compliant records."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


class ComplianceCertificate(Base):
    __tablename__ = "compliance_certificates"
    __table_args__ = (
        Index("ix_certificates_tenant", "tenant_id"),
        Index("ix_certificates_record", "record_id"),
        Index("ix_certificates_number", "certificate_number"),
        Index("ix_certificates_status", "status"),
        CheckConstraint(
            "rspo_trace_model IS NULL OR rspo_trace_model IN "
            "('mass_balance','segregated','identity_preserved')",
            name="ck_compliance_certificates_rspo_trace_model",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("compliance_records.id", ondelete="RESTRICT"), nullable=False
    )
    certificate_number: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    framework_slug: Mapped[str] = mapped_column(Text, nullable=False)
    asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    status: Mapped[str] = mapped_column(Text, nullable=False, default="generating")

    pdf_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    pdf_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    pdf_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    verify_url: Mapped[str] = mapped_column(Text, nullable=False)
    qr_code_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_until: Mapped[date] = mapped_column(Date, nullable=False)

    generated_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    generated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    generation_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # RSPO chain-of-custody model emitido en el certificado (palma).
    rspo_trace_model: Mapped[str | None] = mapped_column(String(20), nullable=True)

    solana_cnft_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    solana_tx_sig: Mapped[str | None] = mapped_column(Text, nullable=True)

    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)
