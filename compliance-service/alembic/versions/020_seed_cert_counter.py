"""Seed certificate sequence_counter from existing certificate_number values.

CRITICAL: without this, the first certificate generated post-deploy starts at 1
and collides with TL-{year}-000001 already in the table (UNIQUE).

Revision ID: 020_seed_cert_counter
Revises: 019_plot_extra
"""
from alembic import op
from sqlalchemy import text
from datetime import datetime

revision = "020_seed_cert_counter"
down_revision = "019_plot_extra"
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
                    COALESCE(MAX(CAST(SUBSTRING(certificate_number FROM '\\d+$') AS BIGINT)), 0),
                    NOW()
                FROM compliance_certificates
                WHERE certificate_number LIKE :prefix
                  AND certificate_number ~ ('^TL-' || :ystr || '-[0-9]+$')
                ON CONFLICT (scope) DO UPDATE
                    SET value = GREATEST(sequence_counters.value, EXCLUDED.value)
                """
            ),
            {"scope": f"certificate-{y}", "prefix": f"TL-{y}-%", "ystr": str(y)},
        )


def downgrade() -> None:
    pass
