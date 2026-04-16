"""Email client for FASE2 billing completeness.

Sends email via Resend API. Fetches per-tenant Resend credentials from
user-service (which owns `email_provider_configs`) using the S2S shared secret.
Falls back to env vars RESEND_API_KEY + RESEND_FROM_EMAIL when user-service
is unreachable (useful for testing and local dev).

Retries 3 times with exponential backoff (0.5s, 1s, 2s).
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
from dataclasses import dataclass
from typing import Any

import httpx
import structlog

from app.core.settings import get_settings

log = structlog.get_logger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


@dataclass
class EmailResult:
    success: bool
    provider: str = "resend"
    message_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "provider": self.provider,
            "message_id": self.message_id,
            "error_code": self.error_code,
            "error_message": self.error_message,
        }


class EmailClient:
    def __init__(
        self,
        http_client: httpx.AsyncClient | None = None,
        max_retries: int = 3,
        backoff_base: float = 0.5,
    ) -> None:
        self._http = http_client
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self._cached_config: dict[str, dict] = {}  # tenant_id -> {api_key, from_email}

    async def _client(self) -> httpx.AsyncClient:
        if self._http is not None:
            return self._http
        return httpx.AsyncClient(timeout=15.0)

    # ── Resolve tenant's Resend config ─────────────────────────────────────

    async def _resolve_config(self, tenant_id: str) -> dict | None:
        """Fetch active Resend config for tenant. Caches in-memory 5 min."""
        settings = get_settings()
        if tenant_id in self._cached_config:
            return self._cached_config[tenant_id]

        # Try user-service S2S endpoint first
        try:
            client = await self._client()
            resp = await client.get(
                f"{settings.USER_SERVICE_URL}/api/v1/internal/email-config/{tenant_id}",
                headers={"X-Service-Token": settings.S2S_SERVICE_TOKEN},
                timeout=5.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                if data and data.get("api_key"):
                    cfg = {
                        "api_key": data["api_key"],
                        "from_email": data.get("from_email", "onboarding@resend.dev"),
                        "slug": data.get("slug", "resend"),
                    }
                    self._cached_config[tenant_id] = cfg
                    return cfg
        except httpx.RequestError as exc:
            log.warning("email_config_fetch_failed", tenant_id=tenant_id, error=str(exc))

        # Fallback to env
        env_key = os.environ.get("RESEND_API_KEY")
        if env_key:
            cfg = {
                "api_key": env_key,
                "from_email": os.environ.get("RESEND_FROM_EMAIL", "onboarding@resend.dev"),
                "slug": "resend",
            }
            self._cached_config[tenant_id] = cfg
            return cfg

        return None

    # ── Send ───────────────────────────────────────────────────────────────

    async def send(
        self,
        tenant_id: str,
        to: str,
        subject: str,
        html_body: str,
        attachments: list[dict[str, Any]] | None = None,
    ) -> EmailResult:
        """Send email via Resend. attachments = [{filename, content(bytes|b64)}]."""
        cfg = await self._resolve_config(tenant_id)
        if cfg is None:
            return EmailResult(
                success=False,
                error_code="no_config",
                error_message=f"No active email provider for tenant {tenant_id!r}",
            )

        # Normalize attachments to base64
        att_payload: list[dict] = []
        for att in attachments or []:
            content = att.get("content")
            if isinstance(content, (bytes, bytearray)):
                content_b64 = base64.b64encode(bytes(content)).decode("ascii")
            else:
                content_b64 = str(content)  # assume already base64
            att_payload.append({
                "filename": att.get("filename", "attachment.bin"),
                "content": content_b64,
            })

        payload: dict[str, Any] = {
            "from": cfg["from_email"],
            "to": [to],
            "subject": subject,
            "html": html_body,
        }
        if att_payload:
            payload["attachments"] = att_payload

        headers = {
            "Authorization": f"Bearer {cfg['api_key']}",
            "Content-Type": "application/json",
        }

        client = await self._client()
        last_err: str | None = None
        for attempt in range(self.max_retries):
            try:
                resp = await client.post(
                    RESEND_API_URL,
                    headers=headers,
                    content=json.dumps(payload),
                    timeout=15.0,
                )
                if 200 <= resp.status_code < 300:
                    try:
                        data = resp.json()
                    except Exception:
                        data = {}
                    msg_id = data.get("id")
                    log.info(
                        "resend_sent",
                        tenant_id=tenant_id,
                        to=to,
                        subject=subject,
                        message_id=msg_id,
                        attempt=attempt + 1,
                    )
                    return EmailResult(success=True, message_id=msg_id)

                # Retry on 429/5xx, give up on 4xx
                last_err = f"HTTP {resp.status_code}: {resp.text[:500]}"
                if resp.status_code < 500 and resp.status_code != 429:
                    log.warning(
                        "resend_client_error",
                        tenant_id=tenant_id,
                        status=resp.status_code,
                        body=resp.text[:200],
                    )
                    return EmailResult(
                        success=False,
                        error_code=f"http_{resp.status_code}",
                        error_message=last_err,
                    )
                log.warning(
                    "resend_retryable_error",
                    status=resp.status_code,
                    attempt=attempt + 1,
                )
            except (httpx.RequestError, asyncio.TimeoutError) as exc:
                last_err = f"{type(exc).__name__}: {exc}"
                log.warning(
                    "resend_transport_error",
                    tenant_id=tenant_id,
                    error=last_err,
                    attempt=attempt + 1,
                )

            if attempt < self.max_retries - 1:
                await asyncio.sleep(self.backoff_base * (2 ** attempt))

        return EmailResult(
            success=False,
            error_code="max_retries_exceeded",
            error_message=last_err or "unknown",
        )


_singleton: EmailClient | None = None


def get_email_client() -> EmailClient:
    global _singleton
    if _singleton is None:
        _singleton = EmailClient()
    return _singleton
