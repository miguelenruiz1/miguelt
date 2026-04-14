"""Add vereda and frontera_agricola_status for Colombia optimization."""

revision = "029_plot_colombia_fields"
down_revision = "028_plot_degradation_free"

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.add_column("compliance_plots", sa.Column("vereda", sa.Text(), nullable=True))
    op.add_column("compliance_plots", sa.Column("frontera_agricola_status", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("compliance_plots", "frontera_agricola_status")
    op.drop_column("compliance_plots", "vereda")
