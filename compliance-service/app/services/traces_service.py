"""TRACES NT integration — DDS submission to EU information system.

Implements the SOAP-based API for submitting Due Diligence Statements
to the European Commission's TRACES NT system (Regulation EU 2024/3084).
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any
from xml.sax.saxutils import escape as xml_escape

import httpx

from app.core.logging import get_logger
from app.core.settings import get_settings

log = get_logger(__name__)

# TRACES NT WSDL endpoints (V2 in both environments)
TRACES_URLS = {
    "acceptance": "https://eudr-cf-acceptance.tracesnt.ec.europa.eu/tracesnt/ws/EUDRSubmissionServiceV2",
    "production": "https://eudr.tracesnt.ec.europa.eu/tracesnt/ws/EUDRSubmissionServiceV2",
}

# EUDR commodity codes mapping
COMMODITY_HS_MAP = {
    "coffee": "0901", "cafe": "0901",
    "cocoa": "1801", "cacao": "1801",
    "palm_oil": "1511", "palma": "1511",
    "soy": "1201", "soja": "1201",
    "rubber": "4001", "caucho": "4001",
    "cattle": "0102", "ganado": "0102",
    "wood": "4403", "madera": "4403",
}


def _xe(value: Any) -> str:
    """Escape any value for safe inclusion in XML text content."""
    if value is None:
        return ""
    return xml_escape(str(value))


def _plot_geometry(plot: dict) -> dict:
    """Pick the best geometry for a plot: prefer real polygon over a Point."""
    geo = plot.get("geojson_data")
    if isinstance(geo, dict) and geo.get("type") in ("Polygon", "MultiPolygon"):
        return geo
    if isinstance(geo, dict) and geo.get("type") == "Feature" and isinstance(geo.get("geometry"), dict):
        return geo["geometry"]
    if isinstance(geo, dict) and geo.get("type") == "FeatureCollection":
        feats = geo.get("features") or []
        if feats and isinstance(feats[0], dict) and isinstance(feats[0].get("geometry"), dict):
            return feats[0]["geometry"]
    lat = plot.get("lat")
    lng = plot.get("lng")
    if lat is None or lng is None:
        return {}
    return {"type": "Point", "coordinates": [float(lng), float(lat)]}


def build_dds_payload(
    record: dict,
    plots: list[dict],
    operator: dict | None = None,
) -> dict[str, Any]:
    """Build DDS payload matching TRACES NT schema.

    Returns a structured dict that mirrors the TRACES NT DDS fields. Uses real
    polygons when available (not just points) and tolerates None values.
    """
    features = []
    for plot in plots:
        geometry = _plot_geometry(plot)
        if not geometry:
            continue
        feature = {
            "type": "Feature",
            "properties": {
                "plot_code": plot.get("plot_code"),
                "area_ha": plot.get("plot_area_ha"),
                "country": plot.get("country_code", "CO"),
                "municipality": plot.get("municipality"),
                "risk_level": plot.get("risk_level"),
                "deforestation_free": plot.get("deforestation_free"),
                "establishment_date": str(plot.get("establishment_date") or ""),
            },
            "geometry": geometry,
        }
        features.append(feature)

    geojson_collection = {"type": "FeatureCollection", "features": features}
    geojson_b64 = base64.b64encode(
        json.dumps(geojson_collection, ensure_ascii=False).encode("utf-8")
    ).decode("ascii")

    activity_map = {
        "export": "TRADE",
        "import": "IMPORT",
        "domestic_production": "DOMESTIC_PRODUCTION",
    }
    operator_type = (record.get("operator_type") or "OPERATOR").upper()

    hs_code = (record.get("hs_code") or "").strip()
    hs_heading = hs_code[:4] if hs_code else ""

    dds = {
        "internalReferenceNumber": record.get("id") or str(uuid.uuid4()),
        "activityType": activity_map.get(record.get("activity_type", "export"), "TRADE"),
        "operatorType": operator_type,
        "countryOfActivity": record.get("country_of_production") or "CO",

        "operator": {
            "name": record.get("buyer_name") or record.get("supplier_name") or "",
            "address": record.get("buyer_address") or record.get("supplier_address") or "",
            "email": record.get("buyer_email") or record.get("supplier_email") or "",
            "eoriNumber": record.get("operator_eori"),
        },

        "commodities": [
            {
                "hsHeading": hs_heading,
                "hsCode": hs_code,
                "description": record.get("product_description") or "",
                "scientificName": record.get("scientific_name"),
                "quantity": {
                    "netMass": float(record.get("quantity_kg") or 0),
                    "unit": "KGM",
                },
                "countryOfProduction": record.get("country_of_production") or "CO",
            }
        ],

        "geometryGeojson": geojson_b64,
        "geoLocationConfidential": False,

        "productionPeriod": {
            "start": str(record.get("production_period_start") or ""),
            "end": str(record.get("production_period_end") or ""),
        },

        "supplier": {
            "name": record.get("supplier_name") or "",
            "address": record.get("supplier_address") or "",
            "email": record.get("supplier_email") or "",
        },

        "associatedStatements": record.get("prior_dds_references") or [],

        "declarations": {
            "deforestationFree": record.get("deforestation_free_declaration", False),
            "legalCompliance": record.get("legal_compliance_declaration", False),
        },

        "signatory": {
            "name": record.get("signatory_name") or "",
            "role": record.get("signatory_role") or "",
            "date": str(record.get("signatory_date") or ""),
        },

        "tracelog_metadata": {
            "record_id": record.get("id"),
            "framework_slug": record.get("framework_slug"),
            "certificate_number": record.get("certificate_number"),
            "blockchain_verified": True,
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        },
    }

    return dds


def build_soap_envelope(
    dds: dict,
    username: str,
    auth_key: str,
    client_id: str = "eudr-test",
) -> str:
    """Build SOAP XML envelope for TRACES NT submission with WS-Security."""
    import secrets
    from datetime import timedelta

    now = datetime.now(tz=timezone.utc)
    nonce_raw = secrets.token_bytes(16)
    nonce_b64 = base64.b64encode(nonce_raw).decode()
    created = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    expires = (now + timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    digest_input = nonce_raw + created.encode() + auth_key.encode()
    password_digest = base64.b64encode(hashlib.sha1(digest_input).digest()).decode()

    commodity = dds["commodities"][0]
    sci_name_xml = (
        f"<eudr:scientificName>{_xe(commodity.get('scientificName'))}</eudr:scientificName>"
        if commodity.get("scientificName")
        else ""
    )
    eori_xml = (
        f"<eudr:eoriNumber>{_xe(dds['operator']['eoriNumber'])}</eudr:eoriNumber>"
        if dds["operator"].get("eoriNumber")
        else ""
    )

    envelope = f"""<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
               xmlns:eudr="http://ec.europa.eu/tracesnt/eudr">
  <soap:Header>
    <wsse:Security xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd"
                   xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd"
                   soap:mustUnderstand="1">
      <wsu:Timestamp wsu:Id="TS-1">
        <wsu:Created>{_xe(created)}</wsu:Created>
        <wsu:Expires>{_xe(expires)}</wsu:Expires>
      </wsu:Timestamp>
      <wsse:UsernameToken>
        <wsse:Username>{_xe(username)}</wsse:Username>
        <wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordDigest">{_xe(password_digest)}</wsse:Password>
        <wsse:Nonce EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary">{_xe(nonce_b64)}</wsse:Nonce>
        <wsu:Created>{_xe(created)}</wsu:Created>
      </wsse:UsernameToken>
    </wsse:Security>
    <eudr:webServiceClientId>{_xe(client_id)}</eudr:webServiceClientId>
  </soap:Header>
  <soap:Body>
    <eudr:submitDds>
      <eudr:internalReferenceNumber>{_xe(dds['internalReferenceNumber'])}</eudr:internalReferenceNumber>
      <eudr:operatorType>{_xe(dds['operatorType'])}</eudr:operatorType>
      <eudr:activityType>{_xe(dds['activityType'])}</eudr:activityType>
      <eudr:countryOfActivity>{_xe(dds['countryOfActivity'])}</eudr:countryOfActivity>
      <eudr:operator>
        <eudr:name>{_xe(dds['operator']['name'])}</eudr:name>
        <eudr:address>{_xe(dds['operator']['address'])}</eudr:address>
        <eudr:email>{_xe(dds['operator']['email'])}</eudr:email>
        {eori_xml}
      </eudr:operator>
      <eudr:commodity>
        <eudr:hsHeading>{_xe(commodity['hsHeading'])}</eudr:hsHeading>
        <eudr:hsCode>{_xe(commodity['hsCode'])}</eudr:hsCode>
        <eudr:description>{_xe(commodity['description'])}</eudr:description>
        {sci_name_xml}
        <eudr:netMass>{_xe(commodity['quantity']['netMass'])}</eudr:netMass>
        <eudr:netMassUnit>KGM</eudr:netMassUnit>
        <eudr:countryOfProduction>{_xe(commodity['countryOfProduction'])}</eudr:countryOfProduction>
      </eudr:commodity>
      <eudr:geometryGeojson>{_xe(dds['geometryGeojson'])}</eudr:geometryGeojson>
      <eudr:geoLocationConfidential>{str(dds['geoLocationConfidential']).lower()}</eudr:geoLocationConfidential>
      <eudr:productionPeriodStart>{_xe(dds['productionPeriod']['start'])}</eudr:productionPeriodStart>
      <eudr:productionPeriodEnd>{_xe(dds['productionPeriod']['end'])}</eudr:productionPeriodEnd>
      <eudr:supplier>
        <eudr:name>{_xe(dds['supplier']['name'])}</eudr:name>
        <eudr:address>{_xe(dds['supplier']['address'])}</eudr:address>
        <eudr:email>{_xe(dds['supplier']['email'])}</eudr:email>
      </eudr:supplier>
      <eudr:declarations>
        <eudr:deforestationFree>{str(dds['declarations']['deforestationFree']).lower()}</eudr:deforestationFree>
        <eudr:legalCompliance>{str(dds['declarations']['legalCompliance']).lower()}</eudr:legalCompliance>
      </eudr:declarations>
      <eudr:signatory>
        <eudr:name>{_xe(dds['signatory']['name'])}</eudr:name>
        <eudr:role>{_xe(dds['signatory']['role'])}</eudr:role>
        <eudr:date>{_xe(dds['signatory']['date'])}</eudr:date>
      </eudr:signatory>
    </eudr:submitDds>
  </soap:Body>
</soap:Envelope>"""

    return envelope


# Match <referenceNumber> with optional XML namespace prefix.
_REF_RE = re.compile(r"<(?:[a-zA-Z][\w-]*:)?referenceNumber>([^<]+)</(?:[a-zA-Z][\w-]*:)?referenceNumber>")


class TracesNTService:
    """Submit DDS to the EU TRACES NT system."""

    def __init__(
        self,
        username: str | None = None,
        auth_key: str | None = None,
        env: str | None = None,
        client_id: str | None = None,
    ) -> None:
        settings = get_settings()
        self._username = username or settings.TRACES_NT_USERNAME
        self._auth_key = auth_key or settings.TRACES_NT_AUTH_KEY
        self._env = env or settings.TRACES_NT_ENV
        self._client_id = client_id or settings.TRACES_NT_CLIENT_ID
        self._base_url = TRACES_URLS.get(self._env, TRACES_URLS["acceptance"])

    @classmethod
    async def from_db(cls, db, tenant_id=None) -> "TracesNTService":
        """Build instance with per-tenant credentials loaded from DB."""
        from app.services.integration_service import IntegrationCredentialsService
        svc = IntegrationCredentialsService(db, tenant_id=tenant_id)
        creds = await svc.get_credentials("traces_nt")
        return cls(
            username=creds.get("username") or None,
            auth_key=creds.get("auth_key") or None,
            env=creds.get("env") or None,
            client_id=creds.get("client_id") or None,
        )

    @property
    def is_configured(self) -> bool:
        return bool(self._username and self._auth_key)

    async def submit_dds(self, dds: dict) -> dict[str, Any]:
        """Submit a DDS to TRACES NT.

        Returns submission result with reference number.
        """
        if not self.is_configured:
            return {
                "submitted": False,
                "error": "TRACES NT credentials not configured",
                "dds_payload": dds,
            }

        envelope = build_soap_envelope(dds, self._username, self._auth_key, self._client_id)
        timeout = get_settings().TRACES_NT_TIMEOUT

        try:
            async with httpx.AsyncClient(timeout=timeout) as http:
                resp = await http.post(
                    self._base_url,
                    content=envelope.encode("utf-8"),
                    headers={
                        "Content-Type": "text/xml; charset=utf-8",
                        "SOAPAction": "submitDds",
                    },
                )

                if resp.status_code == 200:
                    body = resp.text
                    match = _REF_RE.search(body)
                    ref_number = match.group(1) if match else None

                    log.info("traces_dds_submitted", reference=ref_number, env=self._env)

                    return {
                        "submitted": True,
                        "reference_number": ref_number,
                        "environment": self._env,
                        "submitted_at": datetime.now(tz=timezone.utc).isoformat(),
                    }
                else:
                    log.warning("traces_submit_failed", status=resp.status_code, body=resp.text[:500])
                    return {
                        "submitted": False,
                        "error": f"TRACES NT returned {resp.status_code}",
                        "response_body": resp.text[:500],
                    }

        except Exception as exc:
            log.error("traces_submit_error", exc=str(exc))
            return {"submitted": False, "error": str(exc)}

    def export_dds_json(self, dds: dict) -> str:
        return json.dumps(dds, indent=2, ensure_ascii=False, default=str)
