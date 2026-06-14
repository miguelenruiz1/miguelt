"""WM material master: product warehouse data (SAP Gestión de almacenes 1 & 2).

Revision: 093
Revises: 092
"""
from alembic import op
import sqlalchemy as sa


revision = "093"
down_revision = "092"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wm_product_warehouse_data",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("product_id", sa.String(36),
                  sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("warehouse_id", sa.String(36),
                  sa.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("removal_strategy", sa.String(15), nullable=False, server_default="fifo"),
        sa.Column("putaway_strategy", sa.String(15), nullable=False, server_default="manual"),
        sa.Column("fixed_bin_id", sa.String(36),
                  sa.ForeignKey("warehouse_locations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("picking_storage_type_id", sa.String(36),
                  sa.ForeignKey("wm_storage_types.id", ondelete="SET NULL"), nullable=True),
        sa.Column("wm_uom", sa.String(20), nullable=True),
        sa.Column("lot_managed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("serial_managed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("hazmat", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("gs1_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("storage_unit_type_id", sa.String(36),
                  sa.ForeignKey("wm_package_types.id", ondelete="SET NULL"), nullable=True),
        sa.Column("units_per_storage_unit", sa.Numeric(18, 4), nullable=True),
        sa.Column("max_qty_per_bin", sa.Numeric(18, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("product_id", "warehouse_id", name="uq_wm_product_wh_data"),
    )
    op.create_index("ix_wm_product_wh_data_tenant_id", "wm_product_warehouse_data", ["tenant_id"])
    op.create_index("ix_wm_product_wh_data_product", "wm_product_warehouse_data", ["product_id"])


def downgrade() -> None:
    op.drop_table("wm_product_warehouse_data")
