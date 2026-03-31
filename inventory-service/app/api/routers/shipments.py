"""Shipment documents and trade documents CRUD endpoints."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser
from app.db.session import get_db_session
from app.services.shipment_service import ShipmentDocumentService, TradeDocumentService

router = APIRouter(tags=["shipments"])


# ─── Shipment Document Schemas ───────────────────────────────────────────────

class ShipmentDocCreate(BaseModel):
    document_type: str = Field(..., description="remision | bl | awb | carta_porte | guia_terrestre")
    document_number: str
    purchase_order_id: str | None = None
    sales_order_id: str | None = None
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
    total_weight_kg: Decimal | None = None
    total_volume_m3: Decimal | None = None
    cargo_description: str | None = None
    declared_value: Decimal | None = None
    declared_currency: str | None = None
    issued_date: datetime | None = None
    shipped_date: datetime | None = None
    estimated_arrival: datetime | None = None
    tracking_number: str | None = None
    tracking_url: str | None = None
    notes: str | None = None
    file_url: str | None = None
    metadata: dict[str, Any] = {}


class ShipmentDocUpdate(BaseModel):
    carrier_name: str | None = None
    vehicle_plate: str | None = None
    driver_name: str | None = None
    driver_id_number: str | None = None
    container_number: str | None = None
    seal_number: str | None = None
    total_packages: int | None = None
    total_weight_kg: Decimal | None = None
    total_volume_m3: Decimal | None = None
    shipped_date: datetime | None = None
    estimated_arrival: datetime | None = None
    actual_arrival: datetime | None = None
    tracking_number: str | None = None
    tracking_url: str | None = None
    notes: str | None = None
    file_url: str | None = None


class ShipmentDocOut(BaseModel):
    id: str
    tenant_id: str
    document_type: str
    document_number: str
    purchase_order_id: str | None = None
    sales_order_id: str | None = None
    carrier_name: str | None = None
    vehicle_plate: str | None = None
    driver_name: str | None = None
    origin_city: str | None = None
    destination_city: str | None = None
    origin_country: str | None = None
    destination_country: str | None = None
    vessel_name: str | None = None
    container_number: str | None = None
    flight_number: str | None = None
    total_packages: int | None = None
    total_weight_kg: Decimal | None = None
    status: str
    tracking_number: str | None = None
    tracking_url: str | None = None
    anchor_hash: str | None = None
    anchor_status: str = "none"
    created_at: datetime

    class Config:
        from_attributes = True


class StatusUpdate(BaseModel):
    status: str


# ─── Trade Document Schemas ──────────────────────────────────────────────────

class TradeDocCreate(BaseModel):
    document_type: str = Field(..., description="packing_list | commercial_invoice | bill_of_lading")
    document_number: str | None = None
    purchase_order_id: str | None = None
    sales_order_id: str | None = None
    shipment_document_id: str | None = None
    title: str
    issuing_authority: str | None = None
    issuing_country: str | None = None
    issued_date: datetime | None = None
    expiry_date: datetime | None = None
    description: str | None = None
    content_data: dict[str, Any] = {}
    file_url: str | None = None
    file_hash: str | None = None
    hs_code: str | None = None
    fob_value: Decimal | None = None
    cif_value: Decimal | None = None
    currency: str | None = None
    notes: str | None = None
    metadata: dict[str, Any] = {}


class TradeDocUpdate(BaseModel):
    document_number: str | None = None
    title: str | None = None
    issuing_authority: str | None = None
    issued_date: datetime | None = None
    expiry_date: datetime | None = None
    description: str | None = None
    content_data: dict[str, Any] | None = None
    file_url: str | None = None
    file_hash: str | None = None
    hs_code: str | None = None
    fob_value: Decimal | None = None
    cif_value: Decimal | None = None
    currency: str | None = None
    notes: str | None = None


class TradeDocOut(BaseModel):
    id: str
    tenant_id: str
    document_type: str
    document_number: str | None = None
    purchase_order_id: str | None = None
    sales_order_id: str | None = None
    shipment_document_id: str | None = None
    title: str
    issuing_authority: str | None = None
    issuing_country: str | None = None
    issued_date: datetime | None = None
    expiry_date: datetime | None = None
    status: str
    hs_code: str | None = None
    fob_value: Decimal | None = None
    cif_value: Decimal | None = None
    currency: str | None = None
    file_url: str | None = None
    file_hash: str | None = None
    anchor_hash: str | None = None
    anchor_status: str = "none"
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Shipment Document Endpoints ─────────────────────────────────────────────

@router.get("/api/v1/shipments", response_model=list[ShipmentDocOut])
async def list_shipments(
    user: ModuleUser,
    document_type: str | None = None,
    po_id: str | None = None,
    so_id: str | None = None,
    offset: int = 0, limit: int = 50,
    db: AsyncSession = Depends(get_db_session),
):
    svc = ShipmentDocumentService(db)
    return await svc.list(user["tenant_id"], document_type, po_id, so_id, offset, limit)


@router.post("/api/v1/shipments", response_model=ShipmentDocOut, status_code=201)
async def create_shipment(
    body: ShipmentDocCreate,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    svc = ShipmentDocumentService(db)
    doc = await svc.create(user["tenant_id"], {
        **body.model_dump(exclude={"metadata"}),
        "metadata": body.metadata,
        "created_by": user.get("user_id"),
    })
    await db.commit()
    return doc


@router.get("/api/v1/shipments/{doc_id}", response_model=ShipmentDocOut)
async def get_shipment(doc_id: str, user: ModuleUser, db: AsyncSession = Depends(get_db_session)):
    svc = ShipmentDocumentService(db)
    return await svc.get(doc_id, user["tenant_id"])


@router.patch("/api/v1/shipments/{doc_id}", response_model=ShipmentDocOut)
async def update_shipment(
    doc_id: str, body: ShipmentDocUpdate, user: ModuleUser, db: AsyncSession = Depends(get_db_session),
):
    svc = ShipmentDocumentService(db)
    doc = await svc.update(doc_id, user["tenant_id"], body.model_dump(exclude_none=True))
    await db.commit()
    return doc


@router.post("/api/v1/shipments/{doc_id}/status", response_model=ShipmentDocOut)
async def update_shipment_status(
    doc_id: str, body: StatusUpdate, user: ModuleUser, db: AsyncSession = Depends(get_db_session),
):
    svc = ShipmentDocumentService(db)
    doc = await svc.update_status(doc_id, user["tenant_id"], body.status)
    await db.commit()
    return doc


@router.delete("/api/v1/shipments/{doc_id}", status_code=204)
async def delete_shipment(doc_id: str, user: ModuleUser, db: AsyncSession = Depends(get_db_session)):
    svc = ShipmentDocumentService(db)
    await svc.delete(doc_id, user["tenant_id"])
    await db.commit()


# ─── Trade Document Endpoints ────────────────────────────────────────────────

@router.get("/api/v1/trade-documents", response_model=list[TradeDocOut])
async def list_trade_docs(
    user: ModuleUser,
    document_type: str | None = None,
    po_id: str | None = None,
    so_id: str | None = None,
    shipment_id: str | None = None,
    offset: int = 0, limit: int = 50,
    db: AsyncSession = Depends(get_db_session),
):
    svc = TradeDocumentService(db)
    return await svc.list(user["tenant_id"], document_type, po_id, so_id, shipment_id, offset, limit)


@router.post("/api/v1/trade-documents", response_model=TradeDocOut, status_code=201)
async def create_trade_doc(
    body: TradeDocCreate,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    svc = TradeDocumentService(db)
    doc = await svc.create(user["tenant_id"], {
        **body.model_dump(exclude={"metadata"}),
        "metadata": body.metadata,
        "created_by": user.get("user_id"),
    })
    await db.commit()
    return doc


@router.get("/api/v1/trade-documents/{doc_id}", response_model=TradeDocOut)
async def get_trade_doc(doc_id: str, user: ModuleUser, db: AsyncSession = Depends(get_db_session)):
    svc = TradeDocumentService(db)
    return await svc.get(doc_id, user["tenant_id"])


@router.patch("/api/v1/trade-documents/{doc_id}", response_model=TradeDocOut)
async def update_trade_doc(
    doc_id: str, body: TradeDocUpdate, user: ModuleUser, db: AsyncSession = Depends(get_db_session),
):
    svc = TradeDocumentService(db)
    doc = await svc.update(doc_id, user["tenant_id"], body.model_dump(exclude_none=True))
    await db.commit()
    return doc


@router.post("/api/v1/trade-documents/{doc_id}/approve", response_model=TradeDocOut)
async def approve_trade_doc(doc_id: str, user: ModuleUser, db: AsyncSession = Depends(get_db_session)):
    svc = TradeDocumentService(db)
    doc = await svc.approve(doc_id, user["tenant_id"])
    await db.commit()
    return doc


@router.post("/api/v1/trade-documents/{doc_id}/reject", response_model=TradeDocOut)
async def reject_trade_doc(
    doc_id: str, user: ModuleUser, reason: str | None = None, db: AsyncSession = Depends(get_db_session),
):
    svc = TradeDocumentService(db)
    doc = await svc.reject(doc_id, user["tenant_id"], reason)
    await db.commit()
    return doc


@router.delete("/api/v1/trade-documents/{doc_id}", status_code=204)
async def delete_trade_doc(doc_id: str, user: ModuleUser, db: AsyncSession = Depends(get_db_session)):
    svc = TradeDocumentService(db)
    await svc.delete(doc_id, user["tenant_id"])
    await db.commit()
