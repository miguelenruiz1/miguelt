"""Add capture accuracy + producer scale fields to compliance_plots.

MITECO webinar 2 (Tomas, EFI) highlighted that a polygon without capture
metadata is indefensible in an inspection. MITECO webinar 3 (Alice, EFI)
distinguishes smallholder vs industrial for the legal requirements that
apply. These columns cover both gaps.

Revision ID: 022_plot_accuracy_scale
Revises: 021_plot_tenure
"""
from alembic import op
import sqlalchemy as sa


revision = "022_plot_accuracy_scale"
down_revision = "021_plot_tenure"
branch_labels = None
depends_on = None


VALID_CAPTURE_METHOD = (
    "handheld_gps",   # GPS de mano (smartphone, Garmin, etc.)
    "rtk_gps",        # Real Time Kinematic (cm-level)
    "drone",          # Dron con fotogrametria
    "manual_map",     # Trazado manual sobre imagen satelital
    "cadastral",      # Importado de catastro oficial
    "survey",         # Levantamiento topografico profesional
    "unknown",
)

VALID_PRODUCER_SCALE = (
    "smallholder",    # < 4 ha — requisitos legales reducidos
    "medium",         # 4–50 ha
    "industrial",     # > 50 ha — exige EIA, contratos, FPIC
)


def upgrade() -> None:
    op.add_column(
        "compliance_plots",
        sa.Column("gps_accuracy_m", sa.Numeric(8, 2), nullable=True),
    )
    op.add_column(
        "compliance_plots",
        sa.Column("capture_method", sa.Text(), nullable=True),
    )
    op.add_column(
        "compliance_plots",
        sa.Column("capture_device", sa.Text(), nullable=True),
    )
    op.add_column(
        "compliance_plots",
        sa.Column("capture_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "compliance_plots",
        sa.Column("producer_scale", sa.Text(), nullable=True),
    )

    op.create_check_constraint(
        "ck_compliance_plots_capture_method",
        "compliance_plots",
        "capture_method IS NULL OR capture_method IN ("
        + ",".join(f"'{m}'" for m in VALID_CAPTURE_METHOD)
        + ")",
    )
    op.create_check_constraint(
        "ck_compliance_plots_producer_scale",
        "compliance_plots",
        "producer_scale IS NULL OR producer_scale IN ("
        + ",".join(f"'{s}'" for s in VALID_PRODUCER_SCALE)
        + ")",
    )
    op.create_check_constraint(
        "ck_compliance_plots_gps_accuracy_positive",
        "compliance_plots",
        "gps_accuracy_m IS NULL OR gps_accuracy_m >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_compliance_plots_gps_accuracy_positive", "compliance_plots", type_="check"
    )
    op.drop_constraint(
        "ck_compliance_plots_producer_scale", "compliance_plots", type_="check"
    )
    op.drop_constraint(
        "ck_compliance_plots_capture_method", "compliance_plots", type_="check"
    )
    for col in (
        "producer_scale",
        "capture_date",
        "capture_device",
        "capture_method",
        "gps_accuracy_m",
    ):
        op.drop_column("compliance_plots", col)
