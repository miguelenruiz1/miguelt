"""Atomic counter table for race-free certificate numbering.

Replaces the COUNT(*)+1 pattern (which reused numbers after deletes and was
race-prone) with a single-statement UPSERT counter scoped per year.

Revision ID: 015_seq_counters
Revises: 014_integ_tenant
"""
from alembic import op
import sqlalchemy as sa

revision = "015_seq_counters"
down_revision = "014_integ_tenant"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sequence_counters",
        sa.Column("scope", sa.String(64), nullable=False),
        sa.Column("value", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("scope", name="pk_sequence_counters"),
    )


def downgrade() -> None:
    op.drop_table("sequence_counters")
