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
    icon: str | None = None
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
    state: str
    workflow_state_id: uuid.UUID | None = None
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


class GenericEventRequest(BaseModel):
    """Flexible event request for all event types (system + custom).

    Accepts any event_type slug configured in event_type_configs for the tenant.
    System types: CREATED, HANDOFF, ARRIVED, LOADED, QC, RELEASED, BURN, etc.
    Custom types: any slug created by the tenant admin.
    """
    event_type: str = Field(..., min_length=1, max_length=50, description="Event type slug")
    to_wallet: str | None = Field(None, description="Target wallet (for HANDOFF-like events)")
    location: LocationData | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = None
    result: Literal["pass", "fail"] | None = Field(None, description="For QC/INSPECTION events")
    reason: str | None = Field(None, description="For RELEASED/BURN/DAMAGED events")
    parent_event_id: uuid.UUID | None = Field(
        None,
        description=(
            "Optional parent event for hierarchical timeline. "
            "If omitted, informational events auto-link to the most recent "
            "transition for the same asset."
        ),
    )


class CustodyEventResponse(OrmBase):
    id: uuid.UUID
    asset_id: uuid.UUID
    event_type: str  # system EventType or custom slug from event_type_configs
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
    notes: str | None = None
    evidence_url: str | None = None
    evidence_hash: str | None = None
    evidence_type: str | None = None
    parent_event_id: uuid.UUID | None = None
    created_at: datetime


class CustodyEventListResponse(BaseModel):
    items: list[CustodyEventResponse]
    total: int


# ─── Event Type Config (admin-managed) ────────────────────────────────────────

class EventTypeConfigCreate(BaseModel):
    slug: str = Field(..., min_length=1, max_length=50, pattern=r'^[A-Z0-9_]+$')
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    icon: str = Field(default="circle")
    color: str = Field(default="#6366f1")
    from_states: list[str] = Field(default_factory=list)
    to_state: str | None = None
    is_informational: bool = False
    requires_wallet: bool = False
    requires_notes: bool = False
    requires_reason: bool = False
    requires_admin: bool = False
    sort_order: int = 0


class EventTypeConfigUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    icon: str | None = None
    color: str | None = None
    from_states: list[str] | None = None
    to_state: str | None = None
    is_informational: bool | None = None
    requires_wallet: bool | None = None
    requires_notes: bool | None = None
    requires_reason: bool | None = None
    requires_admin: bool | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class EventTypeConfigResponse(OrmBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    slug: str
    name: str
    description: str | None
    icon: str | None = None
    color: str
    from_states: list[str]
    to_state: str | None
    is_system: bool
    is_informational: bool
    requires_wallet: bool
    requires_notes: bool
    requires_reason: bool
    requires_admin: bool
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ─── Workflow Engine ─────────────────────────────────────────────────────────

class WorkflowStateCreate(BaseModel):
    slug: str = Field(..., min_length=1, max_length=50, pattern=r'^[a-z0-9_]+$')
    label: str = Field(..., min_length=1, max_length=100)
    color: str = Field(default="#6366f1")
    icon: str | None = None
    is_initial: bool = False
    is_terminal: bool = False
    sort_order: int = 0


class WorkflowStateUpdate(BaseModel):
    label: str | None = None
    color: str | None = None
    icon: str | None = None
    is_initial: bool | None = None
    is_terminal: bool | None = None
    sort_order: int | None = None


class WorkflowStateResponse(OrmBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    slug: str
    label: str
    color: str
    icon: str | None
    is_initial: bool
    is_terminal: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime


class WorkflowStateReorderRequest(BaseModel):
    """List of state IDs in desired order."""
    state_ids: list[uuid.UUID] = Field(..., min_length=1)


class WorkflowTransitionCreate(BaseModel):
    from_state_id: uuid.UUID | None = None  # null = wildcard (any non-terminal state)
    to_state_id: uuid.UUID
    event_type_slug: str | None = None
    label: str | None = None
    requires_data: dict[str, Any] | None = None


class WorkflowTransitionResponse(OrmBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    from_state_id: uuid.UUID | None
    from_state: WorkflowStateResponse | None = None
    to_state_id: uuid.UUID
    to_state: WorkflowStateResponse | None = None
    event_type_slug: str | None
    label: str | None
    requires_data: dict[str, Any] | None
    created_at: datetime


class WorkflowEventTypeCreate(BaseModel):
    slug: str = Field(..., min_length=1, max_length=50, pattern=r'^[A-Z0-9_]+$')
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    icon: str = Field(default="circle")
    color: str = Field(default="#6366f1")
    is_informational: bool = False
    requires_wallet: bool = False
    requires_notes: bool = False
    requires_reason: bool = False
    requires_admin: bool = False
    data_schema: dict[str, Any] | None = None
    required_documents: dict[str, Any] | None = None
    compliance_required_documents: dict[str, Any] | None = None
    sort_order: int = 0


class WorkflowEventTypeUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    icon: str | None = None
    color: str | None = None
    is_informational: bool | None = None
    requires_wallet: bool | None = None
    requires_notes: bool | None = None
    requires_reason: bool | None = None
    requires_admin: bool | None = None
    data_schema: dict[str, Any] | None = None
    required_documents: dict[str, Any] | None = None
    compliance_required_documents: dict[str, Any] | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class WorkflowEventTypeResponse(OrmBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    slug: str
    name: str
    description: str | None
    icon: str | None = None
    color: str
    is_informational: bool
    requires_wallet: bool
    requires_notes: bool
    requires_reason: bool
    requires_admin: bool
    data_schema: dict[str, Any] | None
    required_documents: dict[str, Any] | None
    compliance_required_documents: dict[str, Any] | None
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ─── Available Actions (workflow-driven) ─────────────────────────────────────

class ActionStateInfo(BaseModel):
    slug: str
    label: str
    color: str
    icon: str | None = None
    is_terminal: bool = False


class ActionEventTypeInfo(BaseModel):
    slug: str
    name: str
    description: str | None = None
    icon: str | None = None
    color: str
    is_informational: bool = False
    requires_wallet: bool = False
    requires_notes: bool = False
    requires_reason: bool = False
    requires_admin: bool = False


class AvailableActionResponse(BaseModel):
    transition_id: str
    to_state: ActionStateInfo | None = None
    event_type_slug: str | None = None
    label: str | None = None
    event_type: ActionEventTypeInfo | None = None


INDUSTRY_PRESETS = {
    "supply_chain": {
        "states": [
            {"slug": "in_custody", "label": "En custodia", "color": "#8b5cf6", "icon": "package", "is_initial": True, "sort_order": 0},
            {"slug": "in_transit", "label": "En tránsito", "color": "#f59e0b", "icon": "truck", "sort_order": 1},
            {"slug": "loaded", "label": "Cargado", "color": "#3b82f6", "icon": "container", "sort_order": 2},
            {"slug": "qc_passed", "label": "QC aprobado", "color": "#22c55e", "icon": "check-circle", "sort_order": 3},
            {"slug": "qc_failed", "label": "QC fallido", "color": "#ef4444", "icon": "x-circle", "sort_order": 4},
            {"slug": "customs_hold", "label": "Retención aduana", "color": "#f97316", "icon": "shield-alert", "sort_order": 5},
            {"slug": "damaged", "label": "Dañado", "color": "#dc2626", "icon": "alert-triangle", "sort_order": 6},
            {"slug": "sealed", "label": "Sellado", "color": "#06b6d4", "icon": "lock", "sort_order": 7},
            {"slug": "delivered", "label": "Entregado", "color": "#059669", "icon": "check-circle-2", "sort_order": 8},
            {"slug": "released", "label": "Liberado", "color": "#10b981", "icon": "unlock", "is_terminal": True, "sort_order": 9},
            {"slug": "burned", "label": "Entrega finalizada", "color": "#6b7280", "icon": "flame", "is_terminal": True, "sort_order": 10},
            {"slug": "returned", "label": "Devuelto", "color": "#ea580c", "icon": "undo-2", "sort_order": 11},
        ],
        "transitions": [
            # HANDOFF: transferir custodia → en tránsito
            {"from": "in_custody", "to": "in_transit", "event_type_slug": "HANDOFF", "label": "Transferir custodia"},
            {"from": "in_transit", "to": "in_transit", "event_type_slug": "HANDOFF", "label": "Re-transferir"},
            {"from": "loaded", "to": "in_transit", "event_type_slug": "HANDOFF", "label": "Despachar"},
            {"from": "qc_passed", "to": "in_transit", "event_type_slug": "HANDOFF", "label": "Transferir post-QC"},
            {"from": "qc_failed", "to": "in_transit", "event_type_slug": "HANDOFF", "label": "Transferir post-QC"},
            # ARRIVED: llegada → en custodia
            {"from": "in_transit", "to": "in_custody", "event_type_slug": "ARRIVED", "label": "Registrar llegada"},
            # LOADED: cargar en transporte
            {"from": "in_custody", "to": "loaded", "event_type_slug": "LOADED", "label": "Cargar en transporte"},
            # QC: control de calidad → aprobado o fallido
            {"from": "in_custody", "to": "qc_passed", "event_type_slug": "QC", "label": "QC aprobado"},
            {"from": "in_custody", "to": "qc_failed", "event_type_slug": "QC", "label": "QC fallido"},
            {"from": "loaded", "to": "qc_passed", "event_type_slug": "QC", "label": "QC aprobado"},
            {"from": "loaded", "to": "qc_failed", "event_type_slug": "QC", "label": "QC fallido"},
            {"from": "qc_failed", "to": "qc_passed", "event_type_slug": "QC", "label": "Re-inspección OK"},
            {"from": "qc_failed", "to": "qc_failed", "event_type_slug": "QC", "label": "Re-inspección fallida"},
            # DELIVERED: entrega al destino
            {"from": "in_custody", "to": "delivered", "event_type_slug": "DELIVERED", "label": "Entregar"},
            {"from": "in_transit", "to": "delivered", "event_type_slug": "DELIVERED", "label": "Entregar"},
            {"from": "qc_passed", "to": "delivered", "event_type_slug": "DELIVERED", "label": "Entregar post-QC"},
            # BURN: completar/finalizar entrega (terminal)
            {"from": "in_custody", "to": "burned", "event_type_slug": "BURN", "label": "Finalizar entrega"},
            {"from": "in_transit", "to": "burned", "event_type_slug": "BURN", "label": "Finalizar entrega"},
            {"from": "loaded", "to": "burned", "event_type_slug": "BURN", "label": "Finalizar entrega"},
            {"from": "qc_passed", "to": "burned", "event_type_slug": "BURN", "label": "Finalizar entrega"},
            {"from": "delivered", "to": "burned", "event_type_slug": "BURN", "label": "Cerrar cadena"},
            # RELEASED: liberar del sistema (admin, terminal)
            {"from": "in_custody", "to": "released", "event_type_slug": "RELEASED", "label": "Liberar"},
            {"from": "in_transit", "to": "released", "event_type_slug": "RELEASED", "label": "Liberar"},
            {"from": "loaded", "to": "released", "event_type_slug": "RELEASED", "label": "Liberar"},
            {"from": "qc_passed", "to": "released", "event_type_slug": "RELEASED", "label": "Liberar"},
            {"from": "qc_failed", "to": "released", "event_type_slug": "RELEASED", "label": "Liberar"},
            # CUSTOMS: aduana
            {"from": "in_custody", "to": "customs_hold", "event_type_slug": "CUSTOMS_HOLD", "label": "Retener en aduana"},
            {"from": "in_transit", "to": "customs_hold", "event_type_slug": "CUSTOMS_HOLD", "label": "Retener en aduana"},
            {"from": "customs_hold", "to": "in_custody", "event_type_slug": "CUSTOMS_CLEARED", "label": "Liberar de aduana"},
            # DAMAGED
            {"from": "in_custody", "to": "damaged", "event_type_slug": "DAMAGED", "label": "Reportar daño"},
            {"from": "in_transit", "to": "damaged", "event_type_slug": "DAMAGED", "label": "Reportar daño"},
            {"from": "loaded", "to": "damaged", "event_type_slug": "DAMAGED", "label": "Reportar daño"},
            # SEALED / UNSEALED
            {"from": "loaded", "to": "sealed", "event_type_slug": "SEALED", "label": "Sellar"},
            {"from": "sealed", "to": "loaded", "event_type_slug": "UNSEALED", "label": "Remover sello"},
            # RETURN: devolución (permite retroceder)
            {"from": "delivered", "to": "returned", "event_type_slug": "RETURN", "label": "Devolver"},
            {"from": "returned", "to": "in_transit", "event_type_slug": "HANDOFF", "label": "Re-enviar"},
            {"from": "returned", "to": "in_custody", "event_type_slug": "ARRIVED", "label": "Recibir devolución"},
            # Retrocesos adicionales
            {"from": "damaged", "to": "in_custody", "event_type_slug": "ARRIVED", "label": "Recuperar"},
            {"from": "qc_failed", "to": "in_custody", "event_type_slug": "ARRIVED", "label": "Devolver a custodia"},
        ],
        "event_types": [
            {
                "slug": "CREATED", "name": "Carga registrada", "icon": "plus-circle", "color": "#22c55e",
                "required_documents": {"documents": [
                    {"type": "photo", "label": "Foto del producto", "required": False, "accept": ["image/*"], "max_size_mb": 5},
                ]},
                "compliance_required_documents": {"documents": [
                    {"type": "land_title", "label": "Título de propiedad / parcela", "required": True, "accept": ["application/pdf", "image/*"]},
                ], "block_transition": True},
            },
            {
                "slug": "HANDOFF", "name": "Transferir custodia", "icon": "arrow-right", "color": "#3b82f6", "requires_wallet": True,
                "required_documents": {"documents": [
                    {"type": "remision", "label": "Remisión de transporte", "required": False, "accept": ["application/pdf", "image/*"]},
                    {"type": "photo", "label": "Foto de carga", "required": False, "accept": ["image/*"], "max_size_mb": 5, "max_count": 5},
                ]},
                "compliance_required_documents": {"documents": [
                    {"type": "guia_terrestre", "label": "Guía terrestre", "required": True, "accept": ["application/pdf"]},
                ]},
            },
            {
                "slug": "ARRIVED", "name": "Registrar llegada", "icon": "map-pin", "color": "#8b5cf6",
                "required_documents": {"documents": [
                    {"type": "photo", "label": "Foto de recepción", "required": False, "accept": ["image/*"], "max_size_mb": 5},
                ]},
            },
            {
                "slug": "LOADED", "name": "Cargar en transporte", "icon": "container", "color": "#06b6d4",
                "required_documents": {"documents": [
                    {"type": "photo", "label": "Foto de carga", "required": False, "accept": ["image/*"]},
                ]},
            },
            {
                "slug": "QC", "name": "Control de calidad", "icon": "clipboard-check", "color": "#f59e0b", "requires_notes": True,
                "required_documents": {"documents": [
                    {"type": "qc_report", "label": "Reporte de calidad", "required": False, "accept": ["application/pdf", "image/*"]},
                ]},
                "compliance_required_documents": {"documents": [
                    {"type": "lab_analysis", "label": "Análisis de laboratorio", "required": True, "accept": ["application/pdf"]},
                ]},
            },
            {
                "slug": "DELIVERED", "name": "Entregar", "icon": "check-circle", "color": "#059669", "requires_wallet": True,
                "required_documents": {"documents": [
                    {"type": "pod", "label": "Prueba de entrega", "required": False, "accept": ["application/pdf", "image/*"]},
                    {"type": "signature", "label": "Firma de recepción", "required": False, "accept": ["image/*"]},
                ]},
                "compliance_required_documents": {"documents": [
                    {"type": "pod", "label": "Prueba de entrega", "required": True, "accept": ["application/pdf", "image/*"]},
                ], "block_transition": True},
            },
            {"slug": "BURN", "name": "Finalizar entrega", "icon": "flame", "color": "#ef4444", "requires_reason": True},
            {"slug": "RELEASED", "name": "Liberar (admin)", "icon": "unlock", "color": "#10b981", "requires_reason": True, "requires_admin": True},
            {
                "slug": "CUSTOMS_HOLD", "name": "Retención aduana", "icon": "shield-alert", "color": "#f97316", "requires_reason": True,
                "required_documents": {"documents": [
                    {"type": "customs_notice", "label": "Notificación de retención", "required": False, "accept": ["application/pdf"]},
                ]},
            },
            {
                "slug": "CUSTOMS_CLEARED", "name": "Liberado de aduana", "icon": "shield-check", "color": "#22c55e",
                "required_documents": {"documents": [
                    {"type": "customs_release", "label": "Acta de liberación", "required": False, "accept": ["application/pdf"]},
                ]},
                "compliance_required_documents": {"documents": [
                    {"type": "cert_origen", "label": "Certificado de origen", "required": True, "accept": ["application/pdf"]},
                    {"type": "fitosanitario", "label": "Certificado fitosanitario", "required": True, "accept": ["application/pdf"]},
                    {"type": "dex", "label": "Declaración de exportación (DEX)", "required": True, "accept": ["application/pdf"]},
                ], "block_transition": True},
            },
            {"slug": "DAMAGED", "name": "Reportar daño", "icon": "alert-triangle", "color": "#dc2626", "requires_reason": True,
                "required_documents": {"documents": [
                    {"type": "photo", "label": "Foto del daño", "required": False, "accept": ["image/*"], "max_count": 5},
                ]},
            },
            {
                "slug": "SEALED", "name": "Sellar carga", "icon": "lock", "color": "#06b6d4",
                "required_documents": {"documents": [
                    {"type": "photo", "label": "Foto del sello", "required": False, "accept": ["image/*"]},
                ]},
                "compliance_required_documents": {"documents": [
                    {"type": "bl", "label": "Bill of Lading", "required": True, "accept": ["application/pdf"]},
                    {"type": "insurance_cert", "label": "Certificado de seguro", "required": True, "accept": ["application/pdf"]},
                ]},
            },
            {"slug": "UNSEALED", "name": "Remover sello", "icon": "unlock", "color": "#f59e0b"},
            {"slug": "RETURN", "name": "Devolución", "icon": "undo-2", "color": "#ea580c", "requires_reason": True},
            {"slug": "TEMPERATURE_CHECK", "name": "Lectura de temperatura", "icon": "thermometer", "color": "#ef4444", "is_informational": True},
            {"slug": "INSPECTION", "name": "Inspección", "icon": "search", "color": "#8b5cf6", "is_informational": True,
                "required_documents": {"documents": [
                    {"type": "inspection_report", "label": "Reporte de inspección", "required": False, "accept": ["application/pdf", "image/*"]},
                ]},
            },
            {"slug": "NOTE", "name": "Nota", "icon": "message-square", "color": "#94a3b8", "is_informational": True},
        ],
    },
    "logistics": {
        "states": [
            {"slug": "recibido", "label": "Recibido", "color": "#06b6d4", "icon": "package-check", "is_initial": True, "sort_order": 0},
            {"slug": "en_bodega", "label": "En bodega", "color": "#8b5cf6", "icon": "warehouse", "sort_order": 1},
            {"slug": "en_transito", "label": "En tránsito", "color": "#f59e0b", "icon": "truck", "sort_order": 2},
            {"slug": "en_reparto", "label": "En reparto", "color": "#3b82f6", "icon": "map-pin", "sort_order": 3},
            {"slug": "entregado", "label": "Entregado", "color": "#22c55e", "icon": "check-circle", "is_terminal": True, "sort_order": 4},
            {"slug": "devuelto", "label": "Devuelto", "color": "#f97316", "icon": "undo-2", "sort_order": 5},
        ],
        "transitions": [
            {"from": "recibido", "to": "en_bodega", "label": "Almacenar", "event_type_slug": "ALMACENAMIENTO"},
            {"from": "en_bodega", "to": "en_transito", "label": "Despachar", "event_type_slug": "DESPACHO"},
            {"from": "en_transito", "to": "en_reparto", "label": "Iniciar reparto", "event_type_slug": "REPARTO"},
            {"from": "en_reparto", "to": "entregado", "label": "Entregar", "event_type_slug": "ENTREGA"},
            {"from": "en_transito", "to": "en_bodega", "label": "Devolver a bodega", "event_type_slug": "DEVOLUCION"},
            {"from": "entregado", "to": "devuelto", "label": "Devolver", "event_type_slug": "DEVOLUCION"},
            {"from": "en_reparto", "to": "devuelto", "label": "Rechazar entrega", "event_type_slug": "DEVOLUCION"},
        ],
        "event_types": [
            {
                "slug": "RECEPCION", "name": "Recepción", "icon": "package-check", "color": "#06b6d4",
                "required_documents": {"documents": [
                    {"type": "photo", "label": "Foto de recepción", "required": False, "accept": ["image/*"]},
                    {"type": "remision", "label": "Remisión", "required": False, "accept": ["application/pdf", "image/*"]},
                ]},
            },
            {
                "slug": "ALMACENAMIENTO", "name": "Almacenamiento", "icon": "warehouse", "color": "#8b5cf6",
                "required_documents": {"documents": [
                    {"type": "photo", "label": "Foto de almacenamiento", "required": False, "accept": ["image/*"]},
                ]},
            },
            {
                "slug": "DESPACHO", "name": "Despacho", "icon": "truck", "color": "#f59e0b", "requires_wallet": True,
                "required_documents": {"documents": [
                    {"type": "guia_terrestre", "label": "Guía de transporte", "required": False, "accept": ["application/pdf"]},
                    {"type": "remision", "label": "Remisión de despacho", "required": False, "accept": ["application/pdf", "image/*"]},
                ]},
            },
            {
                "slug": "REPARTO", "name": "Reparto", "icon": "map-pin", "color": "#3b82f6", "requires_wallet": True,
                "required_documents": {"documents": [
                    {"type": "photo", "label": "Foto de reparto", "required": False, "accept": ["image/*"]},
                ]},
            },
            {
                "slug": "ENTREGA", "name": "Entrega", "icon": "check-circle", "color": "#22c55e", "requires_wallet": True,
                "required_documents": {"documents": [
                    {"type": "pod", "label": "Prueba de entrega", "required": False, "accept": ["application/pdf", "image/*"]},
                    {"type": "signature", "label": "Firma de recepción", "required": False, "accept": ["image/*"]},
                ]},
            },
            {"slug": "DEVOLUCION", "name": "Devolución", "icon": "undo-2", "color": "#f97316", "requires_reason": True,
                "required_documents": {"documents": [
                    {"type": "photo", "label": "Foto del estado", "required": False, "accept": ["image/*"]},
                ]},
            },
            {"slug": "NOTA", "name": "Nota", "icon": "message-square", "color": "#94a3b8", "is_informational": True},
        ],
    },
    "pharma": {
        "states": [
            {"slug": "cuarentena", "label": "Cuarentena", "color": "#ef4444", "icon": "shield-alert", "is_initial": True, "sort_order": 0},
            {"slug": "aprobado", "label": "Aprobado", "color": "#22c55e", "icon": "check-circle", "sort_order": 1},
            {"slug": "en_distribucion", "label": "En distribución", "color": "#3b82f6", "icon": "truck", "sort_order": 2},
            {"slug": "dispensado", "label": "Dispensado", "color": "#8b5cf6", "icon": "pill", "is_terminal": True, "sort_order": 3},
            {"slug": "devuelto", "label": "Devuelto", "color": "#f97316", "icon": "undo-2", "sort_order": 4},
        ],
        "transitions": [
            {"from": "cuarentena", "to": "aprobado", "label": "Aprobar QC", "event_type_slug": "APROBACION_QC"},
            {"from": "aprobado", "to": "en_distribucion", "label": "Enviar a distribución", "event_type_slug": "ENVIO_DIST"},
            {"from": "en_distribucion", "to": "dispensado", "label": "Dispensar", "event_type_slug": "DISPENSACION"},
            {"from": "cuarentena", "to": "cuarentena", "label": "Re-inspeccionar", "event_type_slug": "INGRESO_CUARENTENA"},
            {"from": "dispensado", "to": "devuelto", "label": "Devolver", "event_type_slug": "DEVOLUCION"},
        ],
        "event_types": [
            {"slug": "INGRESO_CUARENTENA", "name": "Ingreso a cuarentena", "icon": "shield-alert", "color": "#ef4444"},
            {"slug": "APROBACION_QC", "name": "Aprobación QC", "icon": "check-circle", "color": "#22c55e"},
            {"slug": "ENVIO_DIST", "name": "Envío a distribución", "icon": "truck", "color": "#3b82f6"},
            {"slug": "DISPENSACION", "name": "Dispensación", "icon": "pill", "color": "#8b5cf6"},
            {"slug": "DEVOLUCION", "name": "Devolución", "icon": "undo-2", "color": "#f97316", "requires_reason": True},
            {"slug": "CONTROL_TEMP", "name": "Control de temperatura", "icon": "thermometer", "color": "#f59e0b", "is_informational": True},
        ],
    },
    "coldchain": {
        "states": [
            {"slug": "recepcion", "label": "Recepción", "color": "#06b6d4", "icon": "package-check", "is_initial": True, "sort_order": 0},
            {"slug": "camara_fria", "label": "Cámara fría", "color": "#3b82f6", "icon": "snowflake", "sort_order": 1},
            {"slug": "pre_alistamiento", "label": "Pre-alistamiento", "color": "#f59e0b", "icon": "clipboard-list", "sort_order": 2},
            {"slug": "en_ruta", "label": "En ruta", "color": "#8b5cf6", "icon": "truck", "sort_order": 3},
            {"slug": "entregado", "label": "Entregado", "color": "#22c55e", "icon": "check-circle", "is_terminal": True, "sort_order": 4},
            {"slug": "devuelto", "label": "Devuelto", "color": "#f97316", "icon": "undo-2", "sort_order": 5},
        ],
        "transitions": [
            {"from": "recepcion", "to": "camara_fria", "label": "Almacenar en frío", "event_type_slug": "ALMACENAMIENTO_FRIO"},
            {"from": "camara_fria", "to": "pre_alistamiento", "label": "Alistar", "event_type_slug": "ALISTAMIENTO"},
            {"from": "pre_alistamiento", "to": "en_ruta", "label": "Despachar", "event_type_slug": "DESPACHO_RUTA"},
            {"from": "en_ruta", "to": "entregado", "label": "Entregar", "event_type_slug": "ENTREGA"},
            {"from": "en_ruta", "to": "camara_fria", "label": "Devolver a frío", "event_type_slug": "DEVOLUCION"},
            {"from": "entregado", "to": "devuelto", "label": "Devolver", "event_type_slug": "DEVOLUCION"},
        ],
        "event_types": [
            {"slug": "RECEPCION", "name": "Recepción", "icon": "package-check", "color": "#06b6d4"},
            {"slug": "ALMACENAMIENTO_FRIO", "name": "Almacenamiento frío", "icon": "snowflake", "color": "#3b82f6"},
            {"slug": "ALISTAMIENTO", "name": "Alistamiento", "icon": "clipboard-list", "color": "#f59e0b"},
            {"slug": "DESPACHO_RUTA", "name": "Despacho en ruta", "icon": "truck", "color": "#8b5cf6"},
            {"slug": "ENTREGA", "name": "Entrega", "icon": "check-circle", "color": "#22c55e"},
            {"slug": "DEVOLUCION", "name": "Devolución", "icon": "undo-2", "color": "#f97316", "requires_reason": True},
            {"slug": "LECTURA_TEMP", "name": "Lectura de temperatura", "icon": "thermometer", "color": "#ef4444", "is_informational": True},
        ],
    },
    "retail": {
        "states": [
            {"slug": "en_proveedor", "label": "En proveedor", "color": "#f59e0b", "icon": "factory", "is_initial": True, "sort_order": 0},
            {"slug": "en_bodega", "label": "En bodega", "color": "#8b5cf6", "icon": "warehouse", "sort_order": 1},
            {"slug": "picking", "label": "Picking", "color": "#3b82f6", "icon": "hand", "sort_order": 2},
            {"slug": "despachado", "label": "Despachado", "color": "#06b6d4", "icon": "package", "sort_order": 3},
            {"slug": "recibido_cliente", "label": "Recibido", "color": "#22c55e", "icon": "check-circle", "is_terminal": True, "sort_order": 4},
            {"slug": "devuelto", "label": "Devuelto", "color": "#f97316", "icon": "undo-2", "sort_order": 5},
        ],
        "transitions": [
            {"from": "en_proveedor", "to": "en_bodega", "label": "Recibir en bodega", "event_type_slug": "RECEPCION_BODEGA"},
            {"from": "en_bodega", "to": "picking", "label": "Iniciar picking", "event_type_slug": "INICIO_PICKING"},
            {"from": "picking", "to": "despachado", "label": "Despachar", "event_type_slug": "DESPACHO"},
            {"from": "despachado", "to": "recibido_cliente", "label": "Confirmar recepción", "event_type_slug": "CONFIRMACION"},
            {"from": "recibido_cliente", "to": "devuelto", "label": "Devolver", "event_type_slug": "DEVOLUCION"},
            {"from": "despachado", "to": "devuelto", "label": "Rechazar entrega", "event_type_slug": "DEVOLUCION"},
        ],
        "event_types": [
            {"slug": "RECEPCION_BODEGA", "name": "Recepción en bodega", "icon": "warehouse", "color": "#8b5cf6"},
            {"slug": "INICIO_PICKING", "name": "Inicio picking", "icon": "hand", "color": "#3b82f6"},
            {"slug": "DESPACHO", "name": "Despacho", "icon": "package", "color": "#06b6d4"},
            {"slug": "CONFIRMACION", "name": "Confirmación recepción", "icon": "check-circle", "color": "#22c55e"},
            {"slug": "DEVOLUCION", "name": "Devolución", "icon": "undo-2", "color": "#f97316", "requires_reason": True},
            {"slug": "NOTA", "name": "Nota", "icon": "message-square", "color": "#94a3b8", "is_informational": True},
        ],
    },
    "construction": {
        "states": [
            {"slug": "solicitado", "label": "Solicitado", "color": "#f59e0b", "icon": "file-text", "is_initial": True, "sort_order": 0},
            {"slug": "en_fabricacion", "label": "En fabricación", "color": "#8b5cf6", "icon": "factory", "sort_order": 1},
            {"slug": "en_obra", "label": "En obra", "color": "#3b82f6", "icon": "hard-hat", "sort_order": 2},
            {"slug": "instalado", "label": "Instalado", "color": "#06b6d4", "icon": "wrench", "sort_order": 3},
            {"slug": "cerrado", "label": "Cerrado", "color": "#22c55e", "icon": "check-circle", "is_terminal": True, "sort_order": 4},
            {"slug": "devuelto", "label": "Devuelto", "color": "#f97316", "icon": "undo-2", "sort_order": 5},
        ],
        "transitions": [
            {"from": "solicitado", "to": "en_fabricacion", "label": "Enviar a fabricación", "event_type_slug": "FABRICACION"},
            {"from": "en_fabricacion", "to": "en_obra", "label": "Entregar en obra", "event_type_slug": "ENTREGA_OBRA"},
            {"from": "en_obra", "to": "instalado", "label": "Instalar", "event_type_slug": "INSTALACION"},
            {"from": "instalado", "to": "cerrado", "label": "Cerrar", "event_type_slug": "CIERRE"},
            {"from": "en_obra", "to": "en_fabricacion", "label": "Devolver a fábrica", "event_type_slug": "DEVOLUCION"},
            {"from": "cerrado", "to": "devuelto", "label": "Devolver material", "event_type_slug": "DEVOLUCION"},
        ],
        "event_types": [
            {"slug": "SOLICITUD", "name": "Solicitud", "icon": "file-text", "color": "#f59e0b",
                "required_documents": {"documents": [
                    {"type": "orden_compra", "label": "Orden de compra", "required": False, "accept": ["application/pdf"]},
                ]},
            },
            {"slug": "FABRICACION", "name": "Fabricación", "icon": "factory", "color": "#8b5cf6",
                "required_documents": {"documents": [
                    {"type": "qc_report", "label": "Reporte de calidad", "required": False, "accept": ["application/pdf", "image/*"]},
                ]},
            },
            {"slug": "ENTREGA_OBRA", "name": "Entrega en obra", "icon": "hard-hat", "color": "#3b82f6",
                "required_documents": {"documents": [
                    {"type": "remision", "label": "Remisión de entrega", "required": False, "accept": ["application/pdf", "image/*"]},
                    {"type": "photo", "label": "Foto de entrega", "required": False, "accept": ["image/*"]},
                ]},
            },
            {"slug": "INSTALACION", "name": "Instalación", "icon": "wrench", "color": "#06b6d4",
                "required_documents": {"documents": [
                    {"type": "acta_instalacion", "label": "Acta de instalación", "required": False, "accept": ["application/pdf"]},
                    {"type": "photo", "label": "Foto de instalación", "required": False, "accept": ["image/*"], "max_count": 5},
                ]},
            },
            {"slug": "CIERRE", "name": "Cierre", "icon": "check-circle", "color": "#22c55e",
                "required_documents": {"documents": [
                    {"type": "acta_entrega", "label": "Acta de entrega final", "required": False, "accept": ["application/pdf"]},
                    {"type": "signature", "label": "Firma de conformidad", "required": False, "accept": ["image/*"]},
                ]},
            },
            {"slug": "DEVOLUCION", "name": "Devolución", "icon": "undo-2", "color": "#f97316", "requires_reason": True,
                "required_documents": {"documents": [
                    {"type": "photo", "label": "Foto del estado", "required": False, "accept": ["image/*"]},
                ]},
            },
            {"slug": "INCIDENCIA", "name": "Incidencia", "icon": "alert-triangle", "color": "#ef4444", "is_informational": True,
                "required_documents": {"documents": [
                    {"type": "photo", "label": "Foto de la incidencia", "required": False, "accept": ["image/*"], "max_count": 5},
                ]},
            },
        ],
    },
}


# ─── Media Files ─────────────────────────────────────────────────────────────

class MediaFileResponse(OrmBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    filename: str
    original_filename: str
    content_type: str
    file_size: int
    file_hash: str
    storage_backend: str
    url: str
    category: str
    document_type: str | None
    title: str | None
    description: str | None
    tags: list[str]
    uploaded_by: str | None
    created_at: datetime
    updated_at: datetime


class DocumentRequirement(BaseModel):
    type: str
    label: str
    required: bool = False
    accept: list[str] | None = None
    max_size_mb: int | None = None
    max_count: int | None = None


class DocumentRequirementsResponse(BaseModel):
    event_type_slug: str
    base_requirements: list[DocumentRequirement]
    compliance_requirements: list[DocumentRequirement]
    compliance_active: bool
    merged_requirements: list[DocumentRequirement]
    block_transition: bool


class DocumentMissing(BaseModel):
    type: str
    label: str
    source: str


class DocumentSatisfied(BaseModel):
    type: str
    label: str
    count: int


class DocumentCompletenessResponse(BaseModel):
    complete: bool
    total_uploaded: int
    total_required: int
    missing: list[DocumentMissing]
    satisfied: list[DocumentSatisfied]
    block_transition: bool


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
