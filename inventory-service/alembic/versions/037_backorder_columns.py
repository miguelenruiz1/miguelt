"""Add backorder columns to sales_orders and sales_order_lines.

Revision ID: 037
Revises: 036
"""
import sqlalchemy as sa
from alembic import op

revision = "037"
down_revision = "036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SalesOrder: backorder support columns
    op.add_column("sales_orders", sa.Column("is_backorder", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("sales_orders", sa.Column("parent_so_id", sa.String(36), sa.ForeignKey("sales_orders.id", ondelete="SET NULL"), nullable=True))
    op.add_column("sales_orders", sa.Column("backorder_number", sa.Integer(), nullable=False, server_default="0"))
    op.create_index("ix_sales_orders_parent_so_id", "sales_orders", ["parent_so_id"])

    # SalesOrderLine: original_quantity + backorder_line_id
    op.add_column("sales_order_lines", sa.Column("original_quantity", sa.Numeric(12, 4), nullable=True))
    op.add_column("sales_order_lines", sa.Column("backorder_line_id", sa.String(36), sa.ForeignKey("sales_order_lines.id", ondelete="SET NULL"), nullable=True))

    # Backfill original_quantity = qty_ordered for existing lines
    op.execute("UPDATE sales_order_lines SET original_quantity = qty_ordered WHERE original_quantity IS NULL")


def downgrade() -> None:
    op.drop_column("sales_order_lines", "backorder_line_id")
    op.drop_column("sales_order_lines", "original_quantity")
    op.drop_index("ix_sales_orders_parent_so_id", "sales_orders")
    op.drop_column("sales_orders", "backorder_number")
    op.drop_column("sales_orders", "parent_so_id")
    op.drop_column("sales_orders", "is_backorder")
