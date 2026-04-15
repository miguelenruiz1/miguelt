"""goods_receipts + goods_receipt_lines (GRN documents)

Revision ID: 086
Revises: 085
Create Date: 2026-04-14

Adds a formal Goods Receipt Note (GRN) document that wraps PO reception.
One PO can have 0..N GRNs (partial / multiple deliveries). Each GRN line
records qty_expected vs qty_received and any discrepancy reason, so
operators can audit short / over / damaged receipts against the PO.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "086"
down_revision: Union[str, None] = "085"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "goods_receipts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("grn_number", sa.String(50), nullable=False),
        sa.Column(
            "purchase_order_id",
            sa.String(36),
            sa.ForeignKey("purchase_orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("receipt_date", sa.Date(), nullable=False),
        sa.Column("received_by", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("has_discrepancy", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("attachments", postgresql.JSONB(), nullable=True, server_default=sa.text("'[]'::jsonb")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("tenant_id", "grn_number", name="uq_grn_tenant_number"),
    )
    op.create_index(
        "ix_goods_receipts_tenant_po",
        "goods_receipts",
        ["tenant_id", "purchase_order_id"],
    )

    op.create_table(
        "goods_receipt_lines",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column(
            "grn_id",
            sa.String(36),
            sa.ForeignKey("goods_receipts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "po_line_id",
            sa.String(36),
            sa.ForeignKey("purchase_order_lines.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            sa.String(36),
            sa.ForeignKey("entities.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("qty_expected", sa.Numeric(18, 4), nullable=False),
        sa.Column("qty_received", sa.Numeric(18, 4), nullable=False),
        sa.Column(
            "qty_discrepancy", sa.Numeric(18, 4), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("batch_number", sa.String(100), nullable=True),
        sa.Column("discrepancy_reason", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_grn_lines_grn", "goods_receipt_lines", ["grn_id"])
    op.create_index("ix_grn_lines_po_line", "goods_receipt_lines", ["po_line_id"])
    op.create_index("ix_grn_lines_tenant", "goods_receipt_lines", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_grn_lines_tenant", table_name="goods_receipt_lines")
    op.drop_index("ix_grn_lines_po_line", table_name="goods_receipt_lines")
    op.drop_index("ix_grn_lines_grn", table_name="goods_receipt_lines")
    op.drop_table("goods_receipt_lines")
    op.drop_index("ix_goods_receipts_tenant_po", table_name="goods_receipts")
    op.drop_table("goods_receipts")
