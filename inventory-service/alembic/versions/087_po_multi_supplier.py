"""PO multi-supplier + supplier advances

Revision ID: 087
Revises: 086
Create Date: 2026-04-14

Supports consolidated POs where a single purchase order aggregates
contributions from multiple suppliers (e.g. palma oil extractora
receiving fruit from 5 small producers in one PO). Also tracks a PO-
level advance payment + per-supplier advance, common in the palma
aceitera industry.

Changes:
- purchase_orders.supplier_id becomes NULLABLE (when PO has multi
  supplier children, header supplier is optional).
- purchase_orders gains advance_amount, advance_paid_at, advance_reference.
- New table purchase_order_suppliers (id, tenant_id, purchase_order_id,
  supplier_id, contribution_qty, contribution_amount, advance_to_supplier,
  plot_id).
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "087"
down_revision: Union[str, None] = "086"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Relax supplier_id to nullable
    op.alter_column(
        "purchase_orders",
        "supplier_id",
        existing_type=sa.String(36),
        nullable=True,
    )

    # Advance payment fields on PO header
    op.add_column(
        "purchase_orders",
        sa.Column("advance_amount", sa.Numeric(18, 2), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "purchase_orders",
        sa.Column("advance_paid_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "purchase_orders",
        sa.Column("advance_reference", sa.String(100), nullable=True),
    )

    # Multi-supplier contributions
    op.create_table(
        "purchase_order_suppliers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column(
            "purchase_order_id",
            sa.String(36),
            sa.ForeignKey("purchase_orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "supplier_id",
            sa.String(36),
            sa.ForeignKey("suppliers.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("contribution_qty", sa.Numeric(18, 4), nullable=False, server_default=sa.text("0")),
        sa.Column("contribution_amount", sa.Numeric(18, 2), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "advance_to_supplier", sa.Numeric(18, 2), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("plot_id", sa.String(36), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_po_suppliers_po", "purchase_order_suppliers", ["purchase_order_id"]
    )
    op.create_index(
        "ix_po_suppliers_tenant_supplier",
        "purchase_order_suppliers",
        ["tenant_id", "supplier_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_po_suppliers_tenant_supplier", table_name="purchase_order_suppliers")
    op.drop_index("ix_po_suppliers_po", table_name="purchase_order_suppliers")
    op.drop_table("purchase_order_suppliers")

    op.drop_column("purchase_orders", "advance_reference")
    op.drop_column("purchase_orders", "advance_paid_at")
    op.drop_column("purchase_orders", "advance_amount")

    # Restore supplier_id NOT NULL (will fail if any row is null)
    op.alter_column(
        "purchase_orders",
        "supplier_id",
        existing_type=sa.String(36),
        nullable=False,
    )
