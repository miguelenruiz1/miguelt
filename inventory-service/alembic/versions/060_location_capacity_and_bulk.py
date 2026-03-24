"""Add weight/capacity/blocking to warehouse_locations.

Revision ID: 060
"""
from alembic import op
import sqlalchemy as sa

revision = "060"
down_revision = "059"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("warehouse_locations", sa.Column("max_weight_kg", sa.Numeric(10, 2), nullable=True))
    op.add_column("warehouse_locations", sa.Column("max_capacity", sa.Integer, nullable=True))
    op.add_column("warehouse_locations", sa.Column("blocked_inbound", sa.Boolean, server_default="false", nullable=False))
    op.add_column("warehouse_locations", sa.Column("blocked_outbound", sa.Boolean, server_default="false", nullable=False))
    op.add_column("warehouse_locations", sa.Column("block_reason", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("warehouse_locations", "block_reason")
    op.drop_column("warehouse_locations", "blocked_outbound")
    op.drop_column("warehouse_locations", "blocked_inbound")
    op.drop_column("warehouse_locations", "max_capacity")
    op.drop_column("warehouse_locations", "max_weight_kg")
