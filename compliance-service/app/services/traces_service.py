"""TRACES NT integration — DDS submission to EU information system.

Implements the SOAP-based API for submitting Due Diligence Statements
to the European Commission's TRACES NT system (Regulation EU 2024/3084).

Production: https://webgate.ec.europa.eu/tracesnt/ws/EUDRSubmissionServiceV2
Acceptance: https://webgate.acceptance.ec.europa.eu/tracesnt-alpha/ws/EUDRSubmissionServiceV1
"""
from __future__ import annotations

import base64
import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.logging import get_logger
from app.core.settings import get_settings

log = get_logger(__name__)

# TRACES NT WSDL endpoints
TRACES_URLS = {
    "acceptance": "https://webgate.acceptance.ec.europa.eu/tracesnt-alpha/ws/EUDRSubmissionServiceV1",
    "production": "https://webgate.ec.europa.eu/tracesnt/ws/EUDRSubmissionServiceV2",
}

# EUDR commodity codes mapping
COMMODITY_HS_MAP = {
    "coffee": "0901",
    "cafe": "0901",
    "cocoa": "1801",
    "cacao": "1801",
    "palm_oil": "1511",
    "palma": "1511",
    "soy": "1201",
    "soja": "1201",
    "rubber": "4001",
    "caucho": "4001",
    "cattle": "0102",
    "ganado": "0102",
    "wood": "4403",
    "madera": "4403",
}


def build_dds_payload(
    record: dict,
    plots: list[dict],
    operator: dict | None = None,
) -> dict[str, Any]:
    """Build DDS payload matching TRACES NT schema.

    This can be used for:
    1. JSON export (for manual review/upload)
    2. SOAP submission (converted to XML envelope)

    Returns a structured dict that mirrors the TRACES NT DDS fields.
    """
    # Build GeoJSON FeatureCollection from plots
    features = []
    for plot in plots:
        lat = plot.get("lat")
        lng = plot.get("lng")
        if lat is not None and lng is not None:
            feature = {
                "type": "Feature",
                "properties": {
                    "plot_code": plot.get("plot_code"),
                    "area_ha": plot.get("plot_area_ha"),
                    "country": plot.get("country_code", "CO"),
                    "municipality": plot.get("municipality"),
                    "risk_level": plot.get("risk_level"),
                    "deforestation_free": plot.get("deforestation_free"),
                    "establishment_date": str(plot.get("establishment_date", "")),
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(lng), float(lat)],
                },
            }
            features.append(feature)

    geojson_collection = {
        "type": "FeatureCollection",
        "features": features,
    }

    # Base64 encode the GeoJSON (TRACES NT requirement)
    geojson_b64 = base64.b64encode(
        json.dumps(geojson_collection, ensure_ascii=False).encode("utf-8")
    ).decode("ascii")

    # Map activity type
    activity_map = {
        "export": "TRADE",
        "import": "IMPORT",
        "domestic_production": "DOMESTIC_PRODUCTION",
    }

    # Build DDS structure
    dds = {
        "internalReferenceNumber": record.get("id", str(uuid.uuid4())),
        "activityType": activity_map.get(record.get("activity_type", "export"), "TRADE"),
        "operatorType": "OPERATOR",
        "countryOfActivity": record.get("country_of_production", "CO"),

        # Operator identification (Annex II #1)
        "operator": {
            "name": record.get("buyer_name") or record.get("supplier_name", ""),
            "address": record.get("buyer_address") or record.get("supplier_address", ""),
            "email": record.get("buyer_email") or record.get("supplier_email", ""),
            "eoriNumber": record.get("operator_eori"),
        },

        # Commodities (Annex II #3-4)
        "commodities": [
            {
                "hsHeading": record.get("hs_code", "")[:4],  # TRACES uses 4-digit heading
                "hsCode": record.get("hs_code", ""),
                "description": record.get("product_description", ""),
                "scientificName": record.get("scientific_name"),
                "quantity": {
                    "netMass": float(record.get("quantity_kg", 0)),
                    "unit": "KGM",
                },
                "countryOfProduction": record.get("country_of_production", "CO"),
            }
        ],

        # Geolocation (Annex II #6)
        "geometryGeojson": geojson_b64,
        "geoLocationConfidential": False,

        # Production period (Annex II #7)
        "productionPeriod": {
            "start": str(record.get("production_period_start", "")),
            "end": str(record.get("production_period_end", "")),
        },

        # Supply chain (Annex II #5, #8)
        "supplier": {
            "name": record.get("supplier_name", ""),
            "address": record.get("supplier_address", ""),
            "email": record.get("supplier_email", ""),
        },

        # Associated statements (Annex II #8)
        "associatedStatements": record.get("prior_dds_references") or [],

        # Declarations (Annex II #9)
        "declarations": {
            "deforestationFree": record.get("deforestation_free_declaration", False),
            "legalCompliance": record.get("legal_compliance_declaration", False),
        },

        # Signatory (Annex II #10)
        "signatory": {
            "name": record.get("signatory_name", ""),
            "role": record.get("signatory_role", ""),
            "date": str(record.get("signatory_date", "")),
        },

        # Metadata
        "tracelog_metadata": {
            "record_id": record.get("id"),
            "framework_slug": record.get("framework_slug"),
            "certificate_number": record.get("certificate_number"),
            "blockchain_verified": True,
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        },
    }

    return dds


def build_soap_envelope(dds: dict, username: str, auth_key: str) -> str:
    """Build SOAP XML envelope for TRACES NT submission.

    Implements WS-Security UsernameToken authentication.
    """
    import secrets
    from datetime import datetime, timezone

    now = datetime.now(tz=timezone.utc)
    nonce_raw = secrets.token_bytes(16)
    nonce_b64 = base64.b64encode(nonce_raw).decode()
    created = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    # SHA-1 password digest: Base64(SHA1(nonce + created + password))
    digest_input = nonce_raw + created.encode() + auth_key.encode()
    password_digest = base64.b64encode(hashlib.sha1(digest_input).digest()).decode()

    # Build commodity XML
    commodity = dds["commodities"][0]
    commodity_xml = f"""
        <commodity>
            <hsHeading>{commodity['hsHeading']}</hsHeading>
            <hsCode>{commodity['hsCode']}</hsCode>
            <description>{commodity['description']}</description>
            {f"<scientificName>{commodity['scientificName']}</scientificName>" if commodity.get('scientificName') else ""}
            <netMass>{commodity['quantity']['netMass']}</netMass>
            <netMassUnit>KGM</netMassUnit>
            <countryOfProduction>{commodity['countryOfProduction']}</countryOfProduction>
        </commodity>"""

    envelope = f"""<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
               xmlns:eudr="http://ec.europa.eu/tracesnt/eudr">
  <soap:Header>
    <wsse:Security xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd"
                   xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
      <wsse:UsernameToken>
        <wsse:Username>{username}</wsse:Username>
        <wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordDigest">{password_digest}</wsse:Password>
        <wsse:Nonce EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary">{nonce_b64}</wsse:Nonce>
        <wsu:Created>{created}</wsu:Created>
      </wsse:UsernameToken>
      <eudr:webServiceClientId>eudr-test</eudr:webServiceClientId>
    </wsse:Security>
  </soap:Header>
  <soap:Body>
    <eudr:submitDds>
      <eudr:internalReferenceNumber>{dds['internalReferenceNumber']}</eudr:internalReferenceNumber>
      <eudr:operatorType>{dds['operatorType']}</eudr:operatorType>
      <eudr:activityType>{dds['activityType']}</eudr:activityType>
      <eudr:countryOfActivity>{dds['countryOfActivity']}</eudr:countryOfActivity>
      <eudr:operator>
        <eudr:name>{dds['operator']['name']}</eudr:name>
        <eudr:address>{dds['operator']['address']}</eudr:address>
        <eudr:email>{dds['operator']['email']}</eudr:email>
        {f"<eudr:eoriNumber>{dds['operator']['eoriNumber']}</eudr:eoriNumber>" if dds['operator'].get('eoriNumber') else ""}
      </eudr:operator>
      {commodity_xml}
      <eudr:geometryGeojson>{dds['geometryGeojson']}</eudr:geometryGeojson>
      <eudr:geoLocationConfidential>{str(dds['geoLocationConfidential']).lower()}</eudr:geoLocationConfidential>
      <eudr:productionPeriodStart>{dds['productionPeriod']['start']}</eudr:productionPeriodStart>
      <eudr:productionPeriodEnd>{dds['productionPeriod']['end']}</eudr:productionPeriodEnd>
    </eudr:submitDds>
  </soap:Body>
</soap:Envelope>"""

    return envelope


class TracesNTService:
    """Submit DDS to the EU TRACES NT system."""

    def __init__(self, username: str | None = None, auth_key: str | None = None, env: str | None = None) -> None:
        settings = get_settings()
        self._username = username or settings.TRACES_NT_USERNAME
        self._auth_key = auth_key or settings.TRACES_NT_AUTH_KEY
        self._env = env or settings.TRACES_NT_ENV
        self._base_url = TRACES_URLS.get(self._env, TRACES_URLS["acceptance"])

    @classmethod
    async def from_db(cls, db) -> "TracesNTService":
        """Build instance with credentials loaded from DB."""
        from app.services.integration_service import IntegrationCredentialsService
        svc = IntegrationCredentialsService(db)
        creds = await svc.get_credentials("traces_nt")
        return cls(
            username=creds.get("username") or None,
            auth_key=creds.get("auth_key") or None,
            env=creds.get("env") or None,
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
                "error": "TRACES NT credentials not configured (TRACES_NT_USERNAME / TRACES_NT_AUTH_KEY)",
                "dds_payload": dds,  # Return payload for manual submission
            }

        envelope = build_soap_envelope(dds, self._username, self._auth_key)

        try:
            async with httpx.AsyncClient(timeout=30.0) as http:
                resp = await http.post(
                    self._base_url,
                    content=envelope.encode("utf-8"),
                    headers={
                        "Content-Type": "text/xml; charset=utf-8",
                        "SOAPAction": "submitDds",
                    },
                )

                if resp.status_code == 200:
                    # Parse SOAP response for reference number
                    body = resp.text
                    ref_start = body.find("<referenceNumber>")
                    ref_end = body.find("</referenceNumber>")
                    ref_number = body[ref_start + 17:ref_end] if ref_start > 0 else None

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
            return {
                "submitted": False,
                "error": str(exc),
            }

    def export_dds_json(self, dds: dict) -> str:
        """Export DDS as JSON for manual review or upload."""
        return json.dumps(dds, indent=2, ensure_ascii=False, default=str)
