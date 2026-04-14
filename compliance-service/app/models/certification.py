"""Certification scheme credibility registry.

Implements the credibility framework from MITECO webinar 3 (Alice Visa, EFI):
a certification scheme is only as useful as its scope, transparency, audit
independence and grievance mechanism. Each axis scored 0-3, total 0-12.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, CheckConstraint, Integer, Text, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


class CertificationScheme(Base):
    __tablename__ = "certification_schemes"
    __table_args__ = (
        CheckConstraint(
            "scope IN ('legality','chain_of_custody','sustainability','full')",
            name="ck_certification_schemes_scope",
        ),
        CheckConstraint(
            "scheme_type IN ('commodity_specific','generic','national')",
            name="ck_certification_schemes_type",
        ),
        CheckConstraint(
            "ownership_score BETWEEN 0 AND 3 AND "
            "transparency_score BETWEEN 0 AND 3 AND "
            "audit_score BETWEEN 0 AND 3 AND "
            "grievance_score BETWEEN 0 AND 3",
            name="ck_certification_schemes_scores_range",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    scheme_type: Mapped[str] = mapped_column(Text, nullable=False, default="generic")
    scope: Mapped[str] = mapped_column(Text, nullable=False, default="full")
    commodities: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb")
    )
    ownership_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    transparency_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    audit_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    grievance_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    covers_eudr_ambitos: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb")
    )
    reference_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )
