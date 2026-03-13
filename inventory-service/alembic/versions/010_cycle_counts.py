"""Add cycle_counts, cycle_count_items, and ira_snapshots tables.

Revision ID: 010
Revises: 009
Create Date: 2026-03-02
"""
from alembic import op
import sqlalchemy as sa

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── cycle_counts ─────────────────────────────────────────────────────
    op.create_table(
        "cycle_counts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("count_number", sa.String(20), nullable=False),
        sa.Column(
            "warehouse_id", sa.String(36),
            sa.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("methodology", sa.String(30), nullable=True),
        sa.Column("assigned_counters", sa.Integer, nullable=False, server_default="1"),
        sa.Column("minutes_per_count", sa.Integer, nullable=False, server_default="2"),
        sa.Column("scheduled_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.String(255), nullable=True),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("updated_by", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "count_number", name="uq_cycle_count_number"),
    )
    op.create_index("ix_cycle_counts_tenant_id", "cycle_counts", ["tenant_id"])
    op.create_index("ix_cycle_counts_status", "cycle_counts", ["status"])
    op.create_index("ix_cycle_counts_warehouse_id", "cycle_counts", ["warehouse_id"])

    # ── cycle_count_items ────────────────────────────────────────────────
    op.create_table(
        "cycle_count_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column(
            "cycle_count_id", sa.String(36),
            sa.ForeignKey("cycle_counts.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "product_id", sa.String(36),
            sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "location_id", sa.String(36),
            sa.ForeignKey("warehouse_locations.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column(
            "batch_id", sa.String(36),
            sa.ForeignKey("entity_batches.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column("system_qty", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("counted_qty", sa.Numeric(12, 4), nullable=True),
        sa.Column("discrepancy", sa.Numeric(12, 4), nullable=True),
        sa.Column("recount_qty", sa.Numeric(12, 4), nullable=True),
        sa.Column("recount_discrepancy", sa.Numeric(12, 4), nullable=True),
        sa.Column("root_cause", sa.String(500), nullable=True),
        sa.Column("counted_by", sa.String(255), nullable=True),
        sa.Column("counted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "movement_id", sa.String(36),
            sa.ForeignKey("stock_movements.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_cycle_count_items_tenant_id", "cycle_count_items", ["tenant_id"])
    op.create_index("ix_cycle_count_items_cycle_count_id", "cycle_count_items", ["cycle_count_id"])
    op.create_index("ix_cycle_count_items_product_id", "cycle_count_items", ["product_id"])

    # ── ira_snapshots ────────────────────────────────────────────────────
    op.create_table(
        "ira_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column(
            "cycle_count_id", sa.String(36),
            sa.ForeignKey("cycle_counts.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "warehouse_id", sa.String(36),
            sa.ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column("total_items", sa.Integer, nullable=False, server_default="0"),
        sa.Column("accurate_items", sa.Integer, nullable=False, server_default="0"),
        sa.Column("ira_percentage", sa.Numeric(6, 2), nullable=False, server_default="0"),
        sa.Column("total_system_value", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("total_counted_value", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("value_accuracy", sa.Numeric(6, 2), nullable=False, server_default="0"),
        sa.Column("snapshot_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("cycle_count_id", name="uq_ira_snapshot_cycle_count"),
    )
    op.create_index("ix_ira_snapshots_tenant_id", "ira_snapshots", ["tenant_id"])
    op.create_index("ix_ira_snapshots_warehouse_id", "ira_snapshots", ["warehouse_id"])


def downgrade() -> None:
    op.drop_index("ix_ira_snapshots_warehouse_id", "ira_snapshots")
    op.drop_index("ix_ira_snapshots_tenant_id", "ira_snapshots")
    op.drop_table("ira_snapshots")

    op.drop_index("ix_cycle_count_items_product_id", "cycle_count_items")
    op.drop_index("ix_cycle_count_items_cycle_count_id", "cycle_count_items")
    op.drop_index("ix_cycle_count_items_tenant_id", "cycle_count_items")
    op.drop_table("cycle_count_items")

    op.drop_index("ix_cycle_counts_warehouse_id", "cycle_counts")
    op.drop_index("ix_cycle_counts_status", "cycle_counts")
    op.drop_index("ix_cycle_counts_tenant_id", "cycle_counts")
    op.drop_table("cycle_counts")
