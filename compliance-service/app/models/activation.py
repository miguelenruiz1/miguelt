"""TenantFrameworkActivation — which frameworks a tenant has enabled."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, ForeignKey, Text, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


class TenantFrameworkActivation(Base):
    __tablename__ = "tenant_framework_activations"
    __table_args__ = (
        UniqueConstraint("tenant_id", "framework_id", name="uq_tenant_framework"),
        Index("ix_tenant_framework_tenant", "tenant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    framework_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("compliance_frameworks.id", ondelete="CASCADE"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    export_destination: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    activated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=_utcnow)
    activated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
