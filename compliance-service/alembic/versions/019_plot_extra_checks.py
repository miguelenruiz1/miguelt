"""Add CHECK constraints for plot.risk_level and geolocation_type enums.

Revision ID: 019_plot_extra
Revises: 018_record_checks
"""
from alembic import op

revision = "019_plot_extra"
down_revision = "018_record_checks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_compliance_plots_risk_level",
        "compliance_plots",
        "risk_level IN ('low','standard','high','critical')",
    )
    op.create_check_constraint(
        "ck_compliance_plots_geo_type",
        "compliance_plots",
        "geolocation_type IN ('point','polygon','multipolygon')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_compliance_plots_risk_level", "compliance_plots", type_="check")
    op.drop_constraint("ck_compliance_plots_geo_type", "compliance_plots", type_="check")
