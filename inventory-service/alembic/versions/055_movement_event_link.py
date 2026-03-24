"""Link stock movements to inventory events.

Revision ID: 055
Revises: 054
Create Date: 2026-03-16
"""
from alembic import op
import sqlalchemy as sa

revision = "055"
down_revision = "054"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("stock_movements", sa.Column(
        "event_id", sa.String(36),
        sa.ForeignKey("inventory_events.id", ondelete="SET NULL"),
        nullable=True,
    ))
    op.create_index("ix_stock_movements_event_id", "stock_movements", ["event_id"])

    # Seed system event types per tenant per movement type
    op.execute("""
        INSERT INTO event_types (id, tenant_id, name, slug, description, color, icon, is_active)
        SELECT
            gen_random_uuid()::text,
            tenants.tenant_id,
            mt.name,
            mt.slug,
            'Evento generado automaticamente por movimiento de inventario',
            mt.color,
            mt.slug,
            true
        FROM (SELECT DISTINCT tenant_id FROM entities) tenants
        CROSS JOIN (VALUES
            ('Recepcion de compra',     'sys_purchase',        '#22c55e'),
            ('Despacho de venta',       'sys_sale',            '#6366f1'),
            ('Transferencia',           'sys_transfer',        '#3b82f6'),
            ('Ajuste positivo',         'sys_adjustment_in',   '#10b981'),
            ('Ajuste negativo',         'sys_adjustment_out',  '#f97316'),
            ('Devolucion',              'sys_return',          '#8b5cf6'),
            ('Merma / Desperdicio',     'sys_waste',           '#ef4444'),
            ('Entrada de produccion',   'sys_production_in',   '#14b8a6'),
            ('Consumo de produccion',   'sys_production_out',  '#f59e0b')
        ) AS mt(name, slug, color)
        WHERE NOT EXISTS (
            SELECT 1 FROM event_types et
            WHERE et.tenant_id = tenants.tenant_id AND et.slug = mt.slug
        )
    """)


def downgrade() -> None:
    op.execute("DELETE FROM event_types WHERE slug LIKE 'sys_%'")
    op.drop_index("ix_stock_movements_event_id", table_name="stock_movements")
    op.drop_column("stock_movements", "event_id")
