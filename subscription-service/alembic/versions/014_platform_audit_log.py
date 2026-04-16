"""Central platform audit log for superuser actions (FASE4).

Revision ID: 014
Revises: 013
Create Date: 2026-04-15
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "platform_audit_log",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "timestamp", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.func.now(),
        ),
        sa.Column("superuser_id", sa.String(36), nullable=True),
        sa.Column("superuser_email", sa.String(255), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("target_tenant_id", sa.String(255), nullable=True),
        sa.Column("target_entity_type", sa.String(100), nullable=True),
        sa.Column("target_entity_id", sa.String(255), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("correlation_id", sa.String(64), nullable=True),
    )
    op.create_index("ix_platform_audit_timestamp", "platform_audit_log", ["timestamp"])
    op.create_index("ix_platform_audit_superuser", "platform_audit_log", ["superuser_id"])
    op.create_index("ix_platform_audit_action", "platform_audit_log", ["action"])
    op.create_index("ix_platform_audit_target_tenant", "platform_audit_log", ["target_tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_platform_audit_target_tenant", table_name="platform_audit_log")
    op.drop_index("ix_platform_audit_action", table_name="platform_audit_log")
    op.drop_index("ix_platform_audit_superuser", table_name="platform_audit_log")
    op.drop_index("ix_platform_audit_timestamp", table_name="platform_audit_log")
    op.drop_table("platform_audit_log")
