"""Platform AI settings management — moved from subscription-service."""
from __future__ import annotations

import base64
import hashlib
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import anthropic
import redis.asyncio as aioredis
import structlog
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import get_settings
from app.db.models import PlatformAISettings

log = structlog.get_logger(__name__)


def _get_fernet() -> Fernet:
    """Derive a Fernet key from JWT_SECRET (deterministic, 32-byte URL-safe base64)."""
    secret = get_settings().JWT_SECRET.encode()
    # SHA-256 produces 32 bytes; Fernet needs url-safe base64 of 32 bytes
    key_bytes = hashlib.sha256(secret).digest()
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)


def _mask_key(key: str | None) -> str:
    if not key:
        return ""
    if len(key) <= 11:
        return "********"
    return key[:7] + "************" + key[-4:]


def _encrypt(value: str) -> str:
    """Encrypt a string value using Fernet (symmetric, AES-128-CBC + HMAC)."""
    return _get_fernet().encrypt(value.encode()).decode()


def _decrypt(value: str) -> str:
    """Decrypt a Fernet-encrypted value. Falls back to legacy base64 for migration."""
    try:
        return _get_fernet().decrypt(value.encode()).decode()
    except (InvalidToken, Exception):
        # Legacy fallback: old values stored as plain base64
        try:
            decoded = base64.b64decode(value.encode()).decode()
            log.warning("decrypted_legacy_base64_key", hint="Re-save the API key to upgrade encryption")
            return decoded
        except Exception:
            raise ValueError("Could not decrypt API key")


class AISettingsService:
    def __init__(self, db: AsyncSession, redis: aioredis.Redis | None = None) -> None:
        self.db = db
        self.redis = redis

    async def get_settings(self) -> PlatformAISettings:
        result = await self.db.execute(select(PlatformAISettings).limit(1))
        settings = result.scalar_one_or_none()
        if not settings:
            settings = PlatformAISettings(id=str(uuid.uuid4()))
            self.db.add(settings)
            await self.db.flush()
            await self.db.refresh(settings)
        return settings

    async def get_settings_response(self) -> dict:
        s = await self.get_settings()
        raw_key = _decrypt(s.anthropic_api_key_encrypted) if s.anthropic_api_key_encrypted else None
        return {
            "anthropic_api_key_masked": _mask_key(raw_key),
            "anthropic_api_key_set": bool(raw_key),
            "anthropic_model_analysis": s.anthropic_model_analysis,
            "anthropic_model_premium": s.anthropic_model_premium,
            "anthropic_max_tokens": s.anthropic_max_tokens,
            "anthropic_enabled": s.anthropic_enabled,
            "global_daily_limit_free": s.global_daily_limit_free,
            "global_daily_limit_starter": s.global_daily_limit_starter,
            "global_daily_limit_professional": s.global_daily_limit_professional,
            "global_daily_limit_enterprise": s.global_daily_limit_enterprise,
            "cache_ttl_minutes": s.cache_ttl_minutes,
            "cache_enabled": s.cache_enabled,
            "estimated_cost_per_analysis_usd": float(s.estimated_cost_per_analysis_usd),
            "alert_monthly_cost_usd": float(s.alert_monthly_cost_usd),
            "current_month_calls": s.current_month_calls,
            "current_month_cost_usd": float(s.current_month_cost_usd),
            "pnl_analysis_enabled": s.pnl_analysis_enabled,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        }

    async def update_settings(self, data: dict) -> dict:
        s = await self.get_settings()
        allowed = {"anthropic_model_analysis", "anthropic_model_premium", "anthropic_max_tokens",
                    "anthropic_enabled", "global_daily_limit_free", "global_daily_limit_starter",
                    "global_daily_limit_professional", "global_daily_limit_enterprise",
                    "cache_ttl_minutes", "cache_enabled", "estimated_cost_per_analysis_usd",
                    "alert_monthly_cost_usd", "pnl_analysis_enabled"}
        # Model whitelist. Without this a compromised superuser could set the
        # model to `claude-opus-4-1` (or any future premium tier) and burn
        # six-figure LLM bills quietly. Keep in sync with pricing tiers.
        allowed_models = {
            "claude-haiku-4-5-20251001",
            "claude-haiku-4-5",
            "claude-sonnet-4-6",
            "claude-sonnet-4-7",
            "claude-opus-4-7",
        }
        for k, v in data.items():
            if k not in allowed:
                continue
            if k in {"anthropic_model_analysis", "anthropic_model_premium"} and v is not None:
                if v not in allowed_models:
                    from fastapi import HTTPException
                    raise HTTPException(
                        status_code=400,
                        detail=f"Model '{v}' not in allowlist: {sorted(allowed_models)}",
                    )
            setattr(s, k, v)
        s.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        if self.redis:
            await self.redis.delete("ai:platform:config")
        return await self.get_settings_response()

    async def update_api_key(self, api_key: str) -> dict:
        s = await self.get_settings()
        s.anthropic_api_key_encrypted = _encrypt(api_key)
        s.anthropic_enabled = True
        s.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        if self.redis:
            await self._clear_caches()
            await self.redis.delete("ai:platform:config")
        log.info("ai_api_key_updated")
        return await self.get_settings_response()

    async def test_connection(self) -> dict:
        s = await self.get_settings()
        if not s.anthropic_api_key_encrypted:
            return {"ok": False, "error": "API key no configurada"}
        api_key = _decrypt(s.anthropic_api_key_encrypted)
        start = datetime.now(timezone.utc)
        try:
            client = anthropic.AsyncAnthropic(api_key=api_key)
            await client.messages.create(model=s.anthropic_model_analysis, max_tokens=10, messages=[{"role": "user", "content": "Responde solo: OK"}])
            elapsed = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            return {"ok": True, "latency_ms": int(elapsed), "model": s.anthropic_model_analysis}
        except anthropic.AuthenticationError:
            return {"ok": False, "error": "API key invalida"}
        except Exception as exc:
            # The Anthropic SDK sometimes echoes the bearer token back in the
            # exception message on transport errors. Scrub the key + any
            # recognisable prefix before returning it to the caller.
            return {"ok": False, "error": _scrub_secrets(str(exc), api_key)}

    async def get_metrics(self) -> dict:
        s = await self.get_settings()
        calls_by_tenant: list[dict] = []
        calls_by_day: list[dict] = []
        if self.redis:
            now = datetime.now(timezone.utc)
            month_prefix = now.strftime("%Y-%m")
            tenant_calls: dict[str, int] = {}
            day_calls: dict[str, int] = {}
            async for key in self.redis.scan_iter(match="ai:pnl:rate:*"):
                parts = str(key).split(":")
                if len(parts) >= 5:
                    tid, date_str = parts[3], parts[4]
                    if date_str.startswith(month_prefix):
                        count = int(await self.redis.get(key) or 0)
                        tenant_calls[tid] = tenant_calls.get(tid, 0) + count
                        day_calls[date_str] = day_calls.get(date_str, 0) + count
            cost_per = float(s.estimated_cost_per_analysis_usd)
            for tid, count in sorted(tenant_calls.items(), key=lambda x: -x[1]):
                calls_by_tenant.append({"tenant_id": tid, "calls": count, "cost_usd": round(count * cost_per, 4)})
            for d in sorted(day_calls):
                calls_by_day.append({"date": d, "calls": day_calls[d]})
        total_calls = sum(t["calls"] for t in calls_by_tenant)
        total_cost = sum(t["cost_usd"] for t in calls_by_tenant)
        days_elapsed = max(datetime.now(timezone.utc).day, 1)
        projected = round(total_cost / days_elapsed * 30, 4) if days_elapsed > 0 else 0
        return {
            "current_month": {"total_calls": total_calls, "total_cost_usd": round(total_cost, 4), "calls_by_tenant": calls_by_tenant, "calls_by_module": {"pnl_analysis": total_calls}, "calls_by_day": calls_by_day},
            "projected_month_cost_usd": projected, "alert_threshold_usd": float(s.alert_monthly_cost_usd), "alert_triggered": projected > float(s.alert_monthly_cost_usd),
        }

    async def clear_all_caches(self) -> int:
        if not self.redis:
            return 0
        return await self._clear_caches()

    async def _clear_caches(self) -> int:
        count = 0
        async for key in self.redis.scan_iter(match="ai:pnl:*"):
            if ":rate:" not in str(key):
                await self.redis.delete(key)
                count += 1
        return count

    async def get_decrypted_key(self) -> str | None:
        s = await self.get_settings()
        if not s.anthropic_api_key_encrypted:
            return None
        return _decrypt(s.anthropic_api_key_encrypted)

    async def get_full_config(self) -> dict:
        """Internal: full config dict for analysis service."""
        s = await self.get_settings()
        raw_key = await self.get_decrypted_key()
        return {
            "anthropic_api_key": raw_key or "",
            "anthropic_model_analysis": s.anthropic_model_analysis,
            "anthropic_max_tokens": s.anthropic_max_tokens,
            "anthropic_enabled": s.anthropic_enabled,
            "cache_ttl_minutes": s.cache_ttl_minutes,
            "cache_enabled": s.cache_enabled,
            "pnl_analysis_enabled": s.pnl_analysis_enabled,
            "global_daily_limit_free": s.global_daily_limit_free,
            "global_daily_limit_starter": s.global_daily_limit_starter,
            "global_daily_limit_professional": s.global_daily_limit_professional,
            "global_daily_limit_enterprise": s.global_daily_limit_enterprise,
        }



def _scrub_secrets(msg: str, api_key: str) -> str:
    """Remove the API key + any `sk-…` / `Bearer …` pattern from a message.

    Called on exception strings so a malformed key or network error doesn't
    leak the real key into logs or HTTP responses.
    """
    import re as _re
    if api_key and len(api_key) >= 8:
        msg = msg.replace(api_key, "[redacted]")
    msg = _re.sub(r"sk-[A-Za-z0-9_\-]{10,}", "[redacted]", msg)
    msg = _re.sub(r"(?i)(Bearer|Authorization)[:=\s]+\S+", r"\1 [redacted]", msg)
    # Also cap message length to avoid megabyte-size stack traces leaking.
    if len(msg) > 500:
        msg = msg[:500] + "…"
    return msg

