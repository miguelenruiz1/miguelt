"""Sync production + compliance permissions to all administrador roles.

Revision ID: 018
Revises: 017
Create Date: 2026-04-14

Background
----------
Migrations 011 (production) and 015 (compliance) seeded those permissions
and assigned them to every administrador role that existed AT THE TIME
the migration ran. New tenants registered afterwards have their
administrador role created via AuthService._ensure_seeded, which only
assigns permissions listed in auth_service._PERMISSIONS. Those
production.* and compliance.* entries were never added to _PERMISSIONS,
so administrator roles of tenants registered after 011/015 were missing
them — rendering /production-resources, /compliance/* endpoints 403 for
their admins.

This migration does two things:
  1. Ensures production.manage / production.admin exist (they were never
     created by 011) alongside the existing production.view/.create/
     .execute/.approve.
  2. Re-synchronises production.* and compliance.* to every existing
     administrador role. Idempotent — ON CONFLICT DO NOTHING.

AuthService._PERMISSIONS has also been updated so any tenant registered
after this deploy picks these up naturally.
"""
from __future__ import annotations

from typing import Sequence, Union
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision: str = "018"
down_revision: Union[str, None] = "017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Full set of perms every administrador role should have for these modules.
TARGET_PERMS = [
    # Production
    ("production", "production.view",    "Ver módulo de producción"),
    ("production", "production.create",  "Crear recetas y corridas"),
    ("production", "production.execute", "Ejecutar y finalizar corridas"),
    ("production", "production.approve", "Aprobar o rechazar corridas"),
    ("production", "production.manage",  "Gestionar producción"),
    ("production", "production.admin",   "Administrar producción"),
    # Compliance
    ("compliance", "compliance.view",    "Ver registros y certificados de cumplimiento"),
    ("compliance", "compliance.manage",  "Crear/editar registros y generar certificados"),
    ("compliance", "compliance.admin",   "Configurar integraciones de cumplimiento"),
]


def upgrade() -> None:
    conn = op.get_bind()
    now = datetime.now(timezone.utc)

    # 1. Ensure all target permissions exist.
    for module, slug, name in TARGET_PERMS:
        conn.execute(
            sa.text(
                "INSERT INTO permissions (id, name, slug, module, created_at) "
                "VALUES (:id, :name, :slug, :module, :created_at) "
                "ON CONFLICT (slug) DO NOTHING"
            ),
            {
                "id": str(uuid.uuid4()),
                "name": name,
                "slug": slug,
                "module": module,
                "created_at": now,
            },
        )

    # 2. Re-fetch canonical IDs.
    slugs = [s for _, s, _ in TARGET_PERMS]
    rows = conn.execute(
        sa.text("SELECT id FROM permissions WHERE slug = ANY(:slugs)"),
        {"slugs": slugs},
    ).fetchall()
    perm_ids = [r[0] for r in rows]

    # 3. Assign to every administrador role.
    role_rows = conn.execute(
        sa.text("SELECT id FROM roles WHERE slug = 'administrador'")
    ).fetchall()
    admin_role_ids = [r[0] for r in role_rows]

    for role_id in admin_role_ids:
        for perm_id in perm_ids:
            conn.execute(
                sa.text(
                    "INSERT INTO role_permissions (role_id, permission_id) "
                    "VALUES (:role_id, :perm_id) ON CONFLICT DO NOTHING"
                ),
                {"role_id": role_id, "perm_id": perm_id},
            )


def downgrade() -> None:
    # Non-destructive no-op: 011 and 015 already own the permissions;
    # we don't want to remove them on downgrade.
    pass
