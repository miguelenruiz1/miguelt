"""PO workflow overhaul: approval, supplier invoice, payment terms.

Revision ID: 059
Revises: 058
Create Date: 2026-03-23
"""
from alembic import op
import sqlalchemy as sa

revision = "059"
down_revision = "058"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -- purchase_orders: approval columns --
    op.add_column("purchase_orders", sa.Column("approval_required", sa.Boolean, nullable=False, server_default="false"))
    op.add_column("purchase_orders", sa.Column("approved_by", sa.String(255), nullable=True))
    op.add_column("purchase_orders", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("purchase_orders", sa.Column("rejected_reason", sa.Text, nullable=True))
    op.add_column("purchase_orders", sa.Column("rejected_by", sa.String(255), nullable=True))
    op.add_column("purchase_orders", sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("purchase_orders", sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("purchase_orders", sa.Column("sent_by", sa.String(255), nullable=True))
    op.add_column("purchase_orders", sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("purchase_orders", sa.Column("confirmed_by", sa.String(255), nullable=True))

    # -- purchase_orders: supplier invoice & payment columns --
    op.add_column("purchase_orders", sa.Column("supplier_invoice_number", sa.String(100), nullable=True))
    op.add_column("purchase_orders", sa.Column("supplier_invoice_date", sa.Date, nullable=True))
    op.add_column("purchase_orders", sa.Column("supplier_invoice_total", sa.Numeric(14, 2), nullable=True))
    op.add_column("purchase_orders", sa.Column("payment_terms", sa.String(50), nullable=True))
    op.add_column("purchase_orders", sa.Column("payment_due_date", sa.Date, nullable=True))

    # -- purchase_orders: related sales order FK --
    op.add_column("purchase_orders", sa.Column("related_sales_order_id", sa.String(36), sa.ForeignKey("sales_orders.id", ondelete="SET NULL"), nullable=True))

    # -- tenant_inventory_configs: approval settings --
    op.add_column("tenant_inventory_configs", sa.Column("require_po_approval", sa.Boolean, nullable=False, server_default="false"))
    op.add_column("tenant_inventory_configs", sa.Column("po_approval_threshold", sa.Numeric(14, 2), nullable=True))

    # -- po_approval_logs table --
    op.create_table(
        "po_approval_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("purchase_order_id", sa.String(36), sa.ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("performed_by", sa.String(255), nullable=False),
        sa.Column("performed_by_name", sa.String(255), nullable=True),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("po_total", sa.Numeric(14, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_po_approval_logs_tenant_id", "po_approval_logs", ["tenant_id"])
    op.create_index("ix_po_approval_logs_purchase_order_id", "po_approval_logs", ["purchase_order_id"])


def downgrade() -> None:
    # -- drop po_approval_logs --
    op.drop_index("ix_po_approval_logs_purchase_order_id", table_name="po_approval_logs")
    op.drop_index("ix_po_approval_logs_tenant_id", table_name="po_approval_logs")
    op.drop_table("po_approval_logs")

    # -- tenant_inventory_configs --
    op.drop_column("tenant_inventory_configs", "po_approval_threshold")
    op.drop_column("tenant_inventory_configs", "require_po_approval")

    # -- purchase_orders (reverse order) --
    op.drop_column("purchase_orders", "related_sales_order_id")
    op.drop_column("purchase_orders", "payment_due_date")
    op.drop_column("purchase_orders", "payment_terms")
    op.drop_column("purchase_orders", "supplier_invoice_total")
    op.drop_column("purchase_orders", "supplier_invoice_date")
    op.drop_column("purchase_orders", "supplier_invoice_number")
    op.drop_column("purchase_orders", "confirmed_by")
    op.drop_column("purchase_orders", "confirmed_at")
    op.drop_column("purchase_orders", "sent_by")
    op.drop_column("purchase_orders", "sent_at")
    op.drop_column("purchase_orders", "rejected_at")
    op.drop_column("purchase_orders", "rejected_by")
    op.drop_column("purchase_orders", "rejected_reason")
    op.drop_column("purchase_orders", "approved_at")
    op.drop_column("purchase_orders", "approved_by")
    op.drop_column("purchase_orders", "approval_required")
