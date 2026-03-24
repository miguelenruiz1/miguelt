"""Dynamic pricing, UoM system, and cost history.

Revision ID: 052
Revises: 051
Create Date: 2026-03-14
"""
from alembic import op
import sqlalchemy as sa

revision = "052"
down_revision = "051"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "units_of_measure",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("is_base", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "symbol", name="uq_uom_tenant_symbol"),
    )
    op.create_index("ix_uom_tenant_id", "units_of_measure", ["tenant_id"])

    op.create_table(
        "uom_conversions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("from_uom_id", sa.String(36), sa.ForeignKey("units_of_measure.id", ondelete="CASCADE"), nullable=False),
        sa.Column("to_uom_id", sa.String(36), sa.ForeignKey("units_of_measure.id", ondelete="CASCADE"), nullable=False),
        sa.Column("factor", sa.Numeric(20, 10), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.UniqueConstraint("tenant_id", "from_uom_id", "to_uom_id", name="uq_uom_conv_tenant_from_to"),
    )
    op.create_index("ix_uom_conv_tenant_id", "uom_conversions", ["tenant_id"])

    op.create_table(
        "product_cost_history",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("product_id", sa.String(36), sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("variant_id", sa.String(36), sa.ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("purchase_order_id", sa.String(36), sa.ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("purchase_order_line_id", sa.String(36), sa.ForeignKey("purchase_order_lines.id", ondelete="CASCADE"), nullable=False),
        sa.Column("supplier_id", sa.String(36), sa.ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("supplier_name", sa.String(255), nullable=False),
        sa.Column("uom_purchased", sa.String(20), nullable=False),
        sa.Column("qty_purchased", sa.Numeric(15, 6), nullable=False),
        sa.Column("qty_in_base_uom", sa.Numeric(15, 6), nullable=False),
        sa.Column("unit_cost_purchased", sa.Numeric(14, 6), nullable=False),
        sa.Column("unit_cost_base_uom", sa.Numeric(14, 6), nullable=False),
        sa.Column("total_cost", sa.Numeric(16, 6), nullable=False),
        sa.Column("market_note", sa.Text, nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_cost_history_tenant_product_date", "product_cost_history", ["tenant_id", "product_id", "received_at"])
    op.create_index("ix_cost_history_supplier", "product_cost_history", ["supplier_id"])
    op.create_index("ix_cost_history_product_tenant", "product_cost_history", ["product_id", "tenant_id"])

    op.add_column("purchase_order_lines", sa.Column("uom", sa.String(20), nullable=True))
    op.add_column("purchase_order_lines", sa.Column("qty_in_base_uom", sa.Numeric(15, 6), nullable=True))

    op.add_column("sales_order_lines", sa.Column("uom", sa.String(20), nullable=True))
    op.add_column("sales_order_lines", sa.Column("qty_in_base_uom", sa.Numeric(15, 6), nullable=True))
    op.add_column("sales_order_lines", sa.Column("margin_pct", sa.Numeric(7, 4), nullable=True))

    # Drop the products view (SELECT * FROM entities) before altering columns
    op.execute("DROP VIEW IF EXISTS products")

    op.drop_column("entities", "cost_price")
    op.drop_column("entities", "sale_price")
    op.drop_column("entities", "currency")
    op.drop_column("entities", "secondary_uom")
    op.drop_column("entities", "uom_conversion_factor")

    op.add_column("entities", sa.Column("margin_target", sa.Numeric(5, 2), nullable=True))
    op.add_column("entities", sa.Column("margin_minimum", sa.Numeric(5, 2), nullable=True))
    op.add_column("entities", sa.Column("margin_cost_method", sa.String(20), server_default="last_purchase", nullable=False))
    op.add_column("entities", sa.Column("last_purchase_cost", sa.Numeric(14, 6), nullable=True))
    op.add_column("entities", sa.Column("last_purchase_date", sa.DateTime(timezone=True), nullable=True))
    op.add_column("entities", sa.Column("last_purchase_supplier", sa.String(255), nullable=True))
    op.add_column("entities", sa.Column("suggested_sale_price", sa.Numeric(14, 6), nullable=True))
    op.add_column("entities", sa.Column("minimum_sale_price", sa.Numeric(14, 6), nullable=True))
    op.add_column("entities", sa.Column("preferred_currency", sa.String(3), server_default="COP", nullable=False))

    # Recreate the products view with the new column set
    op.execute("CREATE OR REPLACE VIEW products AS SELECT * FROM entities")

    op.add_column("tenant_inventory_configs", sa.Column("margin_target_global", sa.Numeric(5, 2), server_default="35.00", nullable=False))
    op.add_column("tenant_inventory_configs", sa.Column("margin_minimum_global", sa.Numeric(5, 2), server_default="20.00", nullable=False))
    op.add_column("tenant_inventory_configs", sa.Column("margin_cost_method_global", sa.String(20), server_default="last_purchase", nullable=False))
    op.add_column("tenant_inventory_configs", sa.Column("below_minimum_requires_auth", sa.Boolean, server_default="true", nullable=False))


def downgrade() -> None:
    op.drop_column("tenant_inventory_configs", "below_minimum_requires_auth")
    op.drop_column("tenant_inventory_configs", "margin_cost_method_global")
    op.drop_column("tenant_inventory_configs", "margin_minimum_global")
    op.drop_column("tenant_inventory_configs", "margin_target_global")

    op.execute("DROP VIEW IF EXISTS products")

    op.drop_column("entities", "preferred_currency")
    op.drop_column("entities", "minimum_sale_price")
    op.drop_column("entities", "suggested_sale_price")
    op.drop_column("entities", "last_purchase_supplier")
    op.drop_column("entities", "last_purchase_date")
    op.drop_column("entities", "last_purchase_cost")
    op.drop_column("entities", "margin_cost_method")
    op.drop_column("entities", "margin_minimum")
    op.drop_column("entities", "margin_target")

    op.add_column("entities", sa.Column("uom_conversion_factor", sa.Numeric(12, 6), nullable=True))
    op.add_column("entities", sa.Column("secondary_uom", sa.String(50), nullable=True))
    op.add_column("entities", sa.Column("currency", sa.String(3), nullable=False, server_default="USD"))
    op.add_column("entities", sa.Column("sale_price", sa.Numeric(12, 4), nullable=False, server_default="0"))
    op.add_column("entities", sa.Column("cost_price", sa.Numeric(12, 4), nullable=False, server_default="0"))

    op.execute("CREATE OR REPLACE VIEW products AS SELECT * FROM entities")

    op.drop_column("sales_order_lines", "margin_pct")
    op.drop_column("sales_order_lines", "qty_in_base_uom")
    op.drop_column("sales_order_lines", "uom")
    op.drop_column("purchase_order_lines", "qty_in_base_uom")
    op.drop_column("purchase_order_lines", "uom")

    op.drop_index("ix_cost_history_product_tenant", table_name="product_cost_history")
    op.drop_index("ix_cost_history_supplier", table_name="product_cost_history")
    op.drop_index("ix_cost_history_tenant_product_date", table_name="product_cost_history")
    op.drop_table("product_cost_history")
    op.drop_index("ix_uom_conv_tenant_id", table_name="uom_conversions")
    op.drop_table("uom_conversions")
    op.drop_index("ix_uom_tenant_id", table_name="units_of_measure")
    op.drop_table("units_of_measure")
