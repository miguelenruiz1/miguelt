"""Add payment_gateway_configs table

Revision ID: 004
Revises: 003
Create Date: 2026-02-23
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "payment_gateway_configs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("gateway_slug", sa.String(50), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_test_mode", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("credentials", JSONB, nullable=False, server_default="{}"),
        sa.Column("extra_config", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "gateway_slug", name="uq_tenant_gateway"),
    )
    op.create_index(
        "ix_payment_gateway_configs_tenant_id",
        "payment_gateway_configs",
        ["tenant_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_payment_gateway_configs_tenant_id", "payment_gateway_configs")
    op.drop_table("payment_gateway_configs")
