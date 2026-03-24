"""Create compliance_plots table.

Revision ID: 002_plots
Revises: 001_frameworks_and_activations
Create Date: 2026-03-21
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP
import uuid

revision = "002_plots"
down_revision = "001_frameworks_and_activations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "compliance_plots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", UUID(as_uuid=True), nullable=True),
        sa.Column("plot_code", sa.Text(), nullable=False),
        sa.Column("plot_area_ha", sa.Numeric(10, 4), nullable=True),
        sa.Column("geolocation_type", sa.Text(), nullable=False, server_default="'point'"),
        sa.Column("lat", sa.Numeric(10, 6), nullable=True),
        sa.Column("lng", sa.Numeric(10, 6), nullable=True),
        sa.Column("geojson_arweave_url", sa.Text(), nullable=True),
        sa.Column("geojson_hash", sa.Text(), nullable=True),
        sa.Column("country_code", sa.Text(), nullable=False, server_default="'CO'"),
        sa.Column("region", sa.Text(), nullable=True),
        sa.Column("municipality", sa.Text(), nullable=True),
        sa.Column("land_title_number", sa.Text(), nullable=True),
        sa.Column("land_title_hash", sa.Text(), nullable=True),
        sa.Column("deforestation_free", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("cutoff_date_compliant", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("legal_land_use", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("risk_level", sa.Text(), nullable=False, server_default="'standard'"),
        sa.Column("satellite_report_url", sa.Text(), nullable=True),
        sa.Column("satellite_report_hash", sa.Text(), nullable=True),
        sa.Column("satellite_verified_at", TIMESTAMP(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("metadata", JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("tenant_id", "plot_code", name="uq_plot_tenant_code"),
        sa.Index("ix_plots_tenant", "tenant_id"),
        sa.Index("ix_plots_org", "organization_id"),
    )


def downgrade() -> None:
    op.drop_table("compliance_plots")
