"""FastAPI application factory for compliance-service."""
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

    log.info("compliance_service_starting", version=settings.APP_VERSION)

    # Warm up DB connection pool
    from app.db.session import get_engine
    from sqlalchemy import text

    engine = get_engine()
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    log.info("db_pool_ready")

    # Warm up Redis
    from app.api.deps import get_redis

    rd = await get_redis()
    await rd.ping()
    log.info("redis_ready")

    # Warm up httpx client
    from app.api.deps import get_http_client

    get_http_client()
    log.info("http_client_ready")

    log.info("compliance_service_ready")
    yield

    log.info("compliance_service_shutting_down")
    from app.db.session import close_engine

    await close_engine()

    from app.api import deps

    if deps._http is not None:
        await deps._http.aclose()
        deps._http = None
    if deps._redis is not None:
        await deps._redis.aclose()
        deps._redis = None

    log.info("compliance_service_stopped")


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()

    app = FastAPI(redirect_slashes=False, 
        title="Trace — Compliance Service",
        description="Regulatory compliance: EUDR, frameworks, plots, records and validation.",
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )

    # ─── CORS ─────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://localhost:3000",
        ],
        allow_origin_regex=r"http://localhost:\d+",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ─── Middlewares ──────────────────────────────────────────────────────────
    from app.core.middleware import (
        CorrelationIdMiddleware,
        SecurityHeadersMiddleware,
        TenantMiddleware,
    )

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(TenantMiddleware)
    app.add_middleware(CorrelationIdMiddleware)

    # ─── Exception Handlers ───────────────────────────────────────────────────
    register_exception_handlers(app)

    # ─── Routers ──────────────────────────────────────────────────────────────
    from app.api.v1.health import router as health_router
    from app.api.v1.frameworks import router as frameworks_router
    from app.api.v1.activations import router as activations_router
    from app.api.v1.plots import router as plots_router
    from app.api.v1.records import router as records_router
    from app.api.v1.assets import router as assets_router
    from app.api.v1.certificates import router as certificates_router
    from app.api.v1.risk_assessments import router as risk_assessments_router
    from app.api.v1.supply_chain import router as supply_chain_router

    app.include_router(health_router)
    app.include_router(frameworks_router)
    app.include_router(activations_router)
    app.include_router(plots_router)
    app.include_router(records_router)
    app.include_router(assets_router)
    app.include_router(certificates_router)
    app.include_router(risk_assessments_router)
    app.include_router(supply_chain_router)

    # ─── Prometheus metrics (optional) ────────────────────────────────────────
    try:
        from prometheus_fastapi_instrumentator import Instrumentator

        Instrumentator().instrument(app).expose(app, endpoint="/metrics")
    except ImportError:
        pass

    return app


app = create_app()
