"""Add parent_event_id self-FK to custody_events for hierarchical timeline.

Movements (state transitions like HANDOFF, ARRIVED, LOADED) act as parents.
Informational events (NOTE, INSPECTION, COMPLIANCE_VERIFIED, etc.) can be
linked as children of the most recent transition for the same asset.

The hierarchy is:
  - root events (parent_event_id IS NULL): state-changing transitions
  - child events: informational details associated with the parent transition

Backward compatible: existing rows have parent_event_id = NULL → all treated
as roots, which matches today's flat-list rendering.

Revision ID: 021_event_parent
Revises: 020_blockchain_check
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "021_event_parent"
down_revision = "020_blockchain_check"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "custody_events",
        sa.Column(
            "parent_event_id",
            UUID(as_uuid=True),
            sa.ForeignKey("custody_events.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    # Composite index for "find children of event X for asset Y, ordered by time"
    op.create_index(
        "ix_custody_events_parent",
        "custody_events",
        ["asset_id", "parent_event_id", "timestamp"],
        postgresql_where=sa.text("parent_event_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_custody_events_parent", table_name="custody_events")
    op.drop_column("custody_events", "parent_event_id")
