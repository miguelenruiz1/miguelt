"""Add invoice_provider column to sales_orders.

Revision ID: 032
Revises: 031
"""
from alembic import op
import sqlalchemy as sa

revision = "032"
down_revision = "031"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "sales_orders",
        sa.Column("invoice_provider", sa.String(50), nullable=True),
    )


def downgrade():
    op.drop_column("sales_orders", "invoice_provider")
