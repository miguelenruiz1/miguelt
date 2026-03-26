"""Add shipment_documents, trade_documents, and anchor_rules to trace-service.

These belong in the logistics module, not inventory.

Revision ID: 009
Revises: 008_anchor_requests
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP, JSONB

revision = "009_shipments_trade_docs"
down_revision = "008_anchor_requests"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Anchor Rules ──────────────────────────────────────────────────
    op.create_table(
        "anchor_rules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("trigger_event", sa.String(50), nullable=False),
        sa.Column("conditions", JSONB, nullable=False, server_default="{}"),
        sa.Column("actions", JSONB, nullable=False, server_default='{"anchor": true}'),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("priority", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_anchor_rules_tenant", "anchor_rules", ["tenant_id"])

    # ── Shipment Documents ────────────────────────────────────────────
    op.create_table(
        "shipment_documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("document_type", sa.String(30), nullable=False),
        sa.Column("document_number", sa.String(100), nullable=False),
        sa.Column("carrier_name", sa.String(150), nullable=True),
        sa.Column("carrier_code", sa.String(50), nullable=True),
        sa.Column("vehicle_plate", sa.String(20), nullable=True),
        sa.Column("driver_name", sa.String(150), nullable=True),
        sa.Column("driver_id_number", sa.String(30), nullable=True),
        sa.Column("origin_address", sa.Text, nullable=True),
        sa.Column("destination_address", sa.Text, nullable=True),
        sa.Column("origin_city", sa.String(100), nullable=True),
        sa.Column("destination_city", sa.String(100), nullable=True),
        sa.Column("origin_country", sa.String(3), nullable=True),
        sa.Column("destination_country", sa.String(3), nullable=True),
        sa.Column("vessel_name", sa.String(150), nullable=True),
        sa.Column("voyage_number", sa.String(50), nullable=True),
        sa.Column("container_number", sa.String(50), nullable=True),
        sa.Column("container_type", sa.String(20), nullable=True),
        sa.Column("seal_number", sa.String(50), nullable=True),
        sa.Column("flight_number", sa.String(20), nullable=True),
        sa.Column("total_packages", sa.Integer, nullable=True),
        sa.Column("total_weight_kg", sa.Numeric(12, 4), nullable=True),
        sa.Column("total_volume_m3", sa.Numeric(12, 4), nullable=True),
        sa.Column("cargo_description", sa.Text, nullable=True),
        sa.Column("declared_value", sa.Numeric(14, 2), nullable=True),
        sa.Column("declared_currency", sa.String(3), nullable=True),
        sa.Column("issued_date", TIMESTAMP(timezone=True), nullable=True),
        sa.Column("shipped_date", TIMESTAMP(timezone=True), nullable=True),
        sa.Column("estimated_arrival", TIMESTAMP(timezone=True), nullable=True),
        sa.Column("actual_arrival", TIMESTAMP(timezone=True), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="draft"),
        sa.Column("tracking_number", sa.String(100), nullable=True),
        sa.Column("tracking_url", sa.String(500), nullable=True),
        sa.Column("anchor_hash", sa.String(64), nullable=True),
        sa.Column("anchor_status", sa.String(20), nullable=False, server_default="none"),
        sa.Column("anchor_tx_sig", sa.String(128), nullable=True),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("file_url", sa.String(500), nullable=True),
        sa.Column("reference_id", sa.String(100), nullable=True),
        sa.Column("reference_type", sa.String(50), nullable=True),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_shipment_docs_tenant", "shipment_documents", ["tenant_id"])
    op.create_index("ix_shipment_docs_type", "shipment_documents", ["document_type"])
    op.create_index("ix_shipment_docs_ref", "shipment_documents", ["reference_type", "reference_id"])

    # ── Trade Documents ───────────────────────────────────────────────
    op.create_table(
        "trade_documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("document_type", sa.String(50), nullable=False),
        sa.Column("document_number", sa.String(100), nullable=True),
        sa.Column("shipment_document_id", UUID(as_uuid=True), sa.ForeignKey("shipment_documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("issuing_authority", sa.String(255), nullable=True),
        sa.Column("issuing_country", sa.String(3), nullable=True),
        sa.Column("issued_date", TIMESTAMP(timezone=True), nullable=True),
        sa.Column("expiry_date", TIMESTAMP(timezone=True), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("content_data", JSONB, nullable=False, server_default="{}"),
        sa.Column("file_url", sa.String(500), nullable=True),
        sa.Column("file_hash", sa.String(64), nullable=True),
        sa.Column("hs_code", sa.String(20), nullable=True),
        sa.Column("fob_value", sa.Numeric(14, 2), nullable=True),
        sa.Column("cif_value", sa.Numeric(14, 2), nullable=True),
        sa.Column("currency", sa.String(3), nullable=True),
        sa.Column("anchor_hash", sa.String(64), nullable=True),
        sa.Column("anchor_status", sa.String(20), nullable=False, server_default="none"),
        sa.Column("anchor_tx_sig", sa.String(128), nullable=True),
        sa.Column("anchored_at", TIMESTAMP(timezone=True), nullable=True),
        sa.Column("reference_id", sa.String(100), nullable=True),
        sa.Column("reference_type", sa.String(50), nullable=True),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_trade_docs_tenant", "trade_documents", ["tenant_id"])
    op.create_index("ix_trade_docs_type", "trade_documents", ["document_type"])
    op.create_index("ix_trade_docs_shipment", "trade_documents", ["shipment_document_id"])
    op.create_index("ix_trade_docs_ref", "trade_documents", ["reference_type", "reference_id"])


def downgrade() -> None:
    op.drop_table("trade_documents")
    op.drop_table("shipment_documents")
    op.drop_table("anchor_rules")
