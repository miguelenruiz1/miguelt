"""Change stock_movements.product_id to ondelete=RESTRICT.

Prevents accidental kardex/history loss when a product is hard-deleted.
Soft delete (Product.is_active=false) is the supported pattern.

Revision ID: 077
Revises: 076
"""
from alembic import op
import sqlalchemy as sa

revision = "077"
down_revision = "076"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE stock_movements
        DROP CONSTRAINT IF EXISTS stock_movements_product_id_fkey
        """
    )
    op.create_foreign_key(
        "stock_movements_product_id_fkey",
        "stock_movements",
        "entities",
        ["product_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("stock_movements_product_id_fkey", "stock_movements", type_="foreignkey")
    op.create_foreign_key(
        "stock_movements_product_id_fkey",
        "stock_movements",
        "entities",
        ["product_id"],
        ["id"],
        ondelete="CASCADE",
    )
