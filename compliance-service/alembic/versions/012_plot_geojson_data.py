"""Add geojson_data JSONB column to plots for local polygon storage.

Revision ID: 012_geojson_data
Revises: 011_integrations
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "012_geojson_data"
down_revision = "011_integrations"


def upgrade() -> None:
    op.add_column("compliance_plots", sa.Column("geojson_data", JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column("compliance_plots", "geojson_data")
