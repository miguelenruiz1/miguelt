"""CSV report download endpoints + AI analysis."""
from __future__ import annotations

from datetime import date
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser, get_redis, require_permission
from app.db.session import get_db_session
from app.services.reports_service import ReportsService

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


def _svc(db: AsyncSession = Depends(get_db_session)) -> ReportsService:
    return ReportsService(db)


@router.get("/products")
async def download_products(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("reports.view"))],
    svc: ReportsService = Depends(_svc),
):
    tenant_id = current_user.get("tenant_id", "default")
    csv_data = await svc.products_csv(tenant_id)
    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=productos.csv"},
    )


@router.get("/stock")
async def download_stock(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("reports.view"))],
    svc: ReportsService = Depends(_svc),
):
    tenant_id = current_user.get("tenant_id", "default")
    csv_data = await svc.stock_csv(tenant_id)
    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=stock.csv"},
    )


@router.get("/suppliers")
async def download_suppliers(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("reports.view"))],
    svc: ReportsService = Depends(_svc),
):
    tenant_id = current_user.get("tenant_id", "default")
    csv_data = await svc.suppliers_csv(tenant_id)
    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=proveedores.csv"},
    )


@router.get("/movements")
async def download_movements(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("reports.view"))],
    date_from: date | None = None,
    date_to: date | None = None,
    svc: ReportsService = Depends(_svc),
):
    tenant_id = current_user.get("tenant_id", "default")
    csv_data = await svc.movements_csv(tenant_id, date_from, date_to)
    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=movimientos.csv"},
    )


@router.get("/events")
async def download_events(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("reports.view"))],
    date_from: date | None = None,
    date_to: date | None = None,
    svc: ReportsService = Depends(_svc),
):
    tenant_id = current_user.get("tenant_id", "default")
    csv_data = await svc.events_csv(tenant_id, date_from, date_to)
    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=eventos.csv"},
    )


@router.get("/serials")
async def download_serials(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("reports.view"))],
    svc: ReportsService = Depends(_svc),
):
    tenant_id = current_user.get("tenant_id", "default")
    csv_data = await svc.serials_csv(tenant_id)
    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=seriales.csv"},
    )


@router.get("/batches")
async def download_batches(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("reports.view"))],
    svc: ReportsService = Depends(_svc),
):
    tenant_id = current_user.get("tenant_id", "default")
    csv_data = await svc.batches_csv(tenant_id)
    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=lotes.csv"},
    )


@router.get("/purchase-orders")
async def download_purchase_orders(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("reports.view"))],
    date_from: date | None = None,
    date_to: date | None = None,
    svc: ReportsService = Depends(_svc),
):
    tenant_id = current_user.get("tenant_id", "default")
    csv_data = await svc.purchase_orders_csv(tenant_id, date_from, date_to)
    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=ordenes-compra.csv"},
    )


@router.get("/pnl")
async def get_pnl_report(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("reports.view"))],
    date_from: date | None = None,
    date_to: date | None = None,
    product_id: str | None = None,
    db: AsyncSession = Depends(get_db_session),
):
    from datetime import datetime as _dt, timezone as _tz
    from app.services.pnl_service import PnLService
    tenant_id = current_user.get("tenant_id", "default")
    svc = PnLService(db)
    dt_from = _dt.combine(date_from, _dt.min.time()).replace(tzinfo=_tz.utc) if date_from else _dt(2020, 1, 1, tzinfo=_tz.utc)
    dt_to = _dt.combine(date_to, _dt.max.time()).replace(tzinfo=_tz.utc) if date_to else _dt.now(_tz.utc)
    if product_id:
        return await svc.get_product_pnl(product_id, tenant_id, dt_from, dt_to)
    return await svc.get_full_pnl(tenant_id, dt_from, dt_to)


@router.get("/pnl/pdf")
async def download_pnl_pdf(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("reports.view"))],
    date_from: date | None = None,
    date_to: date | None = None,
    db: AsyncSession = Depends(get_db_session),
):
    from datetime import datetime as _dt, timezone as _tz
    from fastapi.responses import Response
    from app.services.pnl_service import PnLService
    from app.services.pdf_report_service import generate_pnl_pdf
    tenant_id = current_user.get("tenant_id", "default")
    svc = PnLService(db)
    dt_from = _dt.combine(date_from, _dt.min.time()).replace(tzinfo=_tz.utc) if date_from else _dt(2020, 1, 1, tzinfo=_tz.utc)
    dt_to = _dt.combine(date_to, _dt.max.time()).replace(tzinfo=_tz.utc) if date_to else _dt.now(_tz.utc)
    pnl = await svc.get_full_pnl(tenant_id, dt_from, dt_to)
    pdf_bytes = generate_pnl_pdf(pnl, tenant_name="TraceLog")
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=pnl_report.pdf"})


@router.get("/pnl/analysis")
async def get_pnl_ai_analysis(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("reports.view"))],
    date_from: date | None = None,
    date_to: date | None = None,
    force: bool = Query(False, description="Skip cache and regenerate"),
    db: AsyncSession = Depends(get_db_session),
    redis: aioredis.Redis = Depends(get_redis),
):
    """AI-powered P&L analysis using Claude Haiku 4.5."""
    from datetime import datetime as _dt, timezone as _tz
    from app.services.pnl_service import PnLService
    from app.services.ai_analysis_service import AiAnalysisService, AiNotConfiguredError, AiFeatureDisabledError

    tenant_id = current_user.get("tenant_id", "default")
    svc = PnLService(db)
    dt_from = _dt.combine(date_from, _dt.min.time()).replace(tzinfo=_tz.utc) if date_from else _dt(2020, 1, 1, tzinfo=_tz.utc)
    dt_to = _dt.combine(date_to, _dt.max.time()).replace(tzinfo=_tz.utc) if date_to else _dt.now(_tz.utc)

    pnl = await svc.get_full_pnl(tenant_id, dt_from, dt_to)

    from app.core.errors import RateLimitError

    ai_svc = AiAnalysisService(db, redis)
    try:
        analysis = await ai_svc.analyze_pnl(
            pnl_data=pnl,
            tenant_id=tenant_id,
            date_from=str(date_from or "2020-01-01"),
            date_to=str(date_to or _dt.now(_tz.utc).date()),
            force=force,
        )
        return analysis
    except AiNotConfiguredError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail={"error": "ai_not_configured", "message": "Análisis IA no configurado"},
        )
    except AiFeatureDisabledError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "feature_disabled", "message": str(exc)},
        )
    except RateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error": "ai_rate_limit_exceeded", "message": str(exc), "retry_after": "mañana"},
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "ai_unavailable", "message": f"Análisis no disponible: {str(exc)}"},
        )


@router.get("/pnl/memory")
async def get_pnl_memory(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("reports.view"))],
    db: AsyncSession = Depends(get_db_session),
    redis: aioredis.Redis = Depends(get_redis),
):
    """Get AI memory for this tenant (analysis history, detected patterns)."""
    from app.services.ai_analysis_service import AiAnalysisService
    tenant_id = current_user.get("tenant_id", "default")
    ai_svc = AiAnalysisService(db, redis)
    return await ai_svc.get_tenant_memory(tenant_id)


@router.delete("/pnl/memory")
async def delete_pnl_memory(
    current_user: ModuleUser,
    _: Annotated[dict, Depends(require_permission("reports.view"))],
    db: AsyncSession = Depends(get_db_session),
    redis: aioredis.Redis = Depends(get_redis),
):
    """Reset AI memory for this tenant. Useful if the business changes."""
    from app.services.ai_analysis_service import AiAnalysisService
    tenant_id = current_user.get("tenant_id", "default")
    ai_svc = AiAnalysisService(db, redis)
    deleted = await ai_svc.delete_tenant_memory(tenant_id)
    return {"status": "ok", "deleted": deleted}
