"""Add production_in/production_out movement types and fix historical data.

Revision ID: 012
Revises: 011
Create Date: 2026-03-02
"""
from alembic import op

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # movement_type column uses native_enum=False (VARCHAR), so no ALTER TYPE needed.
    # Fix historical production movements that used wrong types.
    op.execute(
        "UPDATE stock_movements SET movement_type='production_out' "
        "WHERE movement_type='waste' AND notes LIKE 'Producción%consumo de componente'"
    )
    op.execute(
        "UPDATE stock_movements SET movement_type='production_in' "
        "WHERE movement_type='purchase' AND notes LIKE 'Producción%producto terminado'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE stock_movements SET movement_type='waste' "
        "WHERE movement_type='production_out'"
    )
    op.execute(
        "UPDATE stock_movements SET movement_type='purchase' "
        "WHERE movement_type='production_in'"
    )
