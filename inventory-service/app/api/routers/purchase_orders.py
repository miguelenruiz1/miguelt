"""Purchase orders endpoints."""
from __future__ import annotations

from typing import Annotated

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, Query, Request, Response, UploadFile
from fastapi.responses import ORJSONResponse

from app.api.deps import ModuleUser, require_permission
from app.db.models import POStatus
from app.db.session import get_db_session
from app.domain.schemas import PaginatedPOs, POCreate, POOut, POUpdate, ReceivePOIn
from app.domain.schemas.purchase_order import (
    ConsolidateRequest, ConsolidationCandidate, ConsolidationResult, ConsolidationInfo,
    PORejectIn, POApprovalLogOut,
)
from app.services.po_service import POService
from app.services.po_consolidation_service import POConsolidationService
from app.services.po_approval_service import POApprovalService
from app.services.audit_service import InventoryAuditService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/purchase-orders", tags=["purchase-orders"])


def _ip(request: Request) -> str | None:
    ff = request.headers.get("X-Forwarded-For")
    return ff.split(",")[0].strip() if ff else (request.client.host if request.client else None)


@router.get("", response_model=PaginatedPOs)
async def list_pos(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("purchase_orders.view"))],
    db: AsyncSession = Depends(get_db_session),
    status: POStatus | None = None,
    supplier_id: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> ORJSONResponse:
    svc = POService(db)
    items, total = await svc.list(
        tenant_id=current_user["tenant_id"],
        status=status,
        supplier_id=supplier_id,
        offset=offset,
        limit=limit,
    )
    return ORJSONResponse({
        "items": [POOut.model_validate(po).model_dump(mode="json") for po in items],
        "total": total,
        "offset": offset,
        "limit": limit,
    })


@router.post("", response_model=POOut, status_code=201)
async def create_po(
    body: POCreate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("purchase_orders.create"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = POService(db)
    audit = InventoryAuditService(db)
    data = body.model_dump()
    lines_raw = data.pop("lines", [])
    lines = [
        {
            "product_id": ln["product_id"],
            "qty_ordered": ln["qty_ordered"],
            "unit_cost": ln["unit_cost"],
            "line_total": ln["qty_ordered"] * ln["unit_cost"],
            "notes": ln.get("notes"),
        }
        for ln in lines_raw
    ]
    po = await svc.create_draft(
        tenant_id=current_user["tenant_id"],
        data={**data, "lines": lines, "created_by": current_user.get("id")},
    )
    po = await svc.get(po.id, current_user["tenant_id"])
    supplier_name = await svc.resolve_supplier_name(data.get("supplier_id"), current_user["tenant_id"])
    await audit.log(
        tenant_id=current_user["tenant_id"], user=current_user,
        action="inventory.po.create", resource_type="purchase_order",
        resource_id=po.id,
        new_data={
            "order_number": po.po_number,
            "supplier_name": supplier_name,
            "lines_count": len(lines),
            **body.model_dump(mode="json"),
        },
        ip_address=_ip(request),
    )
    return ORJSONResponse(POOut.model_validate(po).model_dump(mode="json"), status_code=201)


# ── Consolidation (static paths — must come before /{po_id}) ──────────


@router.post("/consolidate", response_model=ConsolidationResult, status_code=201)
async def consolidate_purchase_orders(
    body: ConsolidateRequest,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("purchase_orders.edit"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = POConsolidationService(db)
    result = await svc.consolidate(body.po_ids, current_user["tenant_id"], current_user.get("id", ""))
    audit = InventoryAuditService(db)
    await audit.log(
        tenant_id=current_user["tenant_id"], user=current_user,
        action="inventory.po.consolidate", resource_type="purchase_order",
        resource_id=result["consolidated_po"].id,
        new_data={"po_ids": body.po_ids},
        ip_address=_ip(request),
    )
    return ORJSONResponse(
        ConsolidationResult(
            consolidated_po=POOut.model_validate(result["consolidated_po"]),
            original_pos=[POOut.model_validate(po) for po in result["original_pos"]],
            lines_merged=result["lines_merged"],
            message=result["message"],
        ).model_dump(mode="json"),
        status_code=201,
    )


@router.get("/consolidation-candidates", response_model=list[ConsolidationCandidate])
async def consolidation_candidates(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("purchase_orders.view"))],
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = POConsolidationService(db)
    candidates = await svc.get_consolidation_candidates(current_user["tenant_id"])
    return ORJSONResponse([
        ConsolidationCandidate(
            supplier_id=c["supplier_id"],
            supplier_name=c["supplier_name"],
            po_count=c["po_count"],
            total_amount=c["total_amount"],
            pos=[POOut.model_validate(po) for po in c["pos"]],
        ).model_dump(mode="json")
        for c in candidates
    ])


@router.delete("/{po_id}", status_code=204)
async def delete_po(
    po_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("purchase_orders.delete"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    svc = POService(db)
    audit = InventoryAuditService(db)
    po = await svc.get(po_id, current_user["tenant_id"])
    await audit.log(
        tenant_id=current_user["tenant_id"], user=current_user,
        action="inventory.po.delete", resource_type="purchase_order",
        resource_id=po_id,
        old_data={"order_number": po.po_number, "status": po.status.value if hasattr(po.status, "value") else str(po.status)},
        new_data={"order_number": po.po_number},
        ip_address=_ip(request),
    )
    await svc.delete(po_id, current_user["tenant_id"])
    return Response(status_code=204)


@router.get("/{po_id}", response_model=POOut)
async def get_po(
    po_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("purchase_orders.view"))],
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = POService(db)
    po = await svc.get(po_id, current_user["tenant_id"])
    return ORJSONResponse(POOut.model_validate(po).model_dump(mode="json"))


@router.patch("/{po_id}", response_model=POOut)
async def update_po(
    po_id: str,
    body: POUpdate,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("purchase_orders.edit"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = POService(db)
    audit = InventoryAuditService(db)
    old = await svc.get(po_id, current_user["tenant_id"])
    old_data = POOut.model_validate(old).model_dump(mode="json")
    update_data = body.model_dump(exclude_none=True)
    update_data["updated_by"] = current_user.get("id")
    po = await svc.update(po_id, current_user["tenant_id"], update_data)
    po = await svc.get(po.id, current_user["tenant_id"])
    await audit.log(
        tenant_id=current_user["tenant_id"], user=current_user,
        action="inventory.po.update", resource_type="purchase_order",
        resource_id=po.id, old_data=old_data,
        new_data={"order_number": po.po_number, **body.model_dump(exclude_none=True)},
        ip_address=_ip(request),
    )
    return ORJSONResponse(POOut.model_validate(po).model_dump(mode="json"))


@router.post("/{po_id}/send", response_model=POOut)
async def send_po(
    po_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("purchase_orders.send"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = POService(db)
    audit = InventoryAuditService(db)
    old_po = await svc.get(po_id, current_user["tenant_id"])
    old_status = old_po.status.value if hasattr(old_po.status, "value") else str(old_po.status)
    po = await svc.send(po_id, current_user["tenant_id"], current_user.get("id"))
    po = await svc.get(po.id, current_user["tenant_id"])
    await audit.log(
        tenant_id=current_user["tenant_id"], user=current_user,
        action="inventory.po.send", resource_type="purchase_order",
        resource_id=po.id,
        old_data={"status": old_status},
        new_data={"order_number": po.po_number, "status": "sent"},
        ip_address=_ip(request),
    )
    return ORJSONResponse(POOut.model_validate(po).model_dump(mode="json"))


@router.post("/{po_id}/confirm", response_model=POOut)
async def confirm_po(
    po_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("purchase_orders.confirm"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = POService(db)
    audit = InventoryAuditService(db)
    old_po = await svc.get(po_id, current_user["tenant_id"])
    old_status = old_po.status.value if hasattr(old_po.status, "value") else str(old_po.status)
    po = await svc.confirm(po_id, current_user["tenant_id"], current_user.get("id"))
    po = await svc.get(po.id, current_user["tenant_id"])
    await audit.log(
        tenant_id=current_user["tenant_id"], user=current_user,
        action="inventory.po.confirm", resource_type="purchase_order",
        resource_id=po.id,
        old_data={"status": old_status},
        new_data={"order_number": po.po_number, "status": "confirmed"},
        ip_address=_ip(request),
    )
    return ORJSONResponse(POOut.model_validate(po).model_dump(mode="json"))


@router.post("/{po_id}/cancel", response_model=POOut)
async def cancel_po(
    po_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("purchase_orders.cancel"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = POService(db)
    audit = InventoryAuditService(db)
    old_po = await svc.get(po_id, current_user["tenant_id"])
    old_status = old_po.status.value if hasattr(old_po.status, "value") else str(old_po.status)
    po = await svc.cancel(po_id, current_user["tenant_id"])
    po = await svc.get(po.id, current_user["tenant_id"])
    await audit.log(
        tenant_id=current_user["tenant_id"], user=current_user,
        action="inventory.po.cancel", resource_type="purchase_order",
        resource_id=po.id,
        old_data={"status": old_status},
        new_data={"order_number": po.po_number, "status": "canceled"},
        ip_address=_ip(request),
    )
    return ORJSONResponse(POOut.model_validate(po).model_dump(mode="json"))


@router.post("/{po_id}/receive", response_model=POOut)
async def receive_po(
    po_id: str,
    body: ReceivePOIn,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("purchase_orders.receive"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = POService(db)
    audit = InventoryAuditService(db)
    po = await svc.receive_items(
        po_id=po_id,
        tenant_id=current_user["tenant_id"],
        line_receipts=[lr.model_dump() for lr in body.lines],
        performed_by=current_user.get("id"),
    )
    # Save attachments + invoice data directly on PO (bypass status check)
    if body.attachments:
        po.attachments = (po.attachments or []) + body.attachments
    if body.supplier_invoice_number:
        po.supplier_invoice_number = body.supplier_invoice_number
    if body.supplier_invoice_date:
        po.supplier_invoice_date = body.supplier_invoice_date
    if body.supplier_invoice_total is not None:
        po.supplier_invoice_total = body.supplier_invoice_total
    if body.payment_terms:
        po.payment_terms = body.payment_terms
    if body.payment_due_date:
        po.payment_due_date = body.payment_due_date
    await db.flush()
    po = await svc.get(po.id, current_user["tenant_id"])
    await audit.log(
        tenant_id=current_user["tenant_id"], user=current_user,
        action="inventory.po.receive", resource_type="purchase_order",
        resource_id=po.id,
        new_data={"order_number": po.po_number, **body.model_dump(mode="json")},
        ip_address=_ip(request),
    )

    # Fire-and-forget: notify trace-service about received items
    from app.clients import trace_client
    for lr in body.lines:
        if lr.received_quantity and lr.received_quantity > 0:
            await trace_client.notify_po_received_background(
                tenant_id=current_user["tenant_id"],
                po_id=po.id,
                entity_id=lr.entity_id,
                warehouse_id=po.warehouse_id,
                quantity=int(lr.received_quantity),
                batch_id=getattr(lr, "batch_id", None),
            )

    return ORJSONResponse(POOut.model_validate(po).model_dump(mode="json"))


# ── Approval workflow ──────────────────────────────────────────────────


@router.post("/{po_id}/submit-approval", response_model=POOut)
async def submit_po_for_approval(
    po_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("purchase_orders.send"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = POService(db)
    approval_svc = POApprovalService(db)
    audit = InventoryAuditService(db)
    po = await svc.get(po_id, current_user["tenant_id"])
    po = await approval_svc.submit_for_approval(
        po, current_user.get("id", ""), current_user.get("full_name"),
    )
    await audit.log(
        tenant_id=current_user["tenant_id"], user=current_user,
        action="inventory.po.submit_approval", resource_type="purchase_order",
        resource_id=po.id,
        new_data={"order_number": po.po_number, "status": "pending_approval"},
        ip_address=_ip(request),
    )
    po = await svc.get(po.id, current_user["tenant_id"])
    return ORJSONResponse(POOut.model_validate(po).model_dump(mode="json"))


@router.post("/{po_id}/approve", response_model=POOut)
async def approve_po(
    po_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("purchase_orders.approve"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = POService(db)
    approval_svc = POApprovalService(db)
    audit = InventoryAuditService(db)
    po = await svc.get(po_id, current_user["tenant_id"])
    po = await approval_svc.approve(
        po, current_user.get("id", ""), current_user.get("full_name"),
    )
    await audit.log(
        tenant_id=current_user["tenant_id"], user=current_user,
        action="inventory.po.approve", resource_type="purchase_order",
        resource_id=po.id,
        new_data={"order_number": po.po_number, "status": "approved"},
        ip_address=_ip(request),
    )
    po = await svc.get(po.id, current_user["tenant_id"])
    return ORJSONResponse(POOut.model_validate(po).model_dump(mode="json"))


@router.post("/{po_id}/reject", response_model=POOut)
async def reject_po(
    po_id: str,
    body: PORejectIn,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("purchase_orders.approve"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = POService(db)
    approval_svc = POApprovalService(db)
    audit = InventoryAuditService(db)
    po = await svc.get(po_id, current_user["tenant_id"])
    po = await approval_svc.reject(
        po, current_user.get("id", ""), body.reason, current_user.get("full_name"),
    )
    await audit.log(
        tenant_id=current_user["tenant_id"], user=current_user,
        action="inventory.po.reject", resource_type="purchase_order",
        resource_id=po.id,
        new_data={"order_number": po.po_number, "status": "draft", "reason": body.reason},
        ip_address=_ip(request),
    )
    po = await svc.get(po.id, current_user["tenant_id"])
    return ORJSONResponse(POOut.model_validate(po).model_dump(mode="json"))


@router.get("/{po_id}/approval-log", response_model=list[POApprovalLogOut])
async def get_po_approval_log(
    po_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("purchase_orders.view"))],
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    approval_svc = POApprovalService(db)
    logs = await approval_svc.get_approval_log(po_id, current_user["tenant_id"])
    return ORJSONResponse([POApprovalLogOut.model_validate(l).model_dump(mode="json") for l in logs])


# ── File upload for PO attachments ────────────────────────────────────


@router.post("/{po_id}/upload-attachment")
async def upload_po_attachment(
    po_id: str,
    file: UploadFile,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("purchase_orders.receive"))],
    db: AsyncSession = Depends(get_db_session),
    classification: str = Query("other"),
) -> ORJSONResponse:
    """Upload a file attachment to a PO via media-service."""
    from app.clients.media_client import upload_file as media_upload

    allowed_types = {"application/pdf", "image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tipo de archivo no permitido. Use PDF, JPG, PNG o WEBP.")

    content = await file.read()
    max_size = 10 * 1024 * 1024  # 10MB
    if len(content) > max_size:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="El archivo excede el límite de 10 MB.")

    media_file = await media_upload(
        tenant_id=current_user["tenant_id"],
        file_bytes=content,
        filename=file.filename or f"po-{po_id}.{file.content_type.split('/')[-1]}",
        content_type=file.content_type,
        category="general",
        document_type=classification,
        title=f"Adjunto OC {po_id} — {classification}",
        uploaded_by=current_user.get("user_id"),
    )
    if not media_file:
        raise HTTPException(status_code=502, detail="Error al subir archivo a media-service")

    attachment = {
        "media_file_id": media_file["id"],
        "url": media_file["url"],
        "name": file.filename or media_file["filename"],
        "type": file.content_type,
        "classification": classification,
    }

    svc = POService(db)
    po = await svc.get(po_id, current_user["tenant_id"])
    existing = po.attachments or []
    po.attachments = existing + [attachment]
    await db.flush()

    return ORJSONResponse(attachment)


# ── Consolidation info / deconsolidate (parameterised paths) ──────────


@router.get("/{po_id}/consolidation-info", response_model=ConsolidationInfo)
async def get_consolidation_info(
    po_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("purchase_orders.view"))],
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = POConsolidationService(db)
    info = await svc.get_consolidation_info(po_id, current_user["tenant_id"])
    return ORJSONResponse(
        ConsolidationInfo(
            type=info["type"],
            consolidated_po=POOut.model_validate(info["consolidated_po"]) if info["consolidated_po"] else None,
            original_pos=[POOut.model_validate(po) for po in info["original_pos"]] if info["original_pos"] else None,
            consolidated_at=info["consolidated_at"],
            consolidated_by=info["consolidated_by"],
        ).model_dump(mode="json")
    )


@router.post("/{po_id}/deconsolidate")
async def deconsolidate_purchase_order(
    po_id: str,
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("purchase_orders.edit"))],
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = POConsolidationService(db)
    originals = await svc.deconsolidate(po_id, current_user["tenant_id"])
    audit = InventoryAuditService(db)
    await audit.log(
        tenant_id=current_user["tenant_id"], user=current_user,
        action="inventory.po.deconsolidate", resource_type="purchase_order",
        resource_id=po_id,
        ip_address=_ip(request),
    )
    return ORJSONResponse([POOut.model_validate(po).model_dump(mode="json") for po in originals])
