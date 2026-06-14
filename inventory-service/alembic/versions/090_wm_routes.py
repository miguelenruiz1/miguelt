"""WM multi-step routes: warehouse step config + routes + rules.

Revision: 090
Revises: 089
"""
from alembic import op
import sqlalchemy as sa


revision = "090"
down_revision = "089"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wm_warehouse_configs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("warehouse_id", sa.String(36),
                  sa.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("receive_steps", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("deliver_steps", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("manufacture_steps", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("warehouse_id", name="uq_wm_warehouse_config_wh"),
    )
    op.create_index("ix_wm_warehouse_configs_tenant_id", "wm_warehouse_configs", ["tenant_id"])

    op.create_table(
        "wm_routes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("warehouse_id", sa.String(36),
                  sa.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("flow", sa.String(15), nullable=False),
        sa.Column("steps", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("warehouse_id", "flow", name="uq_wm_route_wh_flow"),
    )
    op.create_index("ix_wm_routes_tenant_id", "wm_routes", ["tenant_id"])

    op.create_table(
        "wm_route_rules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("route_id", sa.String(36),
                  sa.ForeignKey("wm_routes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("source_zone", sa.String(20), nullable=False),
        sa.Column("dest_zone", sa.String(20), nullable=False),
        sa.Column("operation_code", sa.String(10), nullable=True),
    )
    op.create_index("ix_wm_route_rules_route", "wm_route_rules", ["route_id"])
    op.create_index("ix_wm_route_rules_tenant_id", "wm_route_rules", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("wm_route_rules")
    op.drop_table("wm_routes")
    op.drop_table("wm_warehouse_configs")
