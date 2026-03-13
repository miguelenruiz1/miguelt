"""Add invoice_number column to sales_orders."""

revision = "034"
down_revision = "033"

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.add_column(
        "sales_orders",
        sa.Column("invoice_number", sa.String(50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("sales_orders", "invoice_number")
