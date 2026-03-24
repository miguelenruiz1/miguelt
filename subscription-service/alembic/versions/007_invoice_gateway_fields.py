"""Add gateway_tx_id and gateway_slug to invoices

Revision ID: 007
Revises: 006
Create Date: 2026-03-21

Adds gateway_tx_id (VARCHAR 255, NULLABLE) and gateway_slug (VARCHAR 50, NULLABLE)
to the invoices table, with an index on gateway_tx_id for idempotency checks
in payment webhook processing.
"""
from alembic import op
import sqlalchemy as sa

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("invoices", sa.Column("gateway_tx_id", sa.String(255), nullable=True))
    op.add_column("invoices", sa.Column("gateway_slug", sa.String(50), nullable=True))
    op.create_index("ix_invoices_gateway_tx_id", "invoices", ["gateway_tx_id"])


def downgrade() -> None:
    op.drop_index("ix_invoices_gateway_tx_id", "invoices")
    op.drop_column("invoices", "gateway_slug")
    op.drop_column("invoices", "gateway_tx_id")
