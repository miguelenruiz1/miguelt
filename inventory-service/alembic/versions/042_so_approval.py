"""SO approval workflow: columns, audit log, tenant config."""
from alembic import op
import sqlalchemy as sa

revision = "042"
down_revision = "041"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Approval columns on sales_orders
    op.add_column("sales_orders", sa.Column("approval_required", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("sales_orders", sa.Column("approved_by", sa.String(100), nullable=True))
    op.add_column("sales_orders", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("sales_orders", sa.Column("rejected_by", sa.String(100), nullable=True))
    op.add_column("sales_orders", sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("sales_orders", sa.Column("rejection_reason", sa.String(500), nullable=True))
    op.add_column("sales_orders", sa.Column("approval_requested_at", sa.DateTime(timezone=True), nullable=True))

    # Approval audit log
    op.create_table(
        "so_approval_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("sales_order_id", sa.String(36), sa.ForeignKey("sales_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("performed_by", sa.String(100), nullable=False),
        sa.Column("performed_by_name", sa.String(200), nullable=True),
        sa.Column("reason", sa.String(500), nullable=True),
        sa.Column("so_total_at_action", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_approval_log_so", "so_approval_logs", ["sales_order_id"])

    # Tenant inventory config
    op.create_table(
        "tenant_inventory_configs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False, unique=True),
        sa.Column("so_approval_threshold", sa.Numeric(14, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("tenant_inventory_configs")
    op.drop_index("ix_approval_log_so", table_name="so_approval_logs")
    op.drop_table("so_approval_logs")
    op.drop_column("sales_orders", "approval_requested_at")
    op.drop_column("sales_orders", "rejection_reason")
    op.drop_column("sales_orders", "rejected_at")
    op.drop_column("sales_orders", "rejected_by")
    op.drop_column("sales_orders", "approved_at")
    op.drop_column("sales_orders", "approved_by")
    op.drop_column("sales_orders", "approval_required")
