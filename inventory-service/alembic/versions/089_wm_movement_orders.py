"""WM movement documents: operation types, requirements, movement orders.

Internal warehouse bin->bin movement documents (SAP "transfer order" — the
technical term; user-facing name is "orden de movimiento de almacén"). This is
NOT freight/transport between locations — that lives in the logistics module
(trace-service).

Revision: 089
Revises: 088
"""
from alembic import op
import sqlalchemy as sa


revision = "089"
down_revision = "088"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wm_operation_types",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("warehouse_id", sa.String(36),
                  sa.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=True),
        sa.Column("code", sa.String(10), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("direction", sa.String(12), nullable=False),
        sa.Column("movement_type", sa.String(20), nullable=True),
        sa.Column("source_zone", sa.String(20), nullable=True),
        sa.Column("dest_zone", sa.String(20), nullable=True),
        sa.Column("requires_qa", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "code", name="uq_wm_operation_type_tenant_code"),
    )
    op.create_index("ix_wm_operation_types_tenant_id", "wm_operation_types", ["tenant_id"])

    op.create_table(
        "wm_transfer_requirements",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("warehouse_id", sa.String(36),
                  sa.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("operation_type_id", sa.String(36),
                  sa.ForeignKey("wm_operation_types.id", ondelete="SET NULL"), nullable=True),
        sa.Column("ref_type", sa.String(20), nullable=True),
        sa.Column("ref_id", sa.String(36), nullable=True),
        sa.Column("product_id", sa.String(36),
                  sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("batch_id", sa.String(36),
                  sa.ForeignKey("entity_batches.id", ondelete="SET NULL"), nullable=True),
        sa.Column("variant_id", sa.String(36),
                  sa.ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("uom", sa.String(20), nullable=False, server_default="primary"),
        sa.Column("status", sa.String(15), nullable=False, server_default="open"),
        sa.Column("requested_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_wm_transfer_requirements_tenant_id", "wm_transfer_requirements", ["tenant_id"])
    op.create_index("ix_wm_transfer_req_status", "wm_transfer_requirements", ["tenant_id", "status"])
    op.create_index("ix_wm_transfer_req_ref", "wm_transfer_requirements", ["ref_type", "ref_id"])

    op.create_table(
        "wm_transfer_orders",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("warehouse_id", sa.String(36),
                  sa.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("to_number", sa.String(40), nullable=False),
        sa.Column("operation_type_id", sa.String(36),
                  sa.ForeignKey("wm_operation_types.id", ondelete="SET NULL"), nullable=True),
        sa.Column("requirement_id", sa.String(36),
                  sa.ForeignKey("wm_transfer_requirements.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(15), nullable=False, server_default="open"),
        sa.Column("source_doc_type", sa.String(20), nullable=True),
        sa.Column("source_doc_id", sa.String(36), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_by", sa.String(255), nullable=True),
        sa.UniqueConstraint("tenant_id", "to_number", name="uq_wm_transfer_order_tenant_number"),
    )
    op.create_index("ix_wm_transfer_orders_tenant_id", "wm_transfer_orders", ["tenant_id"])
    op.create_index("ix_wm_transfer_orders_status", "wm_transfer_orders", ["tenant_id", "status"])
    op.create_index("ix_wm_transfer_orders_warehouse", "wm_transfer_orders", ["warehouse_id"])

    op.create_table(
        "wm_transfer_order_lines",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("transfer_order_id", sa.String(36),
                  sa.ForeignKey("wm_transfer_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("product_id", sa.String(36),
                  sa.ForeignKey("entities.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("batch_id", sa.String(36),
                  sa.ForeignKey("entity_batches.id", ondelete="SET NULL"), nullable=True),
        sa.Column("variant_id", sa.String(36),
                  sa.ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("uom", sa.String(20), nullable=False, server_default="primary"),
        sa.Column("source_location_id", sa.String(36),
                  sa.ForeignKey("warehouse_locations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("dest_location_id", sa.String(36),
                  sa.ForeignKey("warehouse_locations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("source_confirmed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("dest_confirmed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("confirmed_qty", sa.Numeric(18, 4), nullable=True),
        sa.Column("status", sa.String(12), nullable=False, server_default="open"),
    )
    op.create_index("ix_wm_to_lines_tenant_id", "wm_transfer_order_lines", ["tenant_id"])
    op.create_index("ix_wm_to_lines_order", "wm_transfer_order_lines", ["transfer_order_id"])


def downgrade() -> None:
    op.drop_table("wm_transfer_order_lines")
    op.drop_table("wm_transfer_orders")
    op.drop_table("wm_transfer_requirements")
    op.drop_table("wm_operation_types")
