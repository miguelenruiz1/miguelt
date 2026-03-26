"""Business logic for shipment documents and trade documents."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, ValidationError
from app.db.models.shipment import ShipmentDocument, TradeDocument


class ShipmentDocumentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(
        self, tenant_id: str, document_type: str | None = None,
        po_id: str | None = None, so_id: str | None = None,
        offset: int = 0, limit: int = 50,
    ):
        q = select(ShipmentDocument).where(ShipmentDocument.tenant_id == tenant_id)
        if document_type:
            q = q.where(ShipmentDocument.document_type == document_type)
        if po_id:
            q = q.where(ShipmentDocument.purchase_order_id == po_id)
        if so_id:
            q = q.where(ShipmentDocument.sales_order_id == so_id)
        q = q.order_by(ShipmentDocument.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def get(self, doc_id: str, tenant_id: str) -> ShipmentDocument:
        q = select(ShipmentDocument).where(
            ShipmentDocument.id == doc_id, ShipmentDocument.tenant_id == tenant_id
        )
        doc = (await self.db.execute(q)).scalar_one_or_none()
        if not doc:
            raise NotFoundError("Documento de transporte no encontrado")
        return doc

    async def create(self, tenant_id: str, data: dict) -> ShipmentDocument:
        if "metadata" in data:
            data["metadata_"] = data.pop("metadata")
        doc = ShipmentDocument(id=str(uuid.uuid4()), tenant_id=tenant_id, **data)
        self.db.add(doc)
        await self.db.flush()

        # Auto-anchor shipment documents
        await self._try_anchor(doc, tenant_id)
        return doc

    async def update(self, doc_id: str, tenant_id: str, data: dict) -> ShipmentDocument:
        doc = await self.get(doc_id, tenant_id)
        if "metadata" in data:
            data["metadata_"] = data.pop("metadata")
        for k, v in data.items():
            if v is not None and hasattr(doc, k):
                setattr(doc, k, v)
        await self.db.flush()
        return doc

    async def update_status(self, doc_id: str, tenant_id: str, status: str) -> ShipmentDocument:
        doc = await self.get(doc_id, tenant_id)
        valid = {"draft", "issued", "in_transit", "delivered", "canceled"}
        if status not in valid:
            raise ValidationError(f"Estado invalido: {status}. Validos: {valid}")
        doc.status = status
        if status == "delivered" and not doc.actual_arrival:
            doc.actual_arrival = datetime.now(timezone.utc)
        await self.db.flush()

        # Re-anchor on delivery
        if status == "delivered":
            await self._try_anchor(doc, tenant_id)
        return doc

    async def delete(self, doc_id: str, tenant_id: str) -> None:
        doc = await self.get(doc_id, tenant_id)
        await self.db.delete(doc)
        await self.db.flush()

    async def _try_anchor(self, doc: ShipmentDocument, tenant_id: str) -> None:
        try:
            from app.utils.hashing import compute_anchor_hash
            from app.clients import trace_client

            payload = {
                "document_type": doc.document_type,
                "document_number": doc.document_number,
                "carrier_name": doc.carrier_name,
                "origin": doc.origin_city or doc.origin_country,
                "destination": doc.destination_city or doc.destination_country,
                "status": doc.status,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "tenant_id": tenant_id,
            }
            anchor_hash = compute_anchor_hash(payload)
            doc.anchor_hash = anchor_hash
            doc.anchor_status = "pending"
            await self.db.flush()

            await trace_client.anchor_event_background(
                tenant_id=tenant_id,
                source_entity_type="shipment_document",
                source_entity_id=doc.id,
                payload_hash=anchor_hash,
            )
        except Exception:
            pass


class TradeDocumentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(
        self, tenant_id: str, document_type: str | None = None,
        po_id: str | None = None, so_id: str | None = None,
        shipment_id: str | None = None,
        offset: int = 0, limit: int = 50,
    ):
        q = select(TradeDocument).where(TradeDocument.tenant_id == tenant_id)
        if document_type:
            q = q.where(TradeDocument.document_type == document_type)
        if po_id:
            q = q.where(TradeDocument.purchase_order_id == po_id)
        if so_id:
            q = q.where(TradeDocument.sales_order_id == so_id)
        if shipment_id:
            q = q.where(TradeDocument.shipment_document_id == shipment_id)
        q = q.order_by(TradeDocument.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def get(self, doc_id: str, tenant_id: str) -> TradeDocument:
        q = select(TradeDocument).where(
            TradeDocument.id == doc_id, TradeDocument.tenant_id == tenant_id
        )
        doc = (await self.db.execute(q)).scalar_one_or_none()
        if not doc:
            raise NotFoundError("Documento de comercio exterior no encontrado")
        return doc

    async def create(self, tenant_id: str, data: dict) -> TradeDocument:
        if "metadata" in data:
            data["metadata_"] = data.pop("metadata")
        if "content_data" not in data:
            data["content_data"] = {}

        # Compute file hash if file_url provided
        doc = TradeDocument(id=str(uuid.uuid4()), tenant_id=tenant_id, **data)
        self.db.add(doc)
        await self.db.flush()

        # Auto-anchor trade documents
        await self._try_anchor(doc, tenant_id)
        return doc

    async def update(self, doc_id: str, tenant_id: str, data: dict) -> TradeDocument:
        doc = await self.get(doc_id, tenant_id)
        if "metadata" in data:
            data["metadata_"] = data.pop("metadata")
        for k, v in data.items():
            if v is not None and hasattr(doc, k):
                setattr(doc, k, v)
        await self.db.flush()
        return doc

    async def approve(self, doc_id: str, tenant_id: str) -> TradeDocument:
        doc = await self.get(doc_id, tenant_id)
        if doc.status not in ("pending", "rejected"):
            raise ValidationError(f"No se puede aprobar documento con estado '{doc.status}'")
        doc.status = "approved"
        await self.db.flush()
        await self._try_anchor(doc, tenant_id)
        return doc

    async def reject(self, doc_id: str, tenant_id: str, reason: str | None = None) -> TradeDocument:
        doc = await self.get(doc_id, tenant_id)
        doc.status = "rejected"
        if reason:
            doc.notes = reason
        await self.db.flush()
        return doc

    async def delete(self, doc_id: str, tenant_id: str) -> None:
        doc = await self.get(doc_id, tenant_id)
        await self.db.delete(doc)
        await self.db.flush()

    async def _try_anchor(self, doc: TradeDocument, tenant_id: str) -> None:
        try:
            from app.utils.hashing import compute_anchor_hash
            from app.clients import trace_client

            payload = {
                "document_type": doc.document_type,
                "document_number": doc.document_number,
                "title": doc.title,
                "issuing_authority": doc.issuing_authority,
                "hs_code": doc.hs_code,
                "file_hash": doc.file_hash,
                "status": doc.status,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "tenant_id": tenant_id,
            }
            anchor_hash = compute_anchor_hash(payload)
            doc.anchor_hash = anchor_hash
            doc.anchor_status = "pending"
            doc.anchored_at = None
            await self.db.flush()

            await trace_client.anchor_event_background(
                tenant_id=tenant_id,
                source_entity_type="trade_document",
                source_entity_id=doc.id,
                payload_hash=anchor_hash,
            )
        except Exception:
            pass
