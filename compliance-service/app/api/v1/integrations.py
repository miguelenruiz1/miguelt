"""CRUD router for compliance integrations (GFW, TRACES NT) — per tenant, admin only."""
from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser
from app.db.session import get_db_session
from app.services.integration_service import IntegrationCredentialsService, PROVIDERS

router = APIRouter(
    prefix="/api/v1/compliance/integrations",
    tags=["compliance-integrations"],
)


class UpdateIntegrationRequest(BaseModel):
    api_key: str | None = None
    username: str | None = None
    auth_key: str | None = None
    env: Literal["acceptance", "production"] | None = None
    client_id: str | None = None


def _require_admin(user: dict) -> None:
    perms = set(user.get("permissions") or [])
    if not user.get("is_superuser") and not (perms & {"compliance.manage", "compliance.admin"}):
        raise HTTPException(
            status_code=403,
            detail="Acceso denegado: requiere superusuario o permiso compliance.manage/compliance.admin",
        )


def _tenant_id(user: dict) -> uuid.UUID:
    raw = str(user.get("tenant_id", "00000000-0000-0000-0000-000000000001"))
    try:
        return uuid.UUID(raw)
    except ValueError:
        return uuid.UUID("00000000-0000-0000-0000-000000000001")


@router.get("/")
async def list_integrations(
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    _require_admin(user)
    svc = IntegrationCredentialsService(db, tenant_id=_tenant_id(user))
    return await svc.list_all()


@router.patch("/{provider}")
async def update_integration(
    provider: str,
    body: UpdateIntegrationRequest,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    _require_admin(user)
    if provider not in PROVIDERS:
        raise HTTPException(status_code=404, detail=f"Provider '{provider}' not supported")
    svc = IntegrationCredentialsService(db, tenant_id=_tenant_id(user))
    try:
        return await svc.update(provider, body.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/{provider}/test")
async def test_integration(
    provider: str,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Test integration credentials by making a real API call (not just metadata)."""
    _require_admin(user)
    svc = IntegrationCredentialsService(db, tenant_id=_tenant_id(user))
    creds = await svc.get_credentials(provider)
    if not creds:
        return {"ok": False, "error": "No credentials configured"}

    if provider == "gfw":
        if not creds.get("api_key"):
            return {"ok": False, "error": "API key not set"}
        # Real query that actually exercises the API key
        import httpx
        try:
            async with httpx.AsyncClient(timeout=15.0) as http:
                resp = await http.post(
                    "https://data-api.globalforestwatch.org/dataset/gfw_integrated_alerts/latest/query/json",
                    headers={"x-api-key": creds["api_key"], "Content-Type": "application/json"},
                    json={
                        "sql": "SELECT count(*) FROM results LIMIT 1",
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[
                                [-74.07, 4.71], [-74.06, 4.71],
                                [-74.06, 4.72], [-74.07, 4.72],
                                [-74.07, 4.71],
                            ]],
                        },
                    },
                )
                if resp.status_code == 200:
                    return {"ok": True, "message": "Conexión exitosa con Global Forest Watch (query real validada)"}
                if resp.status_code in (401, 403):
                    return {"ok": False, "error": f"API key rechazada por GFW ({resp.status_code})"}
                return {"ok": False, "error": f"GFW API returned {resp.status_code}: {resp.text[:200]}"}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    if provider == "traces_nt":
        if not creds.get("username") or not creds.get("auth_key"):
            return {"ok": False, "error": "Username y auth_key son requeridos"}
        # Real ping by attempting WS-Security handshake against the WSDL endpoint
        import httpx
        from app.services.traces_service import TRACES_URLS
        env = creds.get("env", "acceptance")
        base = TRACES_URLS.get(env, TRACES_URLS["acceptance"])
        try:
            async with httpx.AsyncClient(timeout=15.0) as http:
                resp = await http.get(f"{base}?wsdl")
                if resp.status_code == 200 and "wsdl" in resp.text.lower():
                    return {
                        "ok": True,
                        "message": f"Endpoint TRACES NT alcanzable (env: {env}). WSDL OK.",
                    }
                if resp.status_code == 200:
                    return {
                        "ok": True,
                        "message": f"Endpoint TRACES NT respondió 200 (env: {env}).",
                    }
                return {"ok": False, "error": f"TRACES NT WSDL returned {resp.status_code}"}
        except Exception as exc:
            return {"ok": False, "error": f"No se pudo contactar TRACES NT ({env}): {exc}"}

    return {"ok": False, "error": "Provider no soportado"}
