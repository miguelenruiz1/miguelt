"""Add freight cost columns to shipment_documents.

Revision ID: 011_freight_costs
Revises: a1b2c3d4e5f6
"""
from alembic import op
import sqlalchemy as sa

revision = "011_freight_costs"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None

COLUMNS = [
    ("freight_cost", sa.Numeric(14, 2)),
    ("insurance_cost", sa.Numeric(14, 2)),
    ("handling_cost", sa.Numeric(14, 2)),
    ("customs_cost", sa.Numeric(14, 2)),
    ("other_costs", sa.Numeric(14, 2)),
    ("total_logistics_cost", sa.Numeric(14, 2)),
    ("cost_currency", sa.String(3)),
]


def upgrade() -> None:
    for col_name, col_type in COLUMNS:
        op.add_column("shipment_documents", sa.Column(col_name, col_type, nullable=True))


def downgrade() -> None:
    for col_name, _ in reversed(COLUMNS):
        op.drop_column("shipment_documents", col_name)
