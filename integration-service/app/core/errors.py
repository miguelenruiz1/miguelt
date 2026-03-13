"""Custom exceptions + global error handlers."""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import ORJSONResponse


class NotFoundError(Exception):
    def __init__(self, detail: str = "Not found"):
        self.detail = detail


class ValidationError(Exception):
    def __init__(self, detail: str = "Validation error"):
        self.detail = detail


class AdapterError(Exception):
    """Raised when an external adapter call fails."""
    def __init__(self, provider: str, detail: str, status_code: int = 502):
        self.provider = provider
        self.detail = detail
        self.status_code = status_code


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError):
        return ORJSONResponse(status_code=404, content={"detail": exc.detail})

    @app.exception_handler(ValidationError)
    async def validation_handler(request: Request, exc: ValidationError):
        return ORJSONResponse(status_code=422, content={"detail": exc.detail})

    @app.exception_handler(AdapterError)
    async def adapter_handler(request: Request, exc: AdapterError):
        return ORJSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "provider": exc.provider},
        )
