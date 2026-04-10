"""Multi-source deforestation screening for EUDR compliance.

Queries three satellite datasets via the GFW Data API:
  1. GFW Integrated Alerts — near-real-time deforestation alerts
  2. Hansen/UMD Tree Cover Loss — annual loss at 30 m resolution
  3. JRC Global Forest Cover 2020 — EU baseline forest map

API docs: https://data-api.globalforestwatch.org
"""
from __future__ import annotations

import asyncio
import math
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import httpx

from app.core.logging import get_logger
from app.core.settings import get_settings

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
EUDR_CUTOFF = "2020-12-31"
EUDR_CUTOFF_YEAR = 2021  # Hansen uses integer years; loss >= 2021 is post-cutoff
GFW_BASE = "https://data-api.globalforestwatch.org"
BUFFER_DEG = 0.005  # ~500 m default buffer for point queries
PER_SOURCE_TIMEOUT = 30.0  # seconds per individual source query

# Dataset slugs (verified via spike testing 2026-04-10)
DS_GFW_ALERTS = "gfw_integrated_alerts"
DS_HANSEN = "umd_tree_cover_loss"
DS_JRC = "jrc_global_forest_cover"

# ---------------------------------------------------------------------------
# Official source metadata — shown to the user so they know which
# institutions and standards back each verification layer.
# ---------------------------------------------------------------------------
SOURCE_METADATA: dict[str, dict[str, str]] = {
    DS_GFW_ALERTS: {
        "name": "GFW Integrated Deforestation Alerts",
        "institution": "Global Forest Watch — World Resources Institute (WRI)",
        "description": (
            "Sistema de alertas satelitales casi en tiempo real que combina "
            "GLAD-L (Landsat), GLAD-S2 (Sentinel-2) y RADD (radar). "
            "Reconocido por la Comisión Europea como herramienta de referencia "
            "para due diligence bajo el EUDR."
        ),
        "eudr_role": (
            "Detección de deforestación post-fecha de corte (31 dic 2020). "
            "Evalúa si hubo alertas de pérdida de cobertura forestal en la "
            "parcela después de la fecha límite del EUDR."
        ),
        "reference_url": "https://www.globalforestwatch.org/blog/data-and-research/integrated-deforestation-alerts/",
        "dataset": DS_GFW_ALERTS,
    },
    DS_HANSEN: {
        "name": "Hansen Global Forest Change (UMD Tree Cover Loss)",
        "institution": "University of Maryland — Hansen, Potapov, Moore et al.",
        "description": (
            "Dataset científico peer-reviewed de pérdida anual de cobertura "
            "arbórea a resolución de 30 m. Publicado en Science y actualizado "
            "anualmente. Base científica del monitoreo global de deforestación."
        ),
        "eudr_role": (
            "Verificación histórica de pérdida de cobertura arbórea año a año "
            "desde 2001. Pérdida en años >= 2021 indica cambio post-fecha de "
            "corte EUDR."
        ),
        "reference_url": "https://glad.earthengine.app/view/global-forest-change",
        "dataset": DS_HANSEN,
    },
    DS_JRC: {
        "name": "JRC Global Map of Forest Cover 2020",
        "institution": "Joint Research Centre — Comisión Europea (EU Forest Observatory)",
        "description": (
            "Mapa oficial de cobertura forestal a 10 m creado por el brazo "
            "científico de la Unión Europea, específicamente para soportar la "
            "implementación del EUDR. Cobertura global, no solo bosque tropical."
        ),
        "eudr_role": (
            "Establece la línea base: ¿era bosque la parcela en 2020? "
            "Si la parcela NO era bosque, el EUDR no aplica restricciones "
            "de deforestación. Si SÍ era bosque, se requiere verificar que "
            "no hubo pérdida posterior."
        ),
        "reference_url": "https://forest-observatory.ec.europa.eu/",
        "dataset": DS_JRC,
    },
}


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------
def _point_to_polygon(
    lat: float, lng: float, buffer: float = BUFFER_DEG, area_ha: float | None = None,
) -> dict:
    """Create a square polygon around a point for GFW query.

    Corrects longitude buffer by cos(lat) so that the square is geometrically
    accurate at any latitude (not skewed near the poles).
    """
    if area_ha and area_ha > 0:
        side_m = math.sqrt(area_ha * 10_000)
        half_side_m = side_m / 2
        buffer_lat = half_side_m / 111_320
    else:
        buffer_lat = buffer
    cos_lat = max(math.cos(math.radians(lat)), 0.001)
    buffer_lng = buffer_lat / cos_lat
    return {
        "type": "Polygon",
        "coordinates": [[
            [lng - buffer_lng, lat - buffer_lat],
            [lng + buffer_lng, lat - buffer_lat],
            [lng + buffer_lng, lat + buffer_lat],
            [lng - buffer_lng, lat + buffer_lat],
            [lng - buffer_lng, lat - buffer_lat],
        ]],
    }


def _build_geometry(
    lat: float | Decimal | None,
    lng: float | Decimal | None,
    geojson: dict | None = None,
    area_ha: float | Decimal | None = None,
) -> dict | None:
    """Normalise a GeoJSON input or build one from coordinates.

    Returns a Polygon/MultiPolygon dict ready to send to the GFW API,
    or ``None`` when there is not enough information.
    """
    if geojson:
        if geojson.get("type") == "FeatureCollection" and geojson.get("features"):
            return geojson["features"][0].get("geometry", geojson)
        if geojson.get("type") == "Feature":
            return geojson.get("geometry", geojson)
        return geojson
    if lat is not None and lng is not None:
        return _point_to_polygon(
            float(lat), float(lng),
            area_ha=float(area_ha) if area_ha else None,
        )
    return None


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _error_result(source: str, error: str) -> dict[str, Any]:
    """Standard error envelope for a single source."""
    return {
        "source": source,
        "error": error,
        "checked_at": _now_iso(),
        **SOURCE_METADATA.get(source, {}),
    }


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------
class DeforestationService:
    """Multi-source deforestation screening via Global Forest Watch API."""

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or get_settings().GFW_API_KEY

    @classmethod
    async def from_db(cls, db, tenant_id=None) -> "DeforestationService":
        """Build instance with per-tenant credentials loaded from DB."""
        from app.services.integration_service import IntegrationCredentialsService
        svc = IntegrationCredentialsService(db, tenant_id=tenant_id)
        creds = await svc.get_credentials("gfw")
        return cls(api_key=creds.get("api_key") or None)

    # ------------------------------------------------------------------
    # Shared HTTP helper
    # ------------------------------------------------------------------
    async def _query_dataset(
        self,
        dataset: str,
        sql: str,
        geometry: dict,
        timeout: float = PER_SOURCE_TIMEOUT,
    ) -> dict[str, Any]:
        """POST a SQL query to the GFW Data API and return parsed JSON."""
        url = f"{GFW_BASE}/dataset/{dataset}/latest/query/json"
        headers = {"x-api-key": self._api_key, "Content-Type": "application/json"}
        t0 = time.monotonic()
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as http:
            resp = await http.post(url, headers=headers, json={"sql": sql, "geometry": geometry})
        elapsed = time.monotonic() - t0
        log.info("gfw_query", dataset=dataset, status=resp.status_code, elapsed_s=round(elapsed, 2))
        if resp.status_code != 200:
            raise RuntimeError(f"GFW API {resp.status_code}: {resp.text[:300]}")
        return resp.json()

    # ------------------------------------------------------------------
    # 1. GFW Integrated Alerts (existing — refactored)
    # ------------------------------------------------------------------
    async def check_plot(
        self,
        lat: float | Decimal | None = None,
        lng: float | Decimal | None = None,
        geojson: dict | None = None,
        cutoff_date: str = EUDR_CUTOFF,
        area_ha: float | Decimal | None = None,
    ) -> dict[str, Any]:
        """Check GFW integrated deforestation alerts for a plot."""
        source = DS_GFW_ALERTS
        if not self._api_key:
            return {
                "deforestation_free": None,
                "not_configured": True,
                "alerts_count": 0,
                "alerts": [],
                "high_confidence_alerts": 0,
                "error": (
                    "GFW API key no configurada. Configura la integración en "
                    "Cumplimiento → Integraciones para habilitar el screening satelital."
                ),
                "source": "none",
            }

        geometry = _build_geometry(lat, lng, geojson, area_ha)
        if not geometry:
            return {"deforestation_free": None, "alerts_count": 0, "alerts": [], "error": "No coordinates provided", "source": "none"}

        # Validate cutoff_date
        try:
            datetime.fromisoformat(cutoff_date)
        except (TypeError, ValueError):
            return {"deforestation_free": None, "alerts_count": 0, "alerts": [], "error": f"Invalid cutoff_date format: {cutoff_date}", "source": source}

        sql = (
            f"SELECT latitude, longitude, gfw_integrated_alerts__date, "
            f"gfw_integrated_alerts__confidence "
            f"FROM results "
            f"WHERE gfw_integrated_alerts__date >= '{cutoff_date}' "
            f"LIMIT 1000"
        )

        try:
            data = await self._query_dataset(source, sql, geometry, timeout=get_settings().GFW_TIMEOUT)
            alerts = data.get("data", [])
            high_conf = [a for a in alerts if a.get("gfw_integrated_alerts__confidence") in ("high", "highest")]

            result = {
                "deforestation_free": len(alerts) == 0,
                "alerts_count": len(alerts),
                "alerts": alerts[:20],
                "high_confidence_alerts": len(high_conf),
                "checked_at": _now_iso(),
                "source": source,
                "cutoff_date": cutoff_date,
                **SOURCE_METADATA[source],
            }

            log.info(
                "gfw_check_complete",
                alerts=len(alerts), high_confidence=len(high_conf),
                deforestation_free=result["deforestation_free"],
            )
            return result

        except Exception as exc:
            log.error("gfw_check_error", exc=str(exc))
            return {
                "deforestation_free": None, "alerts_count": 0, "alerts": [],
                "high_confidence_alerts": 0,
                "error": str(exc), "checked_at": _now_iso(),
                "source": source, **SOURCE_METADATA[source],
            }

    # ------------------------------------------------------------------
    # 2. Hansen / UMD Tree Cover Loss
    # ------------------------------------------------------------------
    async def check_plot_hansen(
        self,
        geometry: dict,
        cutoff_year: int = EUDR_CUTOFF_YEAR,
    ) -> dict[str, Any]:
        """Check Hansen/UMD tree-cover loss post-cutoff year."""
        source = DS_HANSEN
        sql = (
            f"SELECT umd_tree_cover_loss__year, count(*) as pixel_count "
            f"FROM results "
            f"WHERE umd_tree_cover_loss__year >= {cutoff_year} "
            f"GROUP BY umd_tree_cover_loss__year "
            f"ORDER BY umd_tree_cover_loss__year "
            f"LIMIT 100"
        )
        try:
            data = await self._query_dataset(source, sql, geometry)
            rows = data.get("data", [])
            loss_by_year: dict[int, int] = {}
            total_loss = 0
            for row in rows:
                yr = row.get("umd_tree_cover_loss__year")
                cnt = row.get("count", row.get("pixel_count", 0))
                if yr is not None:
                    loss_by_year[yr] = cnt
                    total_loss += cnt

            result = {
                "source": source,
                "has_loss": total_loss > 0,
                "loss_pixels": total_loss,
                "loss_by_year": loss_by_year,
                "cutoff_year": cutoff_year,
                "checked_at": _now_iso(),
                "error": None,
                **SOURCE_METADATA[source],
            }
            log.info("hansen_check_complete", total_loss=total_loss, years=loss_by_year)
            return result

        except Exception as exc:
            log.error("hansen_check_error", exc=str(exc))
            return {**_error_result(source, str(exc)), "has_loss": None, "loss_pixels": 0, "loss_by_year": {}}

    # ------------------------------------------------------------------
    # 3. JRC Global Forest Cover 2020
    # ------------------------------------------------------------------
    async def check_plot_jrc(
        self,
        geometry: dict,
        area_ha: float | Decimal | None = None,
    ) -> dict[str, Any]:
        """Check JRC forest cover baseline (2020).

        The JRC dataset is a raster — only ``count(*)`` works via the SQL
        query interface.  ``count > 0`` means the area was classified as
        forest in 2020.

        Post-query validation: if the pixel count vastly exceeds what the
        declared plot area allows (>150 pixels/ha), the result is flagged
        as a geometry mismatch so the caller knows the polygon may be wrong.
        """
        source = DS_JRC
        sql = "SELECT count(*) FROM results"
        try:
            data = await self._query_dataset(source, sql, geometry)
            rows = data.get("data", [])
            pixel_count = rows[0].get("count", 0) if rows else 0

            # Each JRC pixel is 10x10m = 100 m²
            forest_area_ha = round(pixel_count * 100 / 10_000, 2)

            # Geometry diagnostics
            coords = geometry.get("coordinates", [[]])[0] if geometry.get("type") == "Polygon" else []
            geometry_type = "poligono exacto" if len(coords) > 5 else "buffer desde coordenadas"

            # Expected pixel count based on declared area
            plot_area = float(area_ha) if area_ha else None
            jrc_pixels_expected = int(plot_area * 100) if plot_area else None
            # Threshold: 150 px/ha accounts for JRC including partial-overlap
            # border pixels — but 152x overshoot is clearly wrong geometry.
            geometry_valid = True
            geometry_error = None
            if plot_area and plot_area > 0 and pixel_count > plot_area * 150:
                geometry_valid = False
                geometry_error = (
                    f"geometry_mismatch: JRC retorno {pixel_count} pixeles "
                    f"({forest_area_ha} ha) para una parcela declarada de "
                    f"{plot_area} ha. El poligono GeoJSON es probablemente "
                    f"mas grande que la parcela real. Verifique los vertices "
                    f"del poligono."
                )
                log.warning(
                    "jrc_geometry_mismatch",
                    pixel_count=pixel_count,
                    forest_area_ha=forest_area_ha,
                    declared_area_ha=plot_area,
                    ratio=round(forest_area_ha / plot_area, 1),
                )

            result = {
                "source": source,
                "was_forest_2020": None if not geometry_valid else (pixel_count > 0),
                "forest_pixel_count": pixel_count,
                "forest_area_ha": forest_area_ha,
                "geometry_type": geometry_type,
                "jrc_pixels_expected": jrc_pixels_expected,
                "jrc_pixels_returned": pixel_count,
                "jrc_geometry_valid": geometry_valid,
                "checked_at": _now_iso(),
                "error": geometry_error,
                **SOURCE_METADATA[source],
            }
            log.info(
                "jrc_check_complete",
                forest_pixels=pixel_count,
                was_forest=result["was_forest_2020"],
                geometry_valid=geometry_valid,
                declared_ha=plot_area,
            )
            return result

        except Exception as exc:
            log.error("jrc_check_error", exc=str(exc))
            return {
                **_error_result(source, str(exc)),
                "was_forest_2020": None,
                "forest_pixel_count": 0,
                "jrc_pixels_expected": int(float(area_ha) * 100) if area_ha else None,
                "jrc_pixels_returned": 0,
                "jrc_geometry_valid": False,
            }

    # ------------------------------------------------------------------
    # 4. Full multi-source EUDR screening
    # ------------------------------------------------------------------
    async def check_plot_full(
        self,
        lat: float | Decimal | None = None,
        lng: float | Decimal | None = None,
        geojson: dict | None = None,
        cutoff_date: str = EUDR_CUTOFF,
        area_ha: float | Decimal | None = None,
    ) -> dict[str, Any]:
        """Run all three sources in parallel and compute composite EUDR risk.

        Risk logic
        ----------
        * JRC says NOT forest in 2020 → ``eudr_risk = "none"``
        * Was forest AND all 3 sources clean → ``eudr_risk = "low"``
        * Was forest AND any source detects loss → ``eudr_risk = "high"``
        * Any source could not be verified → ``eudr_risk = "medium"``
        """
        if not self._api_key:
            return {
                "eudr_compliant": None,
                "eudr_risk": "medium",
                "risk_reason": "GFW API key no configurada. Configura la integración en Cumplimiento → Integraciones.",
                "sources": {},
                "checked_at": _now_iso(),
            }

        geometry = _build_geometry(lat, lng, geojson, area_ha)
        if not geometry:
            return {
                "eudr_compliant": None,
                "eudr_risk": "medium",
                "risk_reason": "No se proporcionaron coordenadas o polígono para la parcela.",
                "sources": {},
                "checked_at": _now_iso(),
            }

        # Run all three in parallel — exceptions are captured, not raised
        t0 = time.monotonic()
        gfw_result, hansen_result, jrc_result = await asyncio.gather(
            self.check_plot(lat, lng, geojson, cutoff_date, area_ha),
            self.check_plot_hansen(geometry),
            self.check_plot_jrc(geometry, area_ha=area_ha),
            return_exceptions=True,
        )
        elapsed = round(time.monotonic() - t0, 2)

        # Normalise exceptions into error dicts
        sources: dict[str, Any] = {}
        for key, res in [
            (DS_GFW_ALERTS, gfw_result),
            (DS_HANSEN, hansen_result),
            (DS_JRC, jrc_result),
        ]:
            if isinstance(res, BaseException):
                sources[key] = _error_result(key, str(res))
            else:
                sources[key] = res

        # Extract values (None = could not verify)
        gfw_clean = sources[DS_GFW_ALERTS].get("deforestation_free")      # True / False / None
        hansen_has_loss = sources[DS_HANSEN].get("has_loss")               # True / False / None
        jrc_was_forest = sources[DS_JRC].get("was_forest_2020")           # True / False / None

        # Determine which sources had errors (including geometry mismatches)
        failed_sources = [k for k, v in sources.items() if v.get("error")]
        # Flag geometry mismatch specifically for clearer diagnostics
        geometry_warnings = []
        if sources.get(DS_JRC, {}).get("jrc_geometry_valid") is False:
            geometry_warnings.append(
                f"JRC: poligono inconsistente con area declarada "
                f"({sources[DS_JRC].get('jrc_pixels_returned', 0)} px retornados "
                f"vs {sources[DS_JRC].get('jrc_pixels_expected', '?')} px esperados)"
            )

        # ----- EUDR decision logic -----
        if jrc_was_forest is False:
            # Not forest in 2020 → EUDR deforestation rules don't apply
            eudr_risk = "none"
            eudr_compliant = True
            risk_reason = (
                "La parcela NO estaba clasificada como bosque en 2020 según el mapa "
                "JRC de la Comisión Europea. Las restricciones de deforestación del "
                "EUDR no aplican a esta parcela."
            )

        elif jrc_was_forest is None:
            # JRC failed — can't determine baseline
            eudr_risk = "medium"
            eudr_compliant = None
            risk_reason = (
                "No se pudo verificar la línea base forestal (JRC). "
                "Se requiere verificación manual o reintento."
            )

        elif failed_sources and jrc_was_forest is True:
            # Was forest but some alert sources failed
            working = [k for k in [DS_GFW_ALERTS, DS_HANSEN] if k not in failed_sources]
            any_detection = False
            for k in working:
                if k == DS_GFW_ALERTS and sources[k].get("deforestation_free") is False:
                    any_detection = True
                if k == DS_HANSEN and sources[k].get("has_loss") is True:
                    any_detection = True

            if any_detection:
                eudr_risk = "high"
                eudr_compliant = False
                risk_reason = (
                    "La parcela ERA bosque en 2020 y al menos una fuente funcional "
                    "detectó pérdida de cobertura post-fecha de corte. "
                    f"Fuentes con error: {', '.join(failed_sources)}."
                )
            else:
                eudr_risk = "medium"
                eudr_compliant = None
                risk_reason = (
                    "La parcela ERA bosque en 2020. Las fuentes funcionales no detectaron "
                    "pérdida, pero no se pudieron verificar todas las fuentes. "
                    f"Fuentes con error: {', '.join(failed_sources)}."
                )

        else:
            # JRC = forest, all sources responded
            gfw_detected = gfw_clean is False
            hansen_detected = hansen_has_loss is True

            if gfw_detected or hansen_detected:
                eudr_risk = "high"
                eudr_compliant = False
                detections = []
                if gfw_detected:
                    cnt = sources[DS_GFW_ALERTS].get("alerts_count", 0)
                    high = sources[DS_GFW_ALERTS].get("high_confidence_alerts", 0)
                    detections.append(f"GFW: {cnt} alertas ({high} alta confianza)")
                if hansen_detected:
                    px = sources[DS_HANSEN].get("loss_pixels", 0)
                    detections.append(f"Hansen: {px} píxeles de pérdida")
                risk_reason = (
                    "La parcela ERA bosque en 2020 y se detectó pérdida de cobertura "
                    f"forestal post-fecha de corte. {'; '.join(detections)}."
                )
            else:
                eudr_risk = "low"
                eudr_compliant = True
                risk_reason = (
                    "La parcela ERA bosque en 2020 y las tres fuentes satelitales "
                    "(GFW, Hansen/UMD, JRC) confirman que NO hubo pérdida de "
                    "cobertura forestal después de la fecha de corte del EUDR "
                    "(31 de diciembre de 2020)."
                )

        result = {
            "eudr_compliant": eudr_compliant,
            "eudr_risk": eudr_risk,
            "risk_reason": risk_reason,
            "sources": sources,
            "checked_at": _now_iso(),
            "elapsed_seconds": elapsed,
            "failed_sources": failed_sources,
            "geometry_warnings": geometry_warnings,
        }

        log.info(
            "eudr_full_screening_complete",
            eudr_risk=eudr_risk, eudr_compliant=eudr_compliant,
            elapsed_s=elapsed, failed=failed_sources,
        )
        return result
