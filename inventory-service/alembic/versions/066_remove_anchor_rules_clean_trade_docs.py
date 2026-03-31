"""Remove anchor_rules table (moved to trace-service) and clean trade_documents.

Per boundary spec: anchor rules belong in trace-service.
TradeDocument types cert_origen, fitosanitario, insurance_cert, invima, dex, dim
belong in trace-service. inventory-service keeps only: packing_list, commercial_invoice,
bill_of_lading.

Revision ID: 066
Revises: 065_trade_and_logistics
"""
from alembic import op
import sqlalchemy as sa

revision = "066"
down_revision = "065"
branch_labels = None
depends_on = None

# Document types that belong in trace-service (not inventory)
TRACE_DOC_TYPES = (
    "cert_origen",
    "fitosanitario",
    "insurance_cert",
    "invima",
    "dex",
    "dim",
)


def upgrade() -> None:
    # 1. Drop anchor_rules table entirely
    op.drop_index("ix_anchor_rules_tenant_entity", table_name="anchor_rules")
    op.drop_index("ix_anchor_rules_tenant", table_name="anchor_rules")
    op.drop_table("anchor_rules")

    # 2. Delete trade_documents rows with types that belong in trace-service
    conn = op.get_bind()
    for doc_type in TRACE_DOC_TYPES:
        conn.execute(
            sa.text("DELETE FROM trade_documents WHERE document_type = :dt"),
            {"dt": doc_type},
        )


def downgrade() -> None:
    # Re-create anchor_rules table
    op.create_table(
        "anchor_rules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("trigger_event", sa.String(50), nullable=False),
        sa.Column("conditions", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("actions", sa.JSON, nullable=False, server_default='{"anchor": true}'),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("priority", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_anchor_rules_tenant", "anchor_rules", ["tenant_id"])
    op.create_index("ix_anchor_rules_tenant_entity", "anchor_rules", ["tenant_id", "entity_type"])
    # Deleted trade_documents rows cannot be restored (data migration)
