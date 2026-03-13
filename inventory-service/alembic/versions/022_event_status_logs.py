"""Add event_status_logs table for tracking status transitions with notes."""

revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.create_table(
        "event_status_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("event_id", sa.String(36), sa.ForeignKey("inventory_events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_status_id", sa.String(36), sa.ForeignKey("event_statuses.id", ondelete="SET NULL"), nullable=True),
        sa.Column("to_status_id", sa.String(36), sa.ForeignKey("event_statuses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("changed_by", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_event_status_logs_event_id", "event_status_logs", ["event_id"])


def downgrade() -> None:
    op.drop_index("ix_event_status_logs_event_id")
    op.drop_table("event_status_logs")
