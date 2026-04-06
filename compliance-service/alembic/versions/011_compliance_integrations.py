"""Compliance integrations table — encrypted API keys for GFW and TRACES NT.

Revision ID: 011
Revises: 010
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP

revision = "011_integrations"
down_revision = "010_risk_fk"


def upgrade() -> None:
    op.create_table(
        "compliance_integrations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("provider", sa.String(50), nullable=False, unique=True),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("credentials_enc", sa.Text, nullable=True),
        sa.Column("config", JSONB, nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", TIMESTAMP(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_compliance_integrations_provider", "compliance_integrations", ["provider"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_compliance_integrations_provider", "compliance_integrations")
    op.drop_table("compliance_integrations")
