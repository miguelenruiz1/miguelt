"""Add missing columns to cycle_counts: methodology, assigned_counters,
minutes_per_count, updated_by.

Revision ID: 014
Revises: 013
Create Date: 2026-03-02
"""
from alembic import op
import sqlalchemy as sa

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def _col_exists(table: str, column: str) -> bool:
    """Check whether a column already exists (Postgres)."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c"
        ),
        {"t": table, "c": column},
    )
    return result.scalar() is not None


def upgrade() -> None:
    if not _col_exists("cycle_counts", "methodology"):
        op.add_column("cycle_counts", sa.Column("methodology", sa.String(30), nullable=True))

    if not _col_exists("cycle_counts", "assigned_counters"):
        op.add_column(
            "cycle_counts",
            sa.Column("assigned_counters", sa.Integer, nullable=False, server_default="1"),
        )

    if not _col_exists("cycle_counts", "minutes_per_count"):
        op.add_column(
            "cycle_counts",
            sa.Column("minutes_per_count", sa.Integer, nullable=False, server_default="2"),
        )

    if not _col_exists("cycle_counts", "updated_by"):
        op.add_column(
            "cycle_counts",
            sa.Column("updated_by", sa.String(255), nullable=True),
        )


def downgrade() -> None:
    for col in ("updated_by", "minutes_per_count", "assigned_counters", "methodology"):
        if _col_exists("cycle_counts", col):
            op.drop_column("cycle_counts", col)
