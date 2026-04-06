"""CRUD router for compliance integrations (GFW, TRACES NT) — superuser only."""
from __future__ import annotations

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
    env: str | None = None


def _require_admin(user: dict) -> None:
    if not user.get("is_superuser") and "compliance.manage" not in (user.get("permissions") or []):
        raise HTTPException(status_code=403, detail="Acceso denegado: requiere superusuario o permiso compliance.manage")


@router.get("/")
async def list_integrations(
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    _require_admin(user)
    svc = IntegrationCredentialsService(db)
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
    svc = IntegrationCredentialsService(db)
    return await svc.update(provider, body.model_dump(exclude_none=True))


@router.post("/{provider}/test")
async def test_integration(
    provider: str,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Test integration credentials by making a small API call."""
    _require_admin(user)
    svc = IntegrationCredentialsService(db)
    creds = await svc.get_credentials(provider)
    if not creds:
        return {"ok": False, "error": "No credentials configured"}

    if provider == "gfw":
        if not creds.get("api_key"):
            return {"ok": False, "error": "API key not set"}
        # Try a simple GET to verify
        import httpx
        try:
            async with httpx.AsyncClient(timeout=10.0) as http:
                resp = await http.get("https://data-api.globalforestwatch.org/dataset/gfw_integrated_alerts/latest", headers={"x-api-key": creds["api_key"]})
                if resp.status_code == 200:
                    return {"ok": True, "message": "Conexión exitosa con Global Forest Watch"}
                return {"ok": False, "error": f"GFW API returned {resp.status_code}"}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    if provider == "traces_nt":
        if not creds.get("username") or not creds.get("auth_key"):
            return {"ok": False, "error": "Username y auth_key son requeridos"}
        return {"ok": True, "message": f"Credenciales TRACES NT configuradas (env: {creds.get('env', 'acceptance')})"}

    return {"ok": False, "error": "Provider no soportado"}
