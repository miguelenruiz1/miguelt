"""Add supplier_types, custom_supplier_fields; extend suppliers with type + custom_attributes

Revision ID: 003
Revises: 002
Create Date: 2026-02-23
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── supplier_types ────────────────────────────────────────────────────────
    op.create_table(
        "supplier_types",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("slug", sa.String(150), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("color", sa.String(20), nullable=True, server_default="#f59e0b"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_supplier_type_tenant_slug"),
    )
    op.create_index("ix_supplier_types_tenant_id", "supplier_types", ["tenant_id"])

    # ── custom_supplier_fields ────────────────────────────────────────────────
    op.create_table(
        "custom_supplier_fields",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("label", sa.String(150), nullable=False),
        sa.Column("field_key", sa.String(100), nullable=False),
        sa.Column("field_type", sa.String(20), nullable=False, server_default="text"),
        sa.Column("options", sa.JSON, nullable=True),
        sa.Column("required", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.UniqueConstraint("tenant_id", "field_key", name="uq_custom_supplier_field_tenant_key"),
    )
    op.create_index("ix_custom_supplier_fields_tenant_id", "custom_supplier_fields", ["tenant_id"])

    # ── extend suppliers ──────────────────────────────────────────────────────
    op.add_column("suppliers", sa.Column(
        "supplier_type_id", sa.String(36),
        sa.ForeignKey("supplier_types.id", ondelete="SET NULL"),
        nullable=True,
    ))
    op.add_column("suppliers", sa.Column(
        "custom_attributes", JSONB, nullable=False, server_default="{}",
    ))


def downgrade() -> None:
    op.drop_column("suppliers", "custom_attributes")
    op.drop_column("suppliers", "supplier_type_id")
    op.drop_index("ix_custom_supplier_fields_tenant_id", "custom_supplier_fields")
    op.drop_table("custom_supplier_fields")
    op.drop_index("ix_supplier_types_tenant_id", "supplier_types")
    op.drop_table("supplier_types")
