"""Atomic counter table for race-free invoice / license numbering.

Revision ID: 011
Revises: 010
"""
from alembic import op
import sqlalchemy as sa

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sequence_counters",
        sa.Column("scope", sa.String(64), nullable=False),  # e.g. 'invoice-2026'
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
