"""Platform AI settings management service."""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import anthropic
import redis.asyncio as aioredis
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PlatformAISettings

log = structlog.get_logger(__name__)


def _mask_key(key: str | None) -> str:
    """Mask API key: show first 7 + dots + last 4."""
    if not key:
        return ""
    if len(key) <= 11:
        return "••••••••"
    return key[:7] + "••••••••••••" + key[-4:]


def _simple_encrypt(value: str) -> str:
    """Simple reversible encoding. In production use Fernet/KMS."""
    import base64
    return base64.b64encode(value.encode()).decode()


def _simple_decrypt(value: str) -> str:
    """Simple reversible decoding."""
    import base64
    return base64.b64decode(value.encode()).decode()


class AISettingsService:
    def __init__(self, db: AsyncSession, redis: aioredis.Redis | None = None) -> None:
        self.db = db
        self.redis = redis

    async def get_settings(self) -> PlatformAISettings:
        """Get the singleton settings row, create if not exists."""
        result = await self.db.execute(select(PlatformAISettings).limit(1))
        settings = result.scalar_one_or_none()
        if not settings:
            settings = PlatformAISettings(id=str(uuid.uuid4()))
            self.db.add(settings)
            await self.db.flush()
            await self.db.refresh(settings)
        return settings

    async def get_settings_response(self) -> dict:
        """Return settings with masked API key."""
        s = await self.get_settings()
        raw_key = _simple_decrypt(s.anthropic_api_key_encrypted) if s.anthropic_api_key_encrypted else None
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
        """Update settings (excluding api_key — use update_api_key for that)."""
        s = await self.get_settings()
        allowed_fields = {
            "anthropic_model_analysis", "anthropic_model_premium", "anthropic_max_tokens",
            "anthropic_enabled", "global_daily_limit_free", "global_daily_limit_starter",
            "global_daily_limit_professional", "global_daily_limit_enterprise",
            "cache_ttl_minutes", "cache_enabled", "estimated_cost_per_analysis_usd",
            "alert_monthly_cost_usd", "pnl_analysis_enabled",
        }
        for key, value in data.items():
            if key in allowed_fields:
                setattr(s, key, value)
        s.updated_at = datetime.now(timezone.utc)
        await self.db.flush()

        # Invalidate config cache so inventory-service picks up changes within seconds
        if self.redis:
            await self.redis.delete("ai:platform:config")
            await self.redis.delete("platform:ai:config")

        return await self.get_settings_response()

    async def update_api_key(self, api_key: str) -> dict:
        """Encrypt and store API key, auto-enable AI, invalidate all caches."""
        s = await self.get_settings()
        s.anthropic_api_key_encrypted = _simple_encrypt(api_key)
        s.anthropic_enabled = True  # Auto-enable when key is set
        s.updated_at = datetime.now(timezone.utc)
        await self.db.flush()

        # Invalidate all AI caches + config cache
        if self.redis:
            await self._clear_all_ai_caches()
            await self.redis.delete("ai:platform:config")
            await self.redis.delete("platform:ai:config")

        log.info("ai_api_key_updated")
        return await self.get_settings_response()

    async def test_connection(self) -> dict:
        """Test Anthropic API connection with a minimal call."""
        s = await self.get_settings()
        if not s.anthropic_api_key_encrypted:
            return {"ok": False, "error": "API key no configurada"}

        api_key = _simple_decrypt(s.anthropic_api_key_encrypted)
        start = datetime.now(timezone.utc)

        try:
            client = anthropic.AsyncAnthropic(api_key=api_key)
            response = await client.messages.create(
                model=s.anthropic_model_analysis,
                max_tokens=10,
                messages=[{"role": "user", "content": "Responde solo: OK"}],
            )
            elapsed = (datetime.now(timezone.utc) - start).total_seconds() * 1000
            return {
                "ok": True,
                "latency_ms": int(elapsed),
                "model": s.anthropic_model_analysis,
            }
        except anthropic.AuthenticationError:
            return {"ok": False, "error": "API key inválida"}
        except anthropic.APIError as exc:
            return {"ok": False, "error": str(exc)}
        except Exception as exc:
            return {"ok": False, "error": f"Error inesperado: {str(exc)}"}

    async def get_metrics(self) -> dict:
        """Get AI usage metrics for current month."""
        s = await self.get_settings()

        # Collect per-tenant usage from Redis
        calls_by_tenant: list[dict] = []
        calls_by_day: list[dict] = []

        if self.redis:
            today = datetime.now(timezone.utc)
            month_prefix = today.strftime("%Y-%m")

            # Scan daily rate keys: ai:pnl:rate:{tenant_id}:{date}
            tenant_calls: dict[str, int] = {}
            day_calls: dict[str, int] = {}
            async for key in self.redis.scan_iter(match="ai:pnl:rate:*"):
                parts = str(key).split(":")
                if len(parts) >= 5:
                    tenant_id = parts[3]
                    date_str = parts[4]
                    if date_str.startswith(month_prefix):
                        count = int(await self.redis.get(key) or 0)
                        tenant_calls[tenant_id] = tenant_calls.get(tenant_id, 0) + count
                        day_calls[date_str] = day_calls.get(date_str, 0) + count

            cost_per_call = float(s.estimated_cost_per_analysis_usd)
            for tid, count in sorted(tenant_calls.items(), key=lambda x: -x[1]):
                calls_by_tenant.append({
                    "tenant_id": tid,
                    "calls": count,
                    "cost_usd": round(count * cost_per_call, 4),
                })

            for date_str in sorted(day_calls):
                calls_by_day.append({"date": date_str, "calls": day_calls[date_str]})

        total_calls = sum(t["calls"] for t in calls_by_tenant)
        total_cost = sum(t["cost_usd"] for t in calls_by_tenant)
        today = datetime.now(timezone.utc)
        days_in_month = 30
        days_elapsed = max(today.day, 1)
        projected = round(total_cost / days_elapsed * days_in_month, 4) if days_elapsed > 0 else 0

        return {
            "current_month": {
                "total_calls": total_calls,
                "total_cost_usd": round(total_cost, 4),
                "calls_by_tenant": calls_by_tenant,
                "calls_by_module": {"pnl_analysis": total_calls},
                "calls_by_day": calls_by_day,
            },
            "projected_month_cost_usd": projected,
            "alert_threshold_usd": float(s.alert_monthly_cost_usd),
            "alert_triggered": projected > float(s.alert_monthly_cost_usd),
        }

    async def clear_all_caches(self) -> int:
        """Clear all AI analysis caches from Redis."""
        if not self.redis:
            return 0
        return await self._clear_all_ai_caches()

    async def _clear_all_ai_caches(self) -> int:
        """Internal: delete all ai:pnl:* cache keys."""
        count = 0
        async for key in self.redis.scan_iter(match="ai:pnl:*"):
            # Don't delete rate limit keys
            if ":rate:" not in str(key):
                await self.redis.delete(key)
                count += 1
        log.info("ai_caches_cleared", count=count)
        return count

    async def get_decrypted_key(self) -> str | None:
        """Get the raw API key (for inter-service use). Never expose to frontend."""
        s = await self.get_settings()
        if not s.anthropic_api_key_encrypted:
            return None
        return _simple_decrypt(s.anthropic_api_key_encrypted)
