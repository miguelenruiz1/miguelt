"""Add original_unit_price to sales_order_lines — stores the base price
when a special or manual price is applied, so the discount is visible.

Revision ID: 050
"""
from alembic import op
import sqlalchemy as sa

revision = "050"
down_revision = "049"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sales_order_lines",
        sa.Column("original_unit_price", sa.Numeric(12, 4), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("sales_order_lines", "original_unit_price")
