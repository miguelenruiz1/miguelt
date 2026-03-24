"""FastAPI application factory."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.middleware import CorrelationIdMiddleware, IdempotencyKeyMiddleware, TenantMiddleware
from app.core.settings import get_settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    log = get_logger(__name__)
    settings = get_settings()

    log.info("trace_service_starting", version=settings.APP_VERSION, debug=settings.DEBUG)

    # Warm up DB connection pool
    from app.db.session import get_engine
    engine = get_engine()
    async with engine.connect() as conn:
        from sqlalchemy import text
        await conn.execute(text("SELECT 1"))
    log.info("db_pool_ready")

    # Warm up Redis
    import asyncio
    import redis.asyncio as aioredis
    try:
        redis_client = aioredis.from_url(settings.REDIS_URL, socket_timeout=5)
        await asyncio.wait_for(redis_client.ping(), timeout=5)
        await redis_client.aclose()
        log.info("redis_ready")
    except (asyncio.TimeoutError, Exception) as e:
        log.warning("redis_warmup_failed", error=str(e))

    log.info("trace_service_ready")
    yield

    # Shutdown
    log.info("trace_service_shutting_down")
    from app.db.session import close_engine
    from app.clients.solana_client import close_solana_client
    from app.services.anchor_service import close_arq_pool

    await close_engine()
    await close_solana_client()
    await close_arq_pool()
    log.info("trace_service_stopped")


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()

    app = FastAPI(
        title="Trace — Chain of Custody API",
        description=(
            "Immutable chain-of-custody tracking for assets/NFTs "
            "with Solana event anchoring."
        ),
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )

    # ─── Middlewares (outermost first) ────────────────────────────────────────
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(IdempotencyKeyMiddleware)
    app.add_middleware(TenantMiddleware)

    # Security headers (added before CORS so it runs after CORS in the stack)
    app.add_middleware(SecurityHeadersMiddleware)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://localhost:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Correlation-Id", "X-Response-Time-Ms"],
    )

    # ─── Exception Handlers ───────────────────────────────────────────────────
    register_exception_handlers(app)

    # ─── Routers ──────────────────────────────────────────────────────────────
    from app.api.routers.health import router as health_router
    from app.api.routers.registry import router as registry_router
    from app.api.routers.custody import router as custody_router
    from app.api.routers.solana import router as solana_router
    from app.api.routers.taxonomy import router as taxonomy_router
    from app.api.routers.tenants import router as tenants_router
    from app.api.routers.event_config import router as event_config_router

    app.include_router(health_router)
    app.include_router(tenants_router, prefix="/api/v1")
    app.include_router(registry_router, prefix="/api/v1")
    app.include_router(custody_router, prefix="/api/v1")
    app.include_router(solana_router, prefix="/api/v1")
    app.include_router(taxonomy_router, prefix="/api/v1")
    app.include_router(event_config_router, prefix="/api/v1")

    # ─── Prometheus metrics (optional) ────────────────────────────────────────
    try:
        from prometheus_fastapi_instrumentator import Instrumentator  # type: ignore
        Instrumentator().instrument(app).expose(app, endpoint="/metrics")
    except ImportError:
        pass

    return app


app = create_app()
