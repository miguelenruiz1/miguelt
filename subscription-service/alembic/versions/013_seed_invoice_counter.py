"""Seed invoice sequence_counter from existing invoice_number values.

CRITICAL: without this, the first invoice generated post-deploy starts at 1
and collides with INV-{year}-0001 already in the table (UNIQUE).

Revision ID: 013
Revises: 012
"""
from alembic import op
from sqlalchemy import text
from datetime import datetime

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    year = datetime.utcnow().year
    for y in range(year - 5, year + 1):
        conn.execute(
            text(
                """
                INSERT INTO sequence_counters (scope, value, updated_at)
                SELECT
                    :scope,
                    COALESCE(MAX(CAST(SUBSTRING(invoice_number FROM '\\d+$') AS BIGINT)), 0),
                    NOW()
                FROM invoices
                WHERE invoice_number LIKE :prefix
                  AND invoice_number ~ ('^INV-' || :ystr || '-[0-9]+$')
                ON CONFLICT (scope) DO UPDATE
                    SET value = GREATEST(sequence_counters.value, EXCLUDED.value)
                """
            ),
            {"scope": f"invoice-{y}", "prefix": f"INV-{y}-%", "ystr": str(y)},
        )


def downgrade() -> None:
    pass
