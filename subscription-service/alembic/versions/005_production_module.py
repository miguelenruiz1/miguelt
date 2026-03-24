"""Add production module to catalog seeds.

Revision ID: 005
Revises: 004
Create Date: 2026-03-16
"""
from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Production module activation is handled dynamically via MODULE_CATALOG
    # No table changes needed — the module_service.py catalog drives discovery
    pass


def downgrade() -> None:
    pass
