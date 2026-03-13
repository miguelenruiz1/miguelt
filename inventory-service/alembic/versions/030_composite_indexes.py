"""Add composite indexes for common query patterns.

P-01: Composite indexes on stock_levels, stock_movements, sales_orders,
      purchase_orders, entity_batches for frequent multi-column queries.
"""
revision = "030"
down_revision = "029"

from alembic import op


def upgrade() -> None:
    # stock_levels: tenant + product + warehouse (most common query)
    op.create_index(
        "ix_stock_levels_tenant_product_wh",
        "stock_levels",
        ["tenant_id", "product_id", "warehouse_id"],
    )

    # stock_movements: tenant + product + created_at (analytics, trend)
    op.create_index(
        "ix_stock_movements_tenant_product_created",
        "stock_movements",
        ["tenant_id", "product_id", "created_at"],
    )
    # stock_movements: tenant + movement_type + created_at (by-type queries)
    op.create_index(
        "ix_stock_movements_tenant_type_created",
        "stock_movements",
        ["tenant_id", "movement_type", "created_at"],
    )

    # sales_orders: tenant + status (list filtered by status)
    op.create_index(
        "ix_sales_orders_tenant_status",
        "sales_orders",
        ["tenant_id", "status"],
    )

    # purchase_orders: tenant + status (list filtered by status)
    op.create_index(
        "ix_purchase_orders_tenant_status",
        "purchase_orders",
        ["tenant_id", "status"],
    )

    # entity_batches: tenant + entity + is_active (FEFO dispatch queries)
    op.create_index(
        "ix_entity_batches_tenant_entity_active",
        "entity_batches",
        ["tenant_id", "entity_id", "is_active"],
    )


def downgrade() -> None:
    op.drop_index("ix_entity_batches_tenant_entity_active", table_name="entity_batches")
    op.drop_index("ix_purchase_orders_tenant_status", table_name="purchase_orders")
    op.drop_index("ix_sales_orders_tenant_status", table_name="sales_orders")
    op.drop_index("ix_stock_movements_tenant_type_created", table_name="stock_movements")
    op.drop_index("ix_stock_movements_tenant_product_created", table_name="stock_movements")
    op.drop_index("ix_stock_levels_tenant_product_wh", table_name="stock_levels")
