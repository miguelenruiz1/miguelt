"""Client for reading tenant module configuration from subscription-service.

Follows the same pattern as inventory-service:
  1. Check Redis cache first  (key: module:trace:{tenant_id})
  2. On cache miss: HTTP GET to subscription-service internal endpoint
  3. Cache result with TTL from settings

The config includes plan limits and pricing — never hardcoded.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal

import httpx
import redis.asyncio as aioredis
import structlog

from app.core.settings import get_settings

log = structlog.get_logger(__name__)

# ─── Singleton clients ──────────────────────────────────────────────────────

_redis: aioredis.Redis | None = None
_http: httpx.AsyncClient | None = None


def get_redis() -> aioredis.Redis:
    """Lazy-init singleton Redis client."""
    global _redis
    if _redis is None:
        settings = get_settings()
        _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


def get_http_client() -> httpx.AsyncClient:
    """Lazy-init singleton HTTP client for inter-service calls."""
    global _http
    if _http is None:
        _http = httpx.AsyncClient(timeout=10.0)
    return _http


async def close_clients() -> None:
    """Shutdown cleanup — called from lifespan."""
    global _redis, _http
    if _http is not None:
        await _http.aclose()
        _http = None
    if _redis is not None:
        await _redis.aclose()
        _redis = None


# ─── Module config data class ───────────────────────────────────────────────

@dataclass(frozen=True)
class LogisticsModuleConfig:
    """Configuration for the logistics module for a given tenant.

    All pricing / limit fields come from the tenant's plan in
    subscription-service.  Never hardcoded in trace-service.
    """

    habilitado: bool
    eventos_incluidos_mes: int | None  # None = unlimited (enterprise)
    precio_evento_usd: Decimal
    templates_max: int | None          # None = unlimited
    cargas_activas_max: int | None     # None = unlimited

    @classmethod
    def from_dict(cls, data: dict) -> LogisticsModuleConfig:
        return cls(
            habilitado=bool(data.get("habilitado", False)),
            eventos_incluidos_mes=data.get("eventos_incluidos_mes"),
            precio_evento_usd=Decimal(str(data.get("precio_evento_usd", "0.00"))),
            templates_max=data.get("templates_max"),
            cargas_activas_max=data.get("cargas_activas_max"),
        )

    @classmethod
    def disabled(cls) -> LogisticsModuleConfig:
        """Return a config representing a disabled module."""
        return cls(
            habilitado=False,
            eventos_incluidos_mes=0,
            precio_evento_usd=Decimal("0.00"),
            templates_max=0,
            cargas_activas_max=0,
        )


# ─── Public API ─────────────────────────────────────────────────────────────

CACHE_KEY_PREFIX = "module:trace"


async def get_module_config(tenant_id: str) -> LogisticsModuleConfig:
    """Read logistics module configuration for a tenant.

    1. Check Redis cache  (key: module:trace:{tenant_id})
    2. On miss: HTTP GET to subscription-service
    3. Cache result for MODULE_CACHE_TTL seconds

    If subscription-service is unreachable, fails open (returns
    a permissive config) so that a transient outage of the billing
    service does not block logistics operations.
    """
    settings = get_settings()
    r = get_redis()
    cache_key = f"{CACHE_KEY_PREFIX}:{tenant_id}"

    # 1. Redis cache hit
    try:
        cached = await r.get(cache_key)
        if cached is not None:
            return LogisticsModuleConfig.from_dict(json.loads(cached))
    except Exception as exc:
        log.warning("redis_cache_read_error", error=str(exc), tenant_id=tenant_id)

    # 2. HTTP fallback to subscription-service
    try:
        client = get_http_client()
        url = (
            f"{settings.SUBSCRIPTION_SERVICE_URL}"
            f"/api/v1/modules/config/{tenant_id}/logistics"
        )
        resp = await client.get(url)

        if resp.status_code == 200:
            data = resp.json()
            config = LogisticsModuleConfig.from_dict(data)
            # Cache the result
            try:
                await r.setex(
                    cache_key,
                    settings.MODULE_CACHE_TTL,
                    json.dumps(data),
                )
            except Exception as exc:
                log.warning("redis_cache_write_error", error=str(exc))
            return config

        # Module not found or not active
        config = LogisticsModuleConfig.disabled()
        try:
            await r.setex(
                cache_key,
                settings.MODULE_CACHE_TTL,
                json.dumps({"habilitado": False}),
            )
        except Exception:
            pass
        return config

    except httpx.RequestError as exc:
        # Fail open: subscription-service unreachable → allow access
        log.warning(
            "subscription_service_unreachable",
            error=str(exc),
            tenant_id=tenant_id,
            action="fail_open",
        )
        return LogisticsModuleConfig(
            habilitado=True,
            eventos_incluidos_mes=None,
            precio_evento_usd=Decimal("0.00"),
            templates_max=None,
            cargas_activas_max=None,
        )


async def invalidate_module_cache(tenant_id: str) -> None:
    """Remove cached config so next request fetches fresh data."""
    try:
        r = get_redis()
        await r.delete(f"{CACHE_KEY_PREFIX}:{tenant_id}")
    except Exception as exc:
        log.warning("redis_cache_invalidate_error", error=str(exc))


# ─── Usage counter ──────────────────────────────────────────────────────────

USAGE_KEY_PREFIX = "trace:usage"
USAGE_TTL = 35 * 24 * 3600  # 35 days — survives the month + margin


async def increment_usage(tenant_id: str, year_month: str) -> int:
    """Atomically increment the monthly event usage counter.

    Args:
        tenant_id: tenant UUID string
        year_month: format "YYYY-MM"

    Returns:
        The new count after increment.
    """
    r = get_redis()
    key = f"{USAGE_KEY_PREFIX}:{tenant_id}:{year_month}"
    count = await r.incr(key)
    if count == 1:
        # First event this month — set TTL
        await r.expire(key, USAGE_TTL)
    return count


async def get_usage(tenant_id: str, year_month: str) -> int:
    """Read current monthly event usage count."""
    r = get_redis()
    key = f"{USAGE_KEY_PREFIX}:{tenant_id}:{year_month}"
    val = await r.get(key)
    return int(val) if val else 0
