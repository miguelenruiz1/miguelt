"""Add RETURN event type and 'devuelto' state to workflow for all tenants.

Also removes is_terminal from 'delivered' equivalent states to allow returns.

Revision ID: 013_return
Revises: 012_evidence
"""
from alembic import op
import sqlalchemy as sa
import uuid

revision = "013_return"
down_revision = "012_evidence"
branch_labels = None
depends_on = None

# Terminal state slugs that should allow returns (remove is_terminal)
DELIVERED_SLUGS = ("entregado", "delivered", "dispensado", "recibido_cliente", "cerrado")


def upgrade() -> None:
    conn = op.get_bind()
    tenant_rows = conn.execute(sa.text("SELECT id FROM tenants")).fetchall()

    for (tenant_id,) in tenant_rows:
        tid = str(tenant_id)

        # 1. Remove is_terminal from delivered-like states so RETURN is allowed
        for slug in DELIVERED_SLUGS:
            conn.execute(
                sa.text(
                    "UPDATE workflow_states SET is_terminal = false "
                    "WHERE tenant_id = :tid AND slug = :slug"
                ),
                {"tid": tid, "slug": slug},
            )

        # 2. Find max sort_order for this tenant
        row = conn.execute(
            sa.text("SELECT COALESCE(MAX(sort_order), 0) FROM workflow_states WHERE tenant_id = :tid"),
            {"tid": tid},
        ).first()
        max_order = row[0] if row else 0

        # 3. Create 'devuelto' state (non-terminal, allows re-processing)
        devuelto_id = str(uuid.uuid4())
        conn.execute(
            sa.text(
                "INSERT INTO workflow_states "
                "(id, tenant_id, slug, label, color, icon, is_initial, is_terminal, sort_order) "
                "VALUES (:id, :tid, 'devuelto', 'Devuelto', '#f97316', 'undo-2', false, false, :order)"
            ),
            {"id": devuelto_id, "tid": tid, "order": max_order + 1},
        )

        # 4. Create transitions from delivered-like states to devuelto
        for slug in DELIVERED_SLUGS:
            from_row = conn.execute(
                sa.text("SELECT id FROM workflow_states WHERE tenant_id = :tid AND slug = :slug"),
                {"tid": tid, "slug": slug},
            ).first()
            if from_row:
                conn.execute(
                    sa.text(
                        "INSERT INTO workflow_transitions "
                        "(id, tenant_id, from_state_id, to_state_id, event_type_slug, label) "
                        "VALUES (:id, :tid, :from_id, :to_id, 'RETURN', 'Devolver') "
                        "ON CONFLICT DO NOTHING"
                    ),
                    {"id": str(uuid.uuid4()), "tid": tid,
                     "from_id": str(from_row[0]), "to_id": devuelto_id},
                )

        # 5. Create RETURN event type
        conn.execute(
            sa.text(
                "INSERT INTO workflow_event_types "
                "(id, tenant_id, slug, name, icon, color, is_informational, "
                "requires_wallet, requires_notes, requires_reason, requires_admin, sort_order) "
                "VALUES (:id, :tid, 'RETURN', 'Devolución', 'undo-2', '#f97316', "
                "false, false, true, true, false, 99) "
                "ON CONFLICT DO NOTHING"
            ),
            {"id": str(uuid.uuid4()), "tid": tid},
        )


def downgrade() -> None:
    conn = op.get_bind()
    # Remove devuelto states, RETURN event types, and transitions
    conn.execute(sa.text("DELETE FROM workflow_transitions WHERE event_type_slug = 'RETURN'"))
    conn.execute(sa.text("DELETE FROM workflow_event_types WHERE slug = 'RETURN'"))
    conn.execute(sa.text("DELETE FROM workflow_states WHERE slug = 'devuelto'"))
    # Restore is_terminal on delivered-like states
    for slug in DELIVERED_SLUGS:
        conn.execute(
            sa.text("UPDATE workflow_states SET is_terminal = true WHERE slug = :slug"),
            {"slug": slug},
        )
