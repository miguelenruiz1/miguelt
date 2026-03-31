"""Allow multiple event types per (from_state, to_state) transition pair.

The original migration 010 deduplicated transitions by (from_state, to_state),
losing event_type_slug for events like PICKUP, GATE_IN, GATE_OUT, DEPARTED
that share a target state with HANDOFF/ARRIVED.

This migration:
1. Drops the old unique constraint on (tenant_id, from_state_id, to_state_id)
2. Adds a new unique constraint on (tenant_id, from_state_id, to_state_id, event_type_slug)
3. Inserts the missing transition rows per tenant

Revision ID: 014_multi_event
Revises: 013_return
"""
from alembic import op
import sqlalchemy as sa
import uuid

revision = "014_multi_event"
down_revision = "013_return"
branch_labels = None
depends_on = None

# Transitions that were lost during dedup in migration 010.
# Format: (from_slug, to_slug, event_type_slug, label)
MISSING_TRANSITIONS = [
    # PICKUP shares (in_custody -> in_transit) with HANDOFF
    ("in_custody", "in_transit", "PICKUP", "Recolección"),
    # GATE_OUT shares (X -> in_transit) with HANDOFF
    ("in_custody", "in_transit", "GATE_OUT", "Gate out"),
    ("loaded",     "in_transit", "GATE_OUT", "Gate out"),
    ("qc_passed",  "in_transit", "GATE_OUT", "Gate out"),
    ("qc_failed",  "in_transit", "GATE_OUT", "Gate out"),
    # DEPARTED shares (X -> in_transit) with HANDOFF
    ("in_custody", "in_transit", "DEPARTED", "Departed"),
    ("loaded",     "in_transit", "DEPARTED", "Departed"),
    # GATE_IN shares (in_transit -> in_custody) with ARRIVED
    ("in_transit", "in_custody", "GATE_IN", "Gate in"),
]


def upgrade() -> None:
    # 1. Drop old unique constraint
    op.drop_constraint("uq_workflow_transitions_pair", "workflow_transitions", type_="unique")

    # 2. Add new unique constraint including event_type_slug
    op.create_unique_constraint(
        "uq_workflow_transitions_event",
        "workflow_transitions",
        ["tenant_id", "from_state_id", "to_state_id", "event_type_slug"],
    )

    # 3. Insert missing transitions for each tenant
    conn = op.get_bind()
    tenant_rows = conn.execute(sa.text("SELECT id FROM tenants")).fetchall()

    for (tenant_id,) in tenant_rows:
        _seed_missing(conn, str(tenant_id))


def _seed_missing(conn, tid: str):
    """Insert the transitions that were lost to dedup."""
    # Build slug -> state_id map for this tenant
    rows = conn.execute(
        sa.text("SELECT slug, id FROM workflow_states WHERE tenant_id = :tid"),
        {"tid": tid},
    ).fetchall()
    slug_to_id = {r[0]: str(r[1]) for r in rows}

    for from_slug, to_slug, evt_slug, label in MISSING_TRANSITIONS:
        from_id = slug_to_id.get(from_slug)
        to_id = slug_to_id.get(to_slug)
        if not from_id or not to_id:
            continue

        # Check if already exists (idempotent)
        existing = conn.execute(
            sa.text(
                "SELECT 1 FROM workflow_transitions "
                "WHERE tenant_id = :tid AND from_state_id = :fid "
                "AND to_state_id = :toid AND event_type_slug = :evt"
            ),
            {"tid": tid, "fid": from_id, "toid": to_id, "evt": evt_slug},
        ).fetchone()
        if existing:
            continue

        conn.execute(
            sa.text(
                "INSERT INTO workflow_transitions "
                "(id, tenant_id, from_state_id, to_state_id, event_type_slug, label) "
                "VALUES (:id, :tid, :fid, :toid, :evt, :label)"
            ),
            {
                "id": str(uuid.uuid4()),
                "tid": tid,
                "fid": from_id,
                "toid": to_id,
                "evt": evt_slug,
                "label": label,
            },
        )

    # Also update existing transitions that have NULL event_type_slug
    # from the original dedup (they kept the first event_type_slug, so those are fine)


def downgrade() -> None:
    # Remove the extra transitions
    conn = op.get_bind()
    for _, _, evt_slug, _ in MISSING_TRANSITIONS:
        conn.execute(
            sa.text(
                "DELETE FROM workflow_transitions WHERE event_type_slug = :evt"
            ),
            {"evt": evt_slug},
        )

    op.drop_constraint("uq_workflow_transitions_event", "workflow_transitions", type_="unique")
    op.create_unique_constraint(
        "uq_workflow_transitions_pair",
        "workflow_transitions",
        ["tenant_id", "from_state_id", "to_state_id"],
    )
