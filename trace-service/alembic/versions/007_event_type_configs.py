"""Create event_type_configs table with system seed data.

Admin-configurable event types per tenant.

Revision ID: 007_event_type_configs
Revises: 006_expanded_events
Create Date: 2026-03-21
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ARRAY, TIMESTAMP

revision = "007_event_type_configs"
down_revision = "006_expanded_events"
branch_labels = None
depends_on = None

DEFAULT_TENANT = "00000000-0000-0000-0000-000000000001"

# ─── System event type seed data ──────────────────────────────────────────────
# (slug, name, icon, color, from_states, to_state, is_informational,
#  requires_wallet, requires_notes, requires_reason, requires_admin, sort_order)
SYSTEM_EVENTS = [
    # Original core events
    ("CREATED",           "Registrado",        "plus-circle",   "#10b981", [],                                                                      "in_custody",    False, False, False, False, False, 0),
    ("HANDOFF",           "Transferencia",     "arrow-right",   "#6366f1", ["in_custody","in_transit","loaded","qc_passed","qc_failed"],              "in_transit",    False, True,  False, False, False, 10),
    ("ARRIVED",           "Llegada",           "map-pin",       "#06b6d4", ["in_transit"],                                                           "in_custody",    False, False, False, False, False, 20),
    ("LOADED",            "Cargado",           "package",       "#8b5cf6", ["in_custody"],                                                           "loaded",        False, False, False, False, False, 30),
    ("QC",                "Control de Calidad","clipboard-check","#f59e0b",["loaded","qc_failed"],                                                   None,            False, False, True,  False, False, 40),
    ("RELEASED",          "Liberado",          "unlock",        "#94a3b8", ["in_custody","in_transit","loaded","qc_passed","qc_failed","sealed","customs_hold","damaged"], "released", False, False, False, True, True, 50),
    ("BURN",              "Entrega Completada","check-circle",  "#06b6d4", ["in_custody","in_transit","loaded","qc_passed","qc_failed","sealed","customs_hold","damaged"], "burned",   False, False, False, True, False, 60),
    # Extended events
    ("PICKUP",            "Recolección",       "truck",         "#6366f1", ["in_custody"],                                                           "in_transit",    False, False, False, False, False, 100),
    ("GATE_IN",           "Ingreso",           "log-in",        "#10b981", ["in_transit"],                                                           "in_custody",    False, False, False, False, False, 110),
    ("GATE_OUT",          "Salida",            "log-out",       "#6366f1", ["in_custody","loaded","qc_passed","qc_failed"],                          "in_transit",    False, False, False, False, False, 120),
    ("DEPARTED",          "Despachado",        "send",          "#6366f1", ["in_custody","loaded","sealed"],                                         "in_transit",    False, False, False, False, False, 130),
    ("CUSTOMS_HOLD",      "Retención Aduana",  "shield",        "#f59e0b", ["in_custody","in_transit"],                                              "customs_hold",  False, False, True,  False, False, 140),
    ("CUSTOMS_CLEARED",   "Aduana Liberada",   "shield-check",  "#10b981", ["customs_hold"],                                                        "in_custody",    False, False, False, False, False, 150),
    ("DAMAGED",           "Daño Reportado",    "alert-triangle","#ef4444", ["in_custody","in_transit","loaded","qc_passed","qc_failed","sealed","customs_hold"], "damaged", False, False, True, True, False, 160),
    ("DELIVERED",         "Entregado",         "check-circle-2","#10b981", ["in_custody","in_transit","qc_passed"],                                  "delivered",     False, False, False, False, False, 170),
    ("SEALED",            "Sellado",           "lock",          "#8b5cf6", ["loaded"],                                                               "sealed",        False, False, False, False, False, 180),
    ("UNSEALED",          "Sello Removido",    "unlock",        "#8b5cf6", ["sealed"],                                                               "loaded",        False, False, False, False, False, 190),
    ("TEMPERATURE_CHECK", "Temp. Check",       "thermometer",   "#06b6d4", ["in_custody","in_transit","loaded","qc_passed","qc_failed","sealed","customs_hold","damaged"], None, True, False, True, False, False, 200),
    ("INSPECTION",        "Inspección",        "search",        "#f59e0b", ["in_custody","in_transit","loaded","qc_passed","qc_failed","sealed","customs_hold","damaged"], None, True, False, True, False, False, 210),
    ("CONSOLIDATED",      "Consolidado",       "layers",        "#94a3b8", ["in_custody","in_transit","loaded","qc_passed","qc_failed","sealed","customs_hold","damaged"], None, True, False, False, False, False, 220),
    ("DECONSOLIDATED",    "Desconsolidado",    "minimize-2",    "#94a3b8", ["in_custody","in_transit","loaded","qc_passed","qc_failed","sealed","customs_hold","damaged"], None, True, False, False, False, False, 230),
    ("NOTE",              "Nota",              "file-text",     "#94a3b8", ["in_custody","in_transit","loaded","qc_passed","qc_failed","sealed","customs_hold","damaged"], None, True, False, False, False, False, 240),
]


def upgrade() -> None:
    op.create_table(
        "event_type_configs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon", sa.Text(), nullable=False, server_default="circle"),
        sa.Column("color", sa.Text(), nullable=False, server_default="#6366f1"),
        sa.Column("from_states", ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("to_state", sa.Text(), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_informational", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("requires_wallet", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("requires_notes", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("requires_reason", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("requires_admin", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_event_type_configs_tenant_slug"),
    )
    op.create_index("ix_event_type_configs_tenant", "event_type_configs", ["tenant_id"])

    # Seed system event types for default tenant
    event_type_configs = sa.table(
        "event_type_configs",
        sa.column("tenant_id", UUID(as_uuid=True)),
        sa.column("slug", sa.Text()),
        sa.column("name", sa.Text()),
        sa.column("icon", sa.Text()),
        sa.column("color", sa.Text()),
        sa.column("from_states", ARRAY(sa.Text())),
        sa.column("to_state", sa.Text()),
        sa.column("is_system", sa.Boolean()),
        sa.column("is_informational", sa.Boolean()),
        sa.column("requires_wallet", sa.Boolean()),
        sa.column("requires_notes", sa.Boolean()),
        sa.column("requires_reason", sa.Boolean()),
        sa.column("requires_admin", sa.Boolean()),
        sa.column("sort_order", sa.Integer()),
    )

    rows = []
    for (slug, name, icon, color, from_states, to_state, is_info,
         req_wallet, req_notes, req_reason, req_admin, sort) in SYSTEM_EVENTS:
        rows.append({
            "tenant_id": DEFAULT_TENANT,
            "slug": slug,
            "name": name,
            "icon": icon,
            "color": color,
            "from_states": from_states,
            "to_state": to_state,
            "is_system": True,
            "is_informational": is_info,
            "requires_wallet": req_wallet,
            "requires_notes": req_notes,
            "requires_reason": req_reason,
            "requires_admin": req_admin,
            "sort_order": sort,
        })
    op.bulk_insert(event_type_configs, rows)


def downgrade() -> None:
    op.drop_index("ix_event_type_configs_tenant", table_name="event_type_configs")
    op.drop_table("event_type_configs")
