"""Atomic counters table for race-free PO/SO/Remission/CC numbering.

Replaces the read-then-MAX+1 pattern in repos with an atomic UPSERT that
increments a per-tenant per-year counter row in a single statement, eliminating
duplicate-number races under concurrency.

Revision ID: 076
Revises: 075
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "076"
down_revision = "075"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sequence_counters",
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("scope", sa.String(64), nullable=False),  # e.g. 'po-2026', 'so-2026'
        sa.Column("value", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("tenant_id", "scope", name="pk_sequence_counters"),
    )


def downgrade() -> None:
    op.drop_table("sequence_counters")
