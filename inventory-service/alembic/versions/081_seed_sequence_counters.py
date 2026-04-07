"""Seed sequence_counters from existing PO/SO/REM numbers per tenant.

CRITICAL post-deploy migration: without this, the first PO/SO/REM created
after switching to the atomic counter starts at 1 and collides with the
existing PO-{year}-0001 row (UNIQUE constraint).

Idempotent: re-running won't bump counters since it uses MAX, not increment.

Revision ID: 081
Revises: 080
"""
from alembic import op
from sqlalchemy import text
from datetime import datetime

revision = "081"
down_revision = "080"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    year = datetime.utcnow().year
    # Look back 5 years to cover any year transitions in long-lived tenants
    years_to_seed = list(range(year - 5, year + 1))

    for y in years_to_seed:
        # PO numbers: PO-{year}-{seq}
        conn.execute(
            text(
                """
                INSERT INTO sequence_counters (tenant_id, scope, value, updated_at)
                SELECT
                    tenant_id::uuid,
                    :scope,
                    MAX(CAST(SUBSTRING(po_number FROM '\\d+$') AS BIGINT)),
                    NOW()
                FROM purchase_orders
                WHERE po_number LIKE :prefix
                  AND po_number ~ ('^PO-' || :ystr || '-[0-9]+$')
                GROUP BY tenant_id
                ON CONFLICT (tenant_id, scope) DO UPDATE
                    SET value = GREATEST(sequence_counters.value, EXCLUDED.value)
                """
            ),
            {"scope": f"po-{y}", "prefix": f"PO-{y}-%", "ystr": str(y)},
        )

        # SO numbers: SO-{year}-{seq}
        conn.execute(
            text(
                """
                INSERT INTO sequence_counters (tenant_id, scope, value, updated_at)
                SELECT
                    tenant_id::uuid,
                    :scope,
                    MAX(CAST(SUBSTRING(order_number FROM '\\d+$') AS BIGINT)),
                    NOW()
                FROM sales_orders
                WHERE order_number LIKE :prefix
                  AND order_number ~ ('^SO-' || :ystr || '-[0-9]+$')
                GROUP BY tenant_id
                ON CONFLICT (tenant_id, scope) DO UPDATE
                    SET value = GREATEST(sequence_counters.value, EXCLUDED.value)
                """
            ),
            {"scope": f"so-{y}", "prefix": f"SO-{y}-%", "ystr": str(y)},
        )

        # Remission numbers: REM-{year}-{seq}
        conn.execute(
            text(
                """
                INSERT INTO sequence_counters (tenant_id, scope, value, updated_at)
                SELECT
                    tenant_id::uuid,
                    :scope,
                    MAX(CAST(SUBSTRING(remission_number FROM '\\d+$') AS BIGINT)),
                    NOW()
                FROM sales_orders
                WHERE remission_number LIKE :prefix
                  AND remission_number ~ ('^REM-' || :ystr || '-[0-9]+$')
                GROUP BY tenant_id
                ON CONFLICT (tenant_id, scope) DO UPDATE
                    SET value = GREATEST(sequence_counters.value, EXCLUDED.value)
                """
            ),
            {"scope": f"rem-{y}", "prefix": f"REM-{y}-%", "ystr": str(y)},
        )


def downgrade() -> None:
    # Cannot reverse: we'd need to know which counters were seeded vs incremented later.
    # Truncating sequence_counters would lose post-deploy state.
    pass
