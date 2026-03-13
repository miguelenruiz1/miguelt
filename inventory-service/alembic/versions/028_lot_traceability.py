"""Add batch_id FK to stock_movements and sales_order_lines for lot traceability."""
revision = "028"
down_revision = "027"

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    # stock_movements.batch_id
    op.add_column(
        "stock_movements",
        sa.Column(
            "batch_id",
            sa.String(36),
            sa.ForeignKey("entity_batches.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_stock_movements_batch_id", "stock_movements", ["batch_id"])

    # sales_order_lines.batch_id
    op.add_column(
        "sales_order_lines",
        sa.Column(
            "batch_id",
            sa.String(36),
            sa.ForeignKey("entity_batches.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_sales_order_lines_batch_id", "sales_order_lines", ["batch_id"])


def downgrade() -> None:
    op.drop_index("ix_sales_order_lines_batch_id", table_name="sales_order_lines")
    op.drop_column("sales_order_lines", "batch_id")
    op.drop_index("ix_stock_movements_batch_id", table_name="stock_movements")
    op.drop_column("stock_movements", "batch_id")
