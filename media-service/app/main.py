"""FastAPI application factory for media-service."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from app.core.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    # Warm up DB
    from app.db.session import get_engine
    engine = get_engine()
    async with engine.connect() as conn:
        from sqlalchemy import text
        await conn.execute(text("SELECT 1"))
    yield
    from app.db.session import close_engine
    await close_engine()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(redirect_slashes=False, 
        title="Media Service — Trace Platform",
        description="Centralized file storage and media library for all Trace modules.",
        version=settings.APP_VERSION,
        docs_url="/docs",
        openapi_url="/openapi.json",
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    from app.api.routers.health import router as health_router
    from app.api.routers.media import router as media_router
    from app.api.routers.internal import router as internal_router

    app.include_router(health_router)
    app.include_router(media_router, prefix="/api/v1")
    app.include_router(internal_router, prefix="/api/v1")

    # Static files for local storage
    uploads_path = Path(settings.UPLOADS_BASE_PATH)
    uploads_path.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(uploads_path)), name="uploads")

    # ─── Prometheus metrics (optional) ────────────────────────────────────────
    try:
        from prometheus_fastapi_instrumentator import Instrumentator  # type: ignore
        Instrumentator().instrument(app).expose(app, endpoint="/metrics")
    except ImportError:
        pass

    return app


app = create_app()
