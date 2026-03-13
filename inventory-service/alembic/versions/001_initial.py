"""Initial schema for inventory-service

Revision ID: 001
Revises:
Create Date: 2026-02-23
"""
from __future__ import annotations

from typing import Sequence, Union
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_STR50 = sa.String(50)


def upgrade() -> None:
    # ── product_categories ────────────────────────────────────────────────────
    op.create_table(
        "product_categories",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("slug", sa.String(150), nullable=False),
        sa.Column("parent_id", sa.String(36), sa.ForeignKey("product_categories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_category_tenant_slug"),
    )
    op.create_index("ix_product_categories_tenant_id", "product_categories", ["tenant_id"])

    # ── products ──────────────────────────────────────────────────────────────
    op.create_table(
        "products",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("sku", sa.String(100), nullable=False),
        sa.Column("barcode", sa.String(100), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("category_id", sa.String(36), sa.ForeignKey("product_categories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("unit_of_measure", sa.String(50), nullable=False, server_default="un"),
        sa.Column("cost_price", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("sale_price", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("track_batches", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("min_stock_level", sa.Integer, nullable=False, server_default="0"),
        sa.Column("reorder_point", sa.Integer, nullable=False, server_default="0"),
        sa.Column("reorder_quantity", sa.Integer, nullable=False, server_default="1"),
        sa.Column("images", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("attributes", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "sku", name="uq_product_tenant_sku"),
    )
    op.create_index("ix_products_tenant_id", "products", ["tenant_id"])

    # ── warehouses ────────────────────────────────────────────────────────────
    op.create_table(
        "warehouses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("type", _STR50, nullable=False, server_default="main"),
        sa.Column("address", postgresql.JSONB, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("is_default", sa.Boolean, nullable=False, server_default="false"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_warehouse_tenant_code"),
    )
    op.create_index("ix_warehouses_tenant_id", "warehouses", ["tenant_id"])

    # ── stock_levels ──────────────────────────────────────────────────────────
    op.create_table(
        "stock_levels",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("product_id", sa.String(36), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("warehouse_id", sa.String(36), sa.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("qty_on_hand", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("qty_reserved", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("reorder_point", sa.Integer, nullable=False, server_default="0"),
        sa.Column("max_stock", sa.Integer, nullable=False, server_default="-1"),
        sa.Column("last_count_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("product_id", "warehouse_id", name="uq_stock_product_warehouse"),
    )
    op.create_index("ix_stock_levels_tenant_id", "stock_levels", ["tenant_id"])

    # ── stock_movements ───────────────────────────────────────────────────────
    op.create_table(
        "stock_movements",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("movement_type", _STR50, nullable=False),
        sa.Column("product_id", sa.String(36), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_warehouse_id", sa.String(36), sa.ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True),
        sa.Column("to_warehouse_id", sa.String(36), sa.ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True),
        sa.Column("quantity", sa.Numeric(12, 4), nullable=False),
        sa.Column("unit_cost", sa.Numeric(12, 4), nullable=True),
        sa.Column("reference", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("batch_number", sa.String(100), nullable=True),
        sa.Column("performed_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_stock_movements_tenant_id", "stock_movements", ["tenant_id"])
    op.create_index("ix_stock_movements_product_id", "stock_movements", ["product_id"])
    op.create_index("ix_stock_movements_type", "stock_movements", ["movement_type"])
    op.create_index("ix_stock_movements_created_at", "stock_movements", ["created_at"])

    # ── suppliers ─────────────────────────────────────────────────────────────
    op.create_table(
        "suppliers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("contact_name", sa.String(255), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("address", postgresql.JSONB, nullable=True),
        sa.Column("payment_terms_days", sa.Integer, nullable=False, server_default="30"),
        sa.Column("lead_time_days", sa.Integer, nullable=False, server_default="7"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "code", name="uq_supplier_tenant_code"),
    )
    op.create_index("ix_suppliers_tenant_id", "suppliers", ["tenant_id"])

    # ── purchase_orders ───────────────────────────────────────────────────────
    op.create_table(
        "purchase_orders",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("po_number", sa.String(50), nullable=False),
        sa.Column("supplier_id", sa.String(36), sa.ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", _STR50, nullable=False, server_default="draft"),
        sa.Column("warehouse_id", sa.String(36), sa.ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True),
        sa.Column("expected_date", sa.Date, nullable=True),
        sa.Column("received_date", sa.Date, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "po_number", name="uq_po_tenant_number"),
    )
    op.create_index("ix_purchase_orders_tenant_id", "purchase_orders", ["tenant_id"])
    op.create_index("ix_purchase_orders_supplier_id", "purchase_orders", ["supplier_id"])
    op.create_index("ix_purchase_orders_status", "purchase_orders", ["status"])

    # ── purchase_order_lines ──────────────────────────────────────────────────
    op.create_table(
        "purchase_order_lines",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("po_id", sa.String(36), sa.ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.String(36), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("qty_ordered", sa.Numeric(12, 4), nullable=False),
        sa.Column("qty_received", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("unit_cost", sa.Numeric(12, 4), nullable=False),
        sa.Column("line_total", sa.Numeric(12, 4), nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
    )
    op.create_index("ix_po_lines_po_id", "purchase_order_lines", ["po_id"])

    # ── seed data for default tenant ──────────────────────────────────────────
    DEFAULT_TENANT = "default"
    conn = op.get_bind()

    wh_id = str(uuid.uuid4())
    conn.execute(
        sa.text(
            "INSERT INTO warehouses (id, tenant_id, name, code, type, is_active, is_default) "
            "VALUES (:id, :tid, 'Principal', 'MAIN', 'main', true, true)"
        ),
        {"id": wh_id, "tid": DEFAULT_TENANT},
    )

    categories = [
        ("Materias Primas", "materias-primas"),
        ("Producto Terminado", "producto-terminado"),
        ("Repuestos", "repuestos"),
        ("Suministros", "suministros"),
    ]
    for name, slug in categories:
        conn.execute(
            sa.text(
                "INSERT INTO product_categories (id, tenant_id, name, slug, sort_order, is_active) "
                "VALUES (:id, :tid, :name, :slug, 0, true)"
            ),
            {"id": str(uuid.uuid4()), "tid": DEFAULT_TENANT, "name": name, "slug": slug},
        )


def downgrade() -> None:
    op.drop_index("ix_po_lines_po_id", "purchase_order_lines")
    op.drop_table("purchase_order_lines")
    op.drop_index("ix_purchase_orders_status", "purchase_orders")
    op.drop_index("ix_purchase_orders_supplier_id", "purchase_orders")
    op.drop_index("ix_purchase_orders_tenant_id", "purchase_orders")
    op.drop_table("purchase_orders")
    op.drop_index("ix_suppliers_tenant_id", "suppliers")
    op.drop_table("suppliers")
    op.drop_index("ix_stock_movements_created_at", "stock_movements")
    op.drop_index("ix_stock_movements_type", "stock_movements")
    op.drop_index("ix_stock_movements_product_id", "stock_movements")
    op.drop_index("ix_stock_movements_tenant_id", "stock_movements")
    op.drop_table("stock_movements")
    op.drop_index("ix_stock_levels_tenant_id", "stock_levels")
    op.drop_table("stock_levels")
    op.drop_index("ix_warehouses_tenant_id", "warehouses")
    op.drop_table("warehouses")
    op.drop_index("ix_products_tenant_id", "products")
    op.drop_table("products")
    op.drop_index("ix_product_categories_tenant_id", "product_categories")
    op.drop_table("product_categories")
