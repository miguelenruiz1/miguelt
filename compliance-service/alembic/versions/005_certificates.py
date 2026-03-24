"""Create compliance_certificates table.

Revision ID: 005_certificates
Revises: 004_plot_links
Create Date: 2026-03-21
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
import uuid

revision = "005_certificates"
down_revision = "004_plot_links"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "compliance_certificates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "record_id",
            UUID(as_uuid=True),
            sa.ForeignKey("compliance_records.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("certificate_number", sa.Text, unique=True, nullable=False),
        sa.Column("framework_slug", sa.Text, nullable=False),
        sa.Column("asset_id", UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.Text, nullable=False, server_default="generating"),
        sa.Column("pdf_url", sa.Text, nullable=True),
        sa.Column("pdf_hash", sa.Text, nullable=True),
        sa.Column("pdf_size_bytes", sa.Integer, nullable=True),
        sa.Column("verify_url", sa.Text, nullable=False),
        sa.Column("qr_code_url", sa.Text, nullable=True),
        sa.Column("valid_from", sa.Date, nullable=False),
        sa.Column("valid_until", sa.Date, nullable=False),
        sa.Column("generated_at", TIMESTAMP(timezone=True), nullable=True),
        sa.Column("generated_by", UUID(as_uuid=True), nullable=True),
        sa.Column("generation_error", sa.Text, nullable=True),
        sa.Column("solana_cnft_address", sa.Text, nullable=True),
        sa.Column("solana_tx_sig", sa.Text, nullable=True),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Index("ix_certificates_tenant", "tenant_id"),
        sa.Index("ix_certificates_record", "record_id"),
        sa.Index("ix_certificates_number", "certificate_number"),
        sa.Index("ix_certificates_status", "status"),
    )


def downgrade() -> None:
    op.drop_table("compliance_certificates")
