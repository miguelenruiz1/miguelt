"""Add discount columns to sales_orders and sales_order_lines.

- SalesOrderLine: change discount_pct from Integer to Numeric(5,2),
  add discount_amount and line_subtotal
- SalesOrder: add discount_pct, discount_reason

Revision ID: 038
Revises: 037
"""
import sqlalchemy as sa
from alembic import op

revision = "038"
down_revision = "037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── SalesOrderLine changes ──
    # Change discount_pct from Integer to Numeric(5,2)
    op.alter_column(
        "sales_order_lines", "discount_pct",
        type_=sa.Numeric(5, 2),
        existing_type=sa.Integer(),
        existing_nullable=False,
        existing_server_default="0",
        postgresql_using="discount_pct::numeric(5,2)",
    )
    # Add discount_amount and line_subtotal
    op.add_column("sales_order_lines", sa.Column("discount_amount", sa.Numeric(12, 4), nullable=False, server_default="0"))
    op.add_column("sales_order_lines", sa.Column("line_subtotal", sa.Numeric(12, 4), nullable=False, server_default="0"))

    # Backfill: discount_amount = unit_price * qty_ordered * discount_pct / 100
    #           line_subtotal = unit_price * qty_ordered - discount_amount
    op.execute("""
        UPDATE sales_order_lines SET
            discount_amount = ROUND(unit_price * qty_ordered * discount_pct / 100, 4),
            line_subtotal = ROUND(unit_price * qty_ordered - (unit_price * qty_ordered * discount_pct / 100), 4)
    """)

    # ── SalesOrder changes ──
    op.add_column("sales_orders", sa.Column("discount_pct", sa.Numeric(5, 2), nullable=False, server_default="0"))
    op.add_column("sales_orders", sa.Column("discount_reason", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("sales_orders", "discount_reason")
    op.drop_column("sales_orders", "discount_pct")
    op.drop_column("sales_order_lines", "line_subtotal")
    op.drop_column("sales_order_lines", "discount_amount")
    op.alter_column(
        "sales_order_lines", "discount_pct",
        type_=sa.Integer(),
        existing_type=sa.Numeric(5, 2),
        existing_nullable=False,
        existing_server_default="0",
        postgresql_using="discount_pct::integer",
    )
