"""Add trade/logistics fields and shipment_documents + trade_documents tables.

Revision ID: 065
Revises: 064_anchor_rules
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "065_trade_and_logistics"
down_revision = "064_anchor_rules"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── PO: incoterms + multi-currency ────────────────────────────────
    op.add_column("purchase_orders", sa.Column("currency", sa.String(3), nullable=False, server_default="COP"))
    op.add_column("purchase_orders", sa.Column("exchange_rate", sa.Numeric(14, 6), nullable=True))
    op.add_column("purchase_orders", sa.Column("incoterm", sa.String(10), nullable=True))
    op.add_column("purchase_orders", sa.Column("origin_country", sa.String(3), nullable=True))
    op.add_column("purchase_orders", sa.Column("destination_country", sa.String(3), nullable=True))
    op.add_column("purchase_orders", sa.Column("port_of_loading", sa.String(100), nullable=True))
    op.add_column("purchase_orders", sa.Column("port_of_discharge", sa.String(100), nullable=True))
    op.add_column("purchase_orders", sa.Column("is_international", sa.Boolean, nullable=False, server_default="false"))

    # ── SO: incoterms + exchange rate ─────────────────────────────────
    op.add_column("sales_orders", sa.Column("exchange_rate", sa.Numeric(14, 6), nullable=True))
    op.add_column("sales_orders", sa.Column("incoterm", sa.String(10), nullable=True))
    op.add_column("sales_orders", sa.Column("origin_country", sa.String(3), nullable=True))
    op.add_column("sales_orders", sa.Column("destination_country", sa.String(3), nullable=True))
    op.add_column("sales_orders", sa.Column("is_international", sa.Boolean, nullable=False, server_default="false"))
    op.add_column("sales_orders", sa.Column("carrier_name", sa.String(150), nullable=True))
    op.add_column("sales_orders", sa.Column("tracking_number", sa.String(100), nullable=True))
    op.add_column("sales_orders", sa.Column("tracking_url", sa.String(500), nullable=True))

    # ── Shipment Documents (guías de remisión, BL, AWB) ───────────────
    op.create_table(
        "shipment_documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("document_type", sa.String(30), nullable=False),  # remision, bl, awb, carta_porte, guia_terrestre
        sa.Column("document_number", sa.String(100), nullable=False),
        sa.Column("purchase_order_id", sa.String(36), sa.ForeignKey("purchase_orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("sales_order_id", sa.String(36), sa.ForeignKey("sales_orders.id", ondelete="SET NULL"), nullable=True),
        # Carrier info
        sa.Column("carrier_name", sa.String(150), nullable=True),
        sa.Column("carrier_code", sa.String(50), nullable=True),
        sa.Column("vehicle_plate", sa.String(20), nullable=True),
        sa.Column("driver_name", sa.String(150), nullable=True),
        sa.Column("driver_id_number", sa.String(30), nullable=True),
        # Route
        sa.Column("origin_address", sa.Text, nullable=True),
        sa.Column("destination_address", sa.Text, nullable=True),
        sa.Column("origin_city", sa.String(100), nullable=True),
        sa.Column("destination_city", sa.String(100), nullable=True),
        sa.Column("origin_country", sa.String(3), nullable=True),
        sa.Column("destination_country", sa.String(3), nullable=True),
        # Maritime/Air specifics
        sa.Column("vessel_name", sa.String(150), nullable=True),
        sa.Column("voyage_number", sa.String(50), nullable=True),
        sa.Column("container_number", sa.String(50), nullable=True),
        sa.Column("container_type", sa.String(20), nullable=True),  # 20ft, 40ft, 40hc, reefer
        sa.Column("seal_number", sa.String(50), nullable=True),
        sa.Column("flight_number", sa.String(20), nullable=True),
        # Cargo
        sa.Column("total_packages", sa.Integer, nullable=True),
        sa.Column("total_weight_kg", sa.Numeric(12, 4), nullable=True),
        sa.Column("total_volume_m3", sa.Numeric(12, 4), nullable=True),
        sa.Column("cargo_description", sa.Text, nullable=True),
        sa.Column("declared_value", sa.Numeric(14, 2), nullable=True),
        sa.Column("declared_currency", sa.String(3), nullable=True),
        # Dates
        sa.Column("issued_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("shipped_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("estimated_arrival", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_arrival", sa.DateTime(timezone=True), nullable=True),
        # Status
        sa.Column("status", sa.String(30), nullable=False, server_default="draft"),  # draft, issued, in_transit, delivered, canceled
        sa.Column("tracking_number", sa.String(100), nullable=True),
        sa.Column("tracking_url", sa.String(500), nullable=True),
        # Blockchain
        sa.Column("anchor_hash", sa.String(64), nullable=True),
        sa.Column("anchor_status", sa.String(20), nullable=False, server_default="none"),
        sa.Column("anchor_tx_sig", sa.String(128), nullable=True),
        # Meta
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("file_url", sa.String(500), nullable=True),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_shipment_docs_tenant", "shipment_documents", ["tenant_id"])
    op.create_index("ix_shipment_docs_type", "shipment_documents", ["document_type"])
    op.create_index("ix_shipment_docs_po", "shipment_documents", ["purchase_order_id"])
    op.create_index("ix_shipment_docs_so", "shipment_documents", ["sales_order_id"])
    op.create_index("ix_shipment_docs_number", "shipment_documents", ["tenant_id", "document_number"])

    # ── Trade Documents (certificados, DEX, DIM, fitosanitarios) ──────
    op.create_table(
        "trade_documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("document_type", sa.String(50), nullable=False),  # cert_origen, fitosanitario, invima, dex, dim, factura_comercial, packing_list, insurance_cert
        sa.Column("document_number", sa.String(100), nullable=True),
        sa.Column("purchase_order_id", sa.String(36), sa.ForeignKey("purchase_orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("sales_order_id", sa.String(36), sa.ForeignKey("sales_orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("shipment_document_id", sa.String(36), sa.ForeignKey("shipment_documents.id", ondelete="SET NULL"), nullable=True),
        # Document details
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("issuing_authority", sa.String(255), nullable=True),  # DIAN, ICA, INVIMA, Cámara de Comercio
        sa.Column("issuing_country", sa.String(3), nullable=True),
        sa.Column("issued_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expiry_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),  # pending, approved, rejected, expired
        # Content
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("content_data", JSONB, nullable=False, server_default="{}"),  # structured data (HS codes, product list, etc.)
        sa.Column("file_url", sa.String(500), nullable=True),
        sa.Column("file_hash", sa.String(64), nullable=True),  # SHA-256 of the file for integrity verification
        # Trade specifics
        sa.Column("hs_code", sa.String(20), nullable=True),  # Código arancelario
        sa.Column("fob_value", sa.Numeric(14, 2), nullable=True),
        sa.Column("cif_value", sa.Numeric(14, 2), nullable=True),
        sa.Column("currency", sa.String(3), nullable=True),
        # Blockchain anchoring
        sa.Column("anchor_hash", sa.String(64), nullable=True),
        sa.Column("anchor_status", sa.String(20), nullable=False, server_default="none"),
        sa.Column("anchor_tx_sig", sa.String(128), nullable=True),
        sa.Column("anchored_at", sa.DateTime(timezone=True), nullable=True),
        # Meta
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_trade_docs_tenant", "trade_documents", ["tenant_id"])
    op.create_index("ix_trade_docs_type", "trade_documents", ["document_type"])
    op.create_index("ix_trade_docs_po", "trade_documents", ["purchase_order_id"])
    op.create_index("ix_trade_docs_so", "trade_documents", ["sales_order_id"])
    op.create_index("ix_trade_docs_shipment", "trade_documents", ["shipment_document_id"])
    op.create_index("ix_trade_docs_anchor", "trade_documents", ["anchor_status"])


def downgrade() -> None:
    op.drop_table("trade_documents")
    op.drop_table("shipment_documents")
    for col in ["tracking_url", "tracking_number", "carrier_name", "is_international",
                 "destination_country", "origin_country", "incoterm", "exchange_rate"]:
        op.drop_column("sales_orders", col)
    for col in ["is_international", "port_of_discharge", "port_of_loading",
                 "destination_country", "origin_country", "incoterm", "exchange_rate", "currency"]:
        op.drop_column("purchase_orders", col)
