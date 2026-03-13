"""Add inventory_audit_logs table and created_by/updated_by to all tables.

Revision ID: 011
Revises: 010
Create Date: 2026-03-02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def _col_exists(table: str, column: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c"
        ),
        {"t": table, "c": column},
    )
    return result.scalar() is not None


def upgrade() -> None:
    # ── 1. inventory_audit_logs ─────────────────────────────────────────
    op.create_table(
        "inventory_audit_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("user_email", sa.String(255), nullable=True),
        sa.Column("action", sa.String(150), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("resource_id", sa.String(255), nullable=False),
        sa.Column("old_data", JSONB, nullable=True),
        sa.Column("new_data", JSONB, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_logs_tenant_id", "inventory_audit_logs", ["tenant_id"])
    op.create_index("ix_audit_logs_user_id", "inventory_audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_resource", "inventory_audit_logs", ["resource_type", "resource_id"])
    op.create_index("ix_audit_logs_action", "inventory_audit_logs", ["action"])
    op.create_index("ix_audit_logs_created_at", "inventory_audit_logs", ["created_at"])

    # ── 2. Add created_by / updated_by to entities (products) ──────────
    op.add_column("entities", sa.Column("created_by", sa.String(255), nullable=True))
    op.add_column("entities", sa.Column("updated_by", sa.String(255), nullable=True))

    # ── 3. Warehouses: created_by, updated_by, created_at, updated_at ──
    op.add_column("warehouses", sa.Column("created_by", sa.String(255), nullable=True))
    op.add_column("warehouses", sa.Column("updated_by", sa.String(255), nullable=True))
    op.add_column("warehouses", sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.add_column("warehouses", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()))

    # ── 4. WarehouseLocations: created_by, updated_by, created_at, updated_at
    op.add_column("warehouse_locations", sa.Column("created_by", sa.String(255), nullable=True))
    op.add_column("warehouse_locations", sa.Column("updated_by", sa.String(255), nullable=True))
    op.add_column("warehouse_locations", sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.add_column("warehouse_locations", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()))

    # ── 5. Suppliers: created_by, updated_by ───────────────────────────
    op.add_column("suppliers", sa.Column("created_by", sa.String(255), nullable=True))
    op.add_column("suppliers", sa.Column("updated_by", sa.String(255), nullable=True))

    # ── 6. PurchaseOrders: updated_by (already has created_by) ─────────
    op.add_column("purchase_orders", sa.Column("updated_by", sa.String(255), nullable=True))

    # ── 7. EntitySerials: created_by, updated_by ───────────────────────
    op.add_column("entity_serials", sa.Column("created_by", sa.String(255), nullable=True))
    op.add_column("entity_serials", sa.Column("updated_by", sa.String(255), nullable=True))

    # ── 8. EntityBatches: created_by, updated_by, updated_at ───────────
    op.add_column("entity_batches", sa.Column("created_by", sa.String(255), nullable=True))
    op.add_column("entity_batches", sa.Column("updated_by", sa.String(255), nullable=True))
    op.add_column("entity_batches", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()))

    # ── 9. EntityRecipes: created_by, updated_by, updated_at ───────────
    op.add_column("entity_recipes", sa.Column("created_by", sa.String(255), nullable=True))
    op.add_column("entity_recipes", sa.Column("updated_by", sa.String(255), nullable=True))
    op.add_column("entity_recipes", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()))

    # ── 10. ProductionRuns: updated_by ─────────────────────────────────
    op.add_column("production_runs", sa.Column("updated_by", sa.String(255), nullable=True))

    # ── 11. CycleCounts: updated_by (already has created_by) ───────────
    if not _col_exists("cycle_counts", "updated_by"):
        op.add_column("cycle_counts", sa.Column("updated_by", sa.String(255), nullable=True))

    # ── 12. InventoryEvents: updated_by (already has reported_by) ──────
    op.add_column("inventory_events", sa.Column("updated_by", sa.String(255), nullable=True))

    # ── 13. Config tables: created_by, updated_by, created_at, updated_at
    _config_tables = [
        "product_types",
        "order_types",
        "movement_types",
        "warehouse_types",
        "custom_product_fields",
        "supplier_types",
        "custom_supplier_fields",
        "custom_warehouse_fields",
        "custom_movement_fields",
    ]
    for tbl in _config_tables:
        op.add_column(tbl, sa.Column("created_by", sa.String(255), nullable=True))
        op.add_column(tbl, sa.Column("updated_by", sa.String(255), nullable=True))
        op.add_column(tbl, sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
        op.add_column(tbl, sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()))

    # ── 14. Taxonomy tables: created_by, updated_by, created_at, updated_at
    _taxonomy_tables = ["taxonomy_vocabularies", "taxonomy_terms"]
    for tbl in _taxonomy_tables:
        op.add_column(tbl, sa.Column("created_by", sa.String(255), nullable=True))
        op.add_column(tbl, sa.Column("updated_by", sa.String(255), nullable=True))
        op.add_column(tbl, sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
        op.add_column(tbl, sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()))


def downgrade() -> None:
    # Taxonomy
    for tbl in ["taxonomy_terms", "taxonomy_vocabularies"]:
        op.drop_column(tbl, "updated_at")
        op.drop_column(tbl, "created_at")
        op.drop_column(tbl, "updated_by")
        op.drop_column(tbl, "created_by")

    # Config
    for tbl in [
        "custom_movement_fields", "custom_warehouse_fields", "custom_supplier_fields",
        "supplier_types", "custom_product_fields", "warehouse_types", "movement_types",
        "order_types", "product_types",
    ]:
        op.drop_column(tbl, "updated_at")
        op.drop_column(tbl, "created_at")
        op.drop_column(tbl, "updated_by")
        op.drop_column(tbl, "created_by")

    op.drop_column("inventory_events", "updated_by")
    op.drop_column("cycle_counts", "updated_by")
    op.drop_column("production_runs", "updated_by")

    op.drop_column("entity_recipes", "updated_at")
    op.drop_column("entity_recipes", "updated_by")
    op.drop_column("entity_recipes", "created_by")

    op.drop_column("entity_batches", "updated_at")
    op.drop_column("entity_batches", "updated_by")
    op.drop_column("entity_batches", "created_by")

    op.drop_column("entity_serials", "updated_by")
    op.drop_column("entity_serials", "created_by")

    op.drop_column("purchase_orders", "updated_by")

    op.drop_column("suppliers", "updated_by")
    op.drop_column("suppliers", "created_by")

    for tbl in ["warehouse_locations", "warehouses"]:
        op.drop_column(tbl, "updated_at")
        op.drop_column(tbl, "created_at")
        op.drop_column(tbl, "updated_by")
        op.drop_column(tbl, "created_by")

    op.drop_column("entities", "updated_by")
    op.drop_column("entities", "created_by")

    # Audit logs
    op.drop_index("ix_audit_logs_created_at", "inventory_audit_logs")
    op.drop_index("ix_audit_logs_action", "inventory_audit_logs")
    op.drop_index("ix_audit_logs_resource", "inventory_audit_logs")
    op.drop_index("ix_audit_logs_user_id", "inventory_audit_logs")
    op.drop_index("ix_audit_logs_tenant_id", "inventory_audit_logs")
    op.drop_table("inventory_audit_logs")
