"""Add email_provider_configs table and email_providers.manage permission.

Revision ID: 007
Revises: 006
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── email_provider_configs table ──────────────────────────────────────────
    op.create_table(
        "email_provider_configs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("provider_slug", sa.String(50), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_test_mode", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("credentials", JSONB, nullable=False, server_default="{}"),
        sa.Column("extra_config", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "provider_slug", name="uq_tenant_email_provider"),
    )
    op.create_index("ix_email_provider_configs_tenant_id", "email_provider_configs", ["tenant_id"])

    # ── Add permission: email_providers.manage ────────────────────────────────
    conn = op.get_bind()
    perm_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    conn.execute(
        sa.text(
            "INSERT INTO permissions (id, name, slug, module, description, created_at) "
            "VALUES (:id, :name, :slug, :module, :desc, :ts)"
        ),
        {
            "id": perm_id,
            "name": "Gestionar proveedores de correo",
            "slug": "email_providers.manage",
            "module": "email_providers",
            "desc": "Configurar y activar proveedores de correo electrónico",
            "ts": now,
        },
    )

    # Assign to all existing "administrador" roles
    rows = conn.execute(
        sa.text("SELECT id FROM roles WHERE slug = 'administrador'")
    ).fetchall()
    for (role_id,) in rows:
        conn.execute(
            sa.text(
                "INSERT INTO role_permissions (role_id, permission_id) VALUES (:rid, :pid) "
                "ON CONFLICT DO NOTHING"
            ),
            {"rid": role_id, "pid": perm_id},
        )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM role_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE slug = 'email_providers.manage')"))
    conn.execute(sa.text("DELETE FROM permissions WHERE slug = 'email_providers.manage'"))
    op.drop_index("ix_email_provider_configs_tenant_id")
    op.drop_table("email_provider_configs")
