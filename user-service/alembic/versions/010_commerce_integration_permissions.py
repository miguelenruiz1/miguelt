"""Add customers, sales_orders, price_lists, variants, and integrations permissions

Revision ID: 010
Revises: 009
Create Date: 2026-03-05
"""
from __future__ import annotations

from typing import Sequence, Union
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_PERMISSIONS = [
    # module, slug, name
    # Customers (4)
    ("inventory", "customers.view",            "Ver clientes"),
    ("inventory", "customers.create",          "Crear clientes"),
    ("inventory", "customers.edit",            "Editar clientes"),
    ("inventory", "customers.manage",          "Gestionar clientes (crear/editar/eliminar)"),
    # Sales Orders (5)
    ("inventory", "sales_orders.view",         "Ver ordenes de venta"),
    ("inventory", "sales_orders.create",       "Crear ordenes de venta"),
    ("inventory", "sales_orders.manage",       "Gestionar ciclo de vida de ordenes"),
    ("inventory", "sales_orders.ship",         "Enviar ordenes (descontar stock)"),
    ("inventory", "sales_orders.cancel",       "Cancelar/devolver ordenes"),
    # Price Lists (3)
    ("inventory", "price_lists.view",          "Ver listas de precios"),
    ("inventory", "price_lists.manage",        "Gestionar listas de precios"),
    ("inventory", "price_lists.set_items",     "Agregar/editar items en listas de precios"),
    # Variants (3)
    ("inventory", "variants.view",             "Ver atributos de variante y variantes"),
    ("inventory", "variants.manage",           "Gestionar variantes de producto"),
    ("inventory", "variants.delete",           "Eliminar variantes"),
    # Integrations (4)
    ("integrations", "integrations.view",      "Ver integraciones y catalogo"),
    ("integrations", "integrations.manage",    "Configurar/activar integraciones"),
    ("integrations", "integrations.sync",      "Ejecutar sincronizaciones"),
    ("integrations", "integrations.invoicing", "Crear facturas via integracion"),
]


def upgrade() -> None:
    conn = op.get_bind()
    now = datetime.now(timezone.utc)

    for module, slug, name in NEW_PERMISSIONS:
        perm_id = str(uuid.uuid4())
        conn.execute(
            sa.text(
                "INSERT INTO permissions (id, name, slug, module, created_at) "
                "VALUES (:id, :name, :slug, :module, :created_at)"
                " ON CONFLICT (slug) DO NOTHING"
            ),
            {"id": perm_id, "name": name, "slug": slug, "module": module, "created_at": now},
        )

    rows = conn.execute(
        sa.text("SELECT id FROM permissions WHERE slug = ANY(:slugs)"),
        {"slugs": [s for _, s, _ in NEW_PERMISSIONS]},
    ).fetchall()
    actual_perm_ids = [r[0] for r in rows]

    role_rows = conn.execute(
        sa.text("SELECT id FROM roles WHERE slug = 'administrador'")
    ).fetchall()
    admin_role_ids = [r[0] for r in role_rows]

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
