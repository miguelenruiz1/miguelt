"""Model fixes: StockLevel.created_at, SalesOrder metadata→extra_data, SerialStatus timestamps.

M-03: Add created_at to stock_levels
M-05: Rename sales_orders.metadata to extra_data
M-09: Add created_at/updated_at to serial_statuses
"""
revision = "029"
down_revision = "028"

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    # ── M-03: StockLevel.created_at ───────────────────────────────────
    op.add_column("stock_levels", sa.Column(
        "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True,
    ))
    # Backfill from updated_at
    op.execute("UPDATE stock_levels SET created_at = updated_at WHERE created_at IS NULL")
    op.alter_column("stock_levels", "created_at", nullable=False)

    # ── M-05: Rename sales_orders.metadata → extra_data ───────────────
    op.alter_column("sales_orders", "metadata", new_column_name="extra_data")

    # ── M-09: SerialStatus timestamps ─────────────────────────────────
    op.add_column("serial_statuses", sa.Column(
        "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True,
    ))
    op.add_column("serial_statuses", sa.Column(
        "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True,
    ))
    # Backfill
    op.execute("UPDATE serial_statuses SET created_at = now() WHERE created_at IS NULL")
    op.execute("UPDATE serial_statuses SET updated_at = now() WHERE updated_at IS NULL")
    op.alter_column("serial_statuses", "created_at", nullable=False)
    op.alter_column("serial_statuses", "updated_at", nullable=False)


def downgrade() -> None:
    op.drop_column("serial_statuses", "updated_at")
    op.drop_column("serial_statuses", "created_at")
    op.alter_column("sales_orders", "extra_data", new_column_name="metadata")
    op.drop_column("stock_levels", "created_at")
