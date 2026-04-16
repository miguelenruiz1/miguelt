"""2FA TOTP columns + user_sessions table for session management.

Revision ID: 019
Revises: 018
Create Date: 2026-04-15

Adds:
  - users.totp_secret (TEXT, nullable)
  - users.totp_enabled (BOOLEAN, default false)
  - users.totp_recovery_codes (JSONB, default '[]') — list of bcrypt hashes
  - user_sessions table for active session tracking

Part of FASE4 security hardening.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 2FA columns on users ────────────────────────────────────────────────
    op.add_column(
        "users",
        sa.Column("totp_secret", sa.Text(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "totp_enabled", sa.Boolean(), nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "totp_recovery_codes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )

    # ── user_sessions table ─────────────────────────────────────────────────
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False, index=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("refresh_jti", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("device_fingerprint", sa.String(128), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.func.now(),
        ),
        sa.Column(
            "last_used_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.func.now(),
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_user_sessions_user_active",
        "user_sessions",
        ["user_id", "revoked_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_sessions_user_active", table_name="user_sessions")
    op.drop_table("user_sessions")
    op.drop_column("users", "totp_recovery_codes")
    op.drop_column("users", "totp_enabled")
    op.drop_column("users", "totp_secret")
