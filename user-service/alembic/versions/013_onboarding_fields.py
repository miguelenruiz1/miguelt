"""Add onboarding fields to users table.

Revision ID: 013
Revises: 012
"""
from alembic import op
import sqlalchemy as sa

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("onboarding_completed", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "users",
        sa.Column("onboarding_step", sa.String(50), nullable=False, server_default="welcome"),
    )
    # Mark all existing users as onboarded so they skip the wizard
    op.execute("UPDATE users SET onboarding_completed = true, onboarding_step = 'complete'")


def downgrade() -> None:
    op.drop_column("users", "onboarding_step")
    op.drop_column("users", "onboarding_completed")
