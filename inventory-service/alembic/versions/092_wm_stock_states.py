"""WM stock states: stock_type on stock_levels.

Revision: 092
Revises: 091
"""
from alembic import op
import sqlalchemy as sa


revision = "092"
down_revision = "091"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "stock_levels",
        sa.Column("stock_type", sa.String(15), nullable=False, server_default="available"),
    )
    op.create_index("ix_stock_levels_stock_type", "stock_levels", ["tenant_id", "stock_type"])


def downgrade() -> None:
    op.drop_index("ix_stock_levels_stock_type", table_name="stock_levels")
    op.drop_column("stock_levels", "stock_type")
