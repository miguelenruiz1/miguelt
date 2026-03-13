"""Add UoM tracking to stock movements.

- uom: records which unit of measure was used when creating the movement
- original_qty: stores the original quantity before conversion (audit trail)
"""
revision = "026"
down_revision = "025"

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.add_column(
        "stock_movements",
        sa.Column("uom", sa.String(20), nullable=False, server_default="primary"),
    )
    op.add_column(
        "stock_movements",
        sa.Column("original_qty", sa.Numeric(12, 4), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("stock_movements", "original_qty")
    op.drop_column("stock_movements", "uom")
