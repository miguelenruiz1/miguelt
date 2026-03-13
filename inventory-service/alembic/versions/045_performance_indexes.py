"""Add performance indexes for stock traceability and warehouse type lookups."""
from alembic import op

revision = "045"
down_revision = "044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_stock_level_traceability", "stock_levels", ["tenant_id", "batch_id", "variant_id"])
    op.create_index("ix_warehouses_warehouse_type_id", "warehouses", ["warehouse_type_id"])


def downgrade() -> None:
    op.drop_index("ix_warehouses_warehouse_type_id", table_name="warehouses")
    op.drop_index("ix_stock_level_traceability", table_name="stock_levels")
