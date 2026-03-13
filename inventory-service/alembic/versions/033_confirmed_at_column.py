"""Add confirmed_at column to sales_orders."""

revision = "033"
down_revision = "032"

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.add_column(
        "sales_orders",
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("sales_orders", "confirmed_at")
