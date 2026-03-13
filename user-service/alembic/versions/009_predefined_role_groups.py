"""Create role_templates table and seed 2 default templates per tenant

Revision ID: 009
Revises: 008
Create Date: 2026-03-04
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.core.role_templates import DEFAULT_TEMPLATES

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "role_templates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False, server_default="default"),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("icon", sa.String(50), nullable=False, server_default="shield"),
        sa.Column("permissions", sa.dialects.postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("is_default", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("slug", "tenant_id", name="uq_role_templates_slug_tenant"),
    )
    op.create_index("ix_role_templates_tenant_id", "role_templates", ["tenant_id"])

    conn = op.get_bind()
    now = datetime.now(timezone.utc)

    # Seed 2 default templates for every existing tenant
    tenant_rows = conn.execute(
        sa.text("SELECT DISTINCT tenant_id FROM roles")
    ).fetchall()
    tenant_ids = [r[0] for r in tenant_rows]

    for tenant_id in tenant_ids:
        for tmpl in DEFAULT_TEMPLATES:
            conn.execute(
                sa.text(
                    "INSERT INTO role_templates (id, tenant_id, slug, name, description, icon, permissions, is_default, created_at, updated_at) "
                    "VALUES (:id, :tid, :slug, :name, :desc, :icon, :perms, TRUE, :now, :now) "
                    "ON CONFLICT (slug, tenant_id) DO NOTHING"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "tid": tenant_id,
                    "slug": tmpl["slug"],
                    "name": tmpl["name"],
                    "desc": tmpl["description"],
                    "icon": tmpl["icon"],
                    "perms": json.dumps(tmpl["permissions"]),
                    "now": now,
                },
            )


def downgrade() -> None:
    op.drop_index("ix_role_templates_tenant_id")
    op.drop_table("role_templates")
