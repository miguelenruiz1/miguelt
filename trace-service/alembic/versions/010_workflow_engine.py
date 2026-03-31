"""Add workflow engine tables: workflow_states, workflow_transitions, workflow_event_types.

Migrates legacy hardcoded asset states to tenant-scoped workflow_state rows,
seeds all valid transitions from VALID_FROM_STATES, seeds all event types,
and links existing assets to their corresponding workflow_state_id.

Revision ID: a1b2c3d4e5f6
Revises: 009_shipments_trade_docs
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP, JSONB
import uuid

revision = "a1b2c3d4e5f6"
down_revision = "009_shipments_trade_docs"
branch_labels = None
depends_on = None

# ── Legacy States ────────────────────────────────────────────────────────────
# (slug, label, color, icon, is_initial, is_terminal, sort_order)
LEGACY_STATES = [
    ("in_custody",    "En custodia",       "#8b5cf6", "package",        True,  False, 0),
    ("in_transit",    "En tránsito",       "#f59e0b", "truck",          False, False, 1),
    ("loaded",        "Cargado",           "#3b82f6", "container",      False, False, 2),
    ("qc_passed",     "QC aprobado",       "#22c55e", "check-circle",   False, False, 3),
    ("qc_failed",     "QC fallido",        "#ef4444", "x-circle",       False, False, 4),
    ("customs_hold",  "Retención aduana",  "#f97316", "shield-alert",   False, False, 5),
    ("damaged",       "Dañado",            "#dc2626", "alert-triangle", False, False, 6),
    ("sealed",        "Sellado",           "#06b6d4", "lock",           False, False, 7),
    ("released",      "Liberado",          "#10b981", "unlock",         False, True,  8),
    ("burned",        "Consumido",         "#6b7280", "flame",          False, True,  9),
    ("delivered",     "Entregado",         "#059669", "check-circle-2", False, True,  10),
]

# ── Legacy Transitions (from VALID_FROM_STATES + EVENT_STATE_TRANSITIONS) ────
# Each tuple: (from_slug, to_slug, event_type_slug, label)
LEGACY_TRANSITIONS = [
    # HANDOFF: from in_custody/in_transit/loaded/qc_passed/qc_failed -> in_transit
    ("in_custody", "in_transit", "HANDOFF", "Handoff"),
    ("in_transit", "in_transit", "HANDOFF", "Handoff (re-route)"),
    ("loaded",     "in_transit", "HANDOFF", "Handoff (loaded)"),
    ("qc_passed",  "in_transit", "HANDOFF", "Handoff (post-QC)"),
    ("qc_failed",  "in_transit", "HANDOFF", "Handoff (post-QC fail)"),
    # ARRIVED: from in_transit -> in_custody
    ("in_transit", "in_custody", "ARRIVED", "Arrived"),
    # LOADED: from in_custody -> loaded
    ("in_custody", "loaded", "LOADED", "Loaded"),
    # QC: from loaded/qc_failed -> qc_passed or qc_failed
    ("loaded",    "qc_passed", "QC", "QC passed"),
    ("loaded",    "qc_failed", "QC", "QC failed"),
    ("qc_failed", "qc_passed", "QC", "QC re-inspect passed"),
    ("qc_failed", "qc_failed", "QC", "QC re-inspect failed"),
    # RELEASED: from any non-terminal -> released
    ("in_custody",   "released", "RELEASED", "Release"),
    ("in_transit",   "released", "RELEASED", "Release"),
    ("loaded",       "released", "RELEASED", "Release"),
    ("qc_passed",    "released", "RELEASED", "Release"),
    ("qc_failed",    "released", "RELEASED", "Release"),
    ("customs_hold", "released", "RELEASED", "Release"),
    ("damaged",      "released", "RELEASED", "Release"),
    ("sealed",       "released", "RELEASED", "Release"),
    # BURN: from any non-terminal -> burned
    ("in_custody",   "burned", "BURN", "Burn"),
    ("in_transit",   "burned", "BURN", "Burn"),
    ("loaded",       "burned", "BURN", "Burn"),
    ("qc_passed",    "burned", "BURN", "Burn"),
    ("qc_failed",    "burned", "BURN", "Burn"),
    ("customs_hold", "burned", "BURN", "Burn"),
    ("damaged",      "burned", "BURN", "Burn"),
    ("sealed",       "burned", "BURN", "Burn"),
    # PICKUP: from in_custody -> in_transit
    ("in_custody", "in_transit", "PICKUP", "Pickup"),
    # GATE_IN: from in_transit -> in_custody
    ("in_transit", "in_custody", "GATE_IN", "Gate in"),
    # GATE_OUT: from in_custody/loaded/qc_passed/qc_failed -> in_transit
    ("in_custody", "in_transit", "GATE_OUT", "Gate out"),
    ("loaded",     "in_transit", "GATE_OUT", "Gate out"),
    ("qc_passed",  "in_transit", "GATE_OUT", "Gate out"),
    ("qc_failed",  "in_transit", "GATE_OUT", "Gate out"),
    # DEPARTED: from in_custody/loaded/sealed -> in_transit
    ("in_custody", "in_transit", "DEPARTED", "Departed"),
    ("loaded",     "in_transit", "DEPARTED", "Departed"),
    ("sealed",     "in_transit", "DEPARTED", "Departed"),
    # CUSTOMS_HOLD: from in_custody/in_transit -> customs_hold
    ("in_custody", "customs_hold", "CUSTOMS_HOLD", "Customs hold"),
    ("in_transit", "customs_hold", "CUSTOMS_HOLD", "Customs hold"),
    # CUSTOMS_CLEARED: from customs_hold -> in_custody
    ("customs_hold", "in_custody", "CUSTOMS_CLEARED", "Customs cleared"),
    # DAMAGED: from any non-terminal -> damaged
    ("in_custody",   "damaged", "DAMAGED", "Damaged"),
    ("in_transit",   "damaged", "DAMAGED", "Damaged"),
    ("loaded",       "damaged", "DAMAGED", "Damaged"),
    ("qc_passed",    "damaged", "DAMAGED", "Damaged"),
    ("qc_failed",    "damaged", "DAMAGED", "Damaged"),
    ("customs_hold", "damaged", "DAMAGED", "Damaged"),
    ("sealed",       "damaged", "DAMAGED", "Damaged"),
    # DELIVERED: from in_custody/in_transit/qc_passed -> delivered
    ("in_custody", "delivered", "DELIVERED", "Delivered"),
    ("in_transit", "delivered", "DELIVERED", "Delivered"),
    ("qc_passed",  "delivered", "DELIVERED", "Delivered"),
    # SEALED: from loaded -> sealed
    ("loaded", "sealed", "SEALED", "Sealed"),
    # UNSEALED: from sealed -> loaded
    ("sealed", "loaded", "UNSEALED", "Unsealed"),
]

# ── Legacy Event Types ───────────────────────────────────────────────────────
# (slug, name, icon, color, is_informational, requires_wallet, requires_notes,
#  requires_reason, requires_admin, sort_order)
LEGACY_EVENT_TYPES = [
    ("CREATED",           "Creado",              "plus-circle",    "#22c55e", False, False, False, False, False, 0),
    ("HANDOFF",           "Handoff",             "arrow-right",    "#3b82f6", False, True,  False, False, False, 1),
    ("ARRIVED",           "Arrived",             "map-pin",        "#8b5cf6", False, False, False, False, False, 2),
    ("LOADED",            "Loaded",              "container",      "#06b6d4", False, False, False, False, False, 3),
    ("QC",                "Control de calidad",  "clipboard-check","#f59e0b", False, False, True,  False, False, 4),
    ("RELEASED",          "Liberado",            "unlock",         "#10b981", False, False, False, True,  True,  5),
    ("BURN",              "Consumido",           "flame",          "#ef4444", False, False, False, True,  False, 6),
    ("PICKUP",            "Recolección",         "package-check",  "#3b82f6", False, True,  False, False, False, 7),
    ("GATE_IN",           "Gate In",             "log-in",         "#8b5cf6", False, False, False, False, False, 8),
    ("GATE_OUT",          "Gate Out",            "log-out",        "#f59e0b", False, False, False, False, False, 9),
    ("DEPARTED",          "Departed",            "plane-takeoff",  "#06b6d4", False, False, False, False, False, 10),
    ("CUSTOMS_HOLD",      "Retención aduana",    "shield-alert",   "#f97316", False, False, True,  False, False, 11),
    ("CUSTOMS_CLEARED",   "Liberado aduana",     "shield-check",   "#22c55e", False, False, False, False, False, 12),
    ("DAMAGED",           "Dañado",              "alert-triangle", "#dc2626", False, False, True,  True,  True,  13),
    ("DELIVERED",         "Entregado",           "check-circle",   "#059669", False, True,  False, False, False, 14),
    ("SEALED",            "Sellado",             "lock",           "#06b6d4", False, False, False, False, False, 15),
    ("UNSEALED",          "Sello removido",      "unlock",         "#f59e0b", False, False, False, False, False, 16),
    ("TEMPERATURE_CHECK", "Control temperatura", "thermometer",    "#ef4444", True,  False, True,  False, False, 17),
    ("INSPECTION",        "Inspección",          "search",         "#8b5cf6", True,  False, True,  False, False, 18),
    ("CONSOLIDATED",      "Consolidado",         "layers",         "#3b82f6", True,  False, False, False, False, 19),
    ("DECONSOLIDATED",    "Desconsolidado",      "layers",         "#f59e0b", True,  False, False, False, False, 20),
    ("NOTE",              "Nota",                "message-square", "#94a3b8", True,  False, True,  False, False, 21),
]


def upgrade() -> None:
    # ── Workflow States ─────────────────────────────────────────────────────
    op.create_table(
        "workflow_states",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("slug", sa.Text, nullable=False),
        sa.Column("label", sa.Text, nullable=False),
        sa.Column("color", sa.Text, nullable=False, server_default="#6b7280"),
        sa.Column("icon", sa.Text, nullable=True),
        sa.Column("is_initial", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("is_terminal", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_workflow_states_tenant_slug"),
    )
    op.create_index("ix_workflow_states_tenant", "workflow_states", ["tenant_id"])

    # ── Workflow Transitions ────────────────────────────────────────────────
    op.create_table(
        "workflow_transitions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_state_id", UUID(as_uuid=True), sa.ForeignKey("workflow_states.id", ondelete="CASCADE"), nullable=True),
        sa.Column("to_state_id", UUID(as_uuid=True), sa.ForeignKey("workflow_states.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type_slug", sa.Text, nullable=True),
        sa.Column("label", sa.Text, nullable=True),
        sa.Column("requires_data", JSONB, nullable=True),
        sa.Column("created_at", TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id", "from_state_id", "to_state_id", name="uq_workflow_transitions_pair"),
    )
    op.create_index("ix_workflow_transitions_tenant", "workflow_transitions", ["tenant_id"])

    # ── Workflow Event Types ────────────────────────────────────────────────
    op.create_table(
        "workflow_event_types",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("slug", sa.Text, nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("icon", sa.Text, nullable=False, server_default="circle"),
        sa.Column("color", sa.Text, nullable=False, server_default="#6366f1"),
        sa.Column("is_informational", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("requires_wallet", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("requires_notes", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("requires_reason", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("requires_admin", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("data_schema", JSONB, nullable=True),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_workflow_event_types_tenant_slug"),
    )
    op.create_index("ix_workflow_event_types_tenant", "workflow_event_types", ["tenant_id"])

    # ── Add workflow_state_id FK to assets ──────────────────────────────────
    op.add_column(
        "assets",
        sa.Column(
            "workflow_state_id",
            UUID(as_uuid=True),
            sa.ForeignKey("workflow_states.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_assets_workflow_state_id", "assets", ["workflow_state_id"])

    # ── Data migration: seed per tenant ─────────────────────────────────────
    conn = op.get_bind()
    tenant_rows = conn.execute(sa.text("SELECT id FROM tenants")).fetchall()

    for (tenant_id,) in tenant_rows:
        _seed_tenant(conn, tenant_id)


def _seed_tenant(conn, tenant_id):
    """Seed workflow states, transitions, and event types for one tenant."""
    tid = str(tenant_id)

    # 1. Create states — build slug -> uuid map
    slug_to_id: dict[str, str] = {}
    for slug, label, color, icon, is_initial, is_terminal, sort_order in LEGACY_STATES:
        state_id = str(uuid.uuid4())
        slug_to_id[slug] = state_id
        conn.execute(
            sa.text(
                "INSERT INTO workflow_states "
                "(id, tenant_id, slug, label, color, icon, is_initial, is_terminal, sort_order) "
                "VALUES (:id, :tid, :slug, :label, :color, :icon, :is_initial, :is_terminal, :sort_order)"
            ),
            {"id": state_id, "tid": tid, "slug": slug, "label": label,
             "color": color, "icon": icon, "is_initial": is_initial,
             "is_terminal": is_terminal, "sort_order": sort_order},
        )

    # 2. Create transitions — deduplicate (from_state, to_state) pairs
    seen_pairs: set[tuple[str, str]] = set()
    for from_slug, to_slug, evt_slug, label in LEGACY_TRANSITIONS:
        from_id = slug_to_id.get(from_slug)
        to_id = slug_to_id.get(to_slug)
        if not from_id or not to_id:
            continue
        pair = (from_id, to_id)
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        conn.execute(
            sa.text(
                "INSERT INTO workflow_transitions "
                "(id, tenant_id, from_state_id, to_state_id, event_type_slug, label) "
                "VALUES (:id, :tid, :from_id, :to_id, :evt_slug, :label)"
            ),
            {"id": str(uuid.uuid4()), "tid": tid, "from_id": from_id,
             "to_id": to_id, "evt_slug": evt_slug, "label": label},
        )

    # 3. Create event types
    for (slug, name, icon, color, is_info, req_wallet, req_notes,
         req_reason, req_admin, sort_order) in LEGACY_EVENT_TYPES:
        conn.execute(
            sa.text(
                "INSERT INTO workflow_event_types "
                "(id, tenant_id, slug, name, icon, color, is_informational, "
                "requires_wallet, requires_notes, requires_reason, requires_admin, sort_order) "
                "VALUES (:id, :tid, :slug, :name, :icon, :color, :is_info, "
                ":req_wallet, :req_notes, :req_reason, :req_admin, :sort_order)"
            ),
            {"id": str(uuid.uuid4()), "tid": tid, "slug": slug, "name": name,
             "icon": icon, "color": color, "is_info": is_info,
             "req_wallet": req_wallet, "req_notes": req_notes,
             "req_reason": req_reason, "req_admin": req_admin,
             "sort_order": sort_order},
        )

    # 4. Link existing assets to their workflow_state_id
    for slug, state_id in slug_to_id.items():
        conn.execute(
            sa.text(
                "UPDATE assets SET workflow_state_id = :state_id "
                "WHERE tenant_id = :tid AND state = :slug"
            ),
            {"state_id": state_id, "tid": tid, "slug": slug},
        )


def downgrade() -> None:
    op.drop_index("ix_assets_workflow_state_id", table_name="assets")
    op.drop_column("assets", "workflow_state_id")

    op.drop_index("ix_workflow_event_types_tenant", table_name="workflow_event_types")
    op.drop_table("workflow_event_types")

    op.drop_index("ix_workflow_transitions_tenant", table_name="workflow_transitions")
    op.drop_table("workflow_transitions")

    op.drop_index("ix_workflow_states_tenant", table_name="workflow_states")
    op.drop_table("workflow_states")
