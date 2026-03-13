"""Add warehouse_id to sales_order_lines for multi-warehouse dispatch.

Revision: 036
Down revision: 035
"""

revision = "036"
down_revision = "035"

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.add_column(
        "sales_order_lines",
        sa.Column("warehouse_id", sa.String(36), sa.ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True),
    )
    # Backfill: inherit warehouse_id from parent SO
    op.execute("""
        UPDATE sales_order_lines sol
        SET warehouse_id = so.warehouse_id
        FROM sales_orders so
        WHERE sol.order_id = so.id
        AND so.warehouse_id IS NOT NULL
    """)


def downgrade() -> None:
    op.drop_column("sales_order_lines", "warehouse_id")
