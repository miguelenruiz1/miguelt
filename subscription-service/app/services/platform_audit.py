"""Platform audit logger — central record of superuser actions (FASE4).

Usage (imperative, not a decorator — FastAPI deps are simpler to wire as a
helper function):

    await log_superuser_action(
        db,
        user=current_user,
        request=request,
        action="platform.change_plan",
        target_tenant_id=tenant_id,
        target_entity_type="subscription",
        metadata={"plan_slug": body.plan_slug},
    )

Fails silent (only logs a warning) so audit outages don't break the
mutating action itself.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PlatformAuditLog


log = logging.getLogger(__name__)


def _ip(request: Request | None) -> str | None:
    if not request:
        return None
    ff = request.headers.get("X-Forwarded-For")
    if ff:
        return ff.split(",")[0].strip()
    return request.client.host if request.client else None


async def log_superuser_action(
    db: AsyncSession,
    *,
    user: dict | None,
    request: Request | None,
    action: str,
    target_tenant_id: str | None = None,
    target_entity_type: str | None = None,
    target_entity_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    try:
        # SAVEPOINT so a failed INSERT doesn't poison the parent txn.
        async with db.begin_nested():
            entry = PlatformAuditLog(
                id=str(uuid.uuid4()),
                superuser_id=(user.get("id") if user else None),
                superuser_email=(user.get("email") if user else None),
                action=action,
                target_tenant_id=target_tenant_id,
                target_entity_type=target_entity_type,
                target_entity_id=target_entity_id,
                event_metadata=metadata or None,
                ip_address=_ip(request),
                user_agent=(request.headers.get("User-Agent") if request else None),
                correlation_id=(request.headers.get("X-Correlation-Id") if request else None),
            )
            db.add(entry)
    except Exception as exc:  # pragma: no cover — best-effort
        log.warning("platform_audit_insert_failed action=%s err=%s", action, exc)


def audit_superuser_action(action: str):
    """Decorator form (optional). Only captures path params from the route.

    Usage:
        @router.post("/tenants/{tenant_id}/change-plan")
        @audit_superuser_action("platform.change_plan")
        async def change_plan(tenant_id: str, body: ChangePlanRequest,
                              current_user: SuperUser, request: Request,
                              db: AsyncSession = Depends(get_db_session), ...):
            ...

    Requires the decorated function to have both `request: Request` and
    `db: AsyncSession` in its signature.
    """
    import functools

    def _decor(fn):
        @functools.wraps(fn)
        async def _wrap(*args, **kwargs):
            result = await fn(*args, **kwargs)
            # Best-effort audit after successful response.
            try:
                request = kwargs.get("request")
                db = kwargs.get("db")
                current_user = kwargs.get("current_user") or kwargs.get("_user")
                target_tenant_id = kwargs.get("tenant_id")
                target_entity_id = kwargs.get("module_slug") or kwargs.get("session_id")
                if db is not None and isinstance(current_user, dict):
                    await log_superuser_action(
                        db,
                        user=current_user,
                        request=request,
                        action=action,
                        target_tenant_id=target_tenant_id,
                        target_entity_id=target_entity_id,
                    )
            except Exception as exc:  # pragma: no cover
                log.warning("audit_superuser_action_wrap_err=%s", exc)
            return result
        return _wrap
    return _decor
