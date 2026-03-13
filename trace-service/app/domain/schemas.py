"""Pydantic v2 request/response models."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from app.domain.types import AssetState, EventType, WalletStatus


# ─── Shared ───────────────────────────────────────────────────────────────────

class OrmBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ─── Tenant ───────────────────────────────────────────────────────────────────

class TenantCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r'^[a-z0-9_-]+$')


class TenantResponse(OrmBase):
    id: uuid.UUID
    name: str
    slug: str
    status: str
    created_at: datetime
    updated_at: datetime


class MerkleTreeResponse(OrmBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    tree_address: str
    tree_authority: str
    max_depth: int
    max_buffer_size: int
    canopy_depth: int
    leaf_count: int
    helius_tree_id: str | None
    create_tx_sig: str | None
    is_simulated: bool
    created_at: datetime
    updated_at: datetime


# ─── Taxonomy — CustodianType ──────────────────────────────────────────────────

class CustodianTypeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=50, pattern=r'^[a-z0-9_-]+$')
    color: str = Field(default="#6366f1")
    icon: str = Field(default="building")
    description: str | None = None
    sort_order: int = Field(default=0)


class CustodianTypeUpdate(BaseModel):
    name: str | None = None
    color: str | None = None
    icon: str | None = None
    description: str | None = None
    sort_order: int | None = None


class CustodianTypeResponse(OrmBase):
    id: uuid.UUID
    name: str
    slug: str
    color: str
    icon: str
    description: str | None
    sort_order: int
    created_at: datetime
    updated_at: datetime


# ─── Taxonomy — Organization ───────────────────────────────────────────────────

class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    custodian_type_id: uuid.UUID
    description: str | None = None
    tags: list[str] = Field(default_factory=list)


class OrganizationUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    status: str | None = None


class OrganizationResponse(OrmBase):
    id: uuid.UUID
    name: str
    custodian_type_id: uuid.UUID
    custodian_type: CustodianTypeResponse | None = None
    description: str | None
    tags: list[str]
    status: str
    wallet_count: int = 0
    created_at: datetime
    updated_at: datetime


class OrganizationListResponse(BaseModel):
    items: list[OrganizationResponse]
    total: int


# ─── Registry Wallet ──────────────────────────────────────────────────────────

class WalletCreate(BaseModel):
    wallet_pubkey: str = Field(..., min_length=32, max_length=64, description="Solana public key")
    tags: list[str] = Field(default_factory=list)
    status: WalletStatus = WalletStatus.ACTIVE
    name: str | None = None
    organization_id: uuid.UUID | None = None


class WalletGenerateRequest(BaseModel):
    tags: list[str] = Field(default_factory=list)
    status: WalletStatus = WalletStatus.ACTIVE
    name: str | None = None
    organization_id: uuid.UUID | None = None


class WalletUpdate(BaseModel):
    tags: list[str] | None = None
    status: WalletStatus | None = None
    name: str | None = None
    organization_id: uuid.UUID | None = None


class WalletResponse(OrmBase):
    id: uuid.UUID
    wallet_pubkey: str
    tags: list[str]
    status: WalletStatus
    name: str | None = None
    organization_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime


class WalletListResponse(BaseModel):
    items: list[WalletResponse]
    total: int


# ─── Assets ───────────────────────────────────────────────────────────────────

class AssetCreate(BaseModel):
    asset_mint: str = Field(..., min_length=1, max_length=64, description="NFT mint address")
    product_type: str = Field(..., min_length=1, max_length=100)
    metadata: dict[str, Any] = Field(default_factory=dict)
    initial_custodian_wallet: str = Field(..., description="Must be allowlisted active wallet")

class AssetMintRequest(BaseModel):
    product_type: str = Field(..., min_length=1, max_length=100)
    metadata: dict[str, Any] = Field(default_factory=dict)
    initial_custodian_wallet: str = Field(..., description="Must be allowlisted active wallet")


class AssetResponse(OrmBase):
    id: uuid.UUID
    asset_mint: str
    product_type: str
    # metadata_ is the Python attr on the ORM model (avoids Base.metadata conflict)
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("metadata_", "metadata"),
    )
    current_custodian_wallet: str
    state: AssetState
    last_event_hash: str | None
    # Blockchain / cNFT fields
    blockchain_asset_id: str | None = None
    blockchain_tree_address: str | None = None
    blockchain_tx_signature: str | None = None
    blockchain_status: str = "SKIPPED"
    is_compressed: bool = False
    created_at: datetime
    updated_at: datetime


class AssetListResponse(BaseModel):
    items: list[AssetResponse]
    total: int


# ─── Custody Events ───────────────────────────────────────────────────────────

class LocationData(BaseModel):
    lat: float | None = Field(None, ge=-90, le=90)
    lng: float | None = Field(None, ge=-180, le=180)
    label: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class HandoffRequest(BaseModel):
    to_wallet: str = Field(..., description="Must be allowlisted active wallet")
    location: LocationData | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class ArrivedRequest(BaseModel):
    location: LocationData | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class LoadedRequest(BaseModel):
    location: LocationData | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class QCRequest(BaseModel):
    result: Literal["pass", "fail"] = Field(..., description="QC result: pass or fail")
    notes: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class ReleaseRequest(BaseModel):
    external_wallet: str = Field(..., description="External wallet — not required to be allowlisted")
    reason: str = Field(..., min_length=1)
    data: dict[str, Any] = Field(default_factory=dict)


class BurnRequest(BaseModel):
    reason: str = Field(..., min_length=1)
    data: dict[str, Any] = Field(default_factory=dict)


class CustodyEventResponse(OrmBase):
    id: uuid.UUID
    asset_id: uuid.UUID
    event_type: EventType
    from_wallet: str | None
    to_wallet: str | None
    timestamp: datetime
    location: dict[str, Any] | None
    data: dict[str, Any]
    prev_event_hash: str | None
    event_hash: str
    solana_tx_sig: str | None
    anchored: bool
    anchor_attempts: int
    anchor_last_error: str | None
    created_at: datetime


class CustodyEventListResponse(BaseModel):
    items: list[CustodyEventResponse]
    total: int


# ─── Solana ───────────────────────────────────────────────────────────────────

class SolanaAccountResponse(BaseModel):
    pubkey: str
    lamports: int | None = None
    owner: str | None = None
    executable: bool | None = None
    data: Any = None
    simulated: bool = False


class SolanaTxResponse(BaseModel):
    signature: str
    slot: int | None = None
    confirmations: int | None = None
    err: Any = None
    simulated: bool = False


# ─── Health ───────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str


class ReadyResponse(BaseModel):
    status: str
    checks: dict[str, str]
