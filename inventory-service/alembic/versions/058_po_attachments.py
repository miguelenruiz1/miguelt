"""Add attachments JSONB column to purchase_orders.

Revision ID: 058
Revises: 057
Create Date: 2026-03-23
"""
from alembic import op
import sqlalchemy as sa

revision = "058"
down_revision = "057"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "purchase_orders",
        sa.Column("attachments", sa.JSON, nullable=True, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("purchase_orders", "attachments")
