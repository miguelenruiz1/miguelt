"""Add degradation_free flag to compliance_plots (EUDR Art. 2(7))."""

revision = "028_plot_degradation_free"
down_revision = "027_plot_scientific_harvest"

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.add_column(
        "compliance_plots",
        sa.Column("degradation_free", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("compliance_plots", "degradation_free")
