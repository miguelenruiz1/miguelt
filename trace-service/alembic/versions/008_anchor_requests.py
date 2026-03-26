"""Add anchor_requests table for Anchoring-as-a-Service.

Revision ID: 008
Revises: 007_event_type_configs
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP, JSONB

revision = "008_anchor_requests"
down_revision = "007_event_type_configs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "anchor_requests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("source_service", sa.String(50), nullable=False),
        sa.Column("source_entity_type", sa.String(50), nullable=False),
        sa.Column("source_entity_id", sa.String(36), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("anchor_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("solana_tx_sig", sa.String(128), nullable=True),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text, nullable=True),
        sa.Column("callback_url", sa.String(500), nullable=True),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("anchored_at", TIMESTAMP(timezone=True), nullable=True),
        sa.Column("updated_at", TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_anchor_requests_status", "anchor_requests", ["anchor_status"])
    op.create_index("ix_anchor_requests_hash", "anchor_requests", ["payload_hash"])
    op.create_index("ix_anchor_requests_tenant", "anchor_requests", ["tenant_id"])
    op.create_index(
        "ix_anchor_requests_source",
        "anchor_requests",
        ["source_service", "source_entity_type", "source_entity_id"],
    )


def downgrade() -> None:
    op.drop_table("anchor_requests")
