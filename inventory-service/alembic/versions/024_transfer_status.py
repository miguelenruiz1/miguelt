"""Add status and completed_at to stock_movements for 2-phase transfers."""
revision = "024"
down_revision = "023"

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.add_column("stock_movements", sa.Column("status", sa.String(20), nullable=False, server_default="completed"))
    op.add_column("stock_movements", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_stock_movements_status", "stock_movements", ["status"])


def downgrade() -> None:
    op.drop_index("ix_stock_movements_status", table_name="stock_movements")
    op.drop_column("stock_movements", "completed_at")
    op.drop_column("stock_movements", "status")
