"""Shipment documents and trade documents — logistics module endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_tenant_id_enforced, get_tenant_id, require_permission
from app.core.logging import get_logger
from app.db.models import ShipmentDocument, TradeDocument, AnchorRule
from app.db.session import get_db_session
from app.utils.hashing import compute_event_hash
from app.utils.json_canonical import canonical_json_bytes
from app.services.anchor_service import enqueue_anchor

import hashlib

log = get_logger(__name__)

router = APIRouter(tags=["logistics"])


def _sha256(data: dict) -> str:
    raw = canonical_json_bytes(data)
    return hashlib.sha256(raw).hexdigest()


# ── Shipment Schemas ──────────────────────────────────────────────────────────

class ShipmentCreate(BaseModel):
    document_type: str
    document_number: str
    carrier_name: str | None = None
    carrier_code: str | None = None
    vehicle_plate: str | None = None
    driver_name: str | None = None
    driver_id_number: str | None = None
    origin_address: str | None = None
    destination_address: str | None = None
    origin_city: str | None = None
    destination_city: str | None = None
    origin_country: str | None = None
    destination_country: str | None = None
    vessel_name: str | None = None
    voyage_number: str | None = None
    container_number: str | None = None
    container_type: str | None = None
    seal_number: str | None = None
    flight_number: str | None = None
    total_packages: int | None = None
    total_weight_kg: float | None = None
    total_volume_m3: float | None = None
    cargo_description: str | None = None
    declared_value: float | None = None
    declared_currency: str | None = None
    issued_date: str | None = None
    shipped_date: str | None = None
    estimated_arrival: str | None = None
    tracking_number: str | None = None
    tracking_url: str | None = None
    notes: str | None = None
    file_url: str | None = None
    reference_id: str | None = None
    reference_type: str | None = None
    metadata: dict[str, Any] = {}

class ShipmentUpdate(BaseModel):
    carrier_name: str | None = None
    vehicle_plate: str | None = None
    driver_name: str | None = None
    container_number: str | None = None
    seal_number: str | None = None
    total_packages: int | None = None
    total_weight_kg: float | None = None
    shipped_date: str | None = None
    estimated_arrival: str | None = None
    actual_arrival: str | None = None
    tracking_number: str | None = None
    tracking_url: str | None = None
    notes: str | None = None

class StatusBody(BaseModel):
    status: str

# ── Trade Doc Schemas ─────────────────────────────────────────────────────────

class TradeDocCreate(BaseModel):
    document_type: str
    document_number: str | None = None
    shipment_document_id: str | None = None
    title: str
    issuing_authority: str | None = None
    issuing_country: str | None = None
    issued_date: str | None = None
    expiry_date: str | None = None
    description: str | None = None
    content_data: dict[str, Any] = {}
    file_url: str | None = None
    file_hash: str | None = None
    hs_code: str | None = None
    fob_value: float | None = None
    cif_value: float | None = None
    currency: str | None = None
    notes: str | None = None
    reference_id: str | None = None
    reference_type: str | None = None
    metadata: dict[str, Any] = {}

class TradeDocUpdate(BaseModel):
    document_number: str | None = None
    title: str | None = None
    issuing_authority: str | None = None
    issued_date: str | None = None
    expiry_date: str | None = None
    description: str | None = None
    file_url: str | None = None
    file_hash: str | None = None
    hs_code: str | None = None
    fob_value: float | None = None
    cif_value: float | None = None
    currency: str | None = None
    notes: str | None = None

# ── Anchor Rule Schemas ───────────────────────────────────────────────────────

class AnchorRuleCreate(BaseModel):
    name: str
    entity_type: str
    trigger_event: str
    conditions: dict[str, Any] = {}
    actions: dict[str, Any] = Field(default_factory=lambda: {"anchor": True})
    is_active: bool = True
    priority: int = 0

class AnchorRuleUpdate(BaseModel):
    name: str | None = None
    conditions: dict[str, Any] | None = None
    actions: dict[str, Any] | None = None
    is_active: bool | None = None
    priority: int | None = None


# ═══════════════════════════════════════════════════════════════════════════════
# SHIPMENT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/shipments")
async def list_shipments(
    tenant_id: uuid.UUID = Depends(get_tenant_id_enforced),
    document_type: str | None = None,
    reference_type: str | None = None,
    reference_id: str | None = None,
    db: AsyncSession = Depends(get_db_session),
):
    q = select(ShipmentDocument).where(ShipmentDocument.tenant_id == tenant_id)
    if document_type:
        q = q.where(ShipmentDocument.document_type == document_type)
    if reference_type:
        q = q.where(ShipmentDocument.reference_type == reference_type)
    if reference_id:
        q = q.where(ShipmentDocument.reference_id == reference_id)
    q = q.order_by(ShipmentDocument.created_at.desc())
    result = await db.execute(q)
    return [_shipment_out(s) for s in result.scalars().all()]


@router.post("/shipments", status_code=201, dependencies=[require_permission("logistics.manage")])
async def create_shipment(
    body: ShipmentCreate,
    tenant_id: uuid.UUID = Depends(get_tenant_id_enforced),
    db: AsyncSession = Depends(get_db_session),
):
    doc = ShipmentDocument(tenant_id=tenant_id)
    for k, v in body.model_dump(exclude={"metadata"}).items():
        if v is not None and hasattr(doc, k):
            setattr(doc, k, v)
    doc.metadata_ = body.metadata
    db.add(doc)
    await db.flush()

    # Auto-anchor
    h = _sha256({"doc_type": body.document_type, "doc_number": body.document_number, "tenant": str(tenant_id), "ts": datetime.now(timezone.utc).isoformat()})
    doc.anchor_hash = h
    doc.anchor_status = "pending"
    await db.commit()
    return _shipment_out(doc)


@router.get("/shipments/{doc_id}")
async def get_shipment(
    doc_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id_enforced),
    db: AsyncSession = Depends(get_db_session),
):
    doc = await _get_shipment(db, doc_id, tenant_id)
    return _shipment_out(doc)


@router.patch("/shipments/{doc_id}", dependencies=[require_permission("logistics.manage")])
async def update_shipment(
    doc_id: uuid.UUID, body: ShipmentUpdate,
    tenant_id: uuid.UUID = Depends(get_tenant_id_enforced),
    db: AsyncSession = Depends(get_db_session),
):
    doc = await _get_shipment(db, doc_id, tenant_id)
    for k, v in body.model_dump(exclude_none=True).items():
        if hasattr(doc, k):
            setattr(doc, k, v)
    await db.commit()
    return _shipment_out(doc)


@router.post("/shipments/{doc_id}/status", dependencies=[require_permission("logistics.manage")])
async def update_shipment_status(
    doc_id: uuid.UUID, body: StatusBody,
    tenant_id: uuid.UUID = Depends(get_tenant_id_enforced),
    db: AsyncSession = Depends(get_db_session),
):
    valid = {"draft", "issued", "in_transit", "delivered", "canceled"}
    if body.status not in valid:
        raise HTTPException(400, f"Invalid status: {body.status}")
    doc = await _get_shipment(db, doc_id, tenant_id)
    doc.status = body.status
    if body.status == "delivered" and not doc.actual_arrival:
        doc.actual_arrival = datetime.now(timezone.utc)
    await db.commit()
    return _shipment_out(doc)


@router.delete("/shipments/{doc_id}", status_code=204, dependencies=[require_permission("logistics.manage")])
async def delete_shipment(
    doc_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id_enforced),
    db: AsyncSession = Depends(get_db_session),
):
    doc = await _get_shipment(db, doc_id, tenant_id)
    await db.delete(doc)
    await db.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# TRADE DOCUMENT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/trade-documents")
async def list_trade_docs(
    tenant_id: uuid.UUID = Depends(get_tenant_id_enforced),
    document_type: str | None = None,
    reference_type: str | None = None,
    reference_id: str | None = None,
    shipment_id: str | None = None,
    db: AsyncSession = Depends(get_db_session),
):
    q = select(TradeDocument).where(TradeDocument.tenant_id == tenant_id)
    if document_type:
        q = q.where(TradeDocument.document_type == document_type)
    if reference_type:
        q = q.where(TradeDocument.reference_type == reference_type)
    if reference_id:
        q = q.where(TradeDocument.reference_id == reference_id)
    if shipment_id:
        q = q.where(TradeDocument.shipment_document_id == uuid.UUID(shipment_id))
    q = q.order_by(TradeDocument.created_at.desc())
    result = await db.execute(q)
    return [_trade_doc_out(d) for d in result.scalars().all()]


@router.post("/trade-documents", status_code=201, dependencies=[require_permission("logistics.manage")])
async def create_trade_doc(
    body: TradeDocCreate,
    tenant_id: uuid.UUID = Depends(get_tenant_id_enforced),
    db: AsyncSession = Depends(get_db_session),
):
    doc = TradeDocument(tenant_id=tenant_id)
    for k, v in body.model_dump(exclude={"metadata"}).items():
        if v is not None and hasattr(doc, k):
            if k == "shipment_document_id" and v:
                setattr(doc, k, uuid.UUID(v))
            else:
                setattr(doc, k, v)
    doc.metadata_ = body.metadata
    db.add(doc)
    await db.flush()

    # Auto-anchor
    h = _sha256({"doc_type": body.document_type, "title": body.title, "tenant": str(tenant_id), "ts": datetime.now(timezone.utc).isoformat()})
    doc.anchor_hash = h
    doc.anchor_status = "pending"
    await db.commit()
    return _trade_doc_out(doc)


@router.get("/trade-documents/{doc_id}")
async def get_trade_doc(
    doc_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id_enforced),
    db: AsyncSession = Depends(get_db_session),
):
    doc = await _get_trade_doc(db, doc_id, tenant_id)
    return _trade_doc_out(doc)


@router.patch("/trade-documents/{doc_id}", dependencies=[require_permission("logistics.manage")])
async def update_trade_doc(
    doc_id: uuid.UUID, body: TradeDocUpdate,
    tenant_id: uuid.UUID = Depends(get_tenant_id_enforced),
    db: AsyncSession = Depends(get_db_session),
):
    doc = await _get_trade_doc(db, doc_id, tenant_id)
    for k, v in body.model_dump(exclude_none=True).items():
        if hasattr(doc, k):
            setattr(doc, k, v)
    await db.commit()
    return _trade_doc_out(doc)


@router.post("/trade-documents/{doc_id}/approve", dependencies=[require_permission("logistics.manage")])
async def approve_trade_doc(
    doc_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id_enforced),
    db: AsyncSession = Depends(get_db_session),
):
    doc = await _get_trade_doc(db, doc_id, tenant_id)
    if doc.status not in ("pending", "rejected"):
        raise HTTPException(400, f"Cannot approve document with status '{doc.status}'")
    doc.status = "approved"
    # Re-anchor on approval
    h = _sha256({"doc_type": doc.document_type, "title": doc.title, "status": "approved", "tenant": str(tenant_id), "ts": datetime.now(timezone.utc).isoformat()})
    doc.anchor_hash = h
    doc.anchor_status = "pending"
    await db.commit()
    return _trade_doc_out(doc)


@router.post("/trade-documents/{doc_id}/reject", dependencies=[require_permission("logistics.manage")])
async def reject_trade_doc(
    doc_id: uuid.UUID,
    reason: str | None = None,
    tenant_id: uuid.UUID = Depends(get_tenant_id_enforced),
    db: AsyncSession = Depends(get_db_session),
):
    doc = await _get_trade_doc(db, doc_id, tenant_id)
    doc.status = "rejected"
    if reason:
        doc.notes = reason
    await db.commit()
    return _trade_doc_out(doc)


@router.delete("/trade-documents/{doc_id}", status_code=204, dependencies=[require_permission("logistics.manage")])
async def delete_trade_doc(
    doc_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id_enforced),
    db: AsyncSession = Depends(get_db_session),
):
    doc = await _get_trade_doc(db, doc_id, tenant_id)
    await db.delete(doc)
    await db.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# ANCHOR RULES ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/anchor-rules")
async def list_anchor_rules(
    tenant_id: uuid.UUID = Depends(get_tenant_id_enforced),
    entity_type: str | None = None,
    db: AsyncSession = Depends(get_db_session),
):
    q = select(AnchorRule).where(AnchorRule.tenant_id == tenant_id)
    if entity_type:
        q = q.where(AnchorRule.entity_type == entity_type)
    q = q.order_by(AnchorRule.priority.desc())
    result = await db.execute(q)
    return [_rule_out(r) for r in result.scalars().all()]


@router.post("/anchor-rules", status_code=201, dependencies=[require_permission("logistics.manage")])
async def create_anchor_rule(
    body: AnchorRuleCreate,
    tenant_id: uuid.UUID = Depends(get_tenant_id_enforced),
    db: AsyncSession = Depends(get_db_session),
):
    rule = AnchorRule(tenant_id=tenant_id, **body.model_dump())
    db.add(rule)
    await db.commit()
    return _rule_out(rule)


@router.patch("/anchor-rules/{rule_id}", dependencies=[require_permission("logistics.manage")])
async def update_anchor_rule(
    rule_id: uuid.UUID, body: AnchorRuleUpdate,
    tenant_id: uuid.UUID = Depends(get_tenant_id_enforced),
    db: AsyncSession = Depends(get_db_session),
):
    rule = await _get_rule(db, rule_id, tenant_id)
    for k, v in body.model_dump(exclude_none=True).items():
        if hasattr(rule, k):
            setattr(rule, k, v)
    await db.commit()
    return _rule_out(rule)


@router.delete("/anchor-rules/{rule_id}", status_code=204, dependencies=[require_permission("logistics.manage")])
async def delete_anchor_rule(
    rule_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id_enforced),
    db: AsyncSession = Depends(get_db_session),
):
    rule = await _get_rule(db, rule_id, tenant_id)
    await db.delete(rule)
    await db.commit()


@router.post("/anchor-rules/seed-defaults", status_code=201, dependencies=[require_permission("logistics.manage")])
async def seed_defaults(
    tenant_id: uuid.UUID = Depends(get_tenant_id_enforced),
    db: AsyncSession = Depends(get_db_session),
):
    existing = (await db.execute(select(AnchorRule).where(AnchorRule.tenant_id == tenant_id))).scalars().all()
    if existing:
        return [_rule_out(r) for r in existing]
    defaults = [
        AnchorRule(tenant_id=tenant_id, name="Anclar recepciones de OC", entity_type="purchase_order", trigger_event="received", conditions={"always": True}, actions={"anchor": True}),
        AnchorRule(tenant_id=tenant_id, name="Anclar entregas de pedidos", entity_type="sales_order", trigger_event="delivered", conditions={"always": True}, actions={"anchor": True}),
        AnchorRule(tenant_id=tenant_id, name="Anclar creacion de lotes", entity_type="batch", trigger_event="created", conditions={"always": True}, actions={"anchor": True}),
    ]
    for r in defaults:
        db.add(r)
    await db.commit()
    return [_rule_out(r) for r in defaults]


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

async def _get_shipment(db: AsyncSession, doc_id: uuid.UUID, tenant_id: uuid.UUID) -> ShipmentDocument:
    q = select(ShipmentDocument).where(ShipmentDocument.id == doc_id, ShipmentDocument.tenant_id == tenant_id)
    doc = (await db.execute(q)).scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Shipment document not found")
    return doc

async def _get_trade_doc(db: AsyncSession, doc_id: uuid.UUID, tenant_id: uuid.UUID) -> TradeDocument:
    q = select(TradeDocument).where(TradeDocument.id == doc_id, TradeDocument.tenant_id == tenant_id)
    doc = (await db.execute(q)).scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Trade document not found")
    return doc

async def _get_rule(db: AsyncSession, rule_id: uuid.UUID, tenant_id: uuid.UUID) -> AnchorRule:
    q = select(AnchorRule).where(AnchorRule.id == rule_id, AnchorRule.tenant_id == tenant_id)
    rule = (await db.execute(q)).scalar_one_or_none()
    if not rule:
        raise HTTPException(404, "Anchor rule not found")
    return rule

def _shipment_out(s: ShipmentDocument) -> dict:
    return {
        "id": str(s.id), "tenant_id": str(s.tenant_id),
        "document_type": s.document_type, "document_number": s.document_number,
        "carrier_name": s.carrier_name, "vehicle_plate": s.vehicle_plate,
        "driver_name": s.driver_name, "origin_city": s.origin_city,
        "destination_city": s.destination_city, "origin_country": s.origin_country,
        "destination_country": s.destination_country, "vessel_name": s.vessel_name,
        "container_number": s.container_number, "flight_number": s.flight_number,
        "total_packages": s.total_packages, "total_weight_kg": s.total_weight_kg,
        "status": s.status, "tracking_number": s.tracking_number,
        "tracking_url": s.tracking_url, "anchor_hash": s.anchor_hash,
        "anchor_status": s.anchor_status, "reference_id": s.reference_id,
        "reference_type": s.reference_type,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }

def _trade_doc_out(d: TradeDocument) -> dict:
    return {
        "id": str(d.id), "tenant_id": str(d.tenant_id),
        "document_type": d.document_type, "document_number": d.document_number,
        "shipment_document_id": str(d.shipment_document_id) if d.shipment_document_id else None,
        "title": d.title, "issuing_authority": d.issuing_authority,
        "issuing_country": d.issuing_country,
        "issued_date": d.issued_date.isoformat() if d.issued_date else None,
        "expiry_date": d.expiry_date.isoformat() if d.expiry_date else None,
        "status": d.status, "hs_code": d.hs_code,
        "fob_value": d.fob_value, "cif_value": d.cif_value,
        "currency": d.currency, "file_url": d.file_url, "file_hash": d.file_hash,
        "anchor_hash": d.anchor_hash, "anchor_status": d.anchor_status,
        "reference_id": d.reference_id, "reference_type": d.reference_type,
        "created_at": d.created_at.isoformat() if d.created_at else None,
    }

def _rule_out(r: AnchorRule) -> dict:
    return {
        "id": str(r.id), "tenant_id": str(r.tenant_id),
        "name": r.name, "entity_type": r.entity_type,
        "trigger_event": r.trigger_event, "conditions": r.conditions,
        "actions": r.actions, "is_active": r.is_active,
        "priority": r.priority, "created_by": r.created_by,
    }
