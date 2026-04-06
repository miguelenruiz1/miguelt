"""Fix currency default from USD to COP.

Revision ID: 075
Revises: 074
"""
from alembic import op

revision = "075"
down_revision = "074"


def upgrade() -> None:
    op.execute("ALTER TABLE sales_orders ALTER COLUMN currency SET DEFAULT 'COP'")
    op.execute("UPDATE sales_orders SET currency = 'COP' WHERE currency = 'USD'")


def downgrade() -> None:
    op.execute("ALTER TABLE sales_orders ALTER COLUMN currency SET DEFAULT 'USD'")
