"""Shipment and trade document models for logistics and international commerce."""
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.purchase_order import PurchaseOrder
    from app.db.models.sales_order import SalesOrder


class ShipmentDocument(Base):
    """Transport documents: guías de remisión, BL, AWB, carta porte, guía terrestre."""
    __tablename__ = "shipment_documents"

    id:               Mapped[str]            = mapped_column(String(36), primary_key=True)
    tenant_id:        Mapped[str]            = mapped_column(String(255), nullable=False)
    document_type:    Mapped[str]            = mapped_column(String(30), nullable=False)
    document_number:  Mapped[str]            = mapped_column(String(100), nullable=False)
    purchase_order_id: Mapped[str | None]    = mapped_column(
        String(36), ForeignKey("purchase_orders.id", ondelete="SET NULL"), nullable=True)
    sales_order_id:   Mapped[str | None]     = mapped_column(
        String(36), ForeignKey("sales_orders.id", ondelete="SET NULL"), nullable=True)

    # Carrier
    carrier_name:     Mapped[str | None]     = mapped_column(String(150), nullable=True)
    carrier_code:     Mapped[str | None]     = mapped_column(String(50), nullable=True)
    vehicle_plate:    Mapped[str | None]     = mapped_column(String(20), nullable=True)
    driver_name:      Mapped[str | None]     = mapped_column(String(150), nullable=True)
    driver_id_number: Mapped[str | None]     = mapped_column(String(30), nullable=True)

    # Route
    origin_address:      Mapped[str | None]  = mapped_column(Text, nullable=True)
    destination_address: Mapped[str | None]  = mapped_column(Text, nullable=True)
    origin_city:         Mapped[str | None]  = mapped_column(String(100), nullable=True)
    destination_city:    Mapped[str | None]  = mapped_column(String(100), nullable=True)
    origin_country:      Mapped[str | None]  = mapped_column(String(3), nullable=True)
    destination_country: Mapped[str | None]  = mapped_column(String(3), nullable=True)

    # Maritime/Air
    vessel_name:      Mapped[str | None]     = mapped_column(String(150), nullable=True)
    voyage_number:    Mapped[str | None]     = mapped_column(String(50), nullable=True)
    container_number: Mapped[str | None]     = mapped_column(String(50), nullable=True)
    container_type:   Mapped[str | None]     = mapped_column(String(20), nullable=True)
    seal_number:      Mapped[str | None]     = mapped_column(String(50), nullable=True)
    flight_number:    Mapped[str | None]     = mapped_column(String(20), nullable=True)

    # Cargo
    total_packages:   Mapped[int | None]     = mapped_column(Integer, nullable=True)
    total_weight_kg:  Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    total_volume_m3:  Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    cargo_description: Mapped[str | None]    = mapped_column(Text, nullable=True)
    declared_value:   Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    declared_currency: Mapped[str | None]    = mapped_column(String(3), nullable=True)

    # Dates
    issued_date:       Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    shipped_date:      Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    estimated_arrival: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_arrival:    Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Status & tracking
    status:           Mapped[str]            = mapped_column(String(30), nullable=False, server_default="draft")
    tracking_number:  Mapped[str | None]     = mapped_column(String(100), nullable=True)
    tracking_url:     Mapped[str | None]     = mapped_column(String(500), nullable=True)

    # Blockchain
    anchor_hash:      Mapped[str | None]     = mapped_column(String(64), nullable=True)
    anchor_status:    Mapped[str]            = mapped_column(String(20), nullable=False, server_default="none")
    anchor_tx_sig:    Mapped[str | None]     = mapped_column(String(128), nullable=True)

    # Meta
    metadata_:        Mapped[dict]           = mapped_column("metadata", JSONB, nullable=False, server_default="{}")
    notes:            Mapped[str | None]     = mapped_column(Text, nullable=True)
    file_url:         Mapped[str | None]     = mapped_column(String(500), nullable=True)
    created_by:       Mapped[str | None]     = mapped_column(String(255), nullable=True)
    created_at:       Mapped[DateTime]       = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:       Mapped[DateTime]       = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    purchase_order: Mapped[PurchaseOrder | None] = relationship("PurchaseOrder", foreign_keys=[purchase_order_id])
    sales_order:    Mapped[SalesOrder | None]    = relationship("SalesOrder", foreign_keys=[sales_order_id])
    trade_documents: Mapped[list[TradeDocument]] = relationship("TradeDocument", back_populates="shipment_document")

    __table_args__ = (
        Index("ix_shipment_docs_tenant", "tenant_id"),
        Index("ix_shipment_docs_type", "document_type"),
        Index("ix_shipment_docs_po", "purchase_order_id"),
        Index("ix_shipment_docs_so", "sales_order_id"),
        Index("ix_shipment_docs_number", "tenant_id", "document_number"),
    )


class TradeDocument(Base):
    """Commercial documents tied to purchase/sales orders: packing_list, commercial_invoice, bill_of_lading."""
    __tablename__ = "trade_documents"

    id:               Mapped[str]            = mapped_column(String(36), primary_key=True)
    tenant_id:        Mapped[str]            = mapped_column(String(255), nullable=False)
    document_type:    Mapped[str]            = mapped_column(String(50), nullable=False)
    document_number:  Mapped[str | None]     = mapped_column(String(100), nullable=True)
    purchase_order_id: Mapped[str | None]    = mapped_column(
        String(36), ForeignKey("purchase_orders.id", ondelete="SET NULL"), nullable=True)
    sales_order_id:   Mapped[str | None]     = mapped_column(
        String(36), ForeignKey("sales_orders.id", ondelete="SET NULL"), nullable=True)
    shipment_document_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("shipment_documents.id", ondelete="SET NULL"), nullable=True)

    # Document details
    title:            Mapped[str]            = mapped_column(String(255), nullable=False)
    issuing_authority: Mapped[str | None]    = mapped_column(String(255), nullable=True)
    issuing_country:  Mapped[str | None]     = mapped_column(String(3), nullable=True)
    issued_date:      Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expiry_date:      Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status:           Mapped[str]            = mapped_column(String(30), nullable=False, server_default="pending")

    # Content
    description:      Mapped[str | None]     = mapped_column(Text, nullable=True)
    content_data:     Mapped[dict]           = mapped_column(JSONB, nullable=False, server_default="{}")
    file_url:         Mapped[str | None]     = mapped_column(String(500), nullable=True)
    file_hash:        Mapped[str | None]     = mapped_column(String(64), nullable=True)

    # Trade specifics
    hs_code:          Mapped[str | None]     = mapped_column(String(20), nullable=True)
    fob_value:        Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    cif_value:        Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    currency:         Mapped[str | None]     = mapped_column(String(3), nullable=True)

    # Blockchain
    anchor_hash:      Mapped[str | None]     = mapped_column(String(64), nullable=True)
    anchor_status:    Mapped[str]            = mapped_column(String(20), nullable=False, server_default="none")
    anchor_tx_sig:    Mapped[str | None]     = mapped_column(String(128), nullable=True)
    anchored_at:      Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Meta
    metadata_:        Mapped[dict]           = mapped_column("metadata", JSONB, nullable=False, server_default="{}")
    notes:            Mapped[str | None]     = mapped_column(Text, nullable=True)
    created_by:       Mapped[str | None]     = mapped_column(String(255), nullable=True)
    created_at:       Mapped[DateTime]       = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:       Mapped[DateTime]       = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    shipment_document: Mapped[ShipmentDocument | None] = relationship("ShipmentDocument", back_populates="trade_documents")

    __table_args__ = (
        Index("ix_trade_docs_tenant", "tenant_id"),
        Index("ix_trade_docs_type", "document_type"),
        Index("ix_trade_docs_po", "purchase_order_id"),
        Index("ix_trade_docs_so", "sales_order_id"),
        Index("ix_trade_docs_shipment", "shipment_document_id"),
        Index("ix_trade_docs_anchor", "anchor_status"),
    )
