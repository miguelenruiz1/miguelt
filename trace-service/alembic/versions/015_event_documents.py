"""Media module — centralized file storage + event document links + doc requirements.

Revision ID: 015_event_docs
Revises: 014_workflow_multi_event_transitions
Create Date: 2026-03-30
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP

revision = "015_event_docs"
down_revision = "014_multi_event"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. media_files — centralized file library ────────────────────────────
    op.create_table(
        "media_files",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False),
        # File identity
        sa.Column("filename", sa.Text, nullable=False),
        sa.Column("original_filename", sa.Text, nullable=False),
        sa.Column("content_type", sa.Text, nullable=False),
        sa.Column("file_size", sa.Integer, nullable=False),
        # Integrity
        sa.Column("file_hash", sa.Text, nullable=False),
        sa.Column("storage_backend", sa.Text, nullable=False, server_default="local"),
        sa.Column("storage_key", sa.Text, nullable=False),
        sa.Column("url", sa.Text, nullable=False),
        # Classification
        sa.Column("category", sa.Text, nullable=False, server_default="general"),
        sa.Column("document_type", sa.Text, nullable=True),
        sa.Column("title", sa.Text, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("tags", sa.ARRAY(sa.Text), nullable=False, server_default="{}"),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        # Ownership
        sa.Column("uploaded_by", sa.Text, nullable=True),
        sa.Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_media_files_tenant", "media_files", ["tenant_id"])
    op.create_index("ix_media_files_category", "media_files", ["category"])
    op.create_index("ix_media_files_document_type", "media_files", ["document_type"])
    op.create_index("ix_media_files_hash", "media_files", ["file_hash"])

    # ── 2. event_document_links — N:M between events and media files ─────────
    op.create_table(
        "event_document_links",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("event_id", UUID(as_uuid=True), sa.ForeignKey("custody_events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("asset_id", UUID(as_uuid=True), sa.ForeignKey("assets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("media_file_id", UUID(as_uuid=True), sa.ForeignKey("media_files.id", ondelete="CASCADE"), nullable=False),
        # Contextual info for this link
        sa.Column("document_type", sa.Text, nullable=False),
        sa.Column("is_required", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("compliance_source", sa.Text, nullable=True),
        sa.Column("linked_by", sa.Text, nullable=True),
        sa.Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_event_doc_links_event", "event_document_links", ["event_id"])
    op.create_index("ix_event_doc_links_asset", "event_document_links", ["asset_id"])
    op.create_index("ix_event_doc_links_media", "event_document_links", ["media_file_id"])
    op.create_index("ix_event_doc_links_tenant", "event_document_links", ["tenant_id"])
    op.create_unique_constraint(
        "uq_event_doc_links_event_media", "event_document_links", ["event_id", "media_file_id"]
    )

    # ── 3. Add required_documents columns to workflow_event_types ────────────
    op.add_column(
        "workflow_event_types",
        sa.Column("required_documents", JSONB, nullable=True),
    )
    op.add_column(
        "workflow_event_types",
        sa.Column("compliance_required_documents", JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("workflow_event_types", "compliance_required_documents")
    op.drop_column("workflow_event_types", "required_documents")
    op.drop_constraint("uq_event_doc_links_event_media", "event_document_links")
    op.drop_index("ix_event_doc_links_tenant", table_name="event_document_links")
    op.drop_index("ix_event_doc_links_media", table_name="event_document_links")
    op.drop_index("ix_event_doc_links_asset", table_name="event_document_links")
    op.drop_index("ix_event_doc_links_event", table_name="event_document_links")
    op.drop_table("event_document_links")
    op.drop_index("ix_media_files_hash", table_name="media_files")
    op.drop_index("ix_media_files_document_type", table_name="media_files")
    op.drop_index("ix_media_files_category", table_name="media_files")
    op.drop_index("ix_media_files_tenant", table_name="media_files")
    op.drop_table("media_files")
