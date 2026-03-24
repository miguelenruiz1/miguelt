"""Add notes and shipment_leg_id to custody_events for Phase 1A.

Revision ID: 006_expanded_events
Revises: 005_performance_indexes
Create Date: 2026-03-21
"""
from alembic import op
import sqlalchemy as sa

revision = "006_expanded_events"
down_revision = "005_performance_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Free-text notes field for any event
    op.add_column(
        "custody_events",
        sa.Column("notes", sa.Text(), nullable=True),
    )
    # FK placeholder for future shipment_legs table (Phase 1B).
    # Added now so Phase 1A events can optionally reference a leg.
    op.add_column(
        "custody_events",
        sa.Column("shipment_leg_id", sa.Uuid(), nullable=True),
    )
    op.create_index(
        "ix_custody_events_leg",
        "custody_events",
        ["shipment_leg_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_custody_events_leg", table_name="custody_events")
    op.drop_column("custody_events", "shipment_leg_id")
    op.drop_column("custody_events", "notes")
