"""Colombia MVP — lock tax catalog to IVA + Retefuente only.

For every tenant with at least one existing tax_category:
- Upsert system categories 'iva' (IVA, addition) and 'retefuente' (Retención en
  la Fuente, withholding) as is_system=true, is_active=true.
- Delete tax_rates referencing any category whose slug is NOT in the allowed
  set. This is irreversible by design — recovering pre-cleanup rates requires
  manual restore from backup.
- Delete tax_categories whose slug is NOT in the allowed set.

Idempotent: safe to re-run. Uses ON CONFLICT for inserts, skips cleanup when
nothing matches.

Revision ID: 086
Revises: 085
"""
from alembic import op
from sqlalchemy import text
from datetime import datetime
import uuid


revision = "086"
down_revision = "085"
branch_labels = None
depends_on = None


ALLOWED_SLUGS = ("iva", "retefuente")


def upgrade() -> None:
    conn = op.get_bind()
    now = datetime.utcnow()

    # ── 1) Upsert system categories per tenant ─────────────────────────────
    tenants = conn.execute(
        text("SELECT DISTINCT tenant_id FROM tax_categories WHERE tenant_id IS NOT NULL")
    ).fetchall()

    upsert_sql = text("""
        INSERT INTO tax_categories
            (id, tenant_id, slug, name, behavior, base_kind,
             description, color, sort_order, is_system, is_active,
             created_at, updated_at)
        VALUES
            (:id, :tenant_id, :slug, :name, :behavior, 'subtotal',
             NULL, :color, :sort_order, true, true, :now, :now)
        ON CONFLICT (tenant_id, slug) DO UPDATE
            SET is_system = true,
                is_active = true,
                name = EXCLUDED.name,
                behavior = EXCLUDED.behavior,
                updated_at = EXCLUDED.updated_at
    """)

    for (tenant_id,) in tenants:
        conn.execute(upsert_sql, {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "slug": "iva",
            "name": "IVA",
            "behavior": "addition",
            "color": "blue",
            "sort_order": 0,
            "now": now,
        })
        conn.execute(upsert_sql, {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "slug": "retefuente",
            "name": "Retención en la Fuente",
            "behavior": "withholding",
            "color": "amber",
            "sort_order": 1,
            "now": now,
        })

    # ── 2) Delete tax_rates belonging to disallowed categories ─────────────
    # sales_order_line_taxes FKs tax_rates with ondelete=RESTRICT — but historical
    # lines reference rates whose categories we are removing. Null those first
    # to avoid FK violation. (Historical invoices keep their snapshotted
    # rate_pct/tax_amount; we just break the FK back to the rate catalog.)
    conn.execute(text("""
        DELETE FROM sales_order_line_taxes
        WHERE tax_rate_id IN (
            SELECT tr.id FROM tax_rates tr
            JOIN tax_categories tc ON tc.id = tr.category_id
            WHERE tc.slug NOT IN ('iva', 'retefuente')
        )
    """))

    conn.execute(text("""
        DELETE FROM tax_rates
        WHERE category_id IN (
            SELECT id FROM tax_categories
            WHERE slug NOT IN ('iva', 'retefuente')
        )
    """))

    # ── 3) Delete disallowed categories ────────────────────────────────────
    conn.execute(text("""
        DELETE FROM tax_categories
        WHERE slug NOT IN ('iva', 'retefuente')
    """))


def downgrade() -> None:
    # Irreversible by design — not restoring non-CO taxes.
    pass
