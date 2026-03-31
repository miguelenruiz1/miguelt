"""Add bridge tables for evidence documents linked to records and plots.

Revision ID: 007_document_links
Revises: 006_eudr_gaps
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "007_document_links"
down_revision = "006_eudr_gaps"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "compliance_record_documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("record_id", UUID(as_uuid=True), sa.ForeignKey("compliance_records.id", ondelete="CASCADE"), nullable=False),
        sa.Column("media_file_id", UUID(as_uuid=True), nullable=False),
        sa.Column("document_type", sa.Text, nullable=False),
        sa.Column("file_hash", sa.Text, nullable=True),
        sa.Column("filename", sa.Text, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("uploaded_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.UniqueConstraint("record_id", "media_file_id", name="uq_recdoc_record_media"),
        sa.Index("ix_recdoc_tenant", "tenant_id"),
        sa.Index("ix_recdoc_record", "record_id"),
    )

    op.create_table(
        "compliance_plot_documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("plot_id", UUID(as_uuid=True), sa.ForeignKey("compliance_plots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("media_file_id", UUID(as_uuid=True), nullable=False),
        sa.Column("document_type", sa.Text, nullable=False),
        sa.Column("file_hash", sa.Text, nullable=True),
        sa.Column("filename", sa.Text, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("uploaded_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.UniqueConstraint("plot_id", "media_file_id", name="uq_plotdoc_plot_media"),
        sa.Index("ix_plotdoc_tenant", "tenant_id"),
        sa.Index("ix_plotdoc_plot", "plot_id"),
    )


def downgrade() -> None:
    op.drop_table("compliance_plot_documents")
    op.drop_table("compliance_record_documents")
