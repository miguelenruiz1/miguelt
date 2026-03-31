"""Production resources, capacity planning, and MRP support.

Adds production_resources, recipe_resources, production_run_resource_costs tables.
Adds total_resource_cost column to production_runs.

Revision ID: 069
Revises: 068
"""
from alembic import op
import sqlalchemy as sa

revision = "069"
down_revision = "068"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── production_resources ─────────────────────────────────────────────────
    op.create_table(
        "production_resources",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("resource_type", sa.String(20), nullable=False, server_default="labor"),
        sa.Column("cost_per_hour", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("cost_per_unit", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("capacity_hours_per_day", sa.Numeric(6, 2), nullable=False, server_default="8"),
        sa.Column("efficiency_pct", sa.Numeric(5, 2), nullable=False, server_default="100"),
        sa.Column("shifts_per_day", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("available_hours_override", sa.Numeric(6, 2), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("updated_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Index("ix_production_resources_tenant", "tenant_id"),
    )

    # ── recipe_resources (junction: recipe ↔ resource) ───────────────────────
    op.create_table(
        "recipe_resources",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("recipe_id", sa.String(36), sa.ForeignKey("entity_recipes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resource_id", sa.String(36), sa.ForeignKey("production_resources.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("hours_per_unit", sa.Numeric(8, 4), nullable=False),
        sa.Column("setup_time_hours", sa.Numeric(8, 4), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.UniqueConstraint("recipe_id", "resource_id", name="uq_recipe_resource"),
        sa.Index("ix_recipe_resources_recipe", "recipe_id"),
    )

    # ── production_run_resource_costs (actual costs per run) ─────────────────
    op.create_table(
        "production_run_resource_costs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("production_run_id", sa.String(36), sa.ForeignKey("production_runs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("resource_id", sa.String(36), sa.ForeignKey("production_resources.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("planned_hours", sa.Numeric(8, 4), nullable=False),
        sa.Column("actual_hours", sa.Numeric(8, 4), nullable=True),
        sa.Column("cost_per_hour", sa.Numeric(12, 4), nullable=False),
        sa.Column("total_cost", sa.Numeric(14, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Index("ix_run_resource_costs_run", "production_run_id"),
    )

    # ── total_resource_cost on production_runs ───────────────────────────────
    op.add_column("production_runs", sa.Column("total_resource_cost", sa.Numeric(14, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("production_runs", "total_resource_cost")
    op.drop_table("production_run_resource_costs")
    op.drop_table("recipe_resources")
    op.drop_table("production_resources")
