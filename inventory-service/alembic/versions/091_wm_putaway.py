"""WM putaway rules, package types, handling units.

Revision: 091
Revises: 090
"""
from alembic import op
import sqlalchemy as sa


revision = "091"
down_revision = "090"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wm_putaway_rules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("warehouse_id", sa.String(36),
                  sa.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("match_product_id", sa.String(36),
                  sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=True),
        sa.Column("match_category_id", sa.String(36),
                  sa.ForeignKey("categories.id", ondelete="CASCADE"), nullable=True),
        sa.Column("match_commodity", sa.String(20), nullable=True),
        sa.Column("dest_storage_type_id", sa.String(36),
                  sa.ForeignKey("wm_storage_types.id", ondelete="SET NULL"), nullable=True),
        sa.Column("dest_storage_section_id", sa.String(36),
                  sa.ForeignKey("wm_storage_sections.id", ondelete="SET NULL"), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_wm_putaway_rules_tenant_id", "wm_putaway_rules", ["tenant_id"])
    op.create_index("ix_wm_putaway_rules_wh", "wm_putaway_rules", ["warehouse_id"])
    op.create_index("ix_wm_putaway_rules_product", "wm_putaway_rules", ["match_product_id"])

    op.create_table(
        "wm_package_types",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("code", sa.String(30), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("max_weight_kg", sa.Numeric(10, 2), nullable=True),
        sa.Column("length_cm", sa.Numeric(8, 2), nullable=True),
        sa.Column("width_cm", sa.Numeric(8, 2), nullable=True),
        sa.Column("height_cm", sa.Numeric(8, 2), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_wm_package_types_tenant_id", "wm_package_types", ["tenant_id"])

    op.create_table(
        "wm_handling_units",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("hu_number", sa.String(40), nullable=False),
        sa.Column("package_type_id", sa.String(36),
                  sa.ForeignKey("wm_package_types.id", ondelete="SET NULL"), nullable=True),
        sa.Column("warehouse_id", sa.String(36),
                  sa.ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True),
        sa.Column("location_id", sa.String(36),
                  sa.ForeignKey("warehouse_locations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(15), nullable=False, server_default="open"),
        sa.Column("gross_weight_kg", sa.Numeric(12, 3), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_wm_handling_units_tenant_id", "wm_handling_units", ["tenant_id"])
    op.create_index("ix_wm_handling_units_hu_number", "wm_handling_units", ["tenant_id", "hu_number"])


def downgrade() -> None:
    op.drop_table("wm_handling_units")
    op.drop_table("wm_package_types")
    op.drop_table("wm_putaway_rules")
