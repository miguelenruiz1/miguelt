"""Global Forest Watch integration — automatic deforestation screening.

Queries the GFW Data API for deforestation alerts within a plot's
coordinates after the EUDR cutoff date (31 Dec 2020).

API docs: https://data-api.globalforestwatch.org
Dataset: gfw_integrated_alerts
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import httpx

from app.core.logging import get_logger
from app.core.settings import get_settings

log = get_logger(__name__)

EUDR_CUTOFF = "2020-12-31"
GFW_BASE = "https://data-api.globalforestwatch.org"
DATASET = "gfw_integrated_alerts"
BUFFER_DEG = 0.005  # ~500m buffer for point queries


def _point_to_polygon(lat: float, lng: float, buffer: float = BUFFER_DEG) -> dict:
    """Create a small square polygon around a point for GFW query."""
    return {
        "type": "Polygon",
        "coordinates": [[
            [lng - buffer, lat - buffer],
            [lng + buffer, lat - buffer],
            [lng + buffer, lat + buffer],
            [lng - buffer, lat + buffer],
            [lng - buffer, lat - buffer],
        ]],
    }


class DeforestationService:
    """Check deforestation alerts via Global Forest Watch API."""

    def __init__(self, api_key: str | None = None) -> None:
        # Prefer DB-stored key, fallback to env var
        self._api_key = api_key or get_settings().GFW_API_KEY

    @classmethod
    async def from_db(cls, db) -> "DeforestationService":
        """Build instance with credentials loaded from DB."""
        from app.services.integration_service import IntegrationCredentialsService
        svc = IntegrationCredentialsService(db)
        creds = await svc.get_credentials("gfw")
        return cls(api_key=creds.get("api_key") or None)

    async def check_plot(
        self,
        lat: float | Decimal | None,
        lng: float | Decimal | None,
        geojson: dict | None = None,
        cutoff_date: str = EUDR_CUTOFF,
    ) -> dict[str, Any]:
        """Check deforestation alerts for a plot.

        Returns:
            {
                "deforestation_free": bool,
                "alerts_count": int,
                "alerts": [...],
                "high_confidence_alerts": int,
                "checked_at": "2026-03-28T...",
                "source": "gfw_integrated_alerts",
                "cutoff_date": "2020-12-31",
            }
        """
        if not self._api_key:
            return {
                "deforestation_free": None,
                "alerts_count": 0,
                "alerts": [],
                "high_confidence_alerts": 0,
                "error": "GFW_API_KEY not configured",
                "source": "none",
            }

        # Build geometry
        if geojson and geojson.get("type") == "Polygon":
            geometry = geojson
        elif lat is not None and lng is not None:
            geometry = _point_to_polygon(float(lat), float(lng))
        else:
            return {
                "deforestation_free": None,
                "alerts_count": 0,
                "alerts": [],
                "error": "No coordinates provided",
                "source": "none",
            }

        # Query GFW
        sql = (
            f"SELECT latitude, longitude, gfw_integrated_alerts__date, "
            f"gfw_integrated_alerts__confidence "
            f"FROM results "
            f"WHERE gfw_integrated_alerts__date >= '{cutoff_date}'"
        )

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as http:
                resp = await http.post(
                    f"{GFW_BASE}/dataset/{DATASET}/latest/query/json",
                    headers={"x-api-key": self._api_key, "Content-Type": "application/json"},
                    json={"sql": sql, "geometry": geometry},
                )

                if resp.status_code != 200:
                    log.warning("gfw_query_failed", status=resp.status_code, body=resp.text[:300])
                    return {
                        "deforestation_free": None,
                        "alerts_count": 0,
                        "alerts": [],
                        "error": f"GFW API error: {resp.status_code}",
                        "source": "gfw_integrated_alerts",
                    }

                data = resp.json()
                alerts = data.get("data", [])
                high_conf = [a for a in alerts if a.get("gfw_integrated_alerts__confidence") == "high"]

                from datetime import datetime, timezone
                result = {
                    "deforestation_free": len(alerts) == 0,
                    "alerts_count": len(alerts),
                    "alerts": alerts[:20],  # Cap at 20 for response size
                    "high_confidence_alerts": len(high_conf),
                    "checked_at": datetime.now(tz=timezone.utc).isoformat(),
                    "source": "gfw_integrated_alerts",
                    "cutoff_date": cutoff_date,
                }

                log.info(
                    "gfw_check_complete",
                    alerts=len(alerts),
                    high_confidence=len(high_conf),
                    deforestation_free=result["deforestation_free"],
                    lat=float(lat) if lat else None,
                    lng=float(lng) if lng else None,
                )

                return result

        except Exception as exc:
            log.error("gfw_check_error", exc=str(exc))
            return {
                "deforestation_free": None,
                "alerts_count": 0,
                "alerts": [],
                "error": str(exc),
                "source": "gfw_integrated_alerts",
            }
