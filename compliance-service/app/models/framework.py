"""ComplianceFramework — catalogue of regulatory norms."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


class ComplianceFramework(Base):
    __tablename__ = "compliance_frameworks"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_frameworks_slug"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    issuing_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_markets: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    applicable_commodities: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    requires_geolocation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_dds: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_scientific_name: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    document_retention_years: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    cutoff_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    legal_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    validation_rules: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    version: Mapped[str] = mapped_column(Text, nullable=False, default="1.0")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)
