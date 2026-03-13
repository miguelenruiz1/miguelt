"""Add email_configs table for per-tenant SMTP configuration

Revision ID: 005
Revises: 004
Create Date: 2026-03-03
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "email_configs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False, unique=True),
        sa.Column("smtp_host", sa.String(255), nullable=True),
        sa.Column("smtp_port", sa.Integer, nullable=False, server_default=sa.text("587")),
        sa.Column("smtp_user", sa.String(255), nullable=True),
        sa.Column("smtp_password", sa.String(500), nullable=True),
        sa.Column("smtp_from", sa.String(255), nullable=True),
        sa.Column("smtp_use_tls", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("admin_email", sa.String(255), nullable=True),
        sa.Column("test_email", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("email_configs")
