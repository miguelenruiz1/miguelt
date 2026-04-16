"""Tests for EmailClient (FASE2)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.services.email_client import EmailClient


class _FakeResponse:
    def __init__(self, status_code: int, body: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._body = body or {}
        self.text = text or str(body or "")

    def json(self):
        return self._body


def _mock_httpx(responses):
    """Build an AsyncClient-like mock cycling through `responses` list."""
    client = MagicMock()
    i = {"n": 0}

    async def _post(*args, **kwargs):
        idx = min(i["n"], len(responses) - 1)
        i["n"] += 1
        r = responses[idx]
        if isinstance(r, Exception):
            raise r
        return r

    client.post = _post
    return client


@pytest.mark.asyncio
async def test_send_success_sets_bearer_and_message_id(monkeypatch):
    # Force config resolution via env fallback
    monkeypatch.setenv("RESEND_API_KEY", "test-key-xyz")
    monkeypatch.setenv("RESEND_FROM_EMAIL", "onboarding@resend.dev")

    captured = {}

    async def fake_post(url, headers=None, content=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["body"] = content
        return _FakeResponse(200, {"id": "re_abc123"})

    fake = MagicMock()
    fake.post = fake_post

    ec = EmailClient(http_client=fake, max_retries=1, backoff_base=0)
    # Bypass user-service fetch
    ec._cached_config["tenant-1"] = {
        "api_key": "test-key-xyz",
        "from_email": "onboarding@resend.dev",
        "slug": "resend",
    }

    result = await ec.send(
        tenant_id="tenant-1",
        to="foo@bar.com",
        subject="hola",
        html_body="<b>hi</b>",
    )
    assert result.success is True
    assert result.message_id == "re_abc123"
    assert captured["headers"]["Authorization"] == "Bearer test-key-xyz"
    assert "foo@bar.com" in captured["body"]


@pytest.mark.asyncio
async def test_send_retries_on_500_then_succeeds():
    responses = [_FakeResponse(500, text="server busy"), _FakeResponse(200, {"id": "re_ok"})]
    fake = _mock_httpx(responses)

    ec = EmailClient(http_client=fake, max_retries=3, backoff_base=0)
    ec._cached_config["t"] = {"api_key": "k", "from_email": "x@y.z", "slug": "resend"}

    result = await ec.send(tenant_id="t", to="a@b.c", subject="s", html_body="b")
    assert result.success is True
    assert result.message_id == "re_ok"


@pytest.mark.asyncio
async def test_send_gives_up_after_max_retries():
    responses = [_FakeResponse(502), _FakeResponse(502), _FakeResponse(502)]
    fake = _mock_httpx(responses)
    ec = EmailClient(http_client=fake, max_retries=3, backoff_base=0)
    ec._cached_config["t"] = {"api_key": "k", "from_email": "x@y.z", "slug": "resend"}

    result = await ec.send(tenant_id="t", to="a@b.c", subject="s", html_body="b")
    assert result.success is False
    assert result.error_code == "max_retries_exceeded"


@pytest.mark.asyncio
async def test_send_4xx_no_retry():
    responses = [_FakeResponse(400, text="bad request")]
    fake = _mock_httpx(responses)
    ec = EmailClient(http_client=fake, max_retries=3, backoff_base=0)
    ec._cached_config["t"] = {"api_key": "k", "from_email": "x@y.z", "slug": "resend"}
    result = await ec.send(tenant_id="t", to="a@b.c", subject="s", html_body="b")
    assert result.success is False
    assert result.error_code == "http_400"


@pytest.mark.asyncio
async def test_send_attachments_base64_encoded():
    captured = {}

    async def fake_post(url, headers=None, content=None, timeout=None):
        captured["body"] = content
        return _FakeResponse(200, {"id": "x"})

    fake = MagicMock()
    fake.post = fake_post
    ec = EmailClient(http_client=fake, max_retries=1, backoff_base=0)
    ec._cached_config["t"] = {"api_key": "k", "from_email": "x@y.z", "slug": "resend"}

    pdf = b"%PDF-1.4 fake body"
    result = await ec.send(
        tenant_id="t",
        to="a@b.c",
        subject="s",
        html_body="b",
        attachments=[{"filename": "x.pdf", "content": pdf}],
    )
    assert result.success is True
    import base64
    assert base64.b64encode(pdf).decode("ascii") in captured["body"]


@pytest.mark.asyncio
async def test_send_returns_error_when_no_config(monkeypatch):
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    ec = EmailClient(max_retries=1, backoff_base=0)
    # Force failed user-service call
    ec._cached_config.clear()

    async def fake_client_ctor(*a, **kw):
        raise httpx.RequestError("no net")

    # Trigger fallback path: _resolve_config will call user-service, fail, then env fallback
    # Since env is missing, result must be no_config
    monkeypatch.setattr(
        ec,
        "_client",
        AsyncMock(side_effect=httpx.RequestError("boom")),
    )
    result = await ec.send(tenant_id="tx", to="a@b", subject="s", html_body="")
    assert result.success is False
    assert result.error_code == "no_config"
