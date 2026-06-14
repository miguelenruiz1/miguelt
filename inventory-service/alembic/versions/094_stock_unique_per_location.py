"""Stock unique per bin: add location_id to stock_levels unique index.

The WM module (bins, putaway, movement orders) needs the same product to live
in multiple bins of the same warehouse. The old unique index
`uq_stock_product_warehouse_batch_variant` did NOT include location_id, so a
second bin for the same (product, warehouse, batch, variant) raised a
UniqueViolation (500 on /stock/receive). Adding location_id to the key is
strictly more permissive — every row unique under the old key stays unique
under the new one, so no data backfill or violation is possible.

Revision: 094
Revises: 093
"""
from alembic import op


revision = "094"
down_revision = "093"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_stock_product_warehouse_batch_variant")
    op.execute(
        "CREATE UNIQUE INDEX uq_stock_product_warehouse_batch_variant "
        "ON stock_levels (product_id, warehouse_id, "
        "COALESCE(batch_id, '___null___'), COALESCE(variant_id, '___null___'), "
        "COALESCE(location_id, '___null___'))"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_stock_product_warehouse_batch_variant")
    op.execute(
        "CREATE UNIQUE INDEX uq_stock_product_warehouse_batch_variant "
        "ON stock_levels (product_id, warehouse_id, "
        "COALESCE(batch_id, '___null___'), COALESCE(variant_id, '___null___'))"
    )
