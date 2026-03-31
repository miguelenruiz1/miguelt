"""Add version and is_default fields to entity_recipes for manufacturing versions.

Revision ID: 070
Revises: 069
"""
from alembic import op
import sqlalchemy as sa

revision = "070"
down_revision = "069"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("entity_recipes", sa.Column("version", sa.String(20), nullable=False, server_default="v1"))
    op.add_column("entity_recipes", sa.Column("is_default", sa.Boolean(), nullable=False, server_default="true"))


def downgrade() -> None:
    op.drop_column("entity_recipes", "is_default")
    op.drop_column("entity_recipes", "version")
