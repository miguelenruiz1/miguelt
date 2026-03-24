"""Create compliance_plot_links table.

Revision ID: 004_plot_links
Revises: 003_records
Create Date: 2026-03-21
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid

revision = "004_plot_links"
down_revision = "003_records"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "compliance_plot_links",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "record_id",
            UUID(as_uuid=True),
            sa.ForeignKey("compliance_records.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "plot_id",
            UUID(as_uuid=True),
            sa.ForeignKey("compliance_plots.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("quantity_from_plot_kg", sa.Numeric(12, 4), nullable=True),
        sa.Column("percentage_from_plot", sa.Numeric(5, 2), nullable=True),
        sa.UniqueConstraint("record_id", "plot_id", name="uq_plot_link_record_plot"),
        sa.Index("ix_plot_links_record", "record_id"),
        sa.Index("ix_plot_links_plot", "plot_id"),
    )


def downgrade() -> None:
    op.drop_table("compliance_plot_links")
