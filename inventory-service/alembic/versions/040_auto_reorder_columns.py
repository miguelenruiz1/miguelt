"""Add auto-reorder columns to products and purchase_orders.

Revision ID: 040
Revises: 039
Create Date: 2026-03-12
"""
from alembic import op
import sqlalchemy as sa

revision = "040"
down_revision = "039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Product: preferred_supplier_id FK + auto_reorder flag
    op.add_column(
        "entities",
        sa.Column("preferred_supplier_id", sa.String(36), nullable=True),
    )
    op.add_column(
        "entities",
        sa.Column("auto_reorder", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_foreign_key(
        "fk_entities_preferred_supplier",
        "entities",
        "suppliers",
        ["preferred_supplier_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # PurchaseOrder: is_auto_generated flag + trigger stock snapshot
    op.add_column(
        "purchase_orders",
        sa.Column("is_auto_generated", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "purchase_orders",
        sa.Column("reorder_trigger_stock", sa.Numeric(12, 4), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("purchase_orders", "reorder_trigger_stock")
    op.drop_column("purchase_orders", "is_auto_generated")
    op.drop_constraint("fk_entities_preferred_supplier", "entities", type_="foreignkey")
    op.drop_column("entities", "auto_reorder")
    op.drop_column("entities", "preferred_supplier_id")
