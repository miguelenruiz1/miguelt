"""Widen Numeric(12,4) columns to Numeric(18,4) for COP amounts.

Revision ID: 072
Revises: 071
"""
from alembic import op

revision = "072"
down_revision = "071"


# All tables and columns that use Numeric(12,4)
COLUMNS_12_4 = [
    ("sales_orders", "total"),
    ("sales_order_lines", "qty_ordered"),
    ("sales_order_lines", "qty_shipped"),
    ("sales_order_lines", "original_quantity"),
    ("sales_order_lines", "unit_price"),
    ("sales_order_lines", "original_unit_price"),
    ("sales_order_lines", "discount_amount"),
    ("sales_order_lines", "line_subtotal"),
    ("purchase_orders", "reorder_trigger_stock"),
    ("purchase_order_lines", "qty_ordered"),
    ("purchase_order_lines", "qty_received"),
    ("purchase_order_lines", "unit_cost"),
    ("purchase_order_lines", "line_total"),
    ("stock_levels", "qty_on_hand"),
    ("stock_levels", "qty_reserved"),
    ("stock_levels", "qty_in_transit"),
    ("stock_levels", "weighted_avg_cost"),
    ("stock_movements", "quantity"),
    ("stock_movements", "original_qty"),
    ("stock_movements", "unit_cost"),
    ("stock_reservations", "quantity"),
    ("customer_prices", "price"),
    ("customer_prices", "min_quantity"),
    ("customer_price_history", "old_price"),
    ("customer_price_history", "new_price"),
    ("product_variants", "cost_price"),
    ("product_variants", "sale_price"),
]


def upgrade() -> None:
    for table, col in COLUMNS_12_4:
        op.execute(f"ALTER TABLE {table} ALTER COLUMN {col} TYPE NUMERIC(18,4)")


def downgrade() -> None:
    for table, col in COLUMNS_12_4:
        op.execute(f"ALTER TABLE {table} ALTER COLUMN {col} TYPE NUMERIC(12,4)")
