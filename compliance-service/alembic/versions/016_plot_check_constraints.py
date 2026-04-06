"""Add CHECK constraints to compliance_plots: lat/lng ranges + positive area.

Revision ID: 016_plot_checks
Revises: 015_seq_counters
"""
from alembic import op

revision = "016_plot_checks"
down_revision = "015_seq_counters"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_compliance_plots_lat_range",
        "compliance_plots",
        "lat IS NULL OR (lat BETWEEN -90 AND 90)",
    )
    op.create_check_constraint(
        "ck_compliance_plots_lng_range",
        "compliance_plots",
        "lng IS NULL OR (lng BETWEEN -180 AND 180)",
    )
    op.create_check_constraint(
        "ck_compliance_plots_area_positive",
        "compliance_plots",
        "plot_area_ha IS NULL OR plot_area_ha > 0",
    )


def downgrade() -> None:
    op.drop_constraint("ck_compliance_plots_lat_range", "compliance_plots", type_="check")
    op.drop_constraint("ck_compliance_plots_lng_range", "compliance_plots", type_="check")
    op.drop_constraint("ck_compliance_plots_area_positive", "compliance_plots", type_="check")
