"""Add subscription-service permissions and assign to administrador roles

Revision ID: 002
Revises: 001
Create Date: 2026-02-23
"""
from __future__ import annotations

from typing import Sequence, Union
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_PERMISSIONS = [
    # module, slug, name
    ("subscription", "subscription.view",   "Ver suscripciones, facturas y métricas"),
    ("subscription", "subscription.manage", "Crear/modificar/cancelar suscripciones"),
    ("plans",        "plans.view",           "Ver planes disponibles"),
    ("plans",        "plans.manage",         "Crear/editar/archivar planes"),
    ("licenses",     "licenses.view",        "Ver claves de licencia"),
    ("licenses",     "licenses.manage",      "Generar/revocar licencias"),
]


def upgrade() -> None:
    conn = op.get_bind()
    now = datetime.now(timezone.utc)

    # 1. Insert 6 new permissions
    perm_ids: list[str] = []
    for module, slug, name in NEW_PERMISSIONS:
        perm_id = str(uuid.uuid4())
        perm_ids.append(perm_id)
        conn.execute(
            sa.text(
                "INSERT INTO permissions (id, name, slug, module, created_at) "
                "VALUES (:id, :name, :slug, :module, :created_at)"
                " ON CONFLICT (slug) DO NOTHING"
            ),
            {"id": perm_id, "name": name, "slug": slug, "module": module, "created_at": now},
        )

    # Re-fetch actual IDs in case ON CONFLICT skipped some inserts
    rows = conn.execute(
        sa.text("SELECT id FROM permissions WHERE slug = ANY(:slugs)"),
        {"slugs": [s for _, s, _ in NEW_PERMISSIONS]},
    ).fetchall()
    actual_perm_ids = [r[0] for r in rows]

    # 2. Find all administrador roles
    role_rows = conn.execute(
        sa.text("SELECT id FROM roles WHERE slug = 'administrador'")
    ).fetchall()
    admin_role_ids = [r[0] for r in role_rows]

    # 3. Assign each permission to each administrador role
    for role_id in admin_role_ids:
        for perm_id in actual_perm_ids:
            conn.execute(
                sa.text(
                    "INSERT INTO role_permissions (role_id, permission_id) "
                    "VALUES (:role_id, :perm_id) ON CONFLICT DO NOTHING"
                ),
                {"role_id": role_id, "perm_id": perm_id},
            )


def downgrade() -> None:
    conn = op.get_bind()
    slugs = [s for _, s, _ in NEW_PERMISSIONS]
    conn.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE permission_id IN "
            "(SELECT id FROM permissions WHERE slug = ANY(:slugs))"
        ),
        {"slugs": slugs},
    )
    conn.execute(
        sa.text("DELETE FROM permissions WHERE slug = ANY(:slugs)"),
        {"slugs": slugs},
    )
