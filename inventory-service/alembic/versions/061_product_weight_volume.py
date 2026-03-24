"""Add weight_per_unit and volume_per_unit to products.

Revision ID: 061
"""
from alembic import op
import sqlalchemy as sa

revision = "061"
down_revision = "060"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("entities", sa.Column("weight_per_unit", sa.Numeric(10, 4), nullable=True))
    op.add_column("entities", sa.Column("volume_per_unit", sa.Numeric(10, 4), nullable=True))


def downgrade() -> None:
    op.drop_column("entities", "volume_per_unit")
    op.drop_column("entities", "weight_per_unit")
