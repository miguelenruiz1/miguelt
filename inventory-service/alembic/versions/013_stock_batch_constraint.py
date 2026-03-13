"""Replace stock_levels unique constraint to include batch_id.

Revision ID: 013
Revises: 012
Create Date: 2026-03-02
"""
from alembic import op

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("uq_stock_product_warehouse", "stock_levels", type_="unique")
    op.execute(
        "CREATE UNIQUE INDEX uq_stock_product_warehouse_batch "
        "ON stock_levels (product_id, warehouse_id, COALESCE(batch_id, '___null___'))"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_stock_product_warehouse_batch")
    op.create_unique_constraint(
        "uq_stock_product_warehouse", "stock_levels", ["product_id", "warehouse_id"]
    )
