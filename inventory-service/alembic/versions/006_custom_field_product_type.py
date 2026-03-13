"""Add product_type_id to custom_product_fields for per-type field scoping.

Revision ID: 006
Revises: 005
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "006"
down_revision = "005"


def upgrade() -> None:
    # Add product_type_id column (nullable — existing fields remain global)
    op.add_column(
        "custom_product_fields",
        sa.Column("product_type_id", sa.String(36), nullable=True),
    )

    # Drop old unique constraint and create new one scoped by product_type_id
    op.drop_constraint("uq_custom_field_tenant_key", "custom_product_fields", type_="unique")
    op.create_unique_constraint(
        "uq_custom_field_tenant_key_pt",
        "custom_product_fields",
        ["tenant_id", "field_key", "product_type_id"],
    )

    # Index for fast lookup by tenant + product_type
    op.create_index(
        "ix_custom_product_fields_product_type",
        "custom_product_fields",
        ["tenant_id", "product_type_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_custom_product_fields_product_type", "custom_product_fields")
    op.drop_constraint("uq_custom_field_tenant_key_pt", "custom_product_fields", type_="unique")
    op.create_unique_constraint(
        "uq_custom_field_tenant_key",
        "custom_product_fields",
        ["tenant_id", "field_key"],
    )
    op.drop_column("custom_product_fields", "product_type_id")
