"""Add approval columns to production_runs.

Revision ID: 015
Revises: 014
Create Date: 2026-03-03
"""
from alembic import op
import sqlalchemy as sa

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("production_runs", sa.Column("approved_by", sa.String(255), nullable=True))
    op.add_column("production_runs", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("production_runs", sa.Column("rejection_notes", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("production_runs", "rejection_notes")
    op.drop_column("production_runs", "approved_at")
    op.drop_column("production_runs", "approved_by")
