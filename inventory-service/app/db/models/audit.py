"""Inventory audit log model."""
from __future__ import annotations

from sqlalchemy import DateTime, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class InventoryAuditLog(Base):
    __tablename__ = "inventory_audit_logs"

    id:            Mapped[str]        = mapped_column(String(36), primary_key=True)
    tenant_id:     Mapped[str]        = mapped_column(String(255), nullable=False)
    user_id:       Mapped[str]        = mapped_column(String(255), nullable=False)
    user_email:    Mapped[str | None] = mapped_column(String(255), nullable=True)
    action:        Mapped[str]        = mapped_column(String(150), nullable=False)
    resource_type: Mapped[str]        = mapped_column(String(100), nullable=False)
    resource_id:   Mapped[str]        = mapped_column(String(255), nullable=False)
    old_data:      Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    new_data:      Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    description:   Mapped[str | None] = mapped_column(Text, nullable=True)
    user_name:     Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_address:    Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent:    Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at:    Mapped[DateTime]   = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_audit_logs_tenant_id", "tenant_id"),
        Index("ix_audit_logs_user_id", "user_id"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_created_at", "created_at"),
    )
