"""Multi-commodity: commodity_type, HS/incoterm per line, plot origins, quality tests, multi-output recipes.

- entities.commodity_type, sales_orders.commodity_type: discriminator for UI filters / pricing.
- sales_order_lines.hs_code / incoterm: per-line override of the header
  (same export can mix cacao + coffee rows with different Incoterms).
- batch_plot_origins: lineage from EntityBatch to compliance plots
  (cross-DB — plot_id not FK-enforced, app-layer validates).
- batch_quality_tests: generic tests (humidity, defects, cadmium, FFA, DOBI,
  MIU, Lovibond, sensory_score, ...). Lab results with pass/fail + threshold.
- production_output_components: enables multi-output recipes (RFF -> CPO + PKO),
  coexisting with legacy single-output entity_recipes.output_entity_id.

Revision: 084
Revises: 083
"""
revision = "084"
down_revision = "083"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    # ── Products (entities) + sales orders ─────────────────────────────────────
    op.add_column(
        "entities",
        sa.Column("commodity_type", sa.String(20), nullable=True),
    )
    op.create_check_constraint(
        "ck_entities_commodity_type",
        "entities",
        "commodity_type IS NULL OR commodity_type IN "
        "('coffee','cacao','palm','other')",
    )

    op.add_column(
        "sales_orders",
        sa.Column("commodity_type", sa.String(20), nullable=True),
    )
    op.create_check_constraint(
        "ck_sales_orders_commodity_type",
        "sales_orders",
        "commodity_type IS NULL OR commodity_type IN "
        "('coffee','cacao','palm','other')",
    )

    op.add_column(
        "sales_order_lines",
        sa.Column("hs_code", sa.String(15), nullable=True),
    )
    op.add_column(
        "sales_order_lines",
        sa.Column("incoterm", sa.String(10), nullable=True),
    )

    # ── batch_plot_origins ─────────────────────────────────────────────────────
    op.create_table(
        "batch_plot_origins",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column(
            "batch_id",
            sa.String(36),
            sa.ForeignKey("entity_batches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Cross-DB pointer to compliance_plots (validated app-side).
        sa.Column("plot_id", sa.String(36), nullable=False),
        sa.Column("plot_code", sa.String(64), nullable=True),
        sa.Column("origin_quantity_kg", sa.Numeric(18, 4), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_batch_plot_origins_tenant_batch",
        "batch_plot_origins",
        ["tenant_id", "batch_id"],
    )
    op.create_index(
        "ix_batch_plot_origins_tenant_plot",
        "batch_plot_origins",
        ["tenant_id", "plot_id"],
    )

    # ── batch_quality_tests ────────────────────────────────────────────────────
    op.create_table(
        "batch_quality_tests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column(
            "batch_id",
            sa.String(36),
            sa.ForeignKey("entity_batches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("test_type", sa.String(40), nullable=False),
        sa.Column("value", sa.Numeric(12, 4), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("threshold_min", sa.Numeric(12, 4), nullable=True),
        sa.Column("threshold_max", sa.Numeric(12, 4), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=True),
        sa.Column("lab", sa.String(255), nullable=True),
        sa.Column("test_date", sa.Date(), nullable=False),
        sa.Column("doc_hash", sa.String(64), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "test_type IN ('humidity','defects','cadmium','ffa','iv','dobi',"
            "'miu','lovibond','sensory_score','other')",
            name="ck_batch_quality_tests_type",
        ),
    )
    op.create_index(
        "ix_batch_quality_tests_tenant_batch_type",
        "batch_quality_tests",
        ["tenant_id", "batch_id", "test_type"],
    )

    # ── production_output_components (multi-output recipes) ────────────────────
    op.create_table(
        "production_output_components",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column(
            "recipe_id",
            sa.String(36),
            sa.ForeignKey("entity_recipes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "output_entity_id",
            sa.String(36),
            nullable=False,
        ),
        sa.Column("output_quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("output_uom_id", sa.String(36), nullable=True),
        sa.Column("conversion_factor", sa.Numeric(8, 6), nullable=True),
        sa.Column(
            "is_main",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_prod_output_components_tenant_recipe",
        "production_output_components",
        ["tenant_id", "recipe_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_prod_output_components_tenant_recipe",
        table_name="production_output_components",
    )
    op.drop_table("production_output_components")

    op.drop_index(
        "ix_batch_quality_tests_tenant_batch_type",
        table_name="batch_quality_tests",
    )
    op.drop_table("batch_quality_tests")

    op.drop_index(
        "ix_batch_plot_origins_tenant_plot",
        table_name="batch_plot_origins",
    )
    op.drop_index(
        "ix_batch_plot_origins_tenant_batch",
        table_name="batch_plot_origins",
    )
    op.drop_table("batch_plot_origins")

    op.drop_column("sales_order_lines", "incoterm")
    op.drop_column("sales_order_lines", "hs_code")

    op.drop_constraint(
        "ck_sales_orders_commodity_type",
        "sales_orders",
        type_="check",
    )
    op.drop_column("sales_orders", "commodity_type")

    op.drop_constraint(
        "ck_entities_commodity_type",
        "entities",
        type_="check",
    )
    op.drop_column("entities", "commodity_type")
