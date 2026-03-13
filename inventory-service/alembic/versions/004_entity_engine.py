"""Entity engine: dynamic types, events, tracking, production, cost layers.

Revision ID: 004
Revises: 003
"""
from __future__ import annotations

import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None

DEFAULT_TENANT = "default"


def _id() -> str:
    return str(uuid.uuid4())


def upgrade() -> None:
    # ─── 1. Config tables ────────────────────────────────────────────────

    op.create_table(
        "entity_types",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("slug", sa.String(150), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("color", sa.String(20), nullable=True, server_default="#8b5cf6"),
        sa.Column("icon", sa.String(50), nullable=True),
        sa.Column("tracks_stock", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("tracks_serials", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("tracks_batches", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("depreciable", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("transformable", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_entity_type_tenant_slug"),
        sa.Index("ix_entity_types_tenant_id", "tenant_id"),
    )

    op.create_table(
        "movement_types",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("slug", sa.String(150), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("direction", sa.String(20), nullable=False, server_default="in"),
        sa.Column("affects_cost", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("requires_reference", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("color", sa.String(20), nullable=True, server_default="#3b82f6"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("is_system", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_movement_type_tenant_slug"),
        sa.Index("ix_movement_types_tenant_id", "tenant_id"),
    )

    op.create_table(
        "warehouse_types",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("slug", sa.String(150), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("color", sa.String(20), nullable=True, server_default="#f59e0b"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("is_system", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_warehouse_type_tenant_slug"),
        sa.Index("ix_warehouse_types_tenant_id", "tenant_id"),
    )

    # ─── 2. Warehouse locations ──────────────────────────────────────────

    op.create_table(
        "warehouse_locations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("warehouse_id", sa.String(36), sa.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parent_location_id", sa.String(36), sa.ForeignKey("warehouse_locations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("location_type", sa.String(20), nullable=False, server_default="bin"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.UniqueConstraint("warehouse_id", "code", name="uq_location_warehouse_code"),
        sa.Index("ix_warehouse_locations_tenant_id", "tenant_id"),
        sa.Index("ix_warehouse_locations_warehouse_id", "warehouse_id"),
    )

    # ─── 3. Event tables ─────────────────────────────────────────────────

    op.create_table(
        "event_types",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("slug", sa.String(150), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("auto_generate_movement_type_id", sa.String(36), sa.ForeignKey("movement_types.id", ondelete="SET NULL"), nullable=True),
        sa.Column("color", sa.String(20), nullable=True, server_default="#ef4444"),
        sa.Column("icon", sa.String(50), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_event_type_tenant_slug"),
        sa.Index("ix_event_types_tenant_id", "tenant_id"),
    )

    op.create_table(
        "event_severities",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("slug", sa.String(150), nullable=False),
        sa.Column("weight", sa.Integer, nullable=False, server_default="1"),
        sa.Column("color", sa.String(20), nullable=True, server_default="#f59e0b"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_event_severity_tenant_slug"),
        sa.Index("ix_event_severities_tenant_id", "tenant_id"),
    )

    op.create_table(
        "event_statuses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("slug", sa.String(150), nullable=False),
        sa.Column("is_final", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("color", sa.String(20), nullable=True, server_default="#6b7280"),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_event_status_tenant_slug"),
        sa.Index("ix_event_statuses_tenant_id", "tenant_id"),
    )

    # ─── 4. Tracking tables ──────────────────────────────────────────────

    op.create_table(
        "serial_statuses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("slug", sa.String(150), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("color", sa.String(20), nullable=True, server_default="#3b82f6"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_serial_status_tenant_slug"),
        sa.Index("ix_serial_statuses_tenant_id", "tenant_id"),
    )

    # ─── 5. Rename products → entities ───────────────────────────────────

    op.rename_table("products", "entities")

    # Update indexes (rename from old naming)
    op.execute("ALTER INDEX IF EXISTS ix_products_tenant_id RENAME TO ix_entities_tenant_id")

    # ─── 6. Add entity_type_id to entities ───────────────────────────────

    op.add_column("entities", sa.Column(
        "entity_type_id", sa.String(36),
        sa.ForeignKey("entity_types.id", ondelete="SET NULL"), nullable=True
    ))

    # ─── 7. Add warehouse_type_id to warehouses ─────────────────────────

    op.add_column("warehouses", sa.Column(
        "warehouse_type_id", sa.String(36),
        sa.ForeignKey("warehouse_types.id", ondelete="SET NULL"), nullable=True
    ))

    # ─── 8. Add movement_type_id to stock_movements ─────────────────────

    op.add_column("stock_movements", sa.Column(
        "movement_type_id", sa.String(36),
        sa.ForeignKey("movement_types.id", ondelete="SET NULL"), nullable=True
    ))

    # ─── 9. Entity batches (needs entities table to exist) ──────────────

    op.create_table(
        "entity_batches",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("entity_id", sa.String(36), sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("batch_number", sa.String(100), nullable=False),
        sa.Column("manufacture_date", sa.Date, nullable=True),
        sa.Column("expiration_date", sa.Date, nullable=True),
        sa.Column("cost", sa.Numeric(12, 4), nullable=True),
        sa.Column("quantity", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "entity_id", "batch_number", name="uq_batch_tenant_entity"),
        sa.Index("ix_entity_batches_tenant_id", "tenant_id"),
        sa.Index("ix_entity_batches_entity_id", "entity_id"),
        sa.Index("ix_entity_batches_expiration", "expiration_date"),
    )

    op.create_table(
        "entity_serials",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("entity_id", sa.String(36), sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("serial_number", sa.String(255), nullable=False),
        sa.Column("status_id", sa.String(36), sa.ForeignKey("serial_statuses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("warehouse_id", sa.String(36), sa.ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True),
        sa.Column("location_id", sa.String(36), sa.ForeignKey("warehouse_locations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("batch_id", sa.String(36), sa.ForeignKey("entity_batches.id", ondelete="SET NULL"), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "entity_id", "serial_number", name="uq_serial_tenant_entity"),
        sa.Index("ix_entity_serials_tenant_id", "tenant_id"),
        sa.Index("ix_entity_serials_entity_id", "entity_id"),
    )

    # ─── 10. Events (needs entities table) ──────────────────────────────

    op.create_table(
        "inventory_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("event_type_id", sa.String(36), sa.ForeignKey("event_types.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("severity_id", sa.String(36), sa.ForeignKey("event_severities.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status_id", sa.String(36), sa.ForeignKey("event_statuses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("warehouse_id", sa.String(36), sa.ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reported_by", sa.String(255), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Index("ix_inventory_events_tenant_id", "tenant_id"),
        sa.Index("ix_inventory_events_type", "event_type_id"),
        sa.Index("ix_inventory_events_occurred", "occurred_at"),
    )

    op.create_table(
        "event_impacts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("event_id", sa.String(36), sa.ForeignKey("inventory_events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_id", sa.String(36), sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("quantity_impact", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("batch_id", sa.String(36), nullable=True),
        sa.Column("serial_id", sa.String(36), nullable=True),
        sa.Column("movement_id", sa.String(36), sa.ForeignKey("stock_movements.id", ondelete="SET NULL"), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
    )

    # ─── 11. Production tables ──────────────────────────────────────────

    op.create_table(
        "entity_recipes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("output_entity_id", sa.String(36), sa.ForeignKey("entities.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("output_quantity", sa.Numeric(12, 4), nullable=False, server_default="1"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Index("ix_entity_recipes_tenant_id", "tenant_id"),
    )

    op.create_table(
        "recipe_components",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("recipe_id", sa.String(36), sa.ForeignKey("entity_recipes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("component_entity_id", sa.String(36), sa.ForeignKey("entities.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity_required", sa.Numeric(12, 4), nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
    )

    op.create_table(
        "production_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("recipe_id", sa.String(36), sa.ForeignKey("entity_recipes.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("run_number", sa.String(50), nullable=False),
        sa.Column("warehouse_id", sa.String(36), sa.ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("multiplier", sa.Numeric(12, 4), nullable=False, server_default="1"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("performed_by", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "run_number", name="uq_production_run_tenant_number"),
        sa.Index("ix_production_runs_tenant_id", "tenant_id"),
        sa.Index("ix_production_runs_status", "status"),
    )

    op.create_table(
        "stock_layers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("entity_id", sa.String(36), sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("warehouse_id", sa.String(36), sa.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("movement_id", sa.String(36), sa.ForeignKey("stock_movements.id", ondelete="SET NULL"), nullable=True),
        sa.Column("quantity_initial", sa.Numeric(12, 4), nullable=False),
        sa.Column("quantity_remaining", sa.Numeric(12, 4), nullable=False),
        sa.Column("unit_cost", sa.Numeric(12, 4), nullable=False),
        sa.Column("batch_id", sa.String(36), sa.ForeignKey("entity_batches.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Index("ix_stock_layers_tenant_id", "tenant_id"),
        sa.Index("ix_stock_layers_entity_wh", "entity_id", "warehouse_id"),
        sa.Index("ix_stock_layers_remaining", "entity_id", "warehouse_id", "quantity_remaining"),
    )

    # ─── 12. StockLevel additions ────────────────────────────────────────

    op.add_column("stock_levels", sa.Column(
        "location_id", sa.String(36),
        sa.ForeignKey("warehouse_locations.id", ondelete="SET NULL"), nullable=True
    ))
    op.add_column("stock_levels", sa.Column(
        "batch_id", sa.String(36),
        sa.ForeignKey("entity_batches.id", ondelete="SET NULL"), nullable=True
    ))
    op.add_column("stock_levels", sa.Column(
        "qty_in_transit", sa.Numeric(12, 4), nullable=False, server_default="0"
    ))

    # ─── 13. Create products VIEW for backward compat ────────────────────

    op.execute("CREATE OR REPLACE VIEW products AS SELECT * FROM entities")

    # ─── 14. Seed data ──────────────────────────────────────────────────

    t = DEFAULT_TENANT

    # Entity types
    et_ids = {}
    for name, slug, desc, icon, ts, tb, dep, trans in [
        ("Producto", "producto", "Producto físico estándar", "package", True, False, False, False),
        ("Activo Fijo", "activo-fijo", "Activo de la empresa", "building2", False, True, False, True),
        ("Servicio", "servicio", "Servicio no almacenable", "wrench", False, False, False, False),
        ("Materia Prima", "materia-prima", "Material para producción", "flask-conical", True, False, True, True),
    ]:
        uid = _id()
        et_ids[slug] = uid
        op.execute(
            sa.text(
                "INSERT INTO entity_types (id, tenant_id, name, slug, description, icon, tracks_stock, tracks_batches, depreciable, transformable) "
                "VALUES (:id, :t, :name, :slug, :desc, :icon, :ts, :tb, :dep, :trans)"
            ).bindparams(id=uid, t=t, name=name, slug=slug, desc=desc, icon=icon, ts=ts, tb=tb, dep=dep, trans=trans)
        )

    # Movement types (9: 7 existing + production_in + production_out)
    mt_ids = {}
    for name, slug, direction, color, sort in [
        ("Compra", "purchase", "in", "#22c55e", 0),
        ("Venta", "sale", "out", "#ef4444", 1),
        ("Transferencia", "transfer", "internal", "#3b82f6", 2),
        ("Ajuste entrada", "adjustment-in", "in", "#a3e635", 3),
        ("Ajuste salida", "adjustment-out", "out", "#f97316", 4),
        ("Devolución", "return", "in", "#06b6d4", 5),
        ("Desperdicio", "waste", "out", "#6b7280", 6),
        ("Producción entrada", "production-in", "in", "#8b5cf6", 7),
        ("Producción salida", "production-out", "out", "#d946ef", 8),
    ]:
        uid = _id()
        mt_ids[slug] = uid
        op.execute(
            sa.text(
                "INSERT INTO movement_types (id, tenant_id, name, slug, direction, color, is_system, sort_order) "
                "VALUES (:id, :t, :name, :slug, :dir, :color, true, :sort)"
            ).bindparams(id=uid, t=t, name=name, slug=slug, dir=direction, color=color, sort=sort)
        )

    # Warehouse types
    wt_ids = {}
    for name, slug, color, sort in [
        ("Principal", "main", "#22c55e", 0),
        ("Secundario", "secondary", "#3b82f6", 1),
        ("Virtual", "virtual", "#a855f7", 2),
        ("Tránsito", "transit", "#f59e0b", 3),
    ]:
        uid = _id()
        wt_ids[slug] = uid
        op.execute(
            sa.text(
                "INSERT INTO warehouse_types (id, tenant_id, name, slug, color, is_system, sort_order) "
                "VALUES (:id, :t, :name, :slug, :color, true, :sort)"
            ).bindparams(id=uid, t=t, name=name, slug=slug, color=color, sort=sort)
        )

    # Event severities
    sev_ids = {}
    for name, slug, weight, color in [
        ("Baja", "baja", 1, "#22c55e"),
        ("Media", "media", 2, "#f59e0b"),
        ("Alta", "alta", 3, "#f97316"),
        ("Crítica", "critica", 4, "#ef4444"),
    ]:
        uid = _id()
        sev_ids[slug] = uid
        op.execute(
            sa.text(
                "INSERT INTO event_severities (id, tenant_id, name, slug, weight, color) "
                "VALUES (:id, :t, :name, :slug, :weight, :color)"
            ).bindparams(id=uid, t=t, name=name, slug=slug, weight=weight, color=color)
        )

    # Event statuses
    est_ids = {}
    for name, slug, is_final, color, sort in [
        ("Abierto", "abierto", False, "#ef4444", 0),
        ("En investigación", "en-investigacion", False, "#f59e0b", 1),
        ("Resuelto", "resuelto", True, "#22c55e", 2),
        ("Cerrado", "cerrado", True, "#6b7280", 3),
    ]:
        uid = _id()
        est_ids[slug] = uid
        op.execute(
            sa.text(
                "INSERT INTO event_statuses (id, tenant_id, name, slug, is_final, color, sort_order) "
                "VALUES (:id, :t, :name, :slug, :final, :color, :sort)"
            ).bindparams(id=uid, t=t, name=name, slug=slug, final=is_final, color=color, sort=sort)
        )

    # Event types
    waste_mt = mt_ids.get("waste")
    for name, slug, color, icon, auto_mt in [
        ("Incendio", "incendio", "#ef4444", "flame", waste_mt),
        ("Robo", "robo", "#dc2626", "shield-alert", waste_mt),
        ("Daño", "dano", "#f97316", "alert-triangle", waste_mt),
        ("Expiración", "expiracion", "#f59e0b", "clock", None),
        ("Auditoría", "auditoria", "#3b82f6", "clipboard-check", None),
    ]:
        uid = _id()
        op.execute(
            sa.text(
                "INSERT INTO event_types (id, tenant_id, name, slug, color, icon, auto_generate_movement_type_id) "
                "VALUES (:id, :t, :name, :slug, :color, :icon, :auto_mt)"
            ).bindparams(id=uid, t=t, name=name, slug=slug, color=color, icon=icon, auto_mt=auto_mt)
        )

    # Serial statuses
    for name, slug, color in [
        ("Disponible", "disponible", "#10b981"),
        ("En tránsito", "en-transito", "#8b5cf6"),
        ("Vendido", "vendido", "#3b82f6"),
        ("Dañado", "danado", "#ef4444"),
        ("En reparación", "en-reparacion", "#f59e0b"),
        ("Dado de baja", "dado-de-baja", "#6b7280"),
    ]:
        uid = _id()
        op.execute(
            sa.text(
                "INSERT INTO serial_statuses (id, tenant_id, name, slug, color) "
                "VALUES (:id, :t, :name, :slug, :color)"
            ).bindparams(id=uid, t=t, name=name, slug=slug, color=color)
        )

    # ─── 15. Backfill entity_type_id for existing entities ──────────────

    product_type_id = et_ids.get("producto")
    if product_type_id:
        op.execute(
            sa.text(
                "UPDATE entities SET entity_type_id = :et_id WHERE tenant_id = :t AND entity_type_id IS NULL"
            ).bindparams(et_id=product_type_id, t=t)
        )

    # ─── 16. Backfill warehouse_type_id ─────────────────────────────────

    for wh_type, wt_slug in [("main", "main"), ("secondary", "secondary"), ("virtual", "virtual"), ("transit", "transit")]:
        wt_id = wt_ids.get(wt_slug)
        if wt_id:
            op.execute(
                sa.text(
                    "UPDATE warehouses SET warehouse_type_id = :wt_id WHERE tenant_id = :t AND type = :wh_type"
                ).bindparams(wt_id=wt_id, t=t, wh_type=wh_type)
            )

    # ─── 17. Backfill movement_type_id ──────────────────────────────────

    legacy_to_slug = {
        "purchase": "purchase",
        "sale": "sale",
        "transfer": "transfer",
        "adjustment_in": "adjustment-in",
        "adjustment_out": "adjustment-out",
        "return": "return",
        "waste": "waste",
    }
    for legacy_val, mt_slug in legacy_to_slug.items():
        mt_id = mt_ids.get(mt_slug)
        if mt_id:
            op.execute(
                sa.text(
                    "UPDATE stock_movements SET movement_type_id = :mt_id WHERE tenant_id = :t AND movement_type = :legacy"
                ).bindparams(mt_id=mt_id, t=t, legacy=legacy_val)
            )


def downgrade() -> None:
    # Drop VIEW first
    op.execute("DROP VIEW IF EXISTS products")

    # Drop new columns
    op.drop_column("stock_levels", "qty_in_transit")
    op.drop_column("stock_levels", "batch_id")
    op.drop_column("stock_levels", "location_id")
    op.drop_column("stock_movements", "movement_type_id")
    op.drop_column("warehouses", "warehouse_type_id")
    op.drop_column("entities", "entity_type_id")

    # Rename back
    op.rename_table("entities", "products")
    op.execute("ALTER INDEX IF EXISTS ix_entities_tenant_id RENAME TO ix_products_tenant_id")

    # Drop new tables (reverse order)
    op.drop_table("stock_layers")
    op.drop_table("production_runs")
    op.drop_table("recipe_components")
    op.drop_table("entity_recipes")
    op.drop_table("event_impacts")
    op.drop_table("inventory_events")
    op.drop_table("entity_serials")
    op.drop_table("entity_batches")
    op.drop_table("event_statuses")
    op.drop_table("event_severities")
    op.drop_table("event_types")
    op.drop_table("serial_statuses")
    op.drop_table("warehouse_locations")
    op.drop_table("warehouse_types")
    op.drop_table("movement_types")
    op.drop_table("entity_types")
