"""Add 52 granular inventory permissions and assign to administrador roles

Revision ID: 008
Revises: 007
Create Date: 2026-03-04
"""
from __future__ import annotations

from typing import Sequence, Union
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_PERMISSIONS = [
    # module, slug, name
    # Products (5)
    ("inventory", "products.view",          "Ver productos"),
    ("inventory", "products.create",        "Crear productos"),
    ("inventory", "products.edit",          "Editar productos"),
    ("inventory", "products.delete",        "Eliminar productos"),
    ("inventory", "products.import",        "Importar productos CSV"),
    # Warehouses (4)
    ("inventory", "warehouses.view",        "Ver bodegas"),
    ("inventory", "warehouses.create",      "Crear bodegas"),
    ("inventory", "warehouses.edit",        "Editar bodegas"),
    ("inventory", "warehouses.delete",      "Eliminar bodegas"),
    # Stock (7)
    ("inventory", "stock.view",             "Ver niveles de stock"),
    ("inventory", "stock.receive",          "Registrar entradas de stock"),
    ("inventory", "stock.issue",            "Registrar salidas de stock"),
    ("inventory", "stock.transfer",         "Transferir stock entre bodegas"),
    ("inventory", "stock.adjust",           "Ajustar stock"),
    ("inventory", "stock.return",           "Registrar devoluciones"),
    ("inventory", "stock.waste",            "Registrar mermas"),
    # Movements (1)
    ("inventory", "movements.view",         "Ver historial de movimientos"),
    # Suppliers (4)
    ("inventory", "suppliers.view",         "Ver proveedores"),
    ("inventory", "suppliers.create",       "Crear proveedores"),
    ("inventory", "suppliers.edit",         "Editar proveedores"),
    ("inventory", "suppliers.delete",       "Eliminar proveedores"),
    # Purchase Orders (5)
    ("inventory", "purchase_orders.view",   "Ver órdenes de compra"),
    ("inventory", "purchase_orders.create", "Crear órdenes de compra"),
    ("inventory", "purchase_orders.edit",   "Editar órdenes de compra"),
    ("inventory", "purchase_orders.approve","Enviar/confirmar/cancelar órdenes"),
    ("inventory", "purchase_orders.receive","Recibir mercancía"),
    # Production (4)
    ("inventory", "production.view",        "Ver corridas de producción"),
    ("inventory", "production.create",      "Crear corridas de producción"),
    ("inventory", "production.execute",     "Ejecutar/finalizar corridas"),
    ("inventory", "production.approve",     "Aprobar/rechazar corridas"),
    # Recipes (3)
    ("inventory", "recipes.view",           "Ver recetas (BOMs)"),
    ("inventory", "recipes.create",         "Crear/editar recetas"),
    ("inventory", "recipes.delete",         "Eliminar recetas"),
    # Batches (3)
    ("inventory", "batches.view",           "Ver lotes"),
    ("inventory", "batches.manage",         "Crear/editar lotes"),
    ("inventory", "batches.delete",         "Eliminar lotes"),
    # Serials (3)
    ("inventory", "serials.view",           "Ver seriales"),
    ("inventory", "serials.manage",         "Crear/editar seriales"),
    ("inventory", "serials.delete",         "Eliminar seriales"),
    # Cycle Counts (4)
    ("inventory", "cycle_counts.view",      "Ver conteos cíclicos"),
    ("inventory", "cycle_counts.create",    "Crear conteos cíclicos"),
    ("inventory", "cycle_counts.execute",   "Iniciar/contar/completar conteos"),
    ("inventory", "cycle_counts.approve",   "Aprobar/cancelar conteos"),
    # Events (3)
    ("inventory", "events.view",            "Ver eventos"),
    ("inventory", "events.create",          "Crear eventos"),
    ("inventory", "events.manage",          "Cambiar estado/impactos"),
    # Configuration (1)
    ("inventory", "config.manage",          "Gestionar configuración de inventario"),
    # Taxonomy (2)
    ("inventory", "taxonomy.view",          "Ver taxonomías"),
    ("inventory", "taxonomy.manage",        "Gestionar vocabularios y términos"),
    # Reports & Analytics (2)
    ("inventory", "reports.view",           "Ver reportes y analytics"),
    ("inventory", "reports.download",       "Descargar reportes CSV"),
    # Audit (1)
    ("inventory", "audit.view_inventory",   "Ver auditoría de inventario"),
]


def upgrade() -> None:
    conn = op.get_bind()
    now = datetime.now(timezone.utc)

    # 1. Insert 52 new permissions
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
