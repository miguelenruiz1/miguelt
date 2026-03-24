"""Exception hierarchy and FastAPI error handlers."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import ORJSONResponse


class ComplianceError(Exception):
    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str = "An unexpected error occurred", **ctx) -> None:
        super().__init__(message)
        self.message = message
        self.ctx = ctx


class NotFoundError(ComplianceError):
    status_code = 404
    error_code = "NOT_FOUND"


class ConflictError(ComplianceError):
    status_code = 409
    error_code = "CONFLICT"


class ValidationError(ComplianceError):
    status_code = 422
    error_code = "VALIDATION_ERROR"


class ForbiddenError(ComplianceError):
    status_code = 403
    error_code = "FORBIDDEN"


class UnauthorizedError(ComplianceError):
    status_code = 401
    error_code = "UNAUTHORIZED"


class ModuleNotActiveError(ComplianceError):
    status_code = 403
    error_code = "MODULE_NOT_ACTIVE"

    def __init__(self, module: str = "compliance") -> None:
        super().__init__(f"Module '{module}' is not active for this tenant")


class CertificateGenerationError(ComplianceError):
    status_code = 500
    error_code = "CERTIFICATE_GENERATION_ERROR"


class CertificateNotReadyError(ComplianceError):
    status_code = 422
    error_code = "CERTIFICATE_NOT_READY"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ComplianceError)
    async def _compliance_error(request: Request, exc: ComplianceError) -> ORJSONResponse:
        correlation_id = getattr(request.state, "correlation_id", None)
        return ORJSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.error_code,
                    "message": exc.message,
                    "correlation_id": correlation_id,
                    **exc.ctx,
                }
            },
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> ORJSONResponse:
        correlation_id = getattr(request.state, "correlation_id", None)
        return ORJSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "correlation_id": correlation_id,
                }
            },
        )
