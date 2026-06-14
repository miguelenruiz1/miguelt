"""WM foundations: storage types, storage sections, bin attributes.

Adds the SAP-WM / Odoo warehouse model on top of the existing warehouse +
location tables. Everything is nullable / defaulted so existing single-location
warehouses keep working unchanged (the WM layer is opt-in).

Revision: 088
Revises: 087
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "088"
down_revision = "087"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Storage types (SAP tipo de almacén) ──────────────────────────────────
    op.create_table(
        "wm_storage_types",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("warehouse_id", sa.String(36),
                  sa.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False, server_default="physical"),
        sa.Column("putaway_strategy", sa.String(30), nullable=False, server_default="manual"),
        sa.Column("removal_strategy", sa.String(30), nullable=False, server_default="fifo"),
        sa.Column("capacity_check", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("handles_hu", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("updated_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("warehouse_id", "code", name="uq_wm_storage_type_wh_code"),
    )
    op.create_index("ix_wm_storage_types_tenant_id", "wm_storage_types", ["tenant_id"])
    op.create_index("ix_wm_storage_types_warehouse_id", "wm_storage_types", ["warehouse_id"])

    # ── Storage sections (SAP área de almacenamiento) ────────────────────────
    op.create_table(
        "wm_storage_sections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("storage_type_id", sa.String(36),
                  sa.ForeignKey("wm_storage_types.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("rotation_class", sa.String(10), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("storage_type_id", "code", name="uq_wm_storage_section_type_code"),
    )
    op.create_index("ix_wm_storage_sections_tenant_id", "wm_storage_sections", ["tenant_id"])
    op.create_index("ix_wm_storage_sections_storage_type_id", "wm_storage_sections", ["storage_type_id"])

    # ── Warehouse: short code (document-sequence prefix) ─────────────────────
    op.add_column("warehouses", sa.Column("short_code", sa.String(10), nullable=True))

    # ── WarehouseLocation: WM bin attributes ─────────────────────────────────
    op.add_column("warehouse_locations",
                  sa.Column("storage_type_id", sa.String(36),
                            sa.ForeignKey("wm_storage_types.id", ondelete="SET NULL"), nullable=True))
    op.add_column("warehouse_locations",
                  sa.Column("storage_section_id", sa.String(36),
                            sa.ForeignKey("wm_storage_sections.id", ondelete="SET NULL"), nullable=True))
    op.add_column("warehouse_locations",
                  sa.Column("location_kind", sa.String(20), nullable=False, server_default="physical"))
    op.add_column("warehouse_locations", sa.Column("height_m", sa.Numeric(8, 2), nullable=True))
    op.add_column("warehouse_locations", sa.Column("max_volume_m3", sa.Numeric(10, 3), nullable=True))
    op.add_column("warehouse_locations",
                  sa.Column("is_fixed_bin", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("warehouse_locations", sa.Column("barcode", sa.String(100), nullable=True))
    op.create_index("ix_warehouse_locations_storage_type", "warehouse_locations", ["storage_type_id"])
    op.create_index("ix_warehouse_locations_barcode", "warehouse_locations", ["tenant_id", "barcode"])


def downgrade() -> None:
    op.drop_index("ix_warehouse_locations_barcode", table_name="warehouse_locations")
    op.drop_index("ix_warehouse_locations_storage_type", table_name="warehouse_locations")
    for col in ("barcode", "is_fixed_bin", "max_volume_m3", "height_m",
                "location_kind", "storage_section_id", "storage_type_id"):
        op.drop_column("warehouse_locations", col)
    op.drop_column("warehouses", "short_code")
    op.drop_index("ix_wm_storage_sections_storage_type_id", table_name="wm_storage_sections")
    op.drop_index("ix_wm_storage_sections_tenant_id", table_name="wm_storage_sections")
    op.drop_table("wm_storage_sections")
    op.drop_index("ix_wm_storage_types_warehouse_id", table_name="wm_storage_types")
    op.drop_index("ix_wm_storage_types_tenant_id", table_name="wm_storage_types")
    op.drop_table("wm_storage_types")
