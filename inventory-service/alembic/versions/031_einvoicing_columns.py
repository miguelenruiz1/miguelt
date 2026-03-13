"""Add electronic invoicing columns to sales_orders.

Columns: cufe, invoice_pdf_url, invoice_status, invoice_remote_id
"""
revision = "031"
down_revision = "030"

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.add_column("sales_orders", sa.Column("cufe", sa.String(255), nullable=True))
    op.add_column("sales_orders", sa.Column("invoice_pdf_url", sa.String(500), nullable=True))
    op.add_column("sales_orders", sa.Column("invoice_status", sa.String(50), nullable=True))
    op.add_column("sales_orders", sa.Column("invoice_remote_id", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("sales_orders", "invoice_remote_id")
    op.drop_column("sales_orders", "invoice_status")
    op.drop_column("sales_orders", "invoice_pdf_url")
    op.drop_column("sales_orders", "cufe")
