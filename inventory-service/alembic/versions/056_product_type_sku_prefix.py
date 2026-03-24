"""Add sku_prefix to product_types.

Revision ID: 056
Revises: 055
Create Date: 2026-03-16
"""
from alembic import op
import sqlalchemy as sa

revision = "056"
down_revision = "055"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("product_types", sa.Column("sku_prefix", sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column("product_types", "sku_prefix")
