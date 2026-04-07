"""Router for compliance plots (production parcels)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser
from app.core.errors import ConflictError, NotFoundError


def _validate_polygon_requirement(
    area_ha,
    geojson_url: str | None,
    geolocation_type: str | None,
    geojson_data: dict | None = None,
):
    """EUDR Art. 9.1.c / Art. 2.28: plots >= 4 ha require polygon geolocation.

    Accepts either a remote `geojson_arweave_url`, a locally-stored `geojson_data`,
    or `geolocation_type='polygon'` as evidence of polygon coverage.
    """
    if area_ha is not None and float(area_ha) >= 4.0:
        has_polygon = (
            bool(geojson_url)
            or bool(geojson_data)
            or geolocation_type == "polygon"
        )
        if not has_polygon:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Parcelas >= 4 ha requieren poligono completo "
                    "— EUDR Art. 9.1.c / Art. 2.28. Use geolocation_type='polygon' "
                    "y proporcione geojson_data o geojson_arweave_url con el poligono de la parcela."
                ),
            )
from app.db.session import get_db_session
from app.models.plot import CompliancePlot
from app.models.plot_link import CompliancePlotLink
from app.models.document_link import CompliancePlotDocument
from app.schemas.plot import PlotCreate, PlotResponse, PlotUpdate
from app.schemas.document_link import DocumentLinkCreate, DocumentLinkResponse, DocumentLinkWithUrl

router = APIRouter(
    prefix="/api/v1/compliance/plots",
    tags=["plots"],
)


def _tenant_id(user: dict) -> uuid.UUID:
    raw = str(user.get("tenant_id", "00000000-0000-0000-0000-000000000001"))
    try:
        return uuid.UUID(raw)
    except ValueError:
        return uuid.UUID("00000000-0000-0000-0000-000000000001")


@router.post("/", response_model=PlotResponse, status_code=status.HTTP_201_CREATED)
async def create_plot(
    body: PlotCreate,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    tid = _tenant_id(user)

    # Check unique plot_code per tenant
    existing = (
        await db.execute(
            select(CompliancePlot).where(
                CompliancePlot.tenant_id == tid,
                CompliancePlot.plot_code == body.plot_code,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise ConflictError(f"Plot code '{body.plot_code}' already exists for this tenant")

    _validate_polygon_requirement(
        body.plot_area_ha,
        body.geojson_arweave_url,
        body.geolocation_type,
        body.geojson_data,
    )

    data = body.model_dump(exclude_unset=True)
    # Map metadata -> metadata_
    if "metadata" in data:
        data["metadata_"] = data.pop("metadata")
    else:
        data["metadata_"] = {}

    plot = CompliancePlot(tenant_id=tid, **data)
    db.add(plot)
    await db.flush()
    await db.refresh(plot)
    return plot


@router.get("/", response_model=list[PlotResponse])
async def list_plots(
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
    organization_id: uuid.UUID | None = Query(None),
    risk_level: str | None = Query(None),
    is_active: bool | None = Query(None),
):
    tid = _tenant_id(user)
    q = select(CompliancePlot).where(CompliancePlot.tenant_id == tid)

    if organization_id is not None:
        q = q.where(CompliancePlot.organization_id == organization_id)
    if risk_level is not None:
        q = q.where(CompliancePlot.risk_level == risk_level)
    if is_active is not None:
        q = q.where(CompliancePlot.is_active.is_(is_active))

    q = q.order_by(CompliancePlot.created_at.desc())
    rows = (await db.execute(q)).scalars().all()
    return rows


@router.get("/{plot_id}", response_model=PlotResponse)
async def get_plot(
    plot_id: uuid.UUID,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    tid = _tenant_id(user)
    plot = (
        await db.execute(
            select(CompliancePlot).where(
                CompliancePlot.id == plot_id,
                CompliancePlot.tenant_id == tid,
            )
        )
    ).scalar_one_or_none()
    if plot is None:
        raise NotFoundError(f"Plot '{plot_id}' not found")
    return plot


@router.patch("/{plot_id}", response_model=PlotResponse)
async def update_plot(
    plot_id: uuid.UUID,
    body: PlotUpdate,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    tid = _tenant_id(user)
    plot = (
        await db.execute(
            select(CompliancePlot).where(
                CompliancePlot.id == plot_id,
                CompliancePlot.tenant_id == tid,
            )
        )
    ).scalar_one_or_none()
    if plot is None:
        raise NotFoundError(f"Plot '{plot_id}' not found")

    update_data = body.model_dump(exclude_unset=True)

    # Validate polygon requirement with merged values
    final_area = update_data.get("plot_area_ha", plot.plot_area_ha)
    final_geojson = update_data.get("geojson_arweave_url", plot.geojson_arweave_url)
    final_geotype = update_data.get("geolocation_type", plot.geolocation_type)
    final_geojson_data = update_data.get("geojson_data", plot.geojson_data)
    _validate_polygon_requirement(final_area, final_geojson, final_geotype, final_geojson_data)

    # EUDR guard: refuse area down-edits that would drop a plot below the 4 ha
    # polygon threshold while it is linked to compliance records. Forces the
    # operator to create a new plot rather than silently invalidating evidence.
    POLYGON_THRESHOLD = 4.0
    prev_area = plot.plot_area_ha
    if (
        prev_area is not None
        and float(prev_area) >= POLYGON_THRESHOLD
        and final_area is not None
        and float(final_area) < POLYGON_THRESHOLD
    ):
        linked_count = (
            await db.execute(
                select(func.count()).select_from(CompliancePlotLink).where(
                    CompliancePlotLink.plot_id == plot_id,
                    CompliancePlotLink.tenant_id == tid,
                )
            )
        ).scalar_one()
        if linked_count and linked_count > 0:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"No se puede reducir el area de una parcela >=4 ha vinculada "
                    f"a {linked_count} registro(s) de cumplimiento. Cree una nueva parcela."
                ),
            )

    if "metadata" in update_data:
        update_data["metadata_"] = update_data.pop("metadata")
    for key, val in update_data.items():
        setattr(plot, key, val)

    await db.flush()
    await db.refresh(plot)

    # Invalidate compliance status of records linked to this plot. Tenant-scoped
    # so a stale cross-tenant link can never write to another tenant's records.
    from app.models.record import ComplianceRecord
    linked_record_ids = (
        await db.execute(
            select(CompliancePlotLink.record_id).where(
                CompliancePlotLink.plot_id == plot_id,
                CompliancePlotLink.tenant_id == tid,
            )
        )
    ).scalars().all()
    if linked_record_ids:
        for rec_id in linked_record_ids:
            rec = (
                await db.execute(
                    select(ComplianceRecord).where(
                        ComplianceRecord.id == rec_id,
                        ComplianceRecord.tenant_id == tid,
                    )
                )
            ).scalar_one_or_none()
            if rec and rec.compliance_status in ("compliant", "partial", "ready", "declared"):
                rec.compliance_status = "incomplete"
                rec.last_validated_at = None
        await db.flush()

    return plot


@router.delete("/{plot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plot(
    plot_id: uuid.UUID,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    tid = _tenant_id(user)
    plot = (
        await db.execute(
            select(CompliancePlot).where(
                CompliancePlot.id == plot_id,
                CompliancePlot.tenant_id == tid,
            )
        )
    ).scalar_one_or_none()
    if plot is None:
        raise NotFoundError(f"Plot '{plot_id}' not found")

    # Check no active record links
    link_count = (
        await db.execute(
            select(func.count()).select_from(CompliancePlotLink).where(
                CompliancePlotLink.plot_id == plot_id
            )
        )
    ).scalar_one()
    if link_count > 0:
        raise ConflictError(
            f"Cannot delete plot '{plot_id}': it is linked to {link_count} compliance record(s)"
        )

    await db.delete(plot)
    await db.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{plot_id}/screen-deforestation")
async def screen_deforestation(
    plot_id: uuid.UUID,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Screen a plot for deforestation alerts using Global Forest Watch API.

    Automatically updates deforestation_free flag based on results.
    Returns the screening results with alert count and details.
    """
    from datetime import datetime, timezone
    from app.services.deforestation_service import DeforestationService

    tid = _tenant_id(user)
    plot = (
        await db.execute(
            select(CompliancePlot).where(
                CompliancePlot.id == plot_id,
                CompliancePlot.tenant_id == tid,
            )
        )
    ).scalar_one_or_none()
    if plot is None:
        raise NotFoundError(f"Plot '{plot_id}' not found")

    # Build geojson — prefer local polygon, fallback to point buffer
    geojson = None
    if plot.geojson_data:
        # Local polygon stored in DB
        geojson = plot.geojson_data
    elif plot.geojson_arweave_url:
        # Try to fetch from Arweave (decentralized storage)
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as http:
                resp = await http.get(plot.geojson_arweave_url)
                if resp.status_code == 200:
                    candidate = resp.json()
                    if isinstance(candidate, dict) and candidate.get("type") in (
                        "Polygon", "MultiPolygon", "Feature", "FeatureCollection"
                    ):
                        geojson = candidate
        except Exception:
            pass  # Fall back to point buffer

    svc = await DeforestationService.from_db(db, tenant_id=tid)
    result = await svc.check_plot(
        lat=plot.lat,
        lng=plot.lng,
        geojson=geojson,
        area_ha=plot.plot_area_ha,
    )

    # Auto-update plot flags based on result
    if result.get("deforestation_free") is not None:
        plot.deforestation_free = result["deforestation_free"]
        plot.satellite_verified_at = datetime.now(tz=timezone.utc)
        plot.metadata_ = {
            **(plot.metadata_ or {}),
            "gfw_screening": {
                "alerts_count": result["alerts_count"],
                "high_confidence": result["high_confidence_alerts"],
                "checked_at": result.get("checked_at"),
                "source": result.get("source"),
                "cutoff_date": result.get("cutoff_date"),
            },
        }
        await db.flush()
        await db.refresh(plot)

    return {
        "plot_id": str(plot_id),
        "plot_code": plot.plot_code,
        **result,
        "deforestation_free_updated": result.get("deforestation_free") is not None,
    }


# ─── Evidence documents ────────────────────────────────────────────────────────

from app.api.deps import get_http_client
from app.core.settings import get_settings


@router.post("/{plot_id}/documents", response_model=DocumentLinkResponse, status_code=status.HTTP_201_CREATED)
async def attach_plot_document(
    plot_id: uuid.UUID,
    body: DocumentLinkCreate,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    tid = _tenant_id(user)

    plot = (
        await db.execute(
            select(CompliancePlot).where(
                CompliancePlot.id == plot_id,
                CompliancePlot.tenant_id == tid,
            )
        )
    ).scalar_one_or_none()
    if plot is None:
        raise NotFoundError(f"Plot '{plot_id}' not found")

    existing = (
        await db.execute(
            select(CompliancePlotDocument).where(
                CompliancePlotDocument.plot_id == plot_id,
                CompliancePlotDocument.media_file_id == body.media_file_id,
                CompliancePlotDocument.tenant_id == tid,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        from app.core.errors import ConflictError
        raise ConflictError("Document already linked to this plot")

    file_hash = None
    filename = None
    try:
        http = get_http_client()
        settings = get_settings()
        resp = await http.get(
            f"{settings.MEDIA_SERVICE_URL}/api/v1/internal/media/files/{body.media_file_id}",
            headers={
                "X-Service-Token": settings.S2S_SERVICE_TOKEN,
                "X-Tenant-Id": str(tid),
            },
        )
        if resp.status_code == 200:
            fdata = resp.json()
            file_hash = fdata.get("file_hash")
            filename = fdata.get("original_filename") or fdata.get("filename")
    except Exception:
        pass

    doc = CompliancePlotDocument(
        tenant_id=tid,
        plot_id=plot_id,
        media_file_id=body.media_file_id,
        document_type=body.document_type,
        file_hash=file_hash,
        filename=filename,
        description=body.description,
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)
    return doc


@router.get("/{plot_id}/documents", response_model=list[DocumentLinkWithUrl])
async def list_plot_documents(
    plot_id: uuid.UUID,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    tid = _tenant_id(user)

    docs = (
        await db.execute(
            select(CompliancePlotDocument).where(
                CompliancePlotDocument.plot_id == plot_id,
                CompliancePlotDocument.tenant_id == tid,
            )
        )
    ).scalars().all()

    results = []
    http = get_http_client()
    settings = get_settings()
    for doc in docs:
        url = None
        try:
            resp = await http.get(
                f"{settings.MEDIA_SERVICE_URL}/api/v1/internal/media/files/{doc.media_file_id}",
                headers={
                    "X-Service-Token": settings.S2S_SERVICE_TOKEN,
                    "X-Tenant-Id": str(tid),
                },
            )
            if resp.status_code == 200:
                url = resp.json().get("url")
        except Exception:
            pass
        r = DocumentLinkWithUrl.model_validate(doc)
        r.url = url
        results.append(r)

    return results


@router.delete("/{plot_id}/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def detach_plot_document(
    plot_id: uuid.UUID,
    doc_id: uuid.UUID,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    tid = _tenant_id(user)
    doc = (
        await db.execute(
            select(CompliancePlotDocument).where(
                CompliancePlotDocument.id == doc_id,
                CompliancePlotDocument.plot_id == plot_id,
                CompliancePlotDocument.tenant_id == tid,
            )
        )
    ).scalar_one_or_none()
    if doc is None:
        raise NotFoundError("Document link not found")

    await db.delete(doc)
    await db.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
