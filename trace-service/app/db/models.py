"""SQLAlchemy ORM models."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    ARRAY,
    Boolean,
    ForeignKey,
    Index,
    Integer,
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
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
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
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
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
    total_weight_kg: Mapped[float | None] = mapped_column(Text, nullable=True)
    total_volume_m3: Mapped[float | None] = mapped_column(Text, nullable=True)
    cargo_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    declared_value: Mapped[float | None] = mapped_column(Text, nullable=True)
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
    fob_value: Mapped[float | None] = mapped_column(Text, nullable=True)
    cif_value: Mapped[float | None] = mapped_column(Text, nullable=True)
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

    # Blockchain / cNFT fields
    blockchain_asset_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    blockchain_tree_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    blockchain_tx_signature: Mapped[str | None] = mapped_column(Text, nullable=True)
    blockchain_status: Mapped[str] = mapped_column(Text, nullable=False, default="SKIPPED")
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
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
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
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=_utcnow
    )

    asset: Mapped["Asset"] = relationship("Asset", back_populates="events", lazy="noload")


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
