"""Add anchor_rules table for configurable blockchain anchoring.

Revision ID: 064
Revises: 063_blockchain_tracking
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "064"
down_revision = "063"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "anchor_rules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("trigger_event", sa.String(50), nullable=False),
        sa.Column("conditions", JSONB, nullable=False, server_default="{}"),
        sa.Column("actions", JSONB, nullable=False, server_default='{"anchor": true}'),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("priority", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_anchor_rules_tenant", "anchor_rules", ["tenant_id"])
    op.create_index("ix_anchor_rules_tenant_entity", "anchor_rules", ["tenant_id", "entity_type"])

    # Add prev_anchor_hash for multi-part approval chain (Phase 3c)
    op.add_column("purchase_orders", sa.Column("prev_anchor_hash", sa.String(64), nullable=True))
    op.add_column("purchase_orders", sa.Column("anchor_chain", JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column("purchase_orders", "anchor_chain")
    op.drop_column("purchase_orders", "prev_anchor_hash")
    op.drop_table("anchor_rules")
