"""Tests targeting remaining uncovered code paths for 95%+ coverage.

Covers:
- app/api/deps.py: get_current_user, require_permission, require_inventory_module,
  require_production_module, is_einvoicing_active, is_einvoicing_sandbox_active
- app/main.py: create_app factory
- app/db/session.py: get_engine, get_session_factory, close_engine
- app/core/security.py: decode_token
- app/services/production_service.py: edge cases (delete non-pending, reject, finish wrong state, etc.)
- app/api/routers/stock.py: endpoint handler bodies via integration tests
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import HTTPException
import jwt

# ═══════════════════════════════════════════════════════════════════════════════
# 1. app/core/security.py — decode_token
# ═══════════════════════════════════════════════════════════════════════════════


class TestDecodeToken:
    def test_decode_valid_token(self):
        from app.core.settings import get_settings
        from app.core.security import decode_token

        settings = get_settings()
        payload = {"sub": "user-1", "type": "access", "exp": 9999999999}
        token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
        result = decode_token(token)
        assert result["sub"] == "user-1"
        assert result["type"] == "access"

    def test_decode_invalid_token_raises(self):
        from jwt import PyJWTError as JWTError
        from app.core.security import decode_token

        with pytest.raises(JWTError):
            decode_token("not-a-real-jwt-token")

    def test_decode_wrong_secret_raises(self):
        from jwt import PyJWTError as JWTError
        from app.core.security import decode_token

        payload = {"sub": "user-1", "type": "access", "exp": 9999999999}
        token = jwt.encode(payload, "wrong-secret-key-totally-different", algorithm="HS256")
        with pytest.raises(JWTError):
            decode_token(token)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. app/api/deps.py — require_permission
# ═══════════════════════════════════════════════════════════════════════════════


class TestRequirePermission:
    @pytest.mark.asyncio
    async def test_superuser_bypasses_permission(self):
        from app.api.deps import require_permission

        checker = require_permission("inventory.view")
        user = {"is_superuser": True, "permissions": []}
        # require_permission returns an inner function that expects CurrentUser
        # We call it directly since it's the inner _check function
        result = await checker(user)
        assert result == user

    @pytest.mark.asyncio
    async def test_user_with_permission_passes(self):
        from app.api.deps import require_permission

        checker = require_permission("inventory.view")
        user = {"is_superuser": False, "permissions": ["inventory.view", "inventory.manage"]}
        result = await checker(user)
        assert result == user

    @pytest.mark.asyncio
    async def test_user_missing_permission_raises_403(self):
        from app.api.deps import require_permission

        checker = require_permission("inventory.admin")
        user = {"is_superuser": False, "permissions": ["inventory.view"]}
        with pytest.raises(HTTPException) as exc_info:
            await checker(user)
        assert exc_info.value.status_code == 403
        assert "inventory.admin" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_user_no_permissions_key_raises_403(self):
        from app.api.deps import require_permission

        checker = require_permission("inventory.view")
        user = {"is_superuser": False}
        with pytest.raises(HTTPException) as exc_info:
            await checker(user)
        assert exc_info.value.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════════
# 3. app/api/deps.py — get_current_user
# ═══════════════════════════════════════════════════════════════════════════════


class TestGetCurrentUser:
    def _make_token(self, payload: dict) -> str:
        from app.core.settings import get_settings
        settings = get_settings()
        return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

    def _make_credentials(self, token: str):
        cred = MagicMock()
        cred.credentials = token
        return cred

    @pytest.mark.asyncio
    async def test_valid_token_cached_user(self):
        from app.api.deps import get_current_user

        token = self._make_token({"sub": "user-42", "type": "access", "exp": 9999999999})
        creds = self._make_credentials(token)

        user_data = {"id": "user-42", "email": "test@test.com", "permissions": []}
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=json.dumps(user_data))
        http = AsyncMock()

        result = await get_current_user(creds, redis, http)
        assert result["id"] == "user-42"
        redis.get.assert_called_once_with("inv_svc:me:user-42")

    @pytest.mark.asyncio
    async def test_valid_token_http_fallback(self):
        from app.api.deps import get_current_user

        token = self._make_token({"sub": "user-99", "type": "access", "exp": 9999999999})
        creds = self._make_credentials(token)

        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.setex = AsyncMock()

        user_data = {"id": "user-99", "email": "u99@test.com", "permissions": ["inventory.view"]}
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = user_data
        http = AsyncMock()
        http.get = AsyncMock(return_value=resp)

        result = await get_current_user(creds, redis, http)
        assert result["id"] == "user-99"
        redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalid_jwt_raises_401(self):
        from app.api.deps import get_current_user

        creds = self._make_credentials("garbage-token")
        redis = AsyncMock()
        http = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(creds, redis, http)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_non_access_token_raises_401(self):
        from app.api.deps import get_current_user

        token = self._make_token({"sub": "user-1", "type": "refresh", "exp": 9999999999})
        creds = self._make_credentials(token)
        redis = AsyncMock()
        http = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(creds, redis, http)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_missing_sub_raises_401(self):
        from app.api.deps import get_current_user

        token = self._make_token({"type": "access", "exp": 9999999999})
        creds = self._make_credentials(token)
        redis = AsyncMock()
        http = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(creds, redis, http)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_http_request_error_raises_503(self):
        from app.api.deps import get_current_user

        token = self._make_token({"sub": "user-1", "type": "access", "exp": 9999999999})
        creds = self._make_credentials(token)

        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        http = AsyncMock()
        http.get = AsyncMock(side_effect=httpx.RequestError("connection failed"))

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(creds, redis, http)
        assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_http_non_200_raises_401(self):
        from app.api.deps import get_current_user

        token = self._make_token({"sub": "user-1", "type": "access", "exp": 9999999999})
        creds = self._make_credentials(token)

        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        resp = MagicMock()
        resp.status_code = 403
        http = AsyncMock()
        http.get = AsyncMock(return_value=resp)

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(creds, redis, http)
        assert exc_info.value.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# 4. app/api/deps.py — require_inventory_module
# ═══════════════════════════════════════════════════════════════════════════════


class TestRequireInventoryModule:
    @pytest.mark.asyncio
    async def test_cached_active(self):
        from app.api.deps import require_inventory_module

        redis = AsyncMock()
        redis.get = AsyncMock(return_value="1")
        http = AsyncMock()
        user = {"tenant_id": "t1", "is_superuser": False, "permissions": []}

        result = await require_inventory_module(user, redis, http)
        assert result == user

    @pytest.mark.asyncio
    async def test_cached_inactive_raises_403(self):
        from app.api.deps import require_inventory_module

        redis = AsyncMock()
        redis.get = AsyncMock(return_value="0")
        http = AsyncMock()
        user = {"tenant_id": "t1", "is_superuser": False, "permissions": []}

        with pytest.raises(HTTPException) as exc_info:
            await require_inventory_module(user, redis, http)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_no_tenant_raises_403(self):
        from app.api.deps import require_inventory_module

        redis = AsyncMock()
        http = AsyncMock()
        user = {"is_superuser": False, "permissions": []}

        with pytest.raises(HTTPException) as exc_info:
            await require_inventory_module(user, redis, http)
        assert exc_info.value.status_code == 403
        assert "No tenant" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_http_fallback_active(self):
        from app.api.deps import require_inventory_module

        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.setex = AsyncMock()

        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"is_active": True}
        http = AsyncMock()
        http.get = AsyncMock(return_value=resp)

        user = {"tenant_id": "t1", "is_superuser": False, "permissions": []}
        result = await require_inventory_module(user, redis, http)
        assert result == user
        redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_http_fallback_inactive(self):
        from app.api.deps import require_inventory_module

        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.setex = AsyncMock()

        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"is_active": False}
        http = AsyncMock()
        http.get = AsyncMock(return_value=resp)

        user = {"tenant_id": "t1", "is_superuser": False, "permissions": []}
        with pytest.raises(HTTPException) as exc_info:
            await require_inventory_module(user, redis, http)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_http_request_error_raises_503(self):
        from app.api.deps import require_inventory_module

        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        http = AsyncMock()
        http.get = AsyncMock(side_effect=httpx.RequestError("connection failed"))

        user = {"tenant_id": "t1", "is_superuser": False, "permissions": []}
        with pytest.raises(HTTPException) as exc_info:
            await require_inventory_module(user, redis, http)
        assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_http_non_200_inactive(self):
        from app.api.deps import require_inventory_module

        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.setex = AsyncMock()

        resp = MagicMock()
        resp.status_code = 404
        resp.json.return_value = {}
        http = AsyncMock()
        http.get = AsyncMock(return_value=resp)

        user = {"tenant_id": "t1", "is_superuser": False, "permissions": []}
        with pytest.raises(HTTPException) as exc_info:
            await require_inventory_module(user, redis, http)
        assert exc_info.value.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════════
# 5. app/api/deps.py — require_production_module
# ═══════════════════════════════════════════════════════════════════════════════


class TestRequireProductionModule:
    @pytest.mark.asyncio
    async def test_both_cached_active(self):
        from app.api.deps import require_production_module

        redis = AsyncMock()
        redis.get = AsyncMock(return_value="1")
        http = AsyncMock()
        user = {"tenant_id": "t1", "is_superuser": False, "permissions": []}

        result = await require_production_module(user, redis, http)
        assert result == user

    @pytest.mark.asyncio
    async def test_no_tenant_raises_403(self):
        from app.api.deps import require_production_module

        redis = AsyncMock()
        http = AsyncMock()
        user = {"is_superuser": False, "permissions": []}

        with pytest.raises(HTTPException) as exc_info:
            await require_production_module(user, redis, http)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_inventory_cached_inactive_raises_403(self):
        from app.api.deps import require_production_module

        async def _get(key):
            if "inventory" in key:
                return "0"
            return "1"

        redis = AsyncMock()
        redis.get = AsyncMock(side_effect=_get)
        http = AsyncMock()
        user = {"tenant_id": "t1", "is_superuser": False, "permissions": []}

        with pytest.raises(HTTPException) as exc_info:
            await require_production_module(user, redis, http)
        assert exc_info.value.status_code == 403
        assert "inventory" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_production_cached_inactive_raises_403(self):
        from app.api.deps import require_production_module

        async def _get(key):
            if "production" in key:
                return "0"
            return "1"

        redis = AsyncMock()
        redis.get = AsyncMock(side_effect=_get)
        http = AsyncMock()
        user = {"tenant_id": "t1", "is_superuser": False, "permissions": []}

        with pytest.raises(HTTPException) as exc_info:
            await require_production_module(user, redis, http)
        assert exc_info.value.status_code == 403
        assert "production" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_http_fallback_both_active(self):
        from app.api.deps import require_production_module

        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.setex = AsyncMock()

        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"is_active": True}
        http = AsyncMock()
        http.get = AsyncMock(return_value=resp)

        user = {"tenant_id": "t1", "is_superuser": False, "permissions": []}
        result = await require_production_module(user, redis, http)
        assert result == user

    @pytest.mark.asyncio
    async def test_http_fallback_production_inactive(self):
        from app.api.deps import require_production_module

        call_count = 0

        async def _get(key):
            return None  # not cached

        async def _http_get(url):
            nonlocal call_count
            call_count += 1
            r = MagicMock()
            if "inventory" in url:
                r.status_code = 200
                r.json.return_value = {"is_active": True}
            else:
                r.status_code = 200
                r.json.return_value = {"is_active": False}
            return r

        redis = AsyncMock()
        redis.get = AsyncMock(side_effect=_get)
        redis.setex = AsyncMock()
        http = AsyncMock()
        http.get = AsyncMock(side_effect=_http_get)

        user = {"tenant_id": "t1", "is_superuser": False, "permissions": []}
        with pytest.raises(HTTPException) as exc_info:
            await require_production_module(user, redis, http)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_http_request_error_raises_503(self):
        from app.api.deps import require_production_module

        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        http = AsyncMock()
        http.get = AsyncMock(side_effect=httpx.RequestError("network"))

        user = {"tenant_id": "t1", "is_superuser": False, "permissions": []}
        with pytest.raises(HTTPException) as exc_info:
            await require_production_module(user, redis, http)
        assert exc_info.value.status_code == 503


# ═══════════════════════════════════════════════════════════════════════════════
# 6. app/api/deps.py — is_einvoicing_active / is_einvoicing_sandbox_active
# ═══════════════════════════════════════════════════════════════════════════════


class TestEinvoicingActive:
    @pytest.mark.asyncio
    async def test_cached_active(self):
        from app.api.deps import is_einvoicing_active

        redis = AsyncMock()
        redis.get = AsyncMock(return_value="1")
        result = await is_einvoicing_active("t1", redis=redis, http_client=AsyncMock())
        assert result is True

    @pytest.mark.asyncio
    async def test_cached_inactive(self):
        from app.api.deps import is_einvoicing_active

        redis = AsyncMock()
        redis.get = AsyncMock(return_value="0")
        result = await is_einvoicing_active("t1", redis=redis, http_client=AsyncMock())
        assert result is False

    @pytest.mark.asyncio
    async def test_http_fallback_active(self):
        from app.api.deps import is_einvoicing_active

        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.setex = AsyncMock()

        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"is_active": True}
        http = AsyncMock()
        http.get = AsyncMock(return_value=resp)

        result = await is_einvoicing_active("t1", redis=redis, http_client=http)
        assert result is True
        redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_http_fallback_inactive(self):
        from app.api.deps import is_einvoicing_active

        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.setex = AsyncMock()

        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"is_active": False}
        http = AsyncMock()
        http.get = AsyncMock(return_value=resp)

        result = await is_einvoicing_active("t1", redis=redis, http_client=http)
        assert result is False

    @pytest.mark.asyncio
    async def test_http_error_returns_false(self):
        from app.api.deps import is_einvoicing_active

        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        http = AsyncMock()
        http.get = AsyncMock(side_effect=httpx.RequestError("fail"))

        result = await is_einvoicing_active("t1", redis=redis, http_client=http)
        assert result is False

    @pytest.mark.asyncio
    async def test_http_non_200_returns_false(self):
        from app.api.deps import is_einvoicing_active

        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.setex = AsyncMock()

        resp = MagicMock()
        resp.status_code = 404
        resp.json.return_value = {}
        http = AsyncMock()
        http.get = AsyncMock(return_value=resp)

        result = await is_einvoicing_active("t1", redis=redis, http_client=http)
        assert result is False


class TestEinvoicingSandboxActive:
    @pytest.mark.asyncio
    async def test_cached_active(self):
        from app.api.deps import is_einvoicing_sandbox_active

        redis = AsyncMock()
        redis.get = AsyncMock(return_value="1")
        result = await is_einvoicing_sandbox_active("t1", redis=redis, http_client=AsyncMock())
        assert result is True

    @pytest.mark.asyncio
    async def test_cached_inactive(self):
        from app.api.deps import is_einvoicing_sandbox_active

        redis = AsyncMock()
        redis.get = AsyncMock(return_value="0")
        result = await is_einvoicing_sandbox_active("t1", redis=redis, http_client=AsyncMock())
        assert result is False

    @pytest.mark.asyncio
    async def test_http_fallback_active(self):
        from app.api.deps import is_einvoicing_sandbox_active

        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.setex = AsyncMock()

        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"is_active": True}
        http = AsyncMock()
        http.get = AsyncMock(return_value=resp)

        result = await is_einvoicing_sandbox_active("t1", redis=redis, http_client=http)
        assert result is True

    @pytest.mark.asyncio
    async def test_http_fallback_inactive(self):
        from app.api.deps import is_einvoicing_sandbox_active

        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.setex = AsyncMock()

        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"is_active": False}
        http = AsyncMock()
        http.get = AsyncMock(return_value=resp)

        result = await is_einvoicing_sandbox_active("t1", redis=redis, http_client=http)
        assert result is False

    @pytest.mark.asyncio
    async def test_http_error_returns_false(self):
        from app.api.deps import is_einvoicing_sandbox_active

        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        http = AsyncMock()
        http.get = AsyncMock(side_effect=httpx.RequestError("fail"))

        result = await is_einvoicing_sandbox_active("t1", redis=redis, http_client=http)
        assert result is False

    @pytest.mark.asyncio
    async def test_http_non_200_returns_false(self):
        from app.api.deps import is_einvoicing_sandbox_active

        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.setex = AsyncMock()

        resp = MagicMock()
        resp.status_code = 500
        resp.json.return_value = {}
        http = AsyncMock()
        http.get = AsyncMock(return_value=resp)

        result = await is_einvoicing_sandbox_active("t1", redis=redis, http_client=http)
        assert result is False


# ═══════════════════════════════════════════════════════════════════════════════
# 7. app/main.py — create_app factory
# ═══════════════════════════════════════════════════════════════════════════════


class TestCreateApp:
    def test_create_app_returns_fastapi_instance(self):
        from app.main import create_app

        app = create_app()
        assert app.title == "Trace — Inventory Service"

    def test_create_app_has_cors(self):
        from app.main import create_app

        app = create_app()
        # CORS middleware is registered
        middleware_classes = [m.cls.__name__ for m in app.user_middleware]
        assert "CORSMiddleware" in middleware_classes

    def test_create_app_has_routes(self):
        from app.main import create_app

        app = create_app()
        route_paths = [getattr(r, "path", "") for r in app.routes]
        all_paths = " ".join(route_paths)
        assert "/api/v1/products" in all_paths
        assert "/api/v1/stock" in all_paths
        assert "/api/v1/categories" in all_paths
        assert "/api/v1/warehouses" in all_paths
        assert "/api/v1/suppliers" in all_paths
        assert "/api/v1/movements" in all_paths
        assert "/api/v1/purchase-orders" in all_paths
        assert "/api/v1/analytics" in all_paths
        assert "/api/v1/recipes" in all_paths
        assert "/api/v1/production-runs" in all_paths

    def test_create_app_has_health(self):
        from app.main import create_app

        app = create_app()
        route_paths = [getattr(r, "path", "") for r in app.routes]
        assert "/health" in route_paths


# ═══════════════════════════════════════════════════════════════════════════════
# 8. app/db/session.py — engine and session
# ═══════════════════════════════════════════════════════════════════════════════


class TestDbSession:
    def test_get_engine_returns_engine(self):
        """get_engine creates an async engine from settings."""
        # We can't easily create a real engine without a DB, but we can verify
        # the function at import level doesn't crash and returns something.
        import app.db.session as sess
        old_engine = sess._engine
        try:
            # Force re-creation by clearing the cached engine
            sess._engine = None
            engine = sess.get_engine()
            assert engine is not None
        finally:
            sess._engine = old_engine

    def test_get_session_factory_returns_factory(self):
        import app.db.session as sess
        old_factory = sess._session_factory
        try:
            sess._session_factory = None
            factory = sess.get_session_factory()
            assert factory is not None
        finally:
            sess._session_factory = old_factory

    @pytest.mark.asyncio
    async def test_close_engine_when_none(self):
        import app.db.session as sess
        old_engine = sess._engine
        try:
            sess._engine = None
            await sess.close_engine()
            assert sess._engine is None
        finally:
            sess._engine = old_engine

    @pytest.mark.asyncio
    async def test_close_engine_disposes(self):
        import app.db.session as sess
        mock_engine = AsyncMock()
        mock_engine.dispose = AsyncMock()
        old_engine = sess._engine
        try:
            sess._engine = mock_engine
            await sess.close_engine()
            mock_engine.dispose.assert_called_once()
            assert sess._engine is None
        finally:
            sess._engine = old_engine


# ═══════════════════════════════════════════════════════════════════════════════
# 9. app/services/production_service.py — edge cases
# ═══════════════════════════════════════════════════════════════════════════════


class TestProductionServiceEdgeCases:
    """Test edge cases not covered by integration tests."""

    @pytest.mark.asyncio
    async def test_delete_run_not_found(self, db):
        from app.services.production_service import ProductionService
        from app.core.errors import NotFoundError

        svc = ProductionService(db)
        with pytest.raises(NotFoundError):
            await svc.delete_run("test-tenant", "nonexistent-id")

    @pytest.mark.asyncio
    async def test_get_run_not_found(self, db):
        from app.services.production_service import ProductionService
        from app.core.errors import NotFoundError

        svc = ProductionService(db)
        with pytest.raises(NotFoundError):
            await svc.get_run("test-tenant", "nonexistent-id")

    @pytest.mark.asyncio
    async def test_execute_run_not_found(self, db):
        from app.services.production_service import ProductionService
        from app.core.errors import NotFoundError

        svc = ProductionService(db)
        with pytest.raises(NotFoundError):
            await svc.execute_run("test-tenant", "nonexistent-id")

    @pytest.mark.asyncio
    async def test_finish_run_not_found(self, db):
        from app.services.production_service import ProductionService
        from app.core.errors import NotFoundError

        svc = ProductionService(db)
        with pytest.raises(NotFoundError):
            await svc.finish_run("test-tenant", "nonexistent-id")

    @pytest.mark.asyncio
    async def test_approve_run_not_found(self, db):
        from app.services.production_service import ProductionService
        from app.core.errors import NotFoundError

        svc = ProductionService(db)
        with pytest.raises(NotFoundError):
            await svc.approve_run("test-tenant", "nonexistent-id")

    @pytest.mark.asyncio
    async def test_reject_run_not_found(self, db):
        from app.services.production_service import ProductionService
        from app.core.errors import NotFoundError

        svc = ProductionService(db)
        with pytest.raises(NotFoundError):
            await svc.reject_run("test-tenant", "nonexistent-id", "reason")

    @pytest.mark.asyncio
    async def test_get_recipe_not_found(self, db):
        from app.services.production_service import ProductionService
        from app.core.errors import NotFoundError

        svc = ProductionService(db)
        with pytest.raises(NotFoundError):
            await svc.get_recipe("test-tenant", "nonexistent-id")

    @pytest.mark.asyncio
    async def test_update_recipe_not_found(self, db):
        from app.services.production_service import ProductionService
        from app.core.errors import NotFoundError

        svc = ProductionService(db)
        with pytest.raises(NotFoundError):
            await svc.update_recipe("test-tenant", "nonexistent-id", {"name": "x"})

    @pytest.mark.asyncio
    async def test_delete_recipe_not_found(self, db):
        from app.services.production_service import ProductionService
        from app.core.errors import NotFoundError

        svc = ProductionService(db)
        with pytest.raises(NotFoundError):
            await svc.delete_recipe("test-tenant", "nonexistent-id")

    @pytest.mark.asyncio
    async def test_create_run_recipe_not_found(self, db):
        from app.services.production_service import ProductionService
        from app.core.errors import NotFoundError

        svc = ProductionService(db)
        with pytest.raises(NotFoundError):
            await svc.create_run("test-tenant", {
                "recipe_id": "nonexistent",
                "warehouse_id": "wh-1",
            })


# ═══════════════════════════════════════════════════════════════════════════════
# 10. Integration: stock router endpoints (via client fixture)
# ═══════════════════════════════════════════════════════════════════════════════


async def _create_product_and_warehouse(client, suffix: str):
    """Helper: create a product + warehouse and return (product_id, warehouse_id)."""
    p = await client.post("/api/v1/products", json={
        "name": f"RC-Prod-{suffix}", "sku": f"RC-{suffix}", "unit_of_measure": "un",
    })
    assert p.status_code == 201
    w = await client.post("/api/v1/warehouses", json={
        "name": f"RC-WH-{suffix}", "code": f"RC-WH-{suffix}", "type": "main",
    })
    assert w.status_code == 201
    return p.json()["id"], w.json()["id"]


@pytest.mark.asyncio
async def test_stock_receive_and_list(client):
    pid, wid = await _create_product_and_warehouse(client, "rcv1")
    resp = await client.post("/api/v1/stock/receive", json={
        "product_id": pid, "warehouse_id": wid,
        "quantity": "100", "unit_cost": "5000",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["product_id"] == pid

    # List stock
    resp = await client.get("/api/v1/stock", params={"product_id": pid})
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


@pytest.mark.asyncio
async def test_stock_issue(client):
    pid, wid = await _create_product_and_warehouse(client, "iss1")
    await client.post("/api/v1/stock/receive", json={
        "product_id": pid, "warehouse_id": wid,
        "quantity": "100", "unit_cost": "5000",
    })
    resp = await client.post("/api/v1/stock/issue", json={
        "product_id": pid, "warehouse_id": wid, "quantity": "10",
    })
    assert resp.status_code == 201
    assert resp.json()["product_id"] == pid


@pytest.mark.asyncio
async def test_stock_transfer(client):
    pid, wid1 = await _create_product_and_warehouse(client, "xfr1")
    w2 = await client.post("/api/v1/warehouses", json={
        "name": "RC-WH-xfr1b", "code": "RC-WH-xfr1b", "type": "secondary",
    })
    wid2 = w2.json()["id"]
    await client.post("/api/v1/stock/receive", json={
        "product_id": pid, "warehouse_id": wid1,
        "quantity": "100", "unit_cost": "5000",
    })
    resp = await client.post("/api/v1/stock/transfer", json={
        "product_id": pid, "from_warehouse_id": wid1,
        "to_warehouse_id": wid2, "quantity": "30",
    })
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_stock_adjust(client):
    pid, wid = await _create_product_and_warehouse(client, "adj1")
    await client.post("/api/v1/stock/receive", json={
        "product_id": pid, "warehouse_id": wid,
        "quantity": "100", "unit_cost": "5000",
    })
    resp = await client.post("/api/v1/stock/adjust", json={
        "product_id": pid, "warehouse_id": wid,
        "new_qty": "80", "reason": "Damaged goods",
    })
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_stock_adjust_in(client):
    pid, wid = await _create_product_and_warehouse(client, "adjin1")
    resp = await client.post("/api/v1/stock/adjust-in", json={
        "product_id": pid, "warehouse_id": wid,
        "quantity": "50", "reason": "Found extra stock",
    })
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_stock_adjust_out(client):
    pid, wid = await _create_product_and_warehouse(client, "adjout1")
    await client.post("/api/v1/stock/receive", json={
        "product_id": pid, "warehouse_id": wid,
        "quantity": "100", "unit_cost": "5000",
    })
    resp = await client.post("/api/v1/stock/adjust-out", json={
        "product_id": pid, "warehouse_id": wid,
        "quantity": "10", "reason": "Shrinkage",
    })
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_stock_return(client):
    pid, wid = await _create_product_and_warehouse(client, "ret1")
    resp = await client.post("/api/v1/stock/return", json={
        "product_id": pid, "warehouse_id": wid,
        "quantity": "5", "reference": "RET-001",
    })
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_stock_waste(client):
    pid, wid = await _create_product_and_warehouse(client, "wst1")
    await client.post("/api/v1/stock/receive", json={
        "product_id": pid, "warehouse_id": wid,
        "quantity": "100", "unit_cost": "5000",
    })
    resp = await client.post("/api/v1/stock/waste", json={
        "product_id": pid, "warehouse_id": wid,
        "quantity": "3", "reason": "Expired",
    })
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_stock_availability(client):
    pid, wid = await _create_product_and_warehouse(client, "avail1")
    await client.post("/api/v1/stock/receive", json={
        "product_id": pid, "warehouse_id": wid,
        "quantity": "100", "unit_cost": "5000",
    })
    resp = await client.get(f"/api/v1/stock/availability/{pid}")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_stock_reservations(client):
    resp = await client.get("/api/v1/stock/reservations")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_stock_initiate_transfer(client):
    pid, wid1 = await _create_product_and_warehouse(client, "init-xfr1")
    w2 = await client.post("/api/v1/warehouses", json={
        "name": "RC-WH-initxfr1b", "code": "RC-WH-initxfr1b", "type": "secondary",
    })
    wid2 = w2.json()["id"]
    await client.post("/api/v1/stock/receive", json={
        "product_id": pid, "warehouse_id": wid1,
        "quantity": "100", "unit_cost": "5000",
    })
    resp = await client.post("/api/v1/stock/transfer/initiate", json={
        "product_id": pid, "from_warehouse_id": wid1,
        "to_warehouse_id": wid2, "quantity": "20",
    })
    assert resp.status_code == 201
    mov_id = resp.json()["id"]

    # Complete the transfer
    resp2 = await client.post(f"/api/v1/stock/transfer/{mov_id}/complete")
    assert resp2.status_code == 200


@pytest.mark.asyncio
async def test_stock_list_with_filters(client):
    pid, wid = await _create_product_and_warehouse(client, "filt1")
    await client.post("/api/v1/stock/receive", json={
        "product_id": pid, "warehouse_id": wid,
        "quantity": "50", "unit_cost": "3000",
    })
    # Filter by warehouse
    resp = await client.get("/api/v1/stock", params={"warehouse_id": wid})
    assert resp.status_code == 200

    # Filter by both
    resp = await client.get("/api/v1/stock", params={
        "product_id": pid, "warehouse_id": wid,
    })
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# 11. app/core/settings.py — validate_log_level
# ═══════════════════════════════════════════════════════════════════════════════


class TestSettings:
    def test_validate_log_level_valid(self):
        from app.core.settings import Settings
        result = Settings.validate_log_level("debug")
        assert result == "DEBUG"

    def test_validate_log_level_invalid(self):
        from app.core.settings import Settings
        with pytest.raises(ValueError, match="LOG_LEVEL must be one of"):
            Settings.validate_log_level("TRACE")


# ═══════════════════════════════════════════════════════════════════════════════
# 12. app/core/errors.py — error_response with correlation_id
# ═══════════════════════════════════════════════════════════════════════════════


class TestErrorHandling:
    def test_error_response_with_correlation_id(self):
        from app.core.errors import _error_response

        request = MagicMock()
        request.state.correlation_id = "test-corr-123"
        resp = _error_response(request, 404, "NOT_FOUND", "Item not found")
        assert resp.status_code == 404
        body = json.loads(resp.body)
        assert body["error"]["correlation_id"] == "test-corr-123"

    def test_error_response_without_correlation_id(self):
        from app.core.errors import _error_response

        request = MagicMock()
        request.state = MagicMock(spec=[])  # no correlation_id attr
        resp = _error_response(request, 500, "INTERNAL_ERROR", "Boom")
        assert resp.status_code == 500
        body = json.loads(resp.body)
        assert "correlation_id" not in body["error"]

    def test_error_response_with_extra(self):
        from app.core.errors import _error_response

        request = MagicMock()
        request.state = MagicMock(spec=[])
        resp = _error_response(request, 422, "VALIDATION_ERROR", "Bad", extra={"fields": ["name"]})
        body = json.loads(resp.body)
        assert body["error"]["detail"] == {"fields": ["name"]}


# ═══════════════════════════════════════════════════════════════════════════════
# 13. app/core/middleware.py — CorrelationIdMiddleware
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_correlation_id_middleware_sets_header(client):
    """The middleware should add X-Correlation-Id to the response."""
    resp = await client.get("/health")
    assert "x-correlation-id" in resp.headers


@pytest.mark.asyncio
async def test_correlation_id_middleware_uses_provided(client):
    """If X-Correlation-Id is sent, it should be echoed back."""
    resp = await client.get("/health", headers={"X-Correlation-Id": "my-corr-id-99"})
    assert resp.headers.get("x-correlation-id") == "my-corr-id-99"


# ═══════════════════════════════════════════════════════════════════════════════
# 14. app/api/deps.py — get_redis / get_http_client singletons
# ═══════════════════════════════════════════════════════════════════════════════


class TestDepsSingletons:
    def test_get_redis_returns_redis_client(self):
        import app.api.deps as deps
        old = deps._redis_client
        try:
            deps._redis_client = None
            client = deps.get_redis()
            assert client is not None
        finally:
            deps._redis_client = old

    def test_get_redis_returns_same_instance(self):
        import app.api.deps as deps
        old = deps._redis_client
        try:
            deps._redis_client = None
            c1 = deps.get_redis()
            c2 = deps.get_redis()
            assert c1 is c2
        finally:
            deps._redis_client = old

    def test_get_http_client_returns_instance(self):
        import app.api.deps as deps
        old = deps._http_client
        try:
            deps._http_client = None
            client = deps.get_http_client()
            assert client is not None
            assert isinstance(client, httpx.AsyncClient)
        finally:
            deps._http_client = old

    def test_get_http_client_returns_same_instance(self):
        import app.api.deps as deps
        old = deps._http_client
        try:
            deps._http_client = None
            c1 = deps.get_http_client()
            c2 = deps.get_http_client()
            assert c1 is c2
        finally:
            deps._http_client = old


# ═══════════════════════════════════════════════════════════════════════════════
# 15. app/core/logging.py — configure_logging, add_app_context
# ═══════════════════════════════════════════════════════════════════════════════


class TestLogging:
    def test_configure_logging_runs_without_error(self):
        from app.core.logging import configure_logging
        configure_logging()  # should not raise

    def test_add_app_context(self):
        from app.core.logging import add_app_context

        event_dict: dict = {"event": "test_event"}
        result = add_app_context(None, "info", event_dict)
        assert "app" in result
        assert "version" in result

    def test_get_logger(self):
        from app.core.logging import get_logger

        log = get_logger("test")
        assert log is not None
