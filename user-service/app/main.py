"""FastAPI application factory for user-service."""
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

    log.info("user_service_starting", version=settings.APP_VERSION)

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

    log.info("user_service_ready")
    yield

    log.info("user_service_shutting_down")
    from app.db.session import close_engine
    await close_engine()
    log.info("user_service_stopped")


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()

    app = FastAPI(redirect_slashes=False, 
        title="Trace — User Service",
        description="Authentication, RBAC, and audit for the Trace platform.",
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )

    # ─── CORS — must be added BEFORE CorrelationIdMiddleware ─────────────────
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
    from app.api.routers.auth import router as auth_router
    from app.api.routers.users import router as users_router
    from app.api.routers.roles import router as roles_router
    from app.api.routers.permissions import router as permissions_router
    from app.api.routers.audit import router as audit_router
    from app.api.routers.email_templates import router as email_templates_router
    from app.api.routers.email_config import router as email_config_router
    from app.api.routers.email_providers import router as email_providers_router
    from app.api.routers.notifications import router as notifications_router
    from app.api.routers.onboarding import router as onboarding_router

    # ─── Static files (uploads) ──────────────────────────────────────────────
    from pathlib import Path
    from fastapi.staticfiles import StaticFiles

    upload_dir = Path(settings.UPLOAD_DIR if hasattr(settings, 'UPLOAD_DIR') else '/app/uploads')
    upload_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(upload_dir)), name="uploads")

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(roles_router)
    app.include_router(permissions_router)
    app.include_router(audit_router)
    app.include_router(email_templates_router)
    app.include_router(email_config_router)
    app.include_router(email_providers_router)
    app.include_router(notifications_router)
    app.include_router(onboarding_router)

    # ─── Prometheus metrics (optional) ────────────────────────────────────────
    try:
        from prometheus_fastapi_instrumentator import Instrumentator  # type: ignore
        Instrumentator().instrument(app).expose(app, endpoint="/metrics")
    except ImportError:
        pass

    return app


app = create_app()
