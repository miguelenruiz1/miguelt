"""Add tenant_module_activations table and seed logistics module

Revision ID: 003
Revises: 001
Create Date: 2026-02-23
"""
from __future__ import annotations

from typing import Sequence, Union
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── tenant_module_activations ──────────────────────────────────────────────
    op.create_table(
        "tenant_module_activations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("module_slug", sa.String(50), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("activated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("activated_by", sa.String(255), nullable=True),
        sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deactivated_by", sa.String(255), nullable=True),
        sa.UniqueConstraint("tenant_id", "module_slug", name="uq_tenant_module"),
    )
    op.create_index(
        "ix_tenant_module_activations_tenant_id",
        "tenant_module_activations",
        ["tenant_id"],
    )

    # ── update plan modules to use new slugs ──────────────────────────────────
    conn = op.get_bind()
    conn.execute(
        sa.text("UPDATE plans SET modules = :m WHERE slug = 'free'"),
        {"m": '["logistics"]'},
    )
    conn.execute(
        sa.text("UPDATE plans SET modules = :m WHERE slug = 'starter'"),
        {"m": '["logistics","inventory","audit"]'},
    )
    conn.execute(
        sa.text("UPDATE plans SET modules = :m WHERE slug = 'professional'"),
        {"m": '["logistics","inventory","audit","analytics"]'},
    )
    conn.execute(
        sa.text("UPDATE plans SET modules = :m WHERE slug = 'enterprise'"),
        {"m": '["logistics","inventory","audit","analytics","api","sso","custom"]'},
    )

    # ── seed logistics as active for all existing tenants ─────────────────────
    now = datetime.now(timezone.utc)
    rows = conn.execute(sa.text("SELECT tenant_id FROM subscriptions")).fetchall()
    for (tenant_id,) in rows:
        conn.execute(
            sa.text(
                "INSERT INTO tenant_module_activations "
                "(id, tenant_id, module_slug, is_active, activated_at) "
                "VALUES (:id, :tid, 'logistics', true, :now) "
                "ON CONFLICT ON CONSTRAINT uq_tenant_module DO NOTHING"
            ),
            {"id": str(uuid.uuid4()), "tid": tenant_id, "now": now},
        )


def downgrade() -> None:
    op.drop_index("ix_tenant_module_activations_tenant_id", "tenant_module_activations")
    op.drop_table("tenant_module_activations")
