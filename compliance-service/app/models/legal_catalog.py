"""Legal requirements catalog models (EUDR Art. 9.1 legalidad).

Three-level model driven by MITECO webinar 3 (Alice Visa, EFI):
  - LegalRequirementCatalog: set of rules per (country, commodity, version)
  - LegalRequirement: individual rule, classified by ambito + scale
  - PlotLegalCompliance: per-plot status against each rule

Ambitos (from the EUDR regulation, Art. 2(40)):
  land_use_rights, environmental_protection, labor_rights,
  human_rights, third_party_rights_fpic, fiscal_customs_anticorruption
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


class LegalRequirementCatalog(Base):
    __tablename__ = "legal_requirement_catalogs"
    __table_args__ = (
        UniqueConstraint("country_code", "commodity", "version", name="uq_legal_catalog_triple"),
        Index("ix_legal_catalogs_country_commodity", "country_code", "commodity"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    country_code: Mapped[str] = mapped_column(Text, nullable=False)
    commodity: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=_utcnow
    )


class LegalRequirement(Base):
    __tablename__ = "legal_requirements"
    __table_args__ = (
        UniqueConstraint("catalog_id", "code", name="uq_legal_requirement_code"),
        CheckConstraint(
            "ambito IN ('land_use_rights','environmental_protection','labor_rights',"
            "'human_rights','third_party_rights_fpic','fiscal_customs_anticorruption')",
            name="ck_legal_requirements_ambito",
        ),
        CheckConstraint(
            "applies_to_scale IN ('all','smallholder','medium','industrial','medium_or_industrial')",
            name="ck_legal_requirements_scale",
        ),
        Index("ix_legal_requirements_catalog", "catalog_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    catalog_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("legal_requirement_catalogs.id", ondelete="CASCADE"),
        nullable=False,
    )
    ambito: Mapped[str] = mapped_column(Text, nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    legal_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    applies_to_scale: Mapped[str] = mapped_column(Text, nullable=False, default="all")
    required_document_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_blocking: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )


class PlotLegalCompliance(Base):
    __tablename__ = "plot_legal_compliance"
    __table_args__ = (
        UniqueConstraint("plot_id", "requirement_id", name="uq_plot_requirement"),
        CheckConstraint(
            "status IN ('satisfied','missing','na','pending')",
            name="ck_plot_legal_compliance_status",
        ),
        CheckConstraint(
            "evidence_weight IN ('primary','secondary','affidavit')",
            name="ck_plot_legal_evidence_weight",
        ),
        Index("ix_plot_legal_compliance_plot", "plot_id"),
        Index("ix_plot_legal_compliance_tenant", "tenant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    plot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("compliance_plots.id", ondelete="CASCADE"),
        nullable=False,
    )
    requirement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("legal_requirements.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    evidence_media_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    evidence_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_weight: Mapped[str] = mapped_column(Text, nullable=False, default="primary")
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )
