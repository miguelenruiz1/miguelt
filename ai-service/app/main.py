"""FastAPI application factory for ai-service."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    log = get_logger(__name__)
    settings = get_settings()
    log.info("ai_service_starting", version=settings.APP_VERSION)

    from app.db.session import get_engine
    from sqlalchemy import text
    engine = get_engine()
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    log.info("db_pool_ready")

    import redis.asyncio as aioredis
    redis_client = aioredis.from_url(settings.REDIS_URL)
    await redis_client.ping()
    await redis_client.aclose()
    log.info("redis_ready")

    from app.api.deps import get_http_client
    get_http_client()
    log.info("http_client_ready")

    log.info("ai_service_ready")
    yield

    log.info("ai_service_shutting_down")
    from app.db.session import close_engine
    await close_engine()

    from app.api import deps
    if deps._http_client is not None:
        await deps._http_client.aclose()
        deps._http_client = None

    log.info("ai_service_stopped")


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()

    app = FastAPI(redirect_slashes=False, 
        title="Trace - AI Service",
        description="Centralized AI analysis, memory, and configuration for all Trace modules.",
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:4173",
                        "http://127.0.0.1:5173", "http://127.0.0.1:5174", "http://127.0.0.1:4173",
                        "http://localhost:3000"],
        allow_origin_regex=r"http://localhost:\d+",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from app.core.middleware import CorrelationIdMiddleware
    app.add_middleware(CorrelationIdMiddleware)

    register_exception_handlers(app)

    from app.api.routers.health import router as health_router
    from app.api.routers.analysis import router as analysis_router
    from app.api.routers.settings import router as settings_router
    from app.api.routers.memory import router as memory_router
    from app.api.routers.metrics import router as metrics_router

    app.include_router(health_router)
    app.include_router(analysis_router)
    app.include_router(settings_router)
    app.include_router(memory_router)
    app.include_router(metrics_router)

    # ─── Prometheus metrics (optional) ────────────────────────────────────────
    try:
        from prometheus_fastapi_instrumentator import Instrumentator  # type: ignore
        Instrumentator().instrument(app).expose(app, endpoint="/metrics")
    except ImportError:
        pass

    # OpenTelemetry tracing (optional)
    try:
        from app.core.tracing import init_tracing
        init_tracing(app, settings.APP_NAME)
    except Exception:
        pass

    return app


app = create_app()
