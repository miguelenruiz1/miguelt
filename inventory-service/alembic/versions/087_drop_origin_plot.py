"""Drop EUDR origin_plot pointers from entities and suppliers.

The compliance (EUDR) module was removed from the platform, so the cross-DB
pointers to compliance_plots no longer have a target. tax_id_type (added in
083) stays — it is generic export-readiness data, not EUDR-specific.

Revision: 087
Revises: 086
"""
from alembic import op
import sqlalchemy as sa


revision = "087"
down_revision = "086"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("suppliers", "origin_plot_code")
    op.drop_column("suppliers", "origin_plot_id")
    op.drop_column("entities", "origin_plot_code")
    op.drop_column("entities", "origin_plot_id")


def downgrade() -> None:
    op.add_column("entities", sa.Column("origin_plot_id", sa.String(36), nullable=True))
    op.add_column("entities", sa.Column("origin_plot_code", sa.String(64), nullable=True))
    op.add_column("suppliers", sa.Column("origin_plot_id", sa.String(36), nullable=True))
    op.add_column("suppliers", sa.Column("origin_plot_code", sa.String(64), nullable=True))
