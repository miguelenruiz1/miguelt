"""AnchorRule model — configurable blockchain anchoring rules per tenant."""
from __future__ import annotations

from sqlalchemy import Boolean, DateTime, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AnchorRule(Base):
    __tablename__ = "anchor_rules"

    id:            Mapped[str]       = mapped_column(String(36), primary_key=True)
    tenant_id:     Mapped[str]       = mapped_column(String(255), nullable=False)
    name:          Mapped[str]       = mapped_column(String(150), nullable=False)
    entity_type:   Mapped[str]       = mapped_column(String(50), nullable=False)
    trigger_event: Mapped[str]       = mapped_column(String(50), nullable=False)
    conditions:    Mapped[dict]      = mapped_column(JSONB, nullable=False, server_default="{}")
    actions:       Mapped[dict]      = mapped_column(JSONB, nullable=False, server_default='{"anchor": true}')
    is_active:     Mapped[bool]      = mapped_column(Boolean, nullable=False, server_default="true")
    priority:      Mapped[int]       = mapped_column(Integer, nullable=False, server_default="0")
    created_by:    Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at:    Mapped[DateTime]  = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:    Mapped[DateTime]  = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_anchor_rules_tenant", "tenant_id"),
        Index("ix_anchor_rules_tenant_entity", "tenant_id", "entity_type"),
    )
