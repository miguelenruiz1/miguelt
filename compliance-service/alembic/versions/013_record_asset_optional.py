"""Make compliance_records.asset_id nullable for standalone records.

Revision ID: 013_asset_optional
Revises: 012_geojson_data
"""
from alembic import op
import sqlalchemy as sa

revision = "013_asset_optional"
down_revision = "012_geojson_data"


def upgrade() -> None:
    op.alter_column(
        "compliance_records",
        "asset_id",
        existing_type=sa.dialects.postgresql.UUID(as_uuid=True),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "compliance_records",
        "asset_id",
        existing_type=sa.dialects.postgresql.UUID(as_uuid=True),
        nullable=False,
    )
