"""Router for compliance plots (production parcels)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser
from app.compliance.geojson_validator import (
    GeoJsonValidationError,
    parse_decimal_geojson_from_body,
    polygon_area_ha_from_geojson,
    validate_geojson_strict,
)
from app.core.errors import ConflictError, NotFoundError


async def _strict_validate_geojson_from_request(
    request: Request, declared_area_ha=None,
) -> dict:
    """Re-parsea el body crudo del request con Decimal-preservation y valida.

    Necesario porque pydantic ya colapso los floats (perdiendo ceros finales)
    para cuando llegamos al handler. Solo asi podemos chequear con precision
    el Art. 2(28) sobre lo que el usuario realmente envio.

    Asume que el caller ya verifico que ``geojson_data`` esta presente en el
    body. Si el reparseo crudo no encuentra el campo, lanza HTTP 500 (es un
    bug interno: pydantic vio el campo pero el reparseo no). Lanza HTTP 422
    con detalle EUDR si la geometria es invalida.
    """
    raw = await request.body()
    geom_dec = parse_decimal_geojson_from_body(raw)
    if geom_dec is None:
        raise HTTPException(
            status_code=500,
            detail=(
                "Error interno: no se pudo re-parsear geojson_data del body para "
                "validacion estricta de precision EUDR. Reportar este caso."
            ),
        )
    try:
        return validate_geojson_strict(geom_dec, declared_area_ha=declared_area_ha)
    except GeoJsonValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"GeoJSON invalido (EUDR Art. 2(28)): {exc}",
        )


def _validate_positive_area(area_ha) -> None:
    """Rechaza areas negativas o cero. None es valido (area opcional)."""
    if area_ha is None:
        return
    try:
        a = float(area_ha)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=422,
            detail=f"plot_area_ha debe ser numerico, recibido: {area_ha!r}",
        )
    if a <= 0:
        raise HTTPException(
            status_code=422,
            detail=f"plot_area_ha debe ser mayor a cero. Recibido: {a} ha.",
        )


def _validate_polygon_requirement(
    area_ha,
    geojson_url: str | None,
    geolocation_type: str | None,
    geojson_data: dict | None = None,
):
    """EUDR Art. 9.1.c / Art. 2(28): plots > 4 ha require polygon geolocation.

    El reglamento dice literalmente "more than four hectares" — la comparacion
    es **estricta** (>), no inclusive. Una parcela de exactamente 4.0 ha puede
    declararse con un solo punto. Solo a partir de 4.000001 ha es obligatorio
    el poligono.

    Accepts either a remote `geojson_arweave_url`, a locally-stored `geojson_data`,
    or `geolocation_type='polygon'` as evidence of polygon coverage.
    """
    if area_ha is not None and float(area_ha) > 4.0:
        has_polygon = (
            bool(geojson_url)
            or bool(geojson_data)
            or geolocation_type == "polygon"
        )
        if not has_polygon:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Parcelas mayores a 4 ha requieren poligono completo "
                    "— EUDR Art. 9.1.c / Art. 2(28). Use geolocation_type='polygon' "
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
    request: Request,
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

    _validate_positive_area(body.plot_area_ha)
    _validate_polygon_requirement(
        body.plot_area_ha,
        body.geojson_arweave_url,
        body.geolocation_type,
        body.geojson_data,
    )

    # EUDR Art. 2(28): validar y normalizar geometria antes de persistir.
    # Re-parsea el body crudo para preservar ceros finales (4.654400 vs 4.6544).
    # Pasamos el area declarada para que el validator rechace polygons cuya
    # area diverja absurdamente (caso real: poligono de 1.5M ha vs declarada 13 ha).
    data = body.model_dump(exclude_unset=True)
    if body.geojson_data is not None:
        normalized = await _strict_validate_geojson_from_request(
            request, declared_area_ha=body.plot_area_ha,
        )
        data["geojson_data"] = normalized
        # Auto-sync: la geometria es la fuente de verdad para EUDR. Si el
        # poligono paso la validacion, sobreescribimos plot_area_ha con el
        # area calculada — asi el screening satelital y el DDS usan numeros
        # consistentes con la geometria, no con la declaracion del operador.
        poly_area = polygon_area_ha_from_geojson(normalized)
        if poly_area > 0:
            data["plot_area_ha"] = round(poly_area, 4)
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
    request: Request,
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

    # EUDR Art. 2(28): si el PATCH incluye geojson_data NO null, re-parseamos
    # el body crudo (preserva ceros finales) y validamos estrictamente. Pasamos
    # el area declarada (la nueva si vino en el PATCH, o la existente del DB)
    # para validacion de consistencia poligono↔area.
    if "geojson_data" in update_data and update_data["geojson_data"] is not None:
        declared_for_check = update_data.get("plot_area_ha", plot.plot_area_ha)
        normalized = await _strict_validate_geojson_from_request(
            request, declared_area_ha=declared_for_check,
        )
        update_data["geojson_data"] = normalized
        # Auto-sync: la geometria manda. Si el caller envio plot_area_ha
        # explicito en este mismo PATCH lo respetamos (asume que el operador
        # esta corrigiendo ambos). Si no, sobreescribimos con el area calculada.
        if "plot_area_ha" not in update_data:
            poly_area = polygon_area_ha_from_geojson(normalized)
            if poly_area > 0:
                update_data["plot_area_ha"] = round(poly_area, 4)

    # Validate polygon requirement with merged values (post-normalizacion).
    final_area = update_data.get("plot_area_ha", plot.plot_area_ha)
    final_geojson = update_data.get("geojson_arweave_url", plot.geojson_arweave_url)
    final_geotype = update_data.get("geolocation_type", plot.geolocation_type)
    final_geojson_data = update_data.get("geojson_data", plot.geojson_data)
    _validate_polygon_requirement(final_area, final_geojson, final_geotype, final_geojson_data)
    _validate_positive_area(final_area)

    # Guard: rechazar borrado explicito de geojson_data en parcelas linkeadas
    # a registros de cumplimiento que requieren poligono (>4 ha). Sin esto,
    # un PATCH con {"geojson_data": null} silenciosamente eliminaria la
    # evidencia de geolocalizacion EUDR.
    if "geojson_data" in update_data and update_data["geojson_data"] is None:
        prev_area_for_guard = plot.plot_area_ha
        if prev_area_for_guard is not None and float(prev_area_for_guard) > 4.0:
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
                        f"No se puede eliminar el geojson_data de una parcela > 4 ha "
                        f"vinculada a {linked_count} registro(s) de cumplimiento. "
                        "Cargue un poligono nuevo en su lugar o desvincule los registros primero."
                    ),
                )

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


@router.post("/{plot_id}/screen-deforestation-full")
async def screen_deforestation_full(
    plot_id: uuid.UUID,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Screen a plot with 3 satellite sources (GFW + Hansen + JRC).

    Runs all sources in parallel and produces a composite EUDR risk
    assessment.  Results are stored under ``metadata_.eudr_full_screening``
    alongside the legacy ``gfw_screening`` key so both views coexist.
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

    # Build geojson — prefer local polygon, fallback to Arweave, then point
    geojson = None
    if plot.geojson_data:
        geojson = plot.geojson_data
    elif plot.geojson_arweave_url:
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
            pass

    svc = await DeforestationService.from_db(db, tenant_id=tid)
    result = await svc.check_plot_full(
        lat=plot.lat,
        lng=plot.lng,
        geojson=geojson,
        area_ha=plot.plot_area_ha,
    )

    # Auto-update plot flags based on composite result
    if result.get("eudr_compliant") is not None:
        plot.deforestation_free = result["eudr_compliant"]
        plot.satellite_verified_at = datetime.now(tz=timezone.utc)

    # Persist per-source results + composite in metadata_
    meta = dict(plot.metadata_ or {})

    # Keep legacy gfw_screening in sync
    gfw_src = result.get("sources", {}).get("gfw_integrated_alerts", {})
    if gfw_src and gfw_src.get("deforestation_free") is not None:
        meta["gfw_screening"] = {
            "alerts_count": gfw_src.get("alerts_count", 0),
            "high_confidence": gfw_src.get("high_confidence_alerts", 0),
            "checked_at": gfw_src.get("checked_at"),
            "source": gfw_src.get("source"),
            "cutoff_date": gfw_src.get("cutoff_date"),
        }

    hansen_src = result.get("sources", {}).get("umd_tree_cover_loss", {})
    if hansen_src:
        meta["hansen_screening"] = {
            "has_loss": hansen_src.get("has_loss"),
            "loss_pixels": hansen_src.get("loss_pixels", 0),
            "loss_by_year": hansen_src.get("loss_by_year", {}),
            "checked_at": hansen_src.get("checked_at"),
            "source": hansen_src.get("source"),
        }

    jrc_src = result.get("sources", {}).get("jrc_global_forest_cover", {})
    if jrc_src:
        meta["jrc_screening"] = {
            "was_forest_2020": jrc_src.get("was_forest_2020"),
            "forest_pixel_count": jrc_src.get("forest_pixel_count", 0),
            "checked_at": jrc_src.get("checked_at"),
            "source": jrc_src.get("source"),
        }

    meta["eudr_full_screening"] = {
        "eudr_compliant": result.get("eudr_compliant"),
        "eudr_risk": result.get("eudr_risk"),
        "risk_reason": result.get("risk_reason"),
        "checked_at": result.get("checked_at"),
        "elapsed_seconds": result.get("elapsed_seconds"),
        "failed_sources": result.get("failed_sources", []),
    }

    plot.metadata_ = meta
    await db.flush()
    await db.refresh(plot)

    # ── Anchor to Solana if plot is linked to assets ─────────────────────────
    # Best-effort: anchor failure does not break the screening response.
    anchor_results: list[dict] = []
    try:
        from app.services.anchor_compliance import anchor_screening_result
        from app.api.deps import get_http_client
        from app.models.record import ComplianceRecord

        # Find all records linked to this plot that have an asset_id
        linked = (
            await db.execute(
                select(CompliancePlotLink.record_id).where(
                    CompliancePlotLink.plot_id == plot_id,
                    CompliancePlotLink.tenant_id == tid,
                )
            )
        ).scalars().all()

        if linked:
            http = get_http_client()
            for record_id in linked:
                rec = (
                    await db.execute(
                        select(ComplianceRecord).where(
                            ComplianceRecord.id == record_id,
                            ComplianceRecord.tenant_id == tid,
                        )
                    )
                ).scalar_one_or_none()
                if rec and rec.asset_id:
                    ar = await anchor_screening_result(
                        http=http,
                        tenant_id=tid,
                        asset_id=rec.asset_id,
                        plot_id=plot_id,
                        plot_code=plot.plot_code,
                        screening_result=result,
                        user_id=str(user.get("user_id", "system")),
                    )
                    anchor_results.append(ar)

        # Persist anchor info in metadata
        if anchor_results:
            meta = dict(plot.metadata_ or {})
            first = anchor_results[0]
            meta["eudr_full_screening"]["anchor"] = {
                "compliance_hash": first["compliance_hash"],
                "anchor_request_id": first["anchor_request_id"],
                "anchor_status": first["anchor_status"],
                "event_id": first["event_id"],
                "anchored_assets": len(anchor_results),
            }
            plot.metadata_ = meta
            await db.flush()
            await db.refresh(plot)

    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning(f"Anchor best-effort failed: {exc}")

    return {
        "plot_id": str(plot_id),
        "plot_code": plot.plot_code,
        **result,
        "anchor": anchor_results[0] if anchor_results else None,
    }


# ─── Anchor callback (called by trace-service ARQ worker) ────────────────────

from pydantic import BaseModel as _BaseModel


class _AnchorCallbackBody(_BaseModel):
    payload_hash: str
    anchor_status: str
    solana_tx_sig: str | None = None


@router.post("/{plot_id}/anchor-callback", status_code=status.HTTP_200_OK)
async def anchor_callback(
    plot_id: uuid.UUID,
    body: _AnchorCallbackBody,
    db: AsyncSession = Depends(get_db_session),
):
    """Webhook called by trace-service when Solana anchoring completes.

    Updates the plot's ``metadata_.eudr_full_screening.anchor`` with
    the Solana transaction signature and final status.
    """
    from datetime import datetime, timezone

    plot = (
        await db.execute(
            select(CompliancePlot).where(CompliancePlot.id == plot_id)
        )
    ).scalar_one_or_none()
    if plot is None:
        raise NotFoundError(f"Plot '{plot_id}' not found")

    meta = dict(plot.metadata_ or {})
    anchor = meta.get("eudr_full_screening", {}).get("anchor")
    if not anchor:
        return {"status": "no_anchor_data", "plot_id": str(plot_id)}

    # Only accept updates for the same hash (idempotency guard)
    if anchor.get("compliance_hash") != body.payload_hash:
        return {"status": "hash_mismatch", "plot_id": str(plot_id)}

    anchor["anchor_status"] = body.anchor_status
    anchor["solana_tx_sig"] = body.solana_tx_sig
    anchor["anchored_at"] = datetime.now(tz=timezone.utc).isoformat()
    meta["eudr_full_screening"]["anchor"] = anchor
    plot.metadata_ = meta
    await db.flush()

    return {
        "status": "updated",
        "plot_id": str(plot_id),
        "anchor_status": body.anchor_status,
        "solana_tx_sig": body.solana_tx_sig,
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
