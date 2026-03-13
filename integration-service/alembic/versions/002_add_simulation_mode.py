"""Add simulation_mode column to integration_configs.

Revision ID: 002
Revises: 001
"""
revision = "002"
down_revision = "001"

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.add_column(
        "integration_configs",
        sa.Column("simulation_mode", sa.Boolean(), nullable=False, server_default="true"),
    )


def downgrade() -> None:
    op.drop_column("integration_configs", "simulation_mode")
