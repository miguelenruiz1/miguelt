"""Add tenant_id to custody_events. Add missing indexes to shipment_documents,
trade_documents, and anchor_rules.

Revision ID: 016_tenant_indexes
Revises: 015_event_docs
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "016_tenant_indexes"
down_revision = "015_event_docs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── custody_events: add tenant_id ────────────────────────────────────────
    op.add_column("custody_events", sa.Column("tenant_id", UUID(as_uuid=True), nullable=True))

    # Backfill from parent assets table
    op.execute("""
        UPDATE custody_events ce
        SET tenant_id = a.tenant_id
        FROM assets a
        WHERE ce.asset_id = a.id
          AND ce.tenant_id IS NULL
    """)

    # Default for any orphans (shouldn't exist but safety)
    op.execute("""
        UPDATE custody_events
        SET tenant_id = '00000000-0000-0000-0000-000000000001'
        WHERE tenant_id IS NULL
    """)

    op.alter_column("custody_events", "tenant_id", nullable=False)

    op.create_foreign_key(
        "fk_custody_events_tenant_id",
        "custody_events", "tenants",
        ["tenant_id"], ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_custody_events_tenant", "custody_events", ["tenant_id"])

    # ── shipment_documents: add missing indexes (if_not_exists) ────────────────
    op.execute("CREATE INDEX IF NOT EXISTS ix_shipment_docs_tenant ON shipment_documents (tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_shipment_docs_status ON shipment_documents (status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_shipment_docs_type ON shipment_documents (document_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_shipment_docs_number ON shipment_documents (document_number)")

    # ── trade_documents: add missing indexes (if_not_exists) ─────────────────
    op.execute("CREATE INDEX IF NOT EXISTS ix_trade_docs_tenant ON trade_documents (tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_trade_docs_status ON trade_documents (status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_trade_docs_type ON trade_documents (document_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_trade_docs_shipment ON trade_documents (shipment_document_id)")

    # ── anchor_rules: add missing indexes (if_not_exists) ────────────────────
    op.execute("CREATE INDEX IF NOT EXISTS ix_anchor_rules_tenant ON anchor_rules (tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_anchor_rules_entity_trigger ON anchor_rules (entity_type, trigger_event)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_anchor_rules_active ON anchor_rules (tenant_id, is_active)")


def downgrade() -> None:
    op.drop_index("ix_anchor_rules_active", "anchor_rules")
    op.drop_index("ix_anchor_rules_entity_trigger", "anchor_rules")
    op.drop_index("ix_anchor_rules_tenant", "anchor_rules")

    op.drop_index("ix_trade_docs_shipment", "trade_documents")
    op.drop_index("ix_trade_docs_type", "trade_documents")
    op.drop_index("ix_trade_docs_status", "trade_documents")
    op.drop_index("ix_trade_docs_tenant", "trade_documents")

    op.drop_index("ix_shipment_docs_number", "shipment_documents")
    op.drop_index("ix_shipment_docs_type", "shipment_documents")
    op.drop_index("ix_shipment_docs_status", "shipment_documents")
    op.drop_index("ix_shipment_docs_tenant", "shipment_documents")

    op.drop_index("ix_custody_events_tenant", "custody_events")
    op.drop_constraint("fk_custody_events_tenant_id", "custody_events", type_="foreignkey")
    op.drop_column("custody_events", "tenant_id")
