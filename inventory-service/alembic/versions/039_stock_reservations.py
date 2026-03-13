"""Create stock_reservations table for SO reservation traceability.

Revision ID: 039
Revises: 038
"""
from alembic import op
import sqlalchemy as sa

revision = "039"
down_revision = "038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "stock_reservations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("sales_order_id", sa.String(36), sa.ForeignKey("sales_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sales_order_line_id", sa.String(36), sa.ForeignKey("sales_order_lines.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.String(36), sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("variant_id", sa.String(36), sa.ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("warehouse_id", sa.String(36), sa.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 4), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("reserved_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_reason", sa.String(50), nullable=True),
    )
    op.create_index("ix_reservation_so", "stock_reservations", ["sales_order_id"])
    op.create_index("ix_reservation_product_wh", "stock_reservations", ["product_id", "warehouse_id"])
    op.create_index("ix_reservation_tenant_status", "stock_reservations", ["tenant_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_reservation_tenant_status", table_name="stock_reservations")
    op.drop_index("ix_reservation_product_wh", table_name="stock_reservations")
    op.drop_index("ix_reservation_so", table_name="stock_reservations")
    op.drop_table("stock_reservations")
