"""FastAPI application factory for subscription-service."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.middleware import CorrelationIdMiddleware
from app.core.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    log = get_logger(__name__)
    settings = get_settings()

    log.info("subscription_service_starting", version=settings.APP_VERSION)

    # Warm up DB connection pool
    from app.db.session import get_engine
    from sqlalchemy import text
    engine = get_engine()
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    log.info("db_pool_ready")

    # Warm up Redis
    import redis.asyncio as aioredis
    redis_client = aioredis.from_url(settings.REDIS_URL)
    await redis_client.ping()
    await redis_client.aclose()
    log.info("redis_ready")

    # Warm up httpx client
    from app.api.deps import get_http_client
    get_http_client()
    log.info("http_client_ready")

    # Start background expiration checker (every hour)
    import asyncio
    from app.services.expiration_service import run_expiration_loop
    expiration_task = asyncio.create_task(run_expiration_loop(interval_seconds=3600))
    log.info("expiration_loop_scheduled", interval=3600)

    log.info("subscription_service_ready")
    yield

    # Cancel background tasks
    expiration_task.cancel()
    try:
        await expiration_task
    except asyncio.CancelledError:
        pass

    log.info("subscription_service_shutting_down")
    from app.db.session import close_engine
    await close_engine()

    # Close httpx client
    from app.api import deps
    if deps._http_client is not None:
        await deps._http_client.aclose()
        deps._http_client = None

    log.info("subscription_service_stopped")


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()

    app = FastAPI(redirect_slashes=False, 
        title="Trace — Subscription Service",
        description="SaaS subscription plans, billing, and license management.",
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
            "http://localhost:5174",
            "http://localhost:4173",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:5174",
            "http://127.0.0.1:4173",
        ],
        allow_origin_regex=r"http://localhost:\d+",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ─── Middlewares ──────────────────────────────────────────────────────────
    app.add_middleware(CorrelationIdMiddleware)

    # ─── Exception Handlers ───────────────────────────────────────────────────
    register_exception_handlers(app)

    # ─── Routers ──────────────────────────────────────────────────────────────
    from app.api.routers.health import router as health_router
    from app.api.routers.plans import router as plans_router
    from app.api.routers.subscriptions import router as subscriptions_router
    from app.api.routers.licenses import router as licenses_router
    from app.api.routers.admin import router as admin_router
    from app.api.routers.modules import router as modules_router
    from app.api.routers.payments import router as payments_router
    from app.api.routers.platform import router as platform_router
    from app.api.routers.usage import router as usage_router
    from app.api.routers.webhooks import router as webhooks_router
    from app.api.routers.checkout import router as checkout_router

    app.include_router(health_router)
    app.include_router(plans_router)
    app.include_router(subscriptions_router)
    app.include_router(licenses_router)
    app.include_router(admin_router)
    app.include_router(modules_router)
    app.include_router(payments_router)
    app.include_router(platform_router)
    app.include_router(usage_router)
    app.include_router(webhooks_router)
    app.include_router(checkout_router)

    return app


app = create_app()
