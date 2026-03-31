"""Add debit note fields to sales_orders for DIAN compliance.

Revision ID: 071
Revises: 070
"""
from alembic import op
import sqlalchemy as sa

revision = "071"
down_revision = "070"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sales_orders", sa.Column("debit_note_cufe", sa.String(255), nullable=True))
    op.add_column("sales_orders", sa.Column("debit_note_number", sa.String(50), nullable=True))
    op.add_column("sales_orders", sa.Column("debit_note_remote_id", sa.String(255), nullable=True))
    op.add_column("sales_orders", sa.Column("debit_note_status", sa.String(50), nullable=True))
    op.add_column("sales_orders", sa.Column("debit_note_reason", sa.Text(), nullable=True))
    op.add_column("sales_orders", sa.Column("debit_note_amount", sa.Numeric(14, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("sales_orders", "debit_note_amount")
    op.drop_column("sales_orders", "debit_note_reason")
    op.drop_column("sales_orders", "debit_note_status")
    op.drop_column("sales_orders", "debit_note_remote_id")
    op.drop_column("sales_orders", "debit_note_number")
    op.drop_column("sales_orders", "debit_note_cufe")
