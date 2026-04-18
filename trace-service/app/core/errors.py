"""Domain errors and FastAPI exception handlers."""
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.responses import ORJSONResponse


# ─── Domain Exceptions ────────────────────────────────────────────────────────

class TraceError(Exception):
    """Base exception for all Trace domain errors."""
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, detail: str, **ctx: Any) -> None:
        self.detail = detail
        self.ctx = ctx
        super().__init__(detail)


class NotFoundError(TraceError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "NOT_FOUND"


class ConflictError(TraceError):
    status_code = status.HTTP_409_CONFLICT
    error_code = "CONFLICT"


class ValidationError(TraceError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code = "VALIDATION_ERROR"


class ForbiddenError(TraceError):
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "FORBIDDEN"


class UnauthorizedError(TraceError):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "UNAUTHORIZED"


class WalletNotAllowlistedError(TraceError):
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "WALLET_NOT_ALLOWLISTED"


class InvalidCustodianError(TraceError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code = "INVALID_CUSTODIAN"


class AssetStateError(TraceError):
    status_code = status.HTTP_409_CONFLICT
    error_code = "ASSET_STATE_ERROR"


class IdempotencyConflictError(TraceError):
    """Same idempotency key used with different payload."""
    status_code = status.HTTP_409_CONFLICT
    error_code = "IDEMPOTENCY_CONFLICT"


class SolanaError(TraceError):
    status_code = status.HTTP_502_BAD_GATEWAY
    error_code = "SOLANA_ERROR"


class CircuitOpenError(TraceError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code = "CIRCUIT_OPEN"


# ─── Error Response Builder ───────────────────────────────────────────────────

def _error_response(
    request: Request,
    status_code: int,
    error_code: str,
    detail: str,
    extra: dict | None = None,
) -> ORJSONResponse:
    body: dict[str, Any] = {
        "error": {
            "code": error_code,
            "message": detail,
        }
    }
    if extra:
        body["error"]["detail"] = extra
    correlation_id = getattr(request.state, "correlation_id", None)
    if correlation_id:
        body["error"]["correlation_id"] = correlation_id
    return ORJSONResponse(status_code=status_code, content=jsonable_encoder(body))


# ─── Exception Handlers ───────────────────────────────────────────────────────

def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(TraceError)
    async def trace_error_handler(request: Request, exc: TraceError) -> ORJSONResponse:
        return _error_response(request, exc.status_code, exc.error_code, exc.detail)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> ORJSONResponse:
        return _error_response(
            request,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "VALIDATION_ERROR",
            "Request validation failed",
            {"errors": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> ORJSONResponse:
        from app.core.logging import get_logger
        log = get_logger(__name__)
        log.error("Unhandled exception", exc_info=exc, path=str(request.url))
        return _error_response(
            request,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "INTERNAL_ERROR",
            "An unexpected error occurred",
        )
