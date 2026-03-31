"""Initial media-service tables: tenants + media_files.

Revision ID: 001_media_tables
Revises: None
Create Date: 2026-03-30
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP

revision = "001_media_tables"
down_revision = None
branch_labels = None
depends_on = None

DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    # Minimal tenants table (synced from user-service)
    op.create_table(
        "tenants",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("slug", sa.Text, nullable=False),
        sa.Column("status", sa.Text, nullable=False, server_default="active"),
        sa.Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_unique_constraint("uq_tenants_slug", "tenants", ["slug"])

    # Seed default tenant
    op.execute(
        f"INSERT INTO tenants (id, name, slug) VALUES ('{DEFAULT_TENANT_ID}', 'Default', 'default') "
        f"ON CONFLICT DO NOTHING"
    )

    # Media files library
    op.create_table(
        "media_files",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("filename", sa.Text, nullable=False),
        sa.Column("original_filename", sa.Text, nullable=False),
        sa.Column("content_type", sa.Text, nullable=False),
        sa.Column("file_size", sa.Integer, nullable=False),
        sa.Column("file_hash", sa.Text, nullable=False),
        sa.Column("storage_backend", sa.Text, nullable=False, server_default="local"),
        sa.Column("storage_key", sa.Text, nullable=False),
        sa.Column("url", sa.Text, nullable=False),
        sa.Column("category", sa.Text, nullable=False, server_default="general"),
        sa.Column("document_type", sa.Text, nullable=True),
        sa.Column("title", sa.Text, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("tags", sa.ARRAY(sa.Text), nullable=False, server_default="{}"),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column("uploaded_by", sa.Text, nullable=True),
        sa.Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_media_files_tenant", "media_files", ["tenant_id"])
    op.create_index("ix_media_files_category", "media_files", ["category"])
    op.create_index("ix_media_files_document_type", "media_files", ["document_type"])
    op.create_index("ix_media_files_hash", "media_files", ["file_hash"])


def downgrade() -> None:
    op.drop_index("ix_media_files_hash", table_name="media_files")
    op.drop_index("ix_media_files_document_type", table_name="media_files")
    op.drop_index("ix_media_files_category", table_name="media_files")
    op.drop_index("ix_media_files_tenant", table_name="media_files")
    op.drop_table("media_files")
    op.drop_constraint("uq_tenants_slug", "tenants")
    op.drop_table("tenants")
