"""Add credit note columns to sales_orders.

Revision: 035
Down revision: 034
"""

revision = "035"
down_revision = "034"

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.add_column("sales_orders", sa.Column("credit_note_cufe", sa.String(255), nullable=True))
    op.add_column("sales_orders", sa.Column("credit_note_number", sa.String(50), nullable=True))
    op.add_column("sales_orders", sa.Column("credit_note_remote_id", sa.String(255), nullable=True))
    op.add_column("sales_orders", sa.Column("credit_note_status", sa.String(50), nullable=True))
    op.add_column("sales_orders", sa.Column("returned_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("sales_orders", "returned_at")
    op.drop_column("sales_orders", "credit_note_status")
    op.drop_column("sales_orders", "credit_note_remote_id")
    op.drop_column("sales_orders", "credit_note_number")
    op.drop_column("sales_orders", "credit_note_cufe")
