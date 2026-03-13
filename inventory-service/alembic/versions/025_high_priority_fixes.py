"""HIGH priority fixes: tenant_id on line tables, FK constraints, indexes, type fixes.

H-01: Add tenant_id to purchase_order_lines, sales_order_lines, recipe_components
H-02: Add FK on custom_product_fields.product_type_id
H-08: Add location_id to purchase_order_lines
M-08: Add indexes on stock_movements.from_warehouse_id/to_warehouse_id
M-10: Change price_list_items.unit_price from FLOAT to NUMERIC(14,4)
"""
revision = "025"
down_revision = "024"

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    # ── H-01: tenant_id on line tables ──────────────────────────────
    # purchase_order_lines
    op.add_column("purchase_order_lines", sa.Column("tenant_id", sa.String(255), nullable=True))
    op.execute("""
        UPDATE purchase_order_lines pol
        SET tenant_id = po.tenant_id
        FROM purchase_orders po
        WHERE pol.po_id = po.id
    """)
    # Fallback: if there are orphan lines with no matching PO
    op.execute("""
        UPDATE purchase_order_lines SET tenant_id = 'default' WHERE tenant_id IS NULL
    """)
    op.alter_column("purchase_order_lines", "tenant_id", nullable=False)
    op.create_index("ix_purchase_order_lines_tenant_id", "purchase_order_lines", ["tenant_id"])

    # sales_order_lines
    op.add_column("sales_order_lines", sa.Column("tenant_id", sa.String(255), nullable=True))
    op.execute("""
        UPDATE sales_order_lines sol
        SET tenant_id = so.tenant_id
        FROM sales_orders so
        WHERE sol.order_id = so.id
    """)
    op.execute("""
        UPDATE sales_order_lines SET tenant_id = 'default' WHERE tenant_id IS NULL
    """)
    op.alter_column("sales_order_lines", "tenant_id", nullable=False)
    op.create_index("ix_sales_order_lines_tenant_id", "sales_order_lines", ["tenant_id"])

    # recipe_components
    op.add_column("recipe_components", sa.Column("tenant_id", sa.String(255), nullable=True))
    op.execute("""
        UPDATE recipe_components rc
        SET tenant_id = er.tenant_id
        FROM entity_recipes er
        WHERE rc.recipe_id = er.id
    """)
    op.execute("""
        UPDATE recipe_components SET tenant_id = 'default' WHERE tenant_id IS NULL
    """)
    op.alter_column("recipe_components", "tenant_id", nullable=False)
    op.create_index("ix_recipe_components_tenant_id", "recipe_components", ["tenant_id"])

    # ── H-02: FK on custom_product_fields.product_type_id ───────────
    op.create_foreign_key(
        "fk_custom_product_fields_product_type",
        "custom_product_fields", "product_types",
        ["product_type_id"], ["id"],
        ondelete="CASCADE",
    )

    # ── H-08: location_id on purchase_order_lines ───────────────────
    op.add_column("purchase_order_lines", sa.Column(
        "location_id", sa.String(36), nullable=True,
    ))
    op.create_foreign_key(
        "fk_po_lines_location",
        "purchase_order_lines", "warehouse_locations",
        ["location_id"], ["id"],
        ondelete="SET NULL",
    )

    # ── M-08: indexes on stock_movements warehouse FKs ──────────────
    op.create_index("ix_stock_movements_from_warehouse", "stock_movements", ["from_warehouse_id"])
    op.create_index("ix_stock_movements_to_warehouse", "stock_movements", ["to_warehouse_id"])

    # ── M-10: unit_price FLOAT → NUMERIC(14,4) ─────────────────────
    op.alter_column(
        "price_list_items", "unit_price",
        type_=sa.Numeric(14, 4),
        existing_type=sa.Float(),
        existing_nullable=False,
        postgresql_using="unit_price::numeric(14,4)",
    )


def downgrade() -> None:
    op.alter_column(
        "price_list_items", "unit_price",
        type_=sa.Float(),
        existing_type=sa.Numeric(14, 4),
        existing_nullable=False,
    )
    op.drop_index("ix_stock_movements_to_warehouse", table_name="stock_movements")
    op.drop_index("ix_stock_movements_from_warehouse", table_name="stock_movements")
    op.drop_constraint("fk_po_lines_location", "purchase_order_lines", type_="foreignkey")
    op.drop_column("purchase_order_lines", "location_id")
    op.drop_constraint("fk_custom_product_fields_product_type", "custom_product_fields", type_="foreignkey")
    op.drop_index("ix_recipe_components_tenant_id", table_name="recipe_components")
    op.drop_column("recipe_components", "tenant_id")
    op.drop_index("ix_sales_order_lines_tenant_id", table_name="sales_order_lines")
    op.drop_column("sales_order_lines", "tenant_id")
    op.drop_index("ix_purchase_order_lines_tenant_id", table_name="purchase_order_lines")
    op.drop_column("purchase_order_lines", "tenant_id")
