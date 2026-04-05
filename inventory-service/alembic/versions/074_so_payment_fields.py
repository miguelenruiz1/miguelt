"""Add payment_form and payment_method to sales_orders.

Revision ID: 074
Revises: 073
"""
from alembic import op
import sqlalchemy as sa

revision = "074"
down_revision = "073"


def upgrade() -> None:
    op.add_column("sales_orders", sa.Column("payment_form", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("sales_orders", sa.Column("payment_method", sa.Integer(), nullable=False, server_default="10"))


def downgrade() -> None:
    op.drop_column("sales_orders", "payment_method")
    op.drop_column("sales_orders", "payment_form")
