"""Billing completeness (FASE2): dunning fields, refund/credit_note, unmatched_payments.

Revision ID: 015
Revises: 014
Create Date: 2026-04-15
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Dunning (Task 3) ────────────────────────────────────────────────────
    op.add_column(
        "invoices",
        sa.Column("last_dunning_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "invoices",
        sa.Column("dunning_count", sa.Integer(), nullable=False, server_default="0"),
    )

    # ── Refund / credit note (Task 5) ───────────────────────────────────────
    op.add_column(
        "invoices",
        sa.Column("parent_invoice_id", sa.String(length=36), nullable=True),
    )
    op.add_column(
        "invoices",
        sa.Column(
            "invoice_type",
            sa.String(length=20),
            nullable=False,
            server_default="standard",
        ),
    )
    op.create_foreign_key(
        "fk_invoices_parent_invoice_id",
        "invoices",
        "invoices",
        ["parent_invoice_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_invoices_parent_invoice_id", "invoices", ["parent_invoice_id"]
    )
    op.create_index("ix_invoices_invoice_type", "invoices", ["invoice_type"])
    op.create_index("ix_invoices_due_date", "invoices", ["due_date"])

    # ── Unmatched payments ledger (Task 4) ──────────────────────────────────
    op.create_table(
        "unmatched_payments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("gateway_slug", sa.String(50), nullable=False),
        sa.Column("gateway_tx_id", sa.String(255), nullable=False),
        sa.Column("reference", sa.String(500), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("currency", sa.String(3), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_invoice_id", sa.String(36), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_unmatched_payments_gateway_tx_id",
        "unmatched_payments",
        ["gateway_slug", "gateway_tx_id"],
        unique=True,
    )
    op.create_index(
        "ix_unmatched_payments_received_at",
        "unmatched_payments",
        ["received_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_unmatched_payments_received_at", table_name="unmatched_payments")
    op.drop_index("ix_unmatched_payments_gateway_tx_id", table_name="unmatched_payments")
    op.drop_table("unmatched_payments")

    op.drop_index("ix_invoices_due_date", table_name="invoices")
    op.drop_index("ix_invoices_invoice_type", table_name="invoices")
    op.drop_index("ix_invoices_parent_invoice_id", table_name="invoices")
    op.drop_constraint("fk_invoices_parent_invoice_id", "invoices", type_="foreignkey")
    op.drop_column("invoices", "invoice_type")
    op.drop_column("invoices", "parent_invoice_id")
    op.drop_column("invoices", "dunning_count")
    op.drop_column("invoices", "last_dunning_at")
