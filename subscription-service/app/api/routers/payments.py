"""Payments router — manage Trace's payment gateway configuration (superuser only)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user
from app.db.session import get_db_session
from app.domain.schemas import GatewayConfigSave
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


def _svc(db: Annotated[AsyncSession, Depends(get_db_session)]) -> PaymentService:
    return PaymentService(db)


def _require_superuser(current_user: CurrentUser) -> dict:
    """Only Trace platform operators (is_superuser) can manage payment gateways."""
    if not current_user.get("is_superuser"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los operadores de la plataforma pueden gestionar las pasarelas de cobro.",
        )
    return current_user


SuperuserDep = Annotated[dict, Depends(_require_superuser)]


@router.get("/catalog", summary="Gateway catalogue (public)")
async def get_catalog(svc: PaymentService = Depends(_svc)) -> list[dict]:
    return svc.get_catalog()


@router.get("/{tenant_id}/active", summary="Active gateway (public, inter-service)")
async def get_active_gateway(
    tenant_id: str,
    svc: PaymentService = Depends(_svc),
) -> dict | None:
    return await svc.get_active(tenant_id)


@router.get("/{tenant_id}", summary="All gateway configs — superuser only")
async def list_gateway_configs(
    tenant_id: str,
    _: SuperuserDep,
    svc: PaymentService = Depends(_svc),
) -> list[dict]:
    return await svc.list_configs(tenant_id)


@router.post("/{tenant_id}/{slug}", summary="Save/update gateway config — superuser only")
async def save_gateway_config(
    tenant_id: str,
    slug: str,
    body: GatewayConfigSave,
    _: SuperuserDep,
    svc: PaymentService = Depends(_svc),
) -> dict:
    try:
        return await svc.save_config(
            tenant_id=tenant_id,
            slug=slug,
            credentials=body.credentials,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/{tenant_id}/{slug}/activate", summary="Set gateway as active — superuser only")
async def activate_gateway(
    tenant_id: str,
    slug: str,
    _: SuperuserDep,
    svc: PaymentService = Depends(_svc),
) -> dict:
    try:
        return await svc.set_active(tenant_id, slug)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.delete("/{tenant_id}/{slug}", summary="Delete gateway config — superuser only")
async def delete_gateway_config(
    tenant_id: str,
    slug: str,
    _: SuperuserDep,
    svc: PaymentService = Depends(_svc),
) -> dict:
    deleted = await svc.delete_config(tenant_id, slug)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No configuration found for gateway '{slug}'",
        )
    return {"deleted": True, "slug": slug}
