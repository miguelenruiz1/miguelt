"""Granular purchase order permissions.

Revision ID: 014
Revises: 013
Create Date: 2026-03-23
"""
from __future__ import annotations

from typing import Sequence, Union
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_PERMISSIONS = [
    # module, slug, name, description
    ("inventory", "purchase_orders.send",      "Enviar OC al proveedor",  "Enviar orden de compra al proveedor por email"),
    ("inventory", "purchase_orders.confirm",   "Confirmar OC",            "Confirmar recepción del proveedor"),
    ("inventory", "purchase_orders.delete",    "Eliminar OC",             "Eliminar órdenes de compra en borrador"),
    ("inventory", "purchase_orders.cancel",    "Cancelar OC",             "Cancelar órdenes de compra"),
    ("inventory", "purchase_orders.view_cost", "Ver costos OC",           "Ver costos unitarios y totales en órdenes de compra"),
]


def upgrade() -> None:
    conn = op.get_bind()
    now = datetime.now(timezone.utc)

    # 1. Insert permissions
    for module, slug, name, description in NEW_PERMISSIONS:
        perm_id = str(uuid.uuid4())
        conn.execute(
            sa.text(
                "INSERT INTO permissions (id, name, slug, module, description, created_at) "
                "VALUES (:id, :name, :slug, :module, :description, :created_at)"
                " ON CONFLICT (slug) DO NOTHING"
            ),
            {"id": perm_id, "name": name, "slug": slug, "module": module, "description": description, "created_at": now},
        )

    # Re-fetch actual IDs in case ON CONFLICT skipped some inserts
    rows = conn.execute(
        sa.text("SELECT id FROM permissions WHERE slug = ANY(:slugs)"),
        {"slugs": [s for _, s, _, _ in NEW_PERMISSIONS]},
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
    slugs = [s for _, s, _, _ in NEW_PERMISSIONS]
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
