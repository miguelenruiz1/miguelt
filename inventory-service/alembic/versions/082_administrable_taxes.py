"""Administrable tax system: tax_categories + multi-stack line taxes.

Adds:
- tax_categories: tenant-managed catalog of tax kinds (e.g. IVA, IRPF, ICMS, IPI).
  Each category declares a behavior ('addition' adds to total, 'withholding'
  subtracts from payable) and a base_kind ('subtotal' or 'subtotal_with_other_additions'
  for cumulative taxes like Brazil's IPI).
- tax_rates.category_id: FK to tax_categories. Backfilled from the legacy
  tax_type string column. tax_type stays for backwards compat (deprecated).
- sales_order_line_taxes: per-line tax stack. Allows N taxes per line, needed
  for Brazil (ICMS+IPI+PIS+COFINS+ISS) and any future country with stacked taxes.
  Existing single-tax lines are backfilled into this table.

After this migration:
- New code paths read sales_order_line_taxes for the source of truth.
- Legacy single-tax columns (tax_rate_id, tax_rate_pct, retention_pct) on
  sales_order_lines stay populated as a summary (sum of additions / sum of
  withholdings) for read-only compatibility with old reports.

Revision ID: 082
Revises: 081
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from datetime import datetime
import uuid


revision = "082"
down_revision = "081"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1) tax_categories ──────────────────────────────────────────────────
    op.create_table(
        "tax_categories",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(50), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("behavior", sa.String(20), nullable=False),  # addition | withholding
        sa.Column("base_kind", sa.String(40), nullable=False, server_default="subtotal"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("color", sa.String(20), nullable=True),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_system", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_tax_category_tenant_slug"),
    )
    op.create_index("ix_tax_category_tenant", "tax_categories", ["tenant_id", "is_active"])

    # ── 2) tax_rates.category_id ───────────────────────────────────────────
    op.add_column(
        "tax_rates",
        sa.Column("category_id", sa.String(36), nullable=True),
    )
    op.create_foreign_key(
        "fk_tax_rates_category",
        "tax_rates", "tax_categories",
        ["category_id"], ["id"],
        ondelete="RESTRICT",
    )

    # ── 3) sales_order_line_taxes ──────────────────────────────────────────
    op.create_table(
        "sales_order_line_taxes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("line_id", sa.String(36), nullable=False),
        sa.Column("tax_rate_id", sa.String(36), nullable=False),
        sa.Column("rate_pct", sa.Numeric(7, 6), nullable=False),  # stored as fraction (0.190000)
        sa.Column("base_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("tax_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("behavior", sa.String(20), nullable=False),  # snapshot at apply time
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["line_id"], ["sales_order_lines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tax_rate_id"], ["tax_rates.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_sol_taxes_line", "sales_order_line_taxes", ["line_id"])
    op.create_index("ix_sol_taxes_tenant", "sales_order_line_taxes", ["tenant_id"])

    # ── 4) Backfill: per tenant + legacy tax_type, create matching categories ──
    # The empty-state setup wizard (frontend) handles fresh tenants. Here we
    # only convert what already exists into the new model.
    conn = op.get_bind()

    # Map of legacy slug → (display name, behavior). Anything not in this map
    # becomes a new category with behavior='addition' that the admin can edit.
    legacy_map = {
        "iva":         ("IVA",                  "addition"),
        "vat":         ("VAT",                  "addition"),
        "tax":         ("Impuesto",             "addition"),
        "ica":         ("ICA",                  "addition"),
        "consumo":     ("Impuesto al consumo",  "addition"),
        "retention":   ("Retención",            "withholding"),
        "retencion":   ("Retención",            "withholding"),
        "withholding": ("Withholding tax",      "withholding"),
        "irpf":        ("IRPF",                 "withholding"),
        "reteiva":     ("ReteIVA",              "withholding"),
        "reteica":     ("ReteICA",              "withholding"),
    }

    existing_pairs = conn.execute(
        text("SELECT DISTINCT tenant_id, tax_type FROM tax_rates WHERE tenant_id IS NOT NULL")
    ).fetchall()
    now = datetime.utcnow()

    for tenant_id, tax_type in existing_pairs:
        if not tax_type:
            tax_type = "impuesto"
        slug = tax_type.strip().lower()
        if slug in legacy_map:
            display_name, behavior = legacy_map[slug]
        else:
            display_name = slug.title()
            behavior = "addition"

        existing = conn.execute(
            text("SELECT id FROM tax_categories WHERE tenant_id = :t AND slug = :s"),
            {"t": tenant_id, "s": slug},
        ).first()
        if not existing:
            conn.execute(
                text("""
                    INSERT INTO tax_categories
                        (id, tenant_id, slug, name, behavior, base_kind,
                         description, color, sort_order, is_system, is_active,
                         created_at, updated_at)
                    VALUES (:id, :t, :s, :n, :b, 'subtotal',
                            null, :c, 100, false, true, :now, :now)
                """),
                {
                    "id": str(uuid.uuid4()), "t": tenant_id, "s": slug,
                    "n": display_name, "b": behavior,
                    "c": "blue" if behavior == "addition" else "amber",
                    "now": now,
                },
            )

    # ── 5) Backfill tax_rates.category_id from tax_type ────────────────────
    conn.execute(text("""
        UPDATE tax_rates tr
        SET category_id = tc.id
        FROM tax_categories tc
        WHERE tc.tenant_id = tr.tenant_id
          AND tc.slug = LOWER(COALESCE(tr.tax_type, 'impuesto'))
          AND tr.category_id IS NULL
    """))

    # ── 6) Backfill sales_order_line_taxes from existing single-tax lines ──
    # For each line with a tax_rate_id, create one row in sales_order_line_taxes.
    # For each line with a non-zero retention_pct, create another row using a
    # placeholder rate (we don't have a withholding rate FK, so we synthesize one
    # against the first available withholding category for that tenant).
    conn.execute(text("""
        INSERT INTO sales_order_line_taxes
            (id, tenant_id, line_id, tax_rate_id, rate_pct, base_amount, tax_amount, behavior, created_at)
        SELECT
            gen_random_uuid()::text,
            sol.tenant_id,
            sol.id,
            sol.tax_rate_id,
            COALESCE(sol.tax_rate_pct, sol.tax_rate / 100.0, 0),
            COALESCE(sol.line_subtotal, sol.line_total, 0),
            COALESCE(sol.tax_amount, 0),
            'addition',
            NOW()
        FROM sales_order_lines sol
        WHERE sol.tax_rate_id IS NOT NULL
    """))

    # Note: we do NOT backfill retention as a separate row because legacy
    # retention_pct doesn't reference any tax_rate_id. The legacy summary fields
    # (retention_pct, retention_amount) on the line stay populated and the
    # service falls back to them when no withholding rows exist for the line.


def downgrade() -> None:
    op.drop_index("ix_sol_taxes_tenant", table_name="sales_order_line_taxes")
    op.drop_index("ix_sol_taxes_line", table_name="sales_order_line_taxes")
    op.drop_table("sales_order_line_taxes")

    op.drop_constraint("fk_tax_rates_category", "tax_rates", type_="foreignkey")
    op.drop_column("tax_rates", "category_id")

    op.drop_index("ix_tax_category_tenant", table_name="tax_categories")
    op.drop_table("tax_categories")
