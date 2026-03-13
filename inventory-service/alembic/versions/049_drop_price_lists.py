"""Drop price_lists module — remove price_list_items, price_lists tables
and price_list_id from customers.

Revision ID: 049
"""
from alembic import op
import sqlalchemy as sa

revision = "049"
down_revision = "048"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Drop price_list_id FK from customers
    op.drop_constraint("customers_price_list_id_fkey", "customers", type_="foreignkey")
    op.drop_column("customers", "price_list_id")

    # 2. Drop unique index added in migration 019
    op.execute("DROP INDEX IF EXISTS uq_price_list_product_qty_variant")

    # 3. Drop tables in dependency order
    op.drop_table("price_list_items")
    op.drop_table("price_lists")


def downgrade() -> None:
    # Recreate price_lists
    op.create_table(
        "price_lists",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("is_default", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("updated_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "code", name="uq_price_list_tenant_code"),
    )
    op.create_index("ix_price_lists_tenant_id", "price_lists", ["tenant_id"])

    # Recreate price_list_items
    op.create_table(
        "price_list_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("price_list_id", sa.String(36), sa.ForeignKey("price_lists.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.String(36), sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("variant_id", sa.String(36), sa.ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("unit_price", sa.Numeric(14, 4), nullable=False),
        sa.Column("min_quantity", sa.Integer, nullable=False, server_default="1"),
        sa.Column("discount_pct", sa.Integer, nullable=False, server_default="0"),
    )
    op.create_index("ix_price_list_items_product_id", "price_list_items", ["product_id"])
    op.execute(
        "CREATE UNIQUE INDEX uq_price_list_product_qty_variant "
        "ON price_list_items (price_list_id, product_id, min_quantity, "
        "COALESCE(variant_id, '___null___'))"
    )

    # Re-add price_list_id to customers
    op.add_column(
        "customers",
        sa.Column("price_list_id", sa.String(36), nullable=True),
    )
    op.create_foreign_key(
        "customers_price_list_id_fkey",
        "customers",
        "price_lists",
        ["price_list_id"],
        ["id"],
        ondelete="SET NULL",
    )
