"""Initial tables: integration_configs, sync_jobs, sync_logs, webhook_logs.

Revision ID: 001
Revises: None
"""
revision = "001"
down_revision = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade() -> None:
    op.create_table(
        "integration_configs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("provider_slug", sa.String(50), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_test_mode", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("credentials_enc", sa.Text, nullable=True),
        sa.Column("extra_config", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("sync_products", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("sync_customers", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("sync_invoices", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("updated_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "provider_slug", name="uq_integration_tenant_provider"),
    )
    op.create_index("ix_integration_configs_tenant_id", "integration_configs", ["tenant_id"])

    op.create_table(
        "sync_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("integration_id", sa.String(36), nullable=False),
        sa.Column("provider_slug", sa.String(50), nullable=False),
        sa.Column("direction", sa.String(20), nullable=False, server_default="push"),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("total_records", sa.Integer, nullable=False, server_default="0"),
        sa.Column("synced_records", sa.Integer, nullable=False, server_default="0"),
        sa.Column("failed_records", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error_summary", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("triggered_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_sync_jobs_tenant_id", "sync_jobs", ["tenant_id"])
    op.create_index("ix_sync_jobs_status", "sync_jobs", ["status"])

    op.create_table(
        "sync_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("sync_job_id", sa.String(36), nullable=False),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("local_id", sa.String(100), nullable=True),
        sa.Column("remote_id", sa.String(100), nullable=True),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="success"),
        sa.Column("error_detail", sa.Text, nullable=True),
        sa.Column("request_data", postgresql.JSONB, nullable=True),
        sa.Column("response_data", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_sync_logs_job_id", "sync_logs", ["sync_job_id"])
    op.create_index("ix_sync_logs_tenant_id", "sync_logs", ["tenant_id"])

    op.create_table(
        "webhook_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=True),
        sa.Column("provider_slug", sa.String(50), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=True),
        sa.Column("payload", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("headers", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("status", sa.String(20), nullable=False, server_default="received"),
        sa.Column("processing_result", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_webhook_logs_provider", "webhook_logs", ["provider_slug"])
    op.create_index("ix_webhook_logs_tenant_id", "webhook_logs", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("webhook_logs")
    op.drop_table("sync_logs")
    op.drop_table("sync_jobs")
    op.drop_table("integration_configs")
