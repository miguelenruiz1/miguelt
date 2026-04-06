"""Compliance integration credentials — encrypted API keys for GFW, TRACES NT, etc."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ComplianceIntegration(Base):
    """Encrypted credentials for compliance integrations (GFW, TRACES NT)."""
    __tablename__ = "compliance_integrations"

    id:              Mapped[str]      = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider:        Mapped[str]      = mapped_column(String(50), nullable=False, unique=True)
    display_name:    Mapped[str]      = mapped_column(String(100), nullable=False)
    credentials_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    config:          Mapped[dict]     = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")
    is_active:       Mapped[bool]     = mapped_column(Boolean, nullable=False, server_default="true")
    created_at:      Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=_utcnow)
    updated_at:      Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=_utcnow, onupdate=_utcnow)
