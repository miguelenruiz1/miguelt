"""Production v2 — separate emission/receipt documents, new statuses, BOM types.

Adds production_emissions, production_emission_lines, production_receipts,
production_receipt_lines tables. Extends production_runs, entity_recipes,
and recipe_components with new fields. Migrates status values.

Revision ID: 068
Revises: 067
"""
from alembic import op
import sqlalchemy as sa

revision = "068"
down_revision = "067"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Extend entity_recipes ────────────────────────────────────────────────
    op.add_column("entity_recipes", sa.Column("bom_type", sa.String(20), nullable=False, server_default="production"))
    op.add_column("entity_recipes", sa.Column("standard_cost", sa.Numeric(14, 2), nullable=False, server_default="0"))
    op.add_column("entity_recipes", sa.Column("planned_production_size", sa.Integer(), nullable=False, server_default="1"))

    # ── Extend recipe_components ─────────────────────────────────────────────
    op.add_column("recipe_components", sa.Column("issue_method", sa.String(20), nullable=False, server_default="manual"))
    op.add_column("recipe_components", sa.Column("scrap_percentage", sa.Numeric(5, 2), nullable=False, server_default="0"))
    op.add_column("recipe_components", sa.Column("lead_time_offset_days", sa.Integer(), nullable=False, server_default="0"))

    # ── Extend production_runs ───────────────────────────────────────────────
    op.add_column("production_runs", sa.Column("order_type", sa.String(20), nullable=False, server_default="standard"))
    op.add_column("production_runs", sa.Column("priority", sa.Integer(), nullable=False, server_default="50"))
    op.add_column("production_runs", sa.Column("planned_start_date", sa.DateTime(timezone=True), nullable=True))
    op.add_column("production_runs", sa.Column("planned_end_date", sa.DateTime(timezone=True), nullable=True))
    op.add_column("production_runs", sa.Column("actual_start_date", sa.DateTime(timezone=True), nullable=True))
    op.add_column("production_runs", sa.Column("actual_end_date", sa.DateTime(timezone=True), nullable=True))
    op.add_column("production_runs", sa.Column("actual_output_quantity", sa.Numeric(12, 4), nullable=True))
    op.add_column("production_runs", sa.Column("total_component_cost", sa.Numeric(14, 2), nullable=True))
    op.add_column("production_runs", sa.Column("total_production_cost", sa.Numeric(14, 2), nullable=True))
    op.add_column("production_runs", sa.Column("unit_production_cost", sa.Numeric(14, 6), nullable=True))
    op.add_column("production_runs", sa.Column("variance_amount", sa.Numeric(14, 2), nullable=True))
    op.add_column("production_runs", sa.Column("linked_sales_order_id", sa.String(36), nullable=True))
    op.add_column("production_runs", sa.Column("linked_customer_id", sa.String(36), nullable=True))

    # ── Migrate existing status values ───────────────────────────────────────
    op.execute("UPDATE production_runs SET status = 'planned' WHERE status = 'pending'")
    op.execute("UPDATE production_runs SET status = 'closed' WHERE status = 'completed'")

    # ── Create production_emissions ──────────────────────────────────────────
    op.create_table(
        "production_emissions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("production_run_id", sa.String(36), sa.ForeignKey("production_runs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("emission_number", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="posted"),
        sa.Column("emission_date", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("warehouse_id", sa.String(36), sa.ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("performed_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Index("ix_prod_emissions_tenant", "tenant_id"),
        sa.Index("ix_prod_emissions_run", "production_run_id"),
    )

    # ── Create production_emission_lines ─────────────────────────────────────
    op.create_table(
        "production_emission_lines",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("emission_id", sa.String(36), sa.ForeignKey("production_emissions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("component_entity_id", sa.String(36), sa.ForeignKey("entities.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("planned_quantity", sa.Numeric(12, 4), nullable=False),
        sa.Column("actual_quantity", sa.Numeric(12, 4), nullable=False),
        sa.Column("unit_cost", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("total_cost", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("batch_id", sa.String(36), sa.ForeignKey("entity_batches.id", ondelete="SET NULL"), nullable=True),
        sa.Column("warehouse_id", sa.String(36), sa.ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("variance_quantity", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Index("ix_prod_emission_lines_emission", "emission_id"),
    )

    # ── Create production_receipts ───────────────────────────────────────────
    op.create_table(
        "production_receipts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("production_run_id", sa.String(36), sa.ForeignKey("production_runs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("receipt_number", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="posted"),
        sa.Column("receipt_date", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("output_warehouse_id", sa.String(36), sa.ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("performed_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Index("ix_prod_receipts_tenant", "tenant_id"),
        sa.Index("ix_prod_receipts_run", "production_run_id"),
    )

    # ── Create production_receipt_lines ───────────────────────────────────────
    op.create_table(
        "production_receipt_lines",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("receipt_id", sa.String(36), sa.ForeignKey("production_receipts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_id", sa.String(36), sa.ForeignKey("entities.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("planned_quantity", sa.Numeric(12, 4), nullable=False),
        sa.Column("received_quantity", sa.Numeric(12, 4), nullable=False),
        sa.Column("unit_cost", sa.Numeric(14, 6), nullable=False, server_default="0"),
        sa.Column("total_cost", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("batch_id", sa.String(36), sa.ForeignKey("entity_batches.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_complete", sa.Boolean(), nullable=False, server_default="false"),
        sa.Index("ix_prod_receipt_lines_receipt", "receipt_id"),
    )


def downgrade() -> None:
    op.drop_table("production_receipt_lines")
    op.drop_table("production_receipts")
    op.drop_table("production_emission_lines")
    op.drop_table("production_emissions")

    # Revert status
    op.execute("UPDATE production_runs SET status = 'pending' WHERE status = 'planned'")
    op.execute("UPDATE production_runs SET status = 'completed' WHERE status = 'closed'")

    # Drop production_runs columns
    for col in ("linked_customer_id", "linked_sales_order_id", "variance_amount",
                "unit_production_cost", "total_production_cost", "total_component_cost",
                "actual_output_quantity", "actual_end_date", "actual_start_date",
                "planned_end_date", "planned_start_date", "priority", "order_type"):
        op.drop_column("production_runs", col)

    # Drop recipe_components columns
    for col in ("lead_time_offset_days", "scrap_percentage", "issue_method"):
        op.drop_column("recipe_components", col)

    # Drop entity_recipes columns
    for col in ("planned_production_size", "standard_cost", "bom_type"):
        op.drop_column("entity_recipes", col)
