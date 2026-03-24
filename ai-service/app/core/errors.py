"""Domain errors and FastAPI exception handlers."""
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import ORJSONResponse


class AppError(Exception):
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, detail: str, **ctx: Any) -> None:
        self.detail = detail
        self.ctx = ctx
        super().__init__(detail)


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "NOT_FOUND"


class ValidationError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code = "VALIDATION_ERROR"


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "FORBIDDEN"


class RateLimitError(AppError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    error_code = "AI_RATE_LIMIT_EXCEEDED"


class AiNotConfiguredError(AppError):
    status_code = status.HTTP_501_NOT_IMPLEMENTED
    error_code = "AI_NOT_CONFIGURED"


class AiFeatureDisabledError(AppError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code = "AI_FEATURE_DISABLED"


def _error_response(request: Request, status_code: int, error_code: str, detail: str, extra: dict | None = None) -> ORJSONResponse:
    body: dict[str, Any] = {"error": {"code": error_code, "message": detail}}
    if extra:
        body["error"]["detail"] = extra
    cid = getattr(request.state, "correlation_id", None)
    if cid:
        body["error"]["correlation_id"] = cid
    return ORJSONResponse(status_code=status_code, content=body)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> ORJSONResponse:
        return _error_response(request, exc.status_code, exc.error_code, exc.detail)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> ORJSONResponse:
        return _error_response(request, 422, "VALIDATION_ERROR", "Request validation failed", {"errors": exc.errors()})

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> ORJSONResponse:
        import structlog
        structlog.get_logger(__name__).error("unhandled_exception", exc_info=exc, path=str(request.url))
        return _error_response(request, 500, "INTERNAL_ERROR", "An unexpected error occurred")
