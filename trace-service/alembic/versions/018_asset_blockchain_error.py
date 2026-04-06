"""Add blockchain_error column to assets so failed mints surface a reason in the UI.

Revision ID: 018_blockchain_err
Revises: 017_customs_icon
"""
from alembic import op
import sqlalchemy as sa

revision = "018_blockchain_err"
down_revision = "017_customs_icon"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "assets",
        sa.Column("blockchain_error", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("assets", "blockchain_error")
