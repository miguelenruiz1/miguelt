"""FastAPI application factory for inventory-service."""
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

    log.info("inventory_service_starting", version=settings.APP_VERSION)

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

    # Start background expiry alert scanner
    import asyncio
    from app.core.settings import get_settings as _gs

    async def _expiry_scan_loop():
        """Run expiry alert check every 24 hours for all tenants."""
        _log = get_logger("expiry_scanner")
        while True:
            try:
                await asyncio.sleep(86400)  # 24 hours
                from app.db.session import get_db
                from app.services.alert_service import AlertService
                from sqlalchemy import text as _text

                async with get_db() as session:
                    rows = (await session.execute(_text("SELECT DISTINCT tenant_id FROM entities"))).all()
                    for (tid,) in rows:
                        svc = AlertService(session)
                        created = await svc.check_expiry_alerts(tid)
                        if created:
                            _log.info("expiry_alerts_created", tenant_id=tid, count=len(created))
            except asyncio.CancelledError:
                break
            except Exception as exc:
                _log.error("expiry_scan_error", error=str(exc))

    expiry_task = asyncio.create_task(_expiry_scan_loop())

    # Start background auto-reorder scanner (daily)
    async def _reorder_scan_loop():
        """Check auto-reorder for all tenants every 24 hours."""
        _log = get_logger("reorder_scanner")
        while True:
            try:
                await asyncio.sleep(86400)  # 24 hours
                from app.db.session import get_db
                from app.services.reorder_service import ReorderService
                from sqlalchemy import text as _text

                async with get_db() as session:
                    rows = (await session.execute(_text("SELECT DISTINCT tenant_id FROM entities"))).all()
                    for (tid,) in rows:
                        svc = ReorderService(session)
                        created = await svc.check_all_products_reorder(tid)
                        if created:
                            _log.info("auto_reorder_scan_created", tenant_id=tid, count=len(created))
                    await session.commit()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                _log.error("reorder_scan_error", error=str(exc))

    reorder_task = asyncio.create_task(_reorder_scan_loop())

    log.info("inventory_service_ready")
    yield

    expiry_task.cancel()
    reorder_task.cancel()

    log.info("inventory_service_shutting_down")
    from app.db.session import close_engine
    await close_engine()

    from app.api import deps
    if deps._http_client is not None:
        await deps._http_client.aclose()
        deps._http_client = None

    from app.clients import trace_client
    await trace_client.close_client()

    log.info("inventory_service_stopped")


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()

    app = FastAPI(
        title="Trace — Inventory Service",
        description="Inventory management: products, warehouses, stock movements and purchase orders.",
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
    from app.api.routers.categories import router as categories_router
    from app.api.routers.products import router as products_router
    from app.api.routers.warehouses import router as warehouses_router
    from app.api.routers.stock import router as stock_router
    from app.api.routers.movements import router as movements_router
    from app.api.routers.suppliers import router as suppliers_router
    from app.api.routers.purchase_orders import router as po_router
    from app.api.routers.analytics import router as analytics_router
    from app.api.routers.config import router as config_router
    from app.api.routers.reports import router as reports_router
    from app.api.routers.events import router as events_router
    from app.api.routers.serials import router as serials_router
    from app.api.routers.batches import router as batches_router
    from app.api.routers.recipes import router as recipes_router
    from app.api.routers.production import router as production_router
    from app.api.routers.cycle_counts import router as cycle_counts_router
    from app.api.routers.audit import router as audit_router
    from app.api.routers.imports import router as imports_router
    from app.api.routers.customers import router as customers_router
    from app.api.routers.sales_orders import router as sales_orders_router
    from app.api.routers.variants import router as variants_router
    from app.api.routers.alerts import router as alerts_router
    from app.api.routers.portal import router as portal_router
    from app.api.routers.reorder import router as reorder_router
    from app.api.routers.customer_prices import router as customer_prices_router
    from app.api.routers.tax_rates import router as tax_rates_router
    from app.api.routers.uom import router as uom_router
    from app.api.routers.partners import router as partners_router
    from app.api.routers.blockchain import router as blockchain_router

    # ─── Static files (uploads) ──────────────────────────────────────────────
    from pathlib import Path
    from fastapi.staticfiles import StaticFiles

    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(upload_dir)), name="uploads")

    app.include_router(health_router)
    app.include_router(categories_router)
    app.include_router(products_router)
    app.include_router(warehouses_router)
    app.include_router(stock_router)
    app.include_router(movements_router)
    app.include_router(suppliers_router)
    app.include_router(po_router)
    app.include_router(analytics_router)
    app.include_router(config_router)
    app.include_router(reports_router)
    app.include_router(events_router)
    app.include_router(serials_router)
    app.include_router(batches_router)
    app.include_router(recipes_router)
    app.include_router(production_router)
    app.include_router(cycle_counts_router)
    app.include_router(audit_router)
    app.include_router(imports_router)
    app.include_router(customers_router)
    app.include_router(sales_orders_router)
    app.include_router(variants_router)
    app.include_router(alerts_router)
    app.include_router(portal_router)
    app.include_router(reorder_router)
    app.include_router(customer_prices_router)
    app.include_router(tax_rates_router)
    app.include_router(uom_router)
    app.include_router(partners_router)
    app.include_router(blockchain_router)

    return app


app = create_app()
