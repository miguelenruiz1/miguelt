"""Costing engine — add cost columns to stock_movements, seed layers for existing stock.

Revision ID: 057
Revises: 056
Create Date: 2026-03-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "057"
down_revision = "056"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add cost_total and layer_consumed_ids to stock_movements (if not already present)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_cols = {c["name"] for c in inspector.get_columns("stock_movements")}

    if "cost_total" not in existing_cols:
        op.add_column("stock_movements", sa.Column("cost_total", sa.Numeric(14, 4), nullable=True))
    if "layer_consumed_ids" not in existing_cols:
        op.add_column("stock_movements", sa.Column("layer_consumed_ids", JSONB, nullable=True))

    # 2. Seed StockLayers for existing StockLevels with qty_on_hand > 0 that have no layers yet
    op.execute(sa.text("""
        INSERT INTO stock_layers (id, tenant_id, entity_id, warehouse_id, quantity_initial, quantity_remaining, unit_cost, created_at)
        SELECT
            gen_random_uuid()::text,
            sl.tenant_id,
            sl.product_id,
            sl.warehouse_id,
            sl.qty_on_hand,
            sl.qty_on_hand,
            COALESCE(sl.weighted_avg_cost, 0),
            NOW()
        FROM stock_levels sl
        WHERE sl.qty_on_hand > 0
          AND NOT EXISTS (
              SELECT 1 FROM stock_layers lyr
              WHERE lyr.entity_id = sl.product_id
                AND lyr.warehouse_id = sl.warehouse_id
                AND lyr.quantity_remaining > 0
          )
    """))

    # 3. Update weighted_avg_cost on StockLevels that have layers but NULL avg cost
    op.execute(sa.text("""
        UPDATE stock_levels sl
        SET weighted_avg_cost = sub.avg_cost
        FROM (
            SELECT entity_id, warehouse_id,
                   CASE WHEN SUM(quantity_remaining) > 0
                        THEN SUM(quantity_remaining * unit_cost) / SUM(quantity_remaining)
                        ELSE 0
                   END AS avg_cost
            FROM stock_layers
            WHERE quantity_remaining > 0
            GROUP BY entity_id, warehouse_id
        ) sub
        WHERE sl.product_id = sub.entity_id
          AND sl.warehouse_id = sub.warehouse_id
          AND sl.weighted_avg_cost IS NULL
          AND sl.qty_on_hand > 0
    """))


def downgrade() -> None:
    op.drop_column("stock_movements", "layer_consumed_ids")
    op.drop_column("stock_movements", "cost_total")
