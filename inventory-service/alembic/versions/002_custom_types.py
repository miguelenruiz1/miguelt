"""Add product_types, order_types, custom_product_fields tables

Revision ID: 002
Revises: 001
Create Date: 2026-02-23
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── product_types ──────────────────────────────────────────────────────────
    op.create_table(
        "product_types",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("slug", sa.String(150), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("color", sa.String(20), nullable=True, server_default="#6366f1"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_product_type_tenant_slug"),
    )
    op.create_index("ix_product_types_tenant_id", "product_types", ["tenant_id"])

    # ── order_types ────────────────────────────────────────────────────────────
    op.create_table(
        "order_types",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("slug", sa.String(150), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("color", sa.String(20), nullable=True, server_default="#10b981"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_order_type_tenant_slug"),
    )
    op.create_index("ix_order_types_tenant_id", "order_types", ["tenant_id"])

    # ── custom_product_fields ──────────────────────────────────────────────────
    op.create_table(
        "custom_product_fields",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("label", sa.String(150), nullable=False),
        sa.Column("field_key", sa.String(100), nullable=False),
        sa.Column("field_type", sa.String(20), nullable=False, server_default="text"),
        sa.Column("options", sa.JSON, nullable=True),
        sa.Column("required", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.UniqueConstraint("tenant_id", "field_key", name="uq_custom_field_tenant_key"),
    )
    op.create_index("ix_custom_product_fields_tenant_id", "custom_product_fields", ["tenant_id"])

    # ── add product_type_id to products ───────────────────────────────────────
    op.add_column(
        "products",
        sa.Column(
            "product_type_id",
            sa.String(36),
            sa.ForeignKey("product_types.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # ── add order_type_id to purchase_orders ──────────────────────────────────
    op.add_column(
        "purchase_orders",
        sa.Column(
            "order_type_id",
            sa.String(36),
            sa.ForeignKey("order_types.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("purchase_orders", "order_type_id")
    op.drop_column("products", "product_type_id")
    op.drop_index("ix_custom_product_fields_tenant_id", "custom_product_fields")
    op.drop_table("custom_product_fields")
    op.drop_index("ix_order_types_tenant_id", "order_types")
    op.drop_table("order_types")
    op.drop_index("ix_product_types_tenant_id", "product_types")
    op.drop_table("product_types")
