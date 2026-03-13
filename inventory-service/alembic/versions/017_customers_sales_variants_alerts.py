"""Add customers, sales orders, product variants, price lists, stock alerts.

Revision ID: 017
Revises: 016
"""
revision = "017"
down_revision = "016"

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade() -> None:
    # ── Customer Types ──────────────────────────────────────────────────
    op.create_table(
        "customer_types",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("color", sa.String(7), nullable=False, server_default="#6366f1"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_by", sa.String(255), nullable=True),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_customer_type_tenant_slug"),
    )
    op.create_index("ix_customer_types_tenant_id", "customer_types", ["tenant_id"])

    # ── Price Lists ─────────────────────────────────────────────────────
    op.create_table(
        "price_lists",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
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

    op.create_table(
        "price_list_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("price_list_id", sa.String(36), sa.ForeignKey("price_lists.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.String(36), sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("unit_price", sa.Float, nullable=False),
        sa.Column("min_quantity", sa.Integer, nullable=False, server_default="1"),
        sa.Column("discount_pct", sa.Integer, nullable=False, server_default="0"),
        sa.UniqueConstraint("price_list_id", "product_id", "min_quantity", name="uq_price_list_product_qty"),
    )
    op.create_index("ix_price_list_items_product_id", "price_list_items", ["product_id"])

    # ── Customers ───────────────────────────────────────────────────────
    op.create_table(
        "customers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("customer_type_id", sa.String(36), sa.ForeignKey("customer_types.id", ondelete="SET NULL"), nullable=True),
        sa.Column("tax_id", sa.String(50), nullable=True),
        sa.Column("contact_name", sa.String(255), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("address", postgresql.JSONB, nullable=True),
        sa.Column("shipping_address", postgresql.JSONB, nullable=True),
        sa.Column("payment_terms_days", sa.Integer, nullable=False, server_default="30"),
        sa.Column("credit_limit", sa.Integer, nullable=False, server_default="0"),
        sa.Column("discount_percent", sa.Integer, nullable=False, server_default="0"),
        sa.Column("price_list_id", sa.String(36), sa.ForeignKey("price_lists.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("custom_attributes", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("updated_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "code", name="uq_customer_tenant_code"),
    )
    op.create_index("ix_customers_tenant_id", "customers", ["tenant_id"])

    # ── Sales Orders ────────────────────────────────────────────────────
    op.create_table(
        "sales_orders",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("order_number", sa.String(50), nullable=False),
        sa.Column("customer_id", sa.String(36), sa.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("warehouse_id", sa.String(36), sa.ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True),
        sa.Column("shipping_address", postgresql.JSONB, nullable=True),
        sa.Column("expected_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("shipped_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("subtotal", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("tax_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("discount_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("total", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_by", sa.String(255), nullable=True),
        sa.UniqueConstraint("tenant_id", "order_number", name="uq_sales_order_tenant_number"),
    )
    op.create_index("ix_sales_orders_tenant_id", "sales_orders", ["tenant_id"])
    op.create_index("ix_sales_orders_customer_id", "sales_orders", ["customer_id"])
    op.create_index("ix_sales_orders_status", "sales_orders", ["status"])

    op.create_table(
        "sales_order_lines",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("order_id", sa.String(36), sa.ForeignKey("sales_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.String(36), sa.ForeignKey("entities.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("qty_ordered", sa.Numeric(12, 4), nullable=False),
        sa.Column("qty_shipped", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("unit_price", sa.Numeric(12, 4), nullable=False),
        sa.Column("discount_pct", sa.Integer, nullable=False, server_default="0"),
        sa.Column("tax_rate", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("line_total", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text, nullable=True),
    )
    op.create_index("ix_sales_order_lines_order_id", "sales_order_lines", ["order_id"])

    # ── Variant Attributes ──────────────────────────────────────────────
    op.create_table(
        "variant_attributes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_variant_attr_tenant_slug"),
    )
    op.create_index("ix_variant_attributes_tenant_id", "variant_attributes", ["tenant_id"])

    op.create_table(
        "variant_attribute_options",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("attribute_id", sa.String(36), sa.ForeignKey("variant_attributes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("value", sa.String(100), nullable=False),
        sa.Column("color_hex", sa.String(7), nullable=True),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.UniqueConstraint("attribute_id", "value", name="uq_variant_option_attr_value"),
    )

    op.create_table(
        "product_variants",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("parent_id", sa.String(36), sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sku", sa.String(100), nullable=False),
        sa.Column("barcode", sa.String(100), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("cost_price", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("sale_price", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("weight", sa.Numeric(10, 3), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("option_values", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("images", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "sku", name="uq_variant_tenant_sku"),
    )
    op.create_index("ix_product_variants_tenant_id", "product_variants", ["tenant_id"])
    op.create_index("ix_product_variants_parent_id", "product_variants", ["parent_id"])

    # ── Stock Alerts ────────────────────────────────────────────────────
    op.create_table(
        "stock_alerts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("product_id", sa.String(36), sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("warehouse_id", sa.String(36), sa.ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True),
        sa.Column("alert_type", sa.String(30), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("current_qty", sa.Integer, nullable=False, server_default="0"),
        sa.Column("threshold_qty", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_read", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_resolved", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_stock_alerts_tenant_id", "stock_alerts", ["tenant_id"])
    op.create_index("ix_stock_alerts_product_id", "stock_alerts", ["product_id"])
    op.create_index("ix_stock_alerts_is_resolved", "stock_alerts", ["is_resolved"])


def downgrade() -> None:
    op.drop_table("stock_alerts")
    op.drop_table("product_variants")
    op.drop_table("variant_attribute_options")
    op.drop_table("variant_attributes")
    op.drop_table("sales_order_lines")
    op.drop_table("sales_orders")
    op.drop_table("customers")
    op.drop_table("price_list_items")
    op.drop_table("price_lists")
    op.drop_table("customer_types")
