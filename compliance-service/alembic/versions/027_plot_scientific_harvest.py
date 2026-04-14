"""Add scientific_name and last_harvest_date to compliance_plots (EUDR Art. 9(1)(a)(d))."""

revision = "027_plot_scientific_harvest"
down_revision = "026_evidence_weight"

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.add_column("compliance_plots", sa.Column("scientific_name", sa.Text(), nullable=True))
    op.add_column("compliance_plots", sa.Column("last_harvest_date", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("compliance_plots", "last_harvest_date")
    op.drop_column("compliance_plots", "scientific_name")
