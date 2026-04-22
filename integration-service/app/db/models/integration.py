"""Core integration models — config, sync jobs, logs, invoice resolutions."""
from __future__ import annotations

from sqlalchemy import (
    Boolean, Date, DateTime, Index, Integer, String, Text, UniqueConstraint, func, text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class IntegrationConfig(Base):
    """Per-tenant integration configuration for an external provider."""
    __tablename__ = "integration_configs"

    id:               Mapped[str]        = mapped_column(String(36), primary_key=True)
    tenant_id:        Mapped[str]        = mapped_column(String(255), nullable=False)
    provider_slug:    Mapped[str]        = mapped_column(String(50), nullable=False)
    display_name:     Mapped[str]        = mapped_column(String(100), nullable=False)
    is_active:        Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="false")
    credentials_enc:  Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_config:     Mapped[dict]       = mapped_column(JSONB, nullable=False, server_default="{}")
    sync_products:    Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="false")
    sync_customers:   Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="false")
    sync_invoices:    Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="true")
    last_sync_at:     Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by:       Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_by:       Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at:       Mapped[DateTime]   = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:       Mapped[DateTime]   = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "provider_slug", name="uq_integration_tenant_provider"),
        Index("ix_integration_configs_tenant_id", "tenant_id"),
    )


class SyncJob(Base):
    """A scheduled or manual sync execution."""
    __tablename__ = "sync_jobs"

    id:               Mapped[str]        = mapped_column(String(36), primary_key=True)
    tenant_id:        Mapped[str]        = mapped_column(String(255), nullable=False)
    integration_id:   Mapped[str]        = mapped_column(String(36), nullable=False)
    provider_slug:    Mapped[str]        = mapped_column(String(50), nullable=False)
    direction:        Mapped[str]        = mapped_column(String(20), nullable=False, server_default="push")
    entity_type:      Mapped[str]        = mapped_column(String(50), nullable=False)
    status:           Mapped[str]        = mapped_column(String(20), nullable=False, server_default="pending")
    total_records:    Mapped[int]        = mapped_column(Integer, nullable=False, server_default="0")
    synced_records:   Mapped[int]        = mapped_column(Integer, nullable=False, server_default="0")
    failed_records:   Mapped[int]        = mapped_column(Integer, nullable=False, server_default="0")
    error_summary:    Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at:       Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at:     Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    triggered_by:     Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at:       Mapped[DateTime]   = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_sync_jobs_tenant_id", "tenant_id"),
        Index("ix_sync_jobs_status", "status"),
    )


class SyncLog(Base):
    """Individual record-level sync result."""
    __tablename__ = "sync_logs"

    id:             Mapped[str]        = mapped_column(String(36), primary_key=True)
    sync_job_id:    Mapped[str]        = mapped_column(String(36), nullable=False)
    tenant_id:      Mapped[str]        = mapped_column(String(255), nullable=False)
    entity_type:    Mapped[str]        = mapped_column(String(50), nullable=False)
    local_id:       Mapped[str | None] = mapped_column(String(100), nullable=True)
    remote_id:      Mapped[str | None] = mapped_column(String(100), nullable=True)
    action:         Mapped[str]        = mapped_column(String(20), nullable=False)
    status:         Mapped[str]        = mapped_column(String(20), nullable=False, server_default="success")
    error_detail:   Mapped[str | None] = mapped_column(Text, nullable=True)
    request_data:   Mapped[dict | None]  = mapped_column(JSONB, nullable=True)
    response_data:  Mapped[dict | None]  = mapped_column(JSONB, nullable=True)
    created_at:     Mapped[DateTime]   = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_sync_logs_job_id", "sync_job_id"),
        Index("ix_sync_logs_tenant_id", "tenant_id"),
    )


class WebhookLog(Base):
    """Incoming webhook event log."""
    __tablename__ = "webhook_logs"

    id:             Mapped[str]        = mapped_column(String(36), primary_key=True)
    tenant_id:      Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_slug:  Mapped[str]        = mapped_column(String(50), nullable=False)
    event_type:     Mapped[str | None] = mapped_column(String(100), nullable=True)
    payload:        Mapped[dict]       = mapped_column(JSONB, nullable=False, server_default="{}")
    headers:        Mapped[dict]       = mapped_column(JSONB, nullable=False, server_default="{}")
    status:         Mapped[str]        = mapped_column(String(20), nullable=False, server_default="received")
    processing_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at:     Mapped[DateTime]   = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_webhook_logs_provider", "provider_slug"),
        Index("ix_webhook_logs_tenant_id", "tenant_id"),
    )


class InvoiceResolution(Base):
    """DIAN invoice numbering resolution per tenant and provider."""
    __tablename__ = "invoice_resolutions"

    id:                Mapped[str]        = mapped_column(String(36), primary_key=True)
    tenant_id:         Mapped[str]        = mapped_column(String(255), nullable=False)
    provider:          Mapped[str]        = mapped_column(String(50), nullable=False)
    is_active:         Mapped[bool]       = mapped_column(Boolean, nullable=False, server_default="true")

    resolution_number: Mapped[str]        = mapped_column(String(50), nullable=False)
    prefix:            Mapped[str]        = mapped_column(String(10), nullable=False)
    range_from:        Mapped[int]        = mapped_column(Integer, nullable=False)
    range_to:          Mapped[int]        = mapped_column(Integer, nullable=False)
    current_number:    Mapped[int]        = mapped_column(Integer, nullable=False, server_default="0")
    valid_from:        Mapped[Date]       = mapped_column(Date, nullable=False)
    valid_to:          Mapped[Date]       = mapped_column(Date, nullable=False)

    created_at:        Mapped[DateTime]   = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:        Mapped[DateTime]   = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_invoice_resolutions_tenant_id", "tenant_id"),
        Index(
            "ix_resolution_tenant_provider_active",
            "tenant_id", "provider",
            unique=True,
            postgresql_where=text("is_active = true"),
        ),
    )


