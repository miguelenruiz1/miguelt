"""Seed compliance module into MODULE_CATALOG.

Revision ID: 006
Revises: 005
Create Date: 2026-03-21

The compliance module is added to the hardcoded MODULE_CATALOG in module_service.py.
This migration is a placeholder to maintain version lineage. The actual catalog
entry is driven by subscription-service code (same pattern as production module).
"""
from alembic import op
import sqlalchemy as sa

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Compliance module activation is handled dynamically via MODULE_CATALOG
    # No table changes needed — the module_service.py catalog drives discovery
    pass


def downgrade() -> None:
    pass
