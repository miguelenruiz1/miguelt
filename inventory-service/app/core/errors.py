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


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    error_code = "CONFLICT"


class ValidationError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code = "VALIDATION_ERROR"


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "FORBIDDEN"


class BadRequestError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "BAD_REQUEST"


class UnauthorizedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "UNAUTHORIZED"


def _error_response(
    request: Request,
    status_code: int,
    error_code: str,
    detail: str,
    extra: dict | None = None,
) -> ORJSONResponse:
    body: dict[str, Any] = {"error": {"code": error_code, "message": detail}}
    if extra:
        body["error"]["detail"] = extra
    correlation_id = getattr(request.state, "correlation_id", None)
    if correlation_id:
        body["error"]["correlation_id"] = correlation_id
    return ORJSONResponse(status_code=status_code, content=body)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> ORJSONResponse:
        import structlog
        structlog.get_logger(__name__).warning(
            "app_error", status=exc.status_code, code=exc.error_code,
            detail=exc.detail, path=str(request.url), method=request.method,
        )
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
        import structlog
        log = structlog.get_logger(__name__)
        log.error("unhandled_exception", exc_info=exc, path=str(request.url))
        return _error_response(
            request,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "INTERNAL_ERROR",
            "An unexpected error occurred",
        )
