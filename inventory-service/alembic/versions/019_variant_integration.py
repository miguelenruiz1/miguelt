"""Add variant_id FK to stock_levels, stock_movements, purchase_order_lines,
price_list_items; update unique constraints to include variant_id.

Revision ID: 019
Revises: 018
Create Date: 2026-03-06
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "019"
down_revision: Union[str, None] = "018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add variant_id FK to stock_levels
    op.add_column("stock_levels", sa.Column(
        "variant_id", sa.String(36),
        sa.ForeignKey("product_variants.id", ondelete="SET NULL"),
        nullable=True,
    ))

    # 2. Add variant_id FK to stock_movements
    op.add_column("stock_movements", sa.Column(
        "variant_id", sa.String(36),
        sa.ForeignKey("product_variants.id", ondelete="SET NULL"),
        nullable=True,
    ))

    # 3. Add variant_id FK to purchase_order_lines
    op.add_column("purchase_order_lines", sa.Column(
        "variant_id", sa.String(36),
        sa.ForeignKey("product_variants.id", ondelete="SET NULL"),
        nullable=True,
    ))

    # 4. Add variant_id FK to price_list_items
    op.add_column("price_list_items", sa.Column(
        "variant_id", sa.String(36),
        sa.ForeignKey("product_variants.id", ondelete="SET NULL"),
        nullable=True,
    ))

    # 5. Update stock_levels unique index to include variant_id
    #    Drop old index from migration 013, create new one with variant_id
    op.execute("DROP INDEX IF EXISTS uq_stock_product_warehouse_batch")
    op.execute(
        "CREATE UNIQUE INDEX uq_stock_product_warehouse_batch_variant "
        "ON stock_levels (product_id, warehouse_id, "
        "COALESCE(batch_id, '___null___'), COALESCE(variant_id, '___null___'))"
    )

    # 6. Update price_list_items unique constraint to include variant_id
    op.drop_constraint("uq_price_list_product_qty", "price_list_items", type_="unique")
    op.execute(
        "CREATE UNIQUE INDEX uq_price_list_product_qty_variant "
        "ON price_list_items (price_list_id, product_id, min_quantity, "
        "COALESCE(variant_id, '___null___'))"
    )


def downgrade() -> None:
    # Revert price_list_items constraint
    op.execute("DROP INDEX IF EXISTS uq_price_list_product_qty_variant")
    op.create_unique_constraint(
        "uq_price_list_product_qty", "price_list_items",
        ["price_list_id", "product_id", "min_quantity"],
    )

    # Revert stock_levels constraint
    op.execute("DROP INDEX IF EXISTS uq_stock_product_warehouse_batch_variant")
    op.execute(
        "CREATE UNIQUE INDEX uq_stock_product_warehouse_batch "
        "ON stock_levels (product_id, warehouse_id, COALESCE(batch_id, '___null___'))"
    )

    # Remove variant_id columns
    op.drop_column("price_list_items", "variant_id")
    op.drop_column("purchase_order_lines", "variant_id")
    op.drop_column("stock_movements", "variant_id")
    op.drop_column("stock_levels", "variant_id")
