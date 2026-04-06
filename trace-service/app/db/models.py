"""SQLAlchemy ORM models."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


# ─── Tenant ───────────────────────────────────────────────────────────────────

class Tenant(Base):
    __tablename__ = "tenants"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_tenants_slug"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="active")
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    organizations: Mapped[list["Organization"]] = relationship(
        "Organization", back_populates="tenant", lazy="noload"
    )
    wallets: Mapped[list["RegistryWallet"]] = relationship(
        "RegistryWallet", back_populates="tenant", lazy="noload"
    )
    merkle_tree: Mapped["TenantMerkleTree | None"] = relationship(
        "TenantMerkleTree", back_populates="tenant", lazy="noload", uselist=False
    )


class TenantMerkleTree(Base):
    __tablename__ = "tenant_merkle_trees"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    tree_address: Mapped[str] = mapped_column(Text, nullable=False)
    tree_authority: Mapped[str] = mapped_column(Text, nullable=False)
    max_depth: Mapped[int] = mapped_column(Integer, nullable=False, default=14)
    max_buffer_size: Mapped[int] = mapped_column(Integer, nullable=False, default=64)
    canopy_depth: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    leaf_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    helius_tree_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    create_tx_sig: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_simulated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    tenant: Mapped["Tenant"] = relationship(
        "Tenant", back_populates="merkle_tree", lazy="noload"
    )


# ─── Anchor Requests (Anchoring-as-a-Service) ────────────────────────────────

class AnchorRequest(Base):
    """
    Generic anchoring request from any microservice.
    Stores a SHA-256 hash and tracks its Solana Memo Program anchoring lifecycle.
    """
    __tablename__ = "anchor_requests"
    __table_args__ = (
        Index("ix_anchor_requests_status", "anchor_status"),
        Index("ix_anchor_requests_hash", "payload_hash"),
        Index("ix_anchor_requests_tenant", "tenant_id"),
        Index(
            "ix_anchor_requests_source",
            "source_service", "source_entity_type", "source_entity_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_service: Mapped[str] = mapped_column(Text, nullable=False)
    source_entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_entity_id: Mapped[str] = mapped_column(Text, nullable=False)
    payload_hash: Mapped[str] = mapped_column(Text, nullable=False)
    anchor_status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    solana_tx_sig: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    callback_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=_utcnow
    )
    anchored_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )


# ─── Anchor Rules ────────────────────────────────────────────────────────────

class AnchorRule(Base):
    """Configurable rules that define what supply chain events get anchored on blockchain."""
    __tablename__ = "anchor_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    trigger_event: Mapped[str] = mapped_column(Text, nullable=False)
    conditions: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    actions: Mapped[dict] = mapped_column(JSONB, nullable=False, default=lambda: {"anchor": True})
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)


# ─── Shipment Documents ──────────────────────────────────────────────────────

class ShipmentDocument(Base):
    """Transport documents: remision, BL, AWB, carta porte, guia terrestre."""
    __tablename__ = "shipment_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    document_type: Mapped[str] = mapped_column(Text, nullable=False)
    document_number: Mapped[str] = mapped_column(Text, nullable=False)
    carrier_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    carrier_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    vehicle_plate: Mapped[str | None] = mapped_column(Text, nullable=True)
    driver_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    driver_id_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    origin_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    destination_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    origin_city: Mapped[str | None] = mapped_column(Text, nullable=True)
    destination_city: Mapped[str | None] = mapped_column(Text, nullable=True)
    origin_country: Mapped[str | None] = mapped_column(Text, nullable=True)
    destination_country: Mapped[str | None] = mapped_column(Text, nullable=True)
    vessel_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    voyage_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    container_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    container_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    seal_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    flight_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_packages: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_weight_kg: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    total_volume_m3: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    cargo_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    declared_value: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    declared_currency: Mapped[str | None] = mapped_column(Text, nullable=True)
    issued_date: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    shipped_date: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    estimated_arrival: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    actual_arrival: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="draft")
    tracking_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    tracking_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    anchor_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    anchor_status: Mapped[str] = mapped_column(Text, nullable=False, default="none")
    anchor_tx_sig: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Freight costs
    freight_cost: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    insurance_cost: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    handling_cost: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    customs_cost: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    other_costs: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    total_logistics_cost: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    cost_currency: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)


# ─── Trade Documents ─────────────────────────────────────────────────────────

class TradeDocument(Base):
    """Trade/compliance documents: cert origen, fitosanitario, INVIMA, DEX, DIM."""
    __tablename__ = "trade_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    document_type: Mapped[str] = mapped_column(Text, nullable=False)
    document_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    shipment_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shipment_documents.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    issuing_authority: Mapped[str | None] = mapped_column(Text, nullable=True)
    issuing_country: Mapped[str | None] = mapped_column(Text, nullable=True)
    issued_date: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    expiry_date: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    file_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    hs_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    fob_value: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    cif_value: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(Text, nullable=True)
    anchor_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    anchor_status: Mapped[str] = mapped_column(Text, nullable=False, default="none")
    anchor_tx_sig: Mapped[str | None] = mapped_column(Text, nullable=True)
    anchored_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    reference_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    shipment_document: Mapped["ShipmentDocument | None"] = relationship("ShipmentDocument", lazy="noload")


# ─── CustodianType ────────────────────────────────────────────────────────────

class CustodianType(Base):
    __tablename__ = "custodian_types"
    __table_args__ = (
        UniqueConstraint("slug", "tenant_id", name="uq_custodian_types_slug_tenant"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(Text, nullable=False)
    color: Mapped[str] = mapped_column(Text, nullable=False, default="#6366f1")
    icon: Mapped[str] = mapped_column(Text, nullable=False, default="building")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    organizations: Mapped[list["Organization"]] = relationship(
        "Organization", back_populates="custodian_type", lazy="noload"
    )


class Organization(Base):
    __tablename__ = "organizations"
    __table_args__ = (
        Index("ix_organizations_type", "custodian_type_id"),
        Index("ix_organizations_status", "status"),
        Index("ix_organizations_tenant", "tenant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    custodian_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("custodian_types.id", ondelete="RESTRICT"),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default="{}"
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, default="active")
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    tenant: Mapped["Tenant"] = relationship(
        "Tenant", back_populates="organizations", lazy="noload"
    )
    custodian_type: Mapped["CustodianType"] = relationship(
        "CustodianType", back_populates="organizations", lazy="noload"
    )
    wallets: Mapped[list["RegistryWallet"]] = relationship(
        "RegistryWallet", back_populates="organization", lazy="noload"
    )


class RegistryWallet(Base):
    __tablename__ = "registry_wallets"
    __table_args__ = (
        UniqueConstraint("wallet_pubkey", name="uq_registry_wallets_pubkey"),
        Index("ix_registry_wallets_status", "status"),
        Index("ix_registry_wallets_org", "organization_id"),
        Index("ix_registry_wallets_tenant", "tenant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
    )
    wallet_pubkey: Mapped[str] = mapped_column(Text, nullable=False)
    encrypted_private_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
    )
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default="{}"
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    tenant: Mapped["Tenant"] = relationship(
        "Tenant", back_populates="wallets", lazy="noload"
    )
    organization: Mapped["Organization | None"] = relationship(
        "Organization", back_populates="wallets", lazy="noload"
    )


class Asset(Base):
    __tablename__ = "assets"
    __table_args__ = (
        UniqueConstraint("asset_mint", name="uq_assets_mint"),
        Index("ix_assets_product_type", "product_type"),
        Index("ix_assets_custodian", "current_custodian_wallet"),
        Index("ix_assets_state", "state"),
        Index("ix_assets_tenant", "tenant_id"),
        CheckConstraint(
            "blockchain_status IN ('PENDING','CONFIRMED','FAILED','SIMULATED','SKIPPED')",
            name="ck_assets_blockchain_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
    )
    asset_mint: Mapped[str] = mapped_column(Text, nullable=False)
    product_type: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    current_custodian_wallet: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(Text, nullable=False)
    last_event_hash: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Workflow engine FK — links to tenant-scoped WorkflowState
    workflow_state_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_states.id", ondelete="SET NULL"), nullable=True
    )

    # Blockchain / cNFT fields
    blockchain_asset_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    blockchain_tree_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    blockchain_tx_signature: Mapped[str | None] = mapped_column(Text, nullable=True)
    blockchain_status: Mapped[str] = mapped_column(Text, nullable=False, default="SKIPPED")
    blockchain_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_compressed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    events: Mapped[list["CustodyEvent"]] = relationship(
        "CustodyEvent", back_populates="asset", lazy="noload"
    )


class CustodyEvent(Base):
    __tablename__ = "custody_events"
    __table_args__ = (
        UniqueConstraint("event_hash", name="uq_custody_events_hash"),
        Index("ix_custody_events_asset_timestamp", "asset_id", "timestamp"),
        Index("ix_custody_events_anchored", "anchored"),
        Index("ix_custody_events_tenant", "tenant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="RESTRICT"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    from_wallet: Mapped[str | None] = mapped_column(Text, nullable=True)
    to_wallet: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    location: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    prev_event_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_hash: Mapped[str] = mapped_column(Text, nullable=False)
    solana_tx_sig: Mapped[str | None] = mapped_column(Text, nullable=True)
    anchored: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    anchor_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    anchor_last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Phase 1A additions
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    shipment_leg_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    # Proof of Delivery evidence
    evidence_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=_utcnow
    )

    asset: Mapped["Asset"] = relationship("Asset", back_populates="events", lazy="noload")
    document_links: Mapped[list["EventDocumentLink"]] = relationship(
        "EventDocumentLink", back_populates="event", lazy="noload"
    )


# ─── Media Module (centralized file library) ────────────────────────────────

class MediaFile(Base):
    """Centralized file storage — the media library."""
    __tablename__ = "media_files"
    __table_args__ = (
        Index("ix_media_files_tenant", "tenant_id"),
        Index("ix_media_files_category", "category"),
        Index("ix_media_files_document_type", "document_type"),
        Index("ix_media_files_hash", "file_hash"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    original_filename: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(Text, nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    file_hash: Mapped[str] = mapped_column(Text, nullable=False)
    storage_backend: Mapped[str] = mapped_column(Text, nullable=False, default="local")
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(Text, nullable=False, default="general")
    document_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default="{}")
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    uploaded_by: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    event_links: Mapped[list["EventDocumentLink"]] = relationship(
        "EventDocumentLink", back_populates="media_file", lazy="noload"
    )


class EventDocumentLink(Base):
    """N:M link between custody events and media files."""
    __tablename__ = "event_document_links"
    __table_args__ = (
        UniqueConstraint("event_id", "media_file_id", name="uq_event_doc_links_event_media"),
        Index("ix_event_doc_links_event", "event_id"),
        Index("ix_event_doc_links_asset", "asset_id"),
        Index("ix_event_doc_links_media", "media_file_id"),
        Index("ix_event_doc_links_tenant", "tenant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("custody_events.id", ondelete="CASCADE"), nullable=False
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    media_file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("media_files.id", ondelete="CASCADE"), nullable=False
    )
    document_type: Mapped[str] = mapped_column(Text, nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    compliance_source: Mapped[str | None] = mapped_column(Text, nullable=True)
    linked_by: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=_utcnow)

    event: Mapped["CustodyEvent"] = relationship("CustodyEvent", back_populates="document_links", lazy="noload")
    media_file: Mapped["MediaFile"] = relationship("MediaFile", back_populates="event_links", lazy="joined")


# ─── Workflow Engine (per-tenant configurable state machine) ──────────────────

class WorkflowState(Base):
    """Tenant-scoped asset states. Replaces hardcoded AssetState enum."""
    __tablename__ = "workflow_states"
    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_workflow_states_tenant_slug"),
        Index("ix_workflow_states_tenant", "tenant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # RESTRICT (matches the rest of the tenant-scoped tables). Deleting a
    # tenant should require explicit cascade in code, not silent FK behavior.
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    slug: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    color: Mapped[str] = mapped_column(Text, nullable=False, default="#6366f1")
    icon: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_initial: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_terminal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)


class WorkflowTransition(Base):
    """Allowed state transitions per tenant. from_state_id=NULL means wildcard (any state)."""
    __tablename__ = "workflow_transitions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "from_state_id", "to_state_id", name="uq_workflow_transitions_pair"),
        Index("ix_workflow_transitions_tenant", "tenant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    from_state_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_states.id", ondelete="CASCADE"), nullable=True
    )
    to_state_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_states.id", ondelete="CASCADE"), nullable=False
    )
    event_type_slug: Mapped[str | None] = mapped_column(Text, nullable=True)
    label: Mapped[str | None] = mapped_column(Text, nullable=True)
    requires_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=_utcnow)

    from_state: Mapped["WorkflowState | None"] = relationship(
        "WorkflowState", foreign_keys=[from_state_id], lazy="joined"
    )
    to_state: Mapped["WorkflowState"] = relationship(
        "WorkflowState", foreign_keys=[to_state_id], lazy="joined"
    )


class WorkflowEventType(Base):
    """Tenant-scoped event types. Replaces hardcoded EventType enum."""
    __tablename__ = "workflow_event_types"
    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_workflow_event_types_tenant_slug"),
        Index("ix_workflow_event_types_tenant", "tenant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    slug: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon: Mapped[str] = mapped_column(Text, nullable=False, default="circle")
    color: Mapped[str] = mapped_column(Text, nullable=False, default="#6366f1")
    is_informational: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_wallet: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_notes: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_reason: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    data_schema: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    required_documents: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    compliance_required_documents: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)


# ─── Event Type Configuration (admin-managed) ─────────────────────────────────

class EventTypeConfig(Base):
    """
    Admin-configurable event types per tenant.
    System types (is_system=True) are seeded and cannot be deleted.
    Admins can create custom types and customize labels/colors/transitions.
    """
    __tablename__ = "event_type_configs"
    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_event_type_configs_tenant_slug"),
        Index("ix_event_type_configs_tenant", "tenant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    slug: Mapped[str] = mapped_column(Text, nullable=False)              # e.g. "CUSTOMS_HOLD"
    name: Mapped[str] = mapped_column(Text, nullable=False)              # e.g. "Retención Aduana"
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon: Mapped[str] = mapped_column(Text, nullable=False, default="circle")
    color: Mapped[str] = mapped_column(Text, nullable=False, default="#6366f1")
    # State machine configuration
    from_states: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list
    )  # which asset states allow this event
    to_state: Mapped[str | None] = mapped_column(Text, nullable=True)    # resulting state (null = informational)
    # Behavior flags
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_informational: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_wallet: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_notes: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_reason: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )
