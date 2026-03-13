"""Add tax_rates table and tax columns to products, sales_orders, sales_order_lines.

Revision ID: 047
"""
from alembic import op
import sqlalchemy as sa

revision = "047"
down_revision = "046"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── tax_rates table ────────────────────────────────────────────────────
    op.create_table(
        "tax_rates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("tax_type", sa.String(20), nullable=False),
        sa.Column("rate", sa.Numeric(5, 4), nullable=False),
        sa.Column("is_default", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("dian_code", sa.String(20), nullable=True),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "name", name="uq_tax_rate_name"),
        sa.Index("ix_tax_rate_tenant", "tenant_id", "tax_type", "is_active"),
    )

    # ── Products: tax columns ──────────────────────────────────────────────
    op.add_column("entities", sa.Column(
        "tax_rate_id", sa.String(36),
        sa.ForeignKey("tax_rates.id", ondelete="SET NULL"), nullable=True,
    ))
    op.add_column("entities", sa.Column(
        "is_tax_exempt", sa.Boolean, nullable=False, server_default="false",
    ))
    op.add_column("entities", sa.Column(
        "retention_rate", sa.Numeric(5, 4), nullable=True,
    ))

    # ── SalesOrderLine: tax columns ────────────────────────────────────────
    op.add_column("sales_order_lines", sa.Column(
        "tax_rate_id", sa.String(36),
        sa.ForeignKey("tax_rates.id", ondelete="SET NULL"), nullable=True,
    ))
    op.add_column("sales_order_lines", sa.Column(
        "tax_rate_pct", sa.Numeric(5, 4), nullable=True,
    ))
    op.add_column("sales_order_lines", sa.Column(
        "tax_amount", sa.Numeric(14, 4), nullable=False, server_default="0",
    ))
    op.add_column("sales_order_lines", sa.Column(
        "retention_pct", sa.Numeric(5, 4), nullable=True,
    ))
    op.add_column("sales_order_lines", sa.Column(
        "retention_amount", sa.Numeric(14, 4), nullable=False, server_default="0",
    ))
    op.add_column("sales_order_lines", sa.Column(
        "line_total_with_tax", sa.Numeric(14, 4), nullable=False, server_default="0",
    ))

    # ── SalesOrder: aggregate tax columns ──────────────────────────────────
    op.add_column("sales_orders", sa.Column(
        "total_retention", sa.Numeric(14, 2), nullable=False, server_default="0",
    ))
    op.add_column("sales_orders", sa.Column(
        "total_with_tax", sa.Numeric(14, 2), nullable=False, server_default="0",
    ))
    op.add_column("sales_orders", sa.Column(
        "total_payable", sa.Numeric(14, 2), nullable=False, server_default="0",
    ))


def downgrade() -> None:
    op.drop_column("sales_orders", "total_payable")
    op.drop_column("sales_orders", "total_with_tax")
    op.drop_column("sales_orders", "total_retention")

    op.drop_column("sales_order_lines", "line_total_with_tax")
    op.drop_column("sales_order_lines", "retention_amount")
    op.drop_column("sales_order_lines", "retention_pct")
    op.drop_column("sales_order_lines", "tax_amount")
    op.drop_column("sales_order_lines", "tax_rate_pct")
    op.drop_column("sales_order_lines", "tax_rate_id")

    op.drop_column("entities", "retention_rate")
    op.drop_column("entities", "is_tax_exempt")
    op.drop_column("entities", "tax_rate_id")

    op.drop_table("tax_rates")
