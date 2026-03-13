"""Add description and user_name to audit logs.

Revision ID: 016
Revises: 015
Create Date: 2026-03-03
"""
from alembic import op
import sqlalchemy as sa

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("inventory_audit_logs", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("inventory_audit_logs", sa.Column("user_name", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("inventory_audit_logs", "user_name")
    op.drop_column("inventory_audit_logs", "description")
