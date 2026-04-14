"""FastAPI dependency functions shared across routers."""
from __future__ import annotations

import json
import re
import uuid
from typing import Annotated

import httpx
import redis.asyncio as aioredis
from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ForbiddenError, NotFoundError, UnauthorizedError
from app.core.settings import get_settings
from app.db.session import get_db_session

_http: httpx.AsyncClient | None = None
_redis: aioredis.Redis | None = None
_bearer = HTTPBearer(auto_error=False)


def get_http_client() -> httpx.AsyncClient:
    global _http
    if _http is None or _http.is_closed:
        _http = httpx.AsyncClient(timeout=10.0)
    return _http


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(get_settings().REDIS_URL, decode_responses=True)
    return _redis


async def get_tenant_id(
    request: Request,
    x_tenant_id: str = Header(..., alias="X-Tenant-Id"),
    db: AsyncSession = Depends(get_db_session),
) -> uuid.UUID:
    """
    Resolves X-Tenant-Id (slug or UUID string) → validated tenant UUID.

    Caches the resolved UUID on request.state._tenant_id to avoid
    double DB lookups when multiple dependencies call this.
    """
    # Input length validation
    if len(x_tenant_id) > 255:
        raise UnauthorizedError("Invalid tenant identifier")

    # Check cache first
    cached = getattr(request.state, "_tenant_id", None)
    if cached is not None:
        return cached

    from app.db.models import Tenant
    from sqlalchemy import select

    # Try parsing as UUID first, then fall back to slug lookup
    tenant_uuid: uuid.UUID | None = None
    try:
        tenant_uuid = uuid.UUID(x_tenant_id)
        result = await db.execute(select(Tenant).where(Tenant.id == tenant_uuid))
        tenant = result.scalar_one_or_none()
    except ValueError:
        # Not a UUID — treat as slug; validate format
        if not re.match(r'^[a-zA-Z0-9_-]+$', x_tenant_id):
            raise UnauthorizedError("Invalid tenant identifier")
        result = await db.execute(select(Tenant).where(Tenant.slug == x_tenant_id))
        tenant = result.scalar_one_or_none()

    if tenant is not None and tenant.status != "active":
        raise UnauthorizedError("Invalid or inactive tenant")

    # Auto-provision: user-service is the source of truth for tenant creation.
    # If a request arrives with a valid JWT and a tenant slug that doesn't exist
    # here yet, create it lazily so all services stay in sync.
    if tenant is None:
        if not re.match(r'^[a-zA-Z0-9_-]+$', x_tenant_id) and tenant_uuid is None:
            raise UnauthorizedError("Invalid tenant identifier")
        new_id = tenant_uuid or uuid.uuid4()
        slug = x_tenant_id if tenant_uuid is None else x_tenant_id
        new_tenant = Tenant(
            id=new_id,
            name=slug.replace("-", " ").title(),
            slug=slug,
            status="active",
            metadata={},
        )
        db.add(new_tenant)
        await db.flush()
        tenant = new_tenant
        # Seed default workflow (states, transitions, event types)
        await _seed_workflow_for_tenant(db, str(new_id))

    request.state._tenant_id = tenant.id
    return tenant.id


async def _seed_workflow_for_tenant(db: AsyncSession, tenant_id: str) -> None:
    """Seed default workflow states, transitions, and event types for a new tenant."""
    from sqlalchemy import text

    _STATES = [
        ("in_custody",   "En custodia",      "#8b5cf6", "package",        True,  False, 0),
        ("in_transit",   "En tránsito",      "#f59e0b", "truck",          False, False, 1),
        ("loaded",       "Cargado",          "#3b82f6", "container",      False, False, 2),
        ("qc_passed",    "QC aprobado",      "#22c55e", "check-circle",   False, False, 3),
        ("qc_failed",    "QC fallido",       "#ef4444", "x-circle",       False, False, 4),
        ("customs_hold", "Retención aduana", "#f97316", "shield-alert",   False, False, 5),
        ("damaged",      "Dañado",           "#dc2626", "alert-triangle", False, False, 6),
        ("sealed",       "Sellado",          "#06b6d4", "lock",           False, False, 7),
        ("released",     "Liberado",         "#10b981", "unlock",         False, True,  8),
        ("burned",       "Consumido",        "#6b7280", "flame",          False, True,  9),
        ("delivered",    "Entregado",        "#059669", "check-circle-2", False, True,  10),
    ]
    _TRANSITIONS = [
        ("in_custody", "in_transit", "HANDOFF", "Handoff"),
        ("in_transit", "in_custody", "ARRIVED", "Arrived"),
        ("in_custody", "loaded",     "LOADED",  "Loaded"),
        ("loaded",     "qc_passed",  "QC",      "QC passed"),
        ("loaded",     "qc_failed",  "QC",      "QC failed"),
        ("qc_failed",  "qc_passed",  "QC",      "QC re-inspect"),
        ("in_custody", "in_transit",  "PICKUP",  "Pickup"),
        ("in_transit", "in_custody",  "GATE_IN", "Gate in"),
        ("in_custody", "in_transit",  "GATE_OUT","Gate out"),
        ("in_custody", "customs_hold","CUSTOMS_HOLD","Customs hold"),
        ("in_transit", "customs_hold","CUSTOMS_HOLD","Customs hold"),
        ("customs_hold","in_custody", "CUSTOMS_CLEARED","Customs cleared"),
        ("loaded",     "sealed",     "SEALED",  "Sealed"),
        ("sealed",     "loaded",     "UNSEALED","Unsealed"),
        ("in_custody", "delivered",  "DELIVERED","Delivered"),
        ("in_transit", "delivered",  "DELIVERED","Delivered"),
        ("qc_passed",  "delivered",  "DELIVERED","Delivered"),
    ]
    # Terminal transitions (from any non-terminal)
    _NON_TERMINAL = [s[0] for s in _STATES if not s[5]]
    for src in _NON_TERMINAL:
        _TRANSITIONS.append((src, "released", "RELEASED", "Release"))
        _TRANSITIONS.append((src, "burned",   "BURN",     "Burn"))
        _TRANSITIONS.append((src, "damaged",  "DAMAGED",  "Damaged"))

    _EVENT_TYPES = [
        ("CREATED",         "Creado",            "plus-circle",   "#22c55e", False, False, False, False, False, 0),
        ("HANDOFF",         "Handoff",           "arrow-right",   "#3b82f6", False, True,  False, False, False, 1),
        ("ARRIVED",         "Arrived",           "map-pin",       "#8b5cf6", False, False, False, False, False, 2),
        ("LOADED",          "Loaded",            "container",     "#06b6d4", False, False, False, False, False, 3),
        ("QC",              "Control de calidad","clipboard-check","#f59e0b",False, False, True,  False, False, 4),
        ("RELEASED",        "Liberado",          "unlock",        "#10b981", False, False, False, True,  True,  5),
        ("BURN",            "Consumido",         "flame",         "#ef4444", False, False, False, True,  False, 6),
        ("PICKUP",          "Recolección",       "package-check", "#3b82f6", False, True,  False, False, False, 7),
        ("GATE_IN",         "Gate In",           "log-in",        "#8b5cf6", False, False, False, False, False, 8),
        ("GATE_OUT",        "Gate Out",          "log-out",       "#f59e0b", False, False, False, False, False, 9),
        ("CUSTOMS_HOLD",    "Retención aduana",  "shield-alert",  "#f97316", False, False, True,  False, False, 10),
        ("CUSTOMS_CLEARED", "Liberado aduana",   "shield-check",  "#22c55e", False, False, False, False, False, 11),
        ("DAMAGED",         "Dañado",            "alert-triangle","#dc2626", False, False, True,  True,  True,  12),
        ("DELIVERED",       "Entregado",         "check-circle",  "#059669", False, True,  False, False, False, 13),
        ("SEALED",          "Sellado",           "lock",          "#06b6d4", False, False, False, False, False, 14),
        ("UNSEALED",        "Sello removido",    "unlock",        "#f59e0b", False, False, False, False, False, 15),
    ]

    slug_to_id: dict[str, str] = {}
    for slug, label, color, icon, is_initial, is_terminal, sort_order in _STATES:
        sid = str(uuid.uuid4())
        slug_to_id[slug] = sid
        await db.execute(text(
            "INSERT INTO workflow_states "
            "(id, tenant_id, slug, label, color, icon, is_initial, is_terminal, sort_order) "
            "VALUES (:id, :tid, :slug, :label, :color, :icon, :ii, :it, :so)"
        ), {"id": sid, "tid": tenant_id, "slug": slug, "label": label,
            "color": color, "icon": icon, "ii": is_initial, "it": is_terminal, "so": sort_order})

    seen: set[tuple[str, str]] = set()
    for from_slug, to_slug, evt_slug, label in _TRANSITIONS:
        fid, tid_val = slug_to_id.get(from_slug), slug_to_id.get(to_slug)
        if not fid or not tid_val:
            continue
        pair = (fid, tid_val)
        if pair in seen:
            continue
        seen.add(pair)
        await db.execute(text(
            "INSERT INTO workflow_transitions "
            "(id, tenant_id, from_state_id, to_state_id, event_type_slug, label) "
            "VALUES (:id, :tid, :fid, :tid2, :es, :lbl)"
        ), {"id": str(uuid.uuid4()), "tid": tenant_id, "fid": fid, "tid2": tid_val,
            "es": evt_slug, "lbl": label})

    for (slug, name, icon, color, is_info, req_w, req_n, req_r, req_a, so) in _EVENT_TYPES:
        await db.execute(text(
            "INSERT INTO workflow_event_types "
            "(id, tenant_id, slug, name, icon, color, is_informational, "
            "requires_wallet, requires_notes, requires_reason, requires_admin, sort_order) "
            "VALUES (:id, :tid, :s, :n, :i, :c, :ii, :rw, :rn, :rr, :ra, :so)"
        ), {"id": str(uuid.uuid4()), "tid": tenant_id, "s": slug, "n": name,
            "i": icon, "c": color, "ii": is_info, "rw": req_w, "rn": req_n,
            "rr": req_r, "ra": req_a, "so": so})

    await db.flush()


async def verify_service_token(
    x_service_token: str = Header(..., alias="X-Service-Token"),
) -> str:
    """Validate inter-service shared secret using constant-time comparison."""
    import secrets as _secrets
    settings = get_settings()
    if not _secrets.compare_digest(x_service_token, settings.S2S_SERVICE_TOKEN):
        raise UnauthorizedError("Invalid service token")
    return x_service_token


# ─── JWT auth (mirrors compliance/inventory pattern) ─────────────────────────

async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    """Validate JWT and return user data. Supports S2S bypass via X-Service-Token."""
    settings = get_settings()

    # S2S bypass for inter-service calls
    service_token = request.headers.get("X-Service-Token")
    if service_token:
        import secrets as _secrets
        if _secrets.compare_digest(service_token, settings.S2S_SERVICE_TOKEN):
            return {
                "id": "system",
                "tenant_id": request.headers.get("X-Tenant-Id", "default"),
                "is_superuser": True,
                "permissions": [],
                "email": "system@trace.internal",
            }
        raise UnauthorizedError("Invalid service token")

    # Allow disabling JWT for dev/tests
    if not settings.REQUIRE_AUTH:
        return {
            "id": request.headers.get("X-User-Id", "1"),
            "tenant_id": request.headers.get("X-Tenant-Id", "default"),
            "is_superuser": False,
            "permissions": [],
            "email": "dev@trace.local",
        }

    if credentials is None:
        raise UnauthorizedError("Missing authorization header")

    import jwt
    from jwt import PyJWTError as JWTError
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise UnauthorizedError("Invalid or expired token")

    if payload.get("type") != "access":
        raise UnauthorizedError("Invalid token type")
    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedError("Token missing subject")

    # Cache user data per tenant header so cross-tenant superusers don't share state
    incoming_tid = request.headers.get("X-Tenant-Id", "default")
    rd = await get_redis()
    jti = payload.get("jti") or "_"
    cache_key = f"trace_svc:me:{user_id}:{incoming_tid}:{jti}"
    cached = await rd.get(cache_key)
    if cached:
        return json.loads(cached)

    http = get_http_client()
    resp = await http.get(
        f"{settings.USER_SERVICE_URL}/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    if resp.status_code != 200:
        raise UnauthorizedError("User not found or token expired")

    user_data = resp.json()
    await rd.setex(cache_key, settings.USER_CACHE_TTL, json.dumps(user_data))
    return user_data


CurrentUser = Annotated[dict, Depends(get_current_user)]


def require_permission(slug: str):
    async def _check(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user.get("is_superuser"):
            return current_user
        if slug not in (current_user.get("permissions") or []):
            raise ForbiddenError(f"Permission '{slug}' required")
        return current_user
    return Depends(_check)


def require_superuser(current_user: dict = Depends(get_current_user)) -> dict:
    if not current_user.get("is_superuser"):
        raise ForbiddenError("Superuser required")
    return current_user


SuperUser = Annotated[dict, Depends(require_superuser)]
