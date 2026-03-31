"""Outbound webhook subscriptions — manage what events Trace sends to external URLs."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import ORJSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_permission
from app.db.session import get_db_session
from app.services.webhook_service import WebhookService

router = APIRouter(prefix="/api/v1/webhooks/subscriptions", tags=["webhook-subscriptions"])

# Available events catalog
EVENTS_CATALOG = [
    {"event": "inventory.po.received", "label": "OC Recibida", "source": "inventory"},
    {"event": "inventory.so.shipped", "label": "OV Despachada", "source": "inventory"},
    {"event": "inventory.so.delivered", "label": "OV Entregada", "source": "inventory"},
    {"event": "inventory.stock.alert", "label": "Alerta de stock", "source": "inventory"},
    {"event": "inventory.movement.created", "label": "Movimiento creado", "source": "inventory"},
    {"event": "production.run.completed", "label": "Produccion completada", "source": "inventory"},
    {"event": "production.run.closed", "label": "Produccion cerrada", "source": "inventory"},
    {"event": "trace.asset.created", "label": "Carga creada", "source": "trace"},
    {"event": "trace.event.recorded", "label": "Evento de custodia", "source": "trace"},
    {"event": "trace.asset.delivered", "label": "Carga entregada", "source": "trace"},
    {"event": "compliance.record.validated", "label": "Registro EUDR validado", "source": "compliance"},
    {"event": "compliance.certificate.generated", "label": "Certificado generado", "source": "compliance"},
    {"event": "compliance.dds.submitted", "label": "DDS enviada a TRACES NT", "source": "compliance"},
    {"event": "media.file.uploaded", "label": "Archivo subido", "source": "media"},
]


def _svc(db: AsyncSession = Depends(get_db_session)) -> WebhookService:
    return WebhookService(db)


@router.get("/events-catalog")
async def get_events_catalog():
    """List all available events that can trigger webhooks."""
    return EVENTS_CATALOG


@router.get("")
async def list_subscriptions(
    current_user: Annotated[dict, Depends(get_current_user)],
    _: Annotated[dict, Depends(require_permission("integrations.view"))],
    svc: WebhookService = Depends(_svc),
):
    tenant_id = current_user.get("tenant_id", "default")
    subs = await svc.list_subscriptions(tenant_id)
    return [_sub_out(s) for s in subs]


@router.post("", status_code=201)
async def create_subscription(
    body: dict,
    current_user: Annotated[dict, Depends(get_current_user)],
    _: Annotated[dict, Depends(require_permission("integrations.manage"))],
    svc: WebhookService = Depends(_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    sub = await svc.create_subscription(tenant_id, body, current_user.get("id"))
    await db.commit()
    return _sub_out(sub)


@router.get("/{sub_id}")
async def get_subscription(
    sub_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    _: Annotated[dict, Depends(require_permission("integrations.view"))],
    svc: WebhookService = Depends(_svc),
):
    tenant_id = current_user.get("tenant_id", "default")
    sub = await svc.get_subscription(tenant_id, sub_id)
    if not sub:
        return Response(status_code=404)
    return _sub_out(sub)


@router.patch("/{sub_id}")
async def update_subscription(
    sub_id: str,
    body: dict,
    current_user: Annotated[dict, Depends(get_current_user)],
    _: Annotated[dict, Depends(require_permission("integrations.manage"))],
    svc: WebhookService = Depends(_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    sub = await svc.update_subscription(tenant_id, sub_id, body)
    if not sub:
        return Response(status_code=404)
    await db.commit()
    return _sub_out(sub)


@router.delete("/{sub_id}", status_code=204)
async def delete_subscription(
    sub_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    _: Annotated[dict, Depends(require_permission("integrations.manage"))],
    svc: WebhookService = Depends(_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    ok = await svc.delete_subscription(tenant_id, sub_id)
    if not ok:
        return Response(status_code=404)
    await db.commit()
    return Response(status_code=204)


@router.post("/{sub_id}/test")
async def test_subscription(
    sub_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    _: Annotated[dict, Depends(require_permission("integrations.manage"))],
    svc: WebhookService = Depends(_svc),
    db: AsyncSession = Depends(get_db_session),
):
    tenant_id = current_user.get("tenant_id", "default")
    result = await svc.send_test(tenant_id, sub_id)
    await db.commit()
    return result


@router.get("/{sub_id}/deliveries")
async def list_deliveries(
    sub_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    _: Annotated[dict, Depends(require_permission("integrations.view"))],
    status: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    svc: WebhookService = Depends(_svc),
):
    tenant_id = current_user.get("tenant_id", "default")
    deliveries = await svc.list_deliveries(tenant_id, sub_id, status, offset, limit)
    return [_delivery_out(d) for d in deliveries]


def _sub_out(s) -> dict:
    return {
        "id": s.id,
        "tenant_id": s.tenant_id,
        "name": s.name,
        "target_url": s.target_url,
        "secret": s.secret[:8] + "..." if s.secret else None,
        "events": s.events,
        "headers": s.headers,
        "is_active": s.is_active,
        "retry_policy": s.retry_policy,
        "max_retries": s.max_retries,
        "last_triggered_at": s.last_triggered_at.isoformat() if s.last_triggered_at else None,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


def _delivery_out(d) -> dict:
    return {
        "id": d.id,
        "subscription_id": d.subscription_id,
        "event_type": d.event_type,
        "status": d.status,
        "http_status": d.http_status,
        "response_body": d.response_body[:500] if d.response_body else None,
        "attempts": d.attempts,
        "next_retry_at": d.next_retry_at.isoformat() if d.next_retry_at else None,
        "created_at": d.created_at.isoformat() if d.created_at else None,
        "delivered_at": d.delivered_at.isoformat() if d.delivered_at else None,
    }
