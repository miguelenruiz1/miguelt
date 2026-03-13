"""Enterprise inventory features: valuation method, secondary UOM, stock indexes,
variant_id on sales order lines, batch expiration alerts.

Revision ID: 018
Revises: 017
Create Date: 2026-03-05
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "018"
down_revision: Union[str, None] = "017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add valuation_method to products (weighted_average is default, also fifo, lifo)
    op.add_column("entities", sa.Column(
        "valuation_method", sa.String(20), nullable=False, server_default="weighted_average"
    ))
    # 2. Secondary UOM support on products
    op.add_column("entities", sa.Column("secondary_uom", sa.String(50), nullable=True))
    op.add_column("entities", sa.Column(
        "uom_conversion_factor", sa.Numeric(12, 6), nullable=True,
    ))
    # 3. Add variant_id FK to sales_order_lines so variants can be sold
    op.add_column("sales_order_lines", sa.Column(
        "variant_id", sa.String(36),
        sa.ForeignKey("product_variants.id", ondelete="SET NULL"),
        nullable=True,
    ))
    # 4. Performance indexes on stock_levels
    op.create_index(
        "ix_stock_levels_product_warehouse",
        "stock_levels",
        ["product_id", "warehouse_id"],
    )
    op.create_index(
        "ix_stock_levels_warehouse",
        "stock_levels",
        ["warehouse_id"],
    )
    # 5. Replace plain index with partial index on entity_batches.expiration_date
    op.execute("DROP INDEX IF EXISTS ix_entity_batches_expiration")
    op.create_index(
        "ix_entity_batches_expiration",
        "entity_batches",
        ["expiration_date"],
        postgresql_where=sa.text("expiration_date IS NOT NULL"),
    )
    # 6. Add weighted_average_cost tracking column to stock_levels
    op.add_column("stock_levels", sa.Column(
        "weighted_avg_cost", sa.Numeric(12, 4), nullable=True,
    ))


def downgrade() -> None:
    op.drop_column("stock_levels", "weighted_avg_cost")
    op.drop_index("ix_entity_batches_expiration", table_name="entity_batches")
    op.drop_index("ix_stock_levels_warehouse", table_name="stock_levels")
    op.drop_index("ix_stock_levels_product_warehouse", table_name="stock_levels")
    op.drop_column("sales_order_lines", "variant_id")
    op.drop_column("entities", "uom_conversion_factor")
    op.drop_column("entities", "secondary_uom")
    op.drop_column("entities", "valuation_method")
