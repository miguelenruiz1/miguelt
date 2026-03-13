"""Add batch_id FK to stock_alerts for expiry tracking."""
revision = "027"
down_revision = "026"

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.add_column(
        "stock_alerts",
        sa.Column("batch_id", sa.String(36), sa.ForeignKey("entity_batches.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_stock_alerts_batch_id", "stock_alerts", ["batch_id"])


def downgrade() -> None:
    op.drop_index("ix_stock_alerts_batch_id", table_name="stock_alerts")
    op.drop_column("stock_alerts", "batch_id")
