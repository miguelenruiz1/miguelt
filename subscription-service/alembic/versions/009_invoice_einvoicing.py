"""Add electronic invoicing fields to invoices for DIAN compliance.

Revision ID: 009
Revises: 008
"""
from alembic import op
import sqlalchemy as sa

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("invoices", sa.Column("cufe", sa.String(255), nullable=True))
    op.add_column("invoices", sa.Column("einvoice_number", sa.String(50), nullable=True))
    op.add_column("invoices", sa.Column("einvoice_pdf_url", sa.String(500), nullable=True))
    op.add_column("invoices", sa.Column("einvoice_status", sa.String(50), nullable=True))
    op.add_column("invoices", sa.Column("einvoice_remote_id", sa.String(255), nullable=True))
    op.add_column("invoices", sa.Column("einvoice_provider", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("invoices", "einvoice_provider")
    op.drop_column("invoices", "einvoice_remote_id")
    op.drop_column("invoices", "einvoice_status")
    op.drop_column("invoices", "einvoice_pdf_url")
    op.drop_column("invoices", "einvoice_number")
    op.drop_column("invoices", "cufe")
