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

# Commodity-specific HS heading sets (Anexo I EU 2023/1115).
COFFEE_HS_HEADINGS = {"0901"}
CACAO_HS_HEADINGS = {"1801", "1802", "1803", "1804", "1805", "1806"}
# Palma: aceite crudo + refinado + derivados (RBD, PKO, biofuels, oleoquimica).
PALM_HS_HEADINGS = {"1207", "1511", "1513", "1517", "2306", "3823", "3826"}

# HS heading prefixes for which TRACES NT requires scientificName populated
# (EUDR Art. 9(1)(a)). Lista basada en Anexo I del Reglamento (UE) 2023/1115.
EUDR_CORE_HS_HEADINGS = (
    COFFEE_HS_HEADINGS | CACAO_HS_HEADINGS | PALM_HS_HEADINGS | {
        "0102",  # cattle / ganado
        "1201",  # soy / soja
        "4001", "4011", "4012", "4013",  # rubber
        "4401", "4402", "4403", "4406", "4407", "4408", "4409",  # wood
        "4410", "4411", "4412", "4413", "4414", "4415", "4416",
        "4418", "4421",
        "4701", "4702", "4703", "4704", "4705",  # pulp
    }
)

# Nombres cientificos aceptados por commodity (Annex I EUDR + practica
# exportadora LATAM). Rechazamos sinonimos sueltos para evitar que el DDS
# quede con strings no parseables por TRACES NT.
ACCEPTED_SCIENTIFIC_NAMES = {
    "coffee": {
        "Coffea arabica L.",
        "Coffea canephora Pierre ex A.Froehner",
    },
    "cacao": {
        "Theobroma cacao L.",
    },
    "palm": {
        "Elaeis guineensis Jacq.",
    },
}


def _xe(value: Any) -> str:
    """Escape any value for safe inclusion in XML text content."""
    if value is None:
        return ""
    return xml_escape(str(value))


EUDR_DDS_DECIMALS = 6  # Art. 2(28): minimo 6 cifras decimales por coordenada


def _pad_coord_token(value: float | int) -> str:
    """Devuelve la representacion textual de *value* con minimo 6 decimales.

    Si el float tiene mas de 6 decimales significativos, los preservamos.
    """
    v = float(value)
    raw = repr(v)
    decimals = EUDR_DDS_DECIMALS
    if "." in raw and "e" not in raw and "E" not in raw:
        current = len(raw.split(".", 1)[1])
        if current > EUDR_DDS_DECIMALS:
            decimals = current
    return f"{v:.{decimals}f}"


def _serialize_geojson_padded(obj: Any) -> str:
    """Serializador JSON manual que pad-ea coordenadas a >=6 decimales.

    Necesario porque ``json.dumps`` invoca ``float.__repr__`` sobre la clase
    base ``float`` (bypasseando subclases) y por lo tanto pierde los ceros
    finales que exige el Art. 2(28) del EUDR.  Hacemos la serializacion a
    mano para garantizar el padding correcto.
    """
    if obj is None:
        return "null"
    if obj is True:
        return "true"
    if obj is False:
        return "false"
    if isinstance(obj, str):
        return json.dumps(obj, ensure_ascii=False)
    if isinstance(obj, int) and not isinstance(obj, bool):
        return str(obj)
    if isinstance(obj, float):
        return _pad_coord_token(obj)
    if isinstance(obj, list):
        return "[" + ",".join(_serialize_geojson_padded(x) for x in obj) + "]"
    if isinstance(obj, tuple):
        return "[" + ",".join(_serialize_geojson_padded(x) for x in obj) + "]"
    if isinstance(obj, dict):
        items = [
            f"{json.dumps(k, ensure_ascii=False)}:{_serialize_geojson_padded(v)}"
            for k, v in obj.items()
        ]
        return "{" + ",".join(items) + "}"
    # Fallback (Decimal, datetime, etc.)
    return json.dumps(obj, ensure_ascii=False, default=str)


def _pad_geometry_for_dds(geom: dict) -> dict:
    """Identidad: el padding ocurre durante la serializacion textual."""
    return geom


def _plot_geometry(plot: dict) -> dict:
    """Pick the best geometry for a plot: prefer real polygon over a Point.

    Always pads coordinates to >=6 decimal places per EUDR Art. 2(28).
    """
    geo = plot.get("geojson_data")
    if isinstance(geo, dict) and geo.get("type") in ("Polygon", "MultiPolygon"):
        return _pad_geometry_for_dds(geo)
    if isinstance(geo, dict) and geo.get("type") == "Feature" and isinstance(geo.get("geometry"), dict):
        return _pad_geometry_for_dds(geo["geometry"])
    if isinstance(geo, dict) and geo.get("type") == "FeatureCollection":
        feats = geo.get("features") or []
        if feats and isinstance(feats[0], dict) and isinstance(feats[0].get("geometry"), dict):
            return _pad_geometry_for_dds(feats[0]["geometry"])
    lat = plot.get("lat")
    lng = plot.get("lng")
    if lat is None or lng is None:
        return {}
    return _pad_geometry_for_dds(
        {"type": "Point", "coordinates": [float(lng), float(lat)]}
    )


ADDITIONAL_INFO_MAX_CHARS = 2000


def _build_additional_information(record: dict, plots: list[dict]) -> str | None:
    """Construye el bloque additionalInformation del DDS con tenencia y trazabilidad.

    Esta es la unica via para transmitir a TRACES NT la evidencia EUDR Art. 8.2.f
    (derechos de uso) ya que el schema oficial no tiene campos estructurados
    para owner/cadastral/tenure. La data se incluye como texto libre indexable.

    Limite ~2000 chars; si excede, truncamos y agregamos elipsis.
    """
    parts: list[str] = []

    # Trazabilidad cross-system
    meta_bits: list[str] = []
    if record.get("certificate_number"):
        meta_bits.append(f"Cert={record.get('certificate_number')}")
    if record.get("framework_slug"):
        meta_bits.append(f"Framework={record.get('framework_slug')}")
    if record.get("asset_id"):
        meta_bits.append(f"AssetID={record.get('asset_id')}")
    if meta_bits:
        parts.append("[Trazabilidad] " + ", ".join(meta_bits))

    # Cadmio (cacao): obligatorio lab test en exportaciones a UE (Reg 2023/915).
    if record.get("cadmium_mg_per_kg") is not None:
        cd_bits = [f"valor={record.get('cadmium_mg_per_kg')} mg/kg"]
        if record.get("cadmium_test_date"):
            cd_bits.append(f"fecha={record.get('cadmium_test_date')}")
        if record.get("cadmium_test_lab"):
            cd_bits.append(f"lab={record.get('cadmium_test_lab')}")
        if record.get("cadmium_eu_compliant") is not None:
            cd_bits.append(
                "EU-compliant" if record.get("cadmium_eu_compliant") else "NO-compliant"
            )
        parts.append("[Cadmio] " + ", ".join(cd_bits))

    # RSPO trace model (palma). TRACES NT no modela RSPO en el schema oficial;
    # el importador UE lo espera en additionalInformation para mass balance.
    if record.get("rspo_trace_model"):
        parts.append(f"[RSPO trace model] {record.get('rspo_trace_model')}")

    # Resumen agregado: tipos de tenencia distintos, cantidad indigenous, etc.
    tenure_types = sorted({
        str(p.get("tenure_type")) for p in plots if p and p.get("tenure_type")
    })
    if tenure_types:
        parts.append(f"[Tenencia tipos] {', '.join(tenure_types)}")

    indig_count = sum(1 for p in plots if p and p.get("indigenous_territory_flag"))
    if indig_count > 0:
        parts.append(
            f"[Territorio indigena/colectivo] {indig_count} parcela(s) — "
            "Art. 10 EUDR due diligence reforzado aplicable"
        )

    # Detalle por parcela (Art. 8.2.f evidence)
    for p in plots:
        if not p:
            continue
        plot_bits: list[str] = []
        code = p.get("plot_code") or "?"
        if p.get("producer_name"):
            ident = ""
            if p.get("producer_id_type") and p.get("producer_id_number"):
                ident = f" {p['producer_id_type']}:{p['producer_id_number']}"
            plot_bits.append(f"productor={p['producer_name']}{ident}")
        if p.get("owner_name") and p.get("owner_name") != p.get("producer_name"):
            ident = ""
            if p.get("owner_id_type") and p.get("owner_id_number"):
                ident = f" {p['owner_id_type']}:{p['owner_id_number']}"
            plot_bits.append(f"titular={p['owner_name']}{ident}")
        if p.get("cadastral_id"):
            plot_bits.append(f"catastro={p['cadastral_id']}")
        if p.get("land_title_number"):
            plot_bits.append(f"folio={p['land_title_number']}")
        if p.get("tenure_type"):
            tenure_bit = f"tenencia={p['tenure_type']}"
            if p.get("tenure_start_date") or p.get("tenure_end_date"):
                start = p.get("tenure_start_date") or ""
                end = p.get("tenure_end_date") or ""
                tenure_bit += f"({start}..{end})"
            plot_bits.append(tenure_bit)
        if plot_bits:
            parts.append(f"[Parcela {code}] " + ", ".join(plot_bits))

    if not parts:
        return None

    text = " | ".join(parts)
    if len(text) > ADDITIONAL_INFO_MAX_CHARS:
        text = text[: ADDITIONAL_INFO_MAX_CHARS - 3] + "..."
    return text


def _build_producer_block(plot: dict, record: dict) -> dict[str, Any]:
    """Construye el sub-objeto producer dentro del commodity para el DDS.

    Pone en orden de prioridad:
      - producer_name del plot (operador real que cultiva)
      - owner_name del plot (titular legal, si difiere)
      - supplier_name del record (cooperativa/exportador como fallback)
      - plot_code (ultimo recurso para que TRACES NT no rechace por nombre vacio)

    Incluye identificacion legal (NIT/cedula), pais, referencia catastral,
    tipo de tenencia y bandera de territorio indigena. Estos campos no son
    parte del schema EUDR DDS oficial pero se mandan dentro del bloque
    producer para preservar la trazabilidad legal cuando TRACES NT lo
    almacene.
    """
    producer_name = (
        (plot.get("producer_name") or "").strip()
        or (plot.get("owner_name") or "").strip()
        or (record.get("supplier_name") or "").strip()
        or (plot.get("plot_code") or "").strip()
        or "Productor sin nombre"
    )[:200]
    country = (
        plot.get("country_code") or record.get("country_of_production") or "CO"
    ).upper()[:2]
    block: dict[str, Any] = {
        "name": producer_name,
        "country": country,
        "geometryReference": plot.get("plot_code") or "",
    }
    # Identificacion del productor (cedula, NIT, RUT, etc.)
    if plot.get("producer_id_number"):
        block["nationalIdentifier"] = {
            "type": (plot.get("producer_id_type") or "ID").upper(),
            "value": str(plot.get("producer_id_number")),
        }
    # Owner separado solo si hay producer_name explicito Y owner_name distinto.
    # Si no hay producer_name pero si owner_name, ya lo usamos como producer
    # arriba — emitir legalOwner ademas seria redundante.
    explicit_producer = (plot.get("producer_name") or "").strip()
    explicit_owner = (plot.get("owner_name") or "").strip()
    if (
        explicit_producer
        and explicit_owner
        and explicit_owner != explicit_producer
    ):
        block["legalOwner"] = {
            "name": explicit_owner[:200],
            "identifierType": (plot.get("owner_id_type") or "ID").upper(),
            "identifier": str(plot.get("owner_id_number") or ""),
        }
    # Identificador catastral oficial (folio matricula SNR / catastro IGAC)
    if plot.get("cadastral_id"):
        block["cadastralReference"] = str(plot.get("cadastral_id"))
    # Tipo de tenencia + vigencia
    if plot.get("tenure_type"):
        tenure: dict[str, Any] = {"type": str(plot.get("tenure_type"))}
        if plot.get("tenure_start_date"):
            tenure["startDate"] = str(plot.get("tenure_start_date"))
        if plot.get("tenure_end_date"):
            tenure["endDate"] = str(plot.get("tenure_end_date"))
        block["landUseRight"] = tenure
    # Bandera de territorio indigena/colectivo (Art. 10 due diligence reforzado)
    if plot.get("indigenous_territory_flag"):
        block["indigenousTerritory"] = True
    return block


def build_dds_payload(
    record: dict,
    plots: list[dict],
    operator: dict | None = None,
) -> dict[str, Any]:
    """Build DDS payload matching TRACES NT schema.

    Returns a structured dict that mirrors the TRACES NT DDS fields. Uses real
    polygons when available (not just points) and tolerates None values.
    """
    # EUDR GeoJSON File Description v1.5 — Feature properties admitidas:
    #   ProducerName    (Optional, string)
    #   ProducerCountry (Optional pero recomendado, ISO 3166-1 alpha-2)
    #   ProductionPlace (Optional, string)
    #   Area            (Optional para Point; defaults a 4 ha si se omite)
    # No incluimos otras propiedades — TRACES NT puede ignorarlas o rechazarlas.

    # Producer name por defecto: el supplier del record. En EUDR el "producer"
    # es quien produce el commodity, semanticamente equivalente al supplier.
    # Si el caller agrega plot["producer_name"] explicito (p.ej. desde el
    # nombre de la organizacion), tiene precedencia.
    default_producer = (record.get("supplier_name") or "").strip()
    default_country = (record.get("country_of_production") or "CO").upper()

    features = []
    for plot in plots:
        geometry = _plot_geometry(plot)
        if not geometry:
            continue

        producer_name = (
            (plot.get("producer_name") or "").strip()
            or default_producer
            or (plot.get("plot_code") or "").strip()
            or "Productor sin nombre"
        )

        # ProducerCountry: ISO 3166-1 alpha-2 estricto. Si el campo no es
        # exactamente 2 caracteres, caemos al pais del record.
        plot_country = (plot.get("country_code") or "").strip().upper()
        if len(plot_country) != 2:
            plot_country = default_country if len(default_country) == 2 else "CO"

        properties: dict[str, Any] = {
            "ProducerName": producer_name,
            "ProducerCountry": plot_country,
        }
        municipality = plot.get("municipality")
        if municipality:
            properties["ProductionPlace"] = str(municipality)

        # Area solo se incluye para Point. El spec dice que para Point es
        # opcional y por defecto TRACES NT lo asume 4 ha si se omite — aqui lo
        # incluimos siempre que tengamos un valor positivo.
        if geometry.get("type") == "Point":
            area = plot.get("plot_area_ha")
            try:
                area_f = float(area) if area is not None else None
            except (TypeError, ValueError):
                area_f = None
            if area_f is not None and area_f > 0:
                properties["Area"] = area_f

        feature = {
            "type": "Feature",
            "properties": properties,
            "geometry": geometry,
        }
        features.append(feature)

    geojson_collection = {"type": "FeatureCollection", "features": features}
    # EUDR Art. 2(28): serializacion con padding manual a >=6 decimales para
    # preservar la precision exigida en cada coordenada.
    geojson_b64 = base64.b64encode(
        _serialize_geojson_padded(geojson_collection).encode("utf-8")
    ).decode("ascii")

    # TRACES NT activity types (verbatim del schema EUDR v1):
    #   IMPORT — entrada de productos al mercado de la UE
    #   DOMESTIC — produccion intra-UE puesta en el mercado
    #   EXPORT — exportacion fuera de la UE
    #   TRADE — operadores intermediarios (no productor primario)
    activity_map = {
        "export": "EXPORT",
        "import": "IMPORT",
        "domestic_production": "DOMESTIC",
        "domestic": "DOMESTIC",
        "trade": "TRADE",
    }
    operator_type = (record.get("operator_type") or "OPERATOR").upper()

    hs_code = (record.get("hs_code") or "").strip()
    hs_heading = hs_code[:4] if hs_code else ""

    # Reference documents — evidencia legal adjunta a las parcelas (titulos,
    # certificados, contratos, etc). EUDR Art. 9.4 exige conservar evidencia
    # de soporte; aqui la pasamos al DDS como reference_documentation entries.
    reference_documents: list[dict[str, Any]] = []
    seen_doc_ids: set[str] = set()
    for plot in plots:
        for doc in plot.get("documents") or []:
            doc_id = str(doc.get("id") or doc.get("media_file_id") or "")
            if doc_id and doc_id in seen_doc_ids:
                continue
            seen_doc_ids.add(doc_id)
            reference_documents.append({
                "documentType": (doc.get("document_type") or "EVIDENCE"),
                "referenceNumber": str(doc.get("id") or doc.get("media_file_id") or ""),
                "filename": doc.get("filename") or "",
                "fileHash": doc.get("file_hash") or "",
                "description": doc.get("description") or "",
                "uploadedAt": str(doc.get("uploaded_at") or ""),
                "plotCode": plot.get("plot_code") or "",
            })
    # Tambien incluimos documentos a nivel del record (certificados, contratos
    # de cumplimiento, declaraciones del proveedor, etc).
    for doc in record.get("documents") or []:
        doc_id = str(doc.get("id") or doc.get("media_file_id") or "")
        if doc_id and doc_id in seen_doc_ids:
            continue
        seen_doc_ids.add(doc_id)
        reference_documents.append({
            "documentType": (doc.get("document_type") or "EVIDENCE"),
            "referenceNumber": str(doc.get("id") or doc.get("media_file_id") or ""),
            "filename": doc.get("filename") or "",
            "fileHash": doc.get("file_hash") or "",
            "description": doc.get("description") or "",
            "uploadedAt": str(doc.get("uploaded_at") or ""),
            "plotCode": "",
        })

    # additionalInformation (Art. 9.1.k): campo libre EUDR. Aqui transmitimos
    # toda la evidencia de tenencia y derechos de uso (Art. 8.2.f) que el
    # schema oficial NO modela como campos estructurados. TRACES NT acepta
    # texto libre — los auditores europeos pueden leer este bloque en el
    # detalle del DDS.
    #
    # Hard-cap: 2000 chars (limite practico observado en TRACES NT).
    additional_information = _build_additional_information(record, plots)

    # geoLocationConfidential — Art. 9.6 EUDR: el operador puede marcar la
    # geolocalizacion como confidencial frente a terceros. Si el record lo
    # solicita explicitamente, propagamos la flag.
    geo_confidential = bool(record.get("geo_location_confidential", False))

    dds = {
        "internalReferenceNumber": record.get("id") or str(uuid.uuid4()),
        "activityType": activity_map.get(
            (record.get("activity_type") or "export").lower(), "EXPORT",
        ),
        "operatorType": operator_type,
        "countryOfActivity": (record.get("country_of_production") or "CO").upper()[:2],

        "operator": {
            "name": record.get("buyer_name") or record.get("supplier_name") or "",
            "address": record.get("buyer_address") or record.get("supplier_address") or "",
            # Email is PII and carries semantic meaning — do NOT fall back to
            # supplier_email if buyer_email is missing. Leaving this empty is
            # preferable to contaminating the operator block with the
            # supplier's contact details.
            "email": record.get("buyer_email") or "",
            "eoriNumber": record.get("operator_eori"),
            "country": (record.get("operator_country") or record.get("country_of_production") or "CO").upper()[:2],
        },

        "commodities": [
            {
                "hsHeading": hs_heading,
                "hsCode": hs_code,
                "description": record.get("product_description") or "",
                "scientificName": record.get("scientific_name"),
                "commonName": record.get("common_name") or record.get("commodity_type"),
                "quantity": {
                    "netMass": float(record.get("quantity_kg") or 0),
                    "supplementaryUnit": record.get("supplementary_unit"),
                    "supplementaryUnitQualifier": record.get("supplementary_unit_qualifier"),
                    "unit": "KGM",
                },
                "countryOfProduction": (record.get("country_of_production") or "CO").upper()[:2],
                "producers": [
                    _build_producer_block(p, record)
                    for p in plots if p
                ],
            }
        ],

        "geometryGeojson": geojson_b64,
        "geoLocationConfidential": geo_confidential,

        "productionPeriod": {
            "start": str(record.get("production_period_start") or ""),
            "end": str(record.get("production_period_end") or ""),
        },

        "supplier": {
            "name": record.get("supplier_name") or "",
            "address": record.get("supplier_address") or "",
            "email": record.get("supplier_email") or "",
            "country": (record.get("supplier_country") or record.get("country_of_production") or "CO").upper()[:2],
        },

        "associatedStatements": record.get("prior_dds_references") or [],
        "referenceDocumentation": reference_documents,
        "additionalInformation": additional_information,

        # EUDR Art. 3 distingue dos atributos no equivalentes:
        #   deforestationFree (Art. 3.a) — sin deforestacion post 2020-12-31
        #   degradationFree   (Art. 2.7) — sin degradacion forestal post 2020-12-31
        # TRACES NT acepta ambos en declarations; el segundo es OBLIGATORIO
        # para productos de madera/celulosa y altamente recomendado para todo.
        "declarations": {
            "deforestationFree": record.get("deforestation_free_declaration", False),
            "degradationFree": record.get("degradation_free_declaration", False),
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
            "plot_count": len(plots),
            "document_count": len(reference_documents),
            # Campos propietarios — no se serializan a TRACES NT pero
            # alimentan _validate_dds_for_submission (cadmio / RSPO / commodity).
            "commodity_type": record.get("commodity_type"),
            "cadmium_eu_compliant": record.get("cadmium_eu_compliant"),
            "rspo_trace_model": record.get("rspo_trace_model"),
        },
    }

    return dds


def _validate_dds_for_submission(dds: dict) -> None:
    """Pre-flight checks before SOAP build.

    Raises HTTPException 422 if mandatory EUDR fields are missing. Centralizing
    this here means each TRACES caller (sync, async, retry worker) gets the
    same validation without duplicating logic.
    """
    from fastapi import HTTPException

    declarations = dds.get("declarations") or {}
    for flag in ("deforestationFree", "degradationFree"):
        val = declarations.get(flag)
        if not isinstance(val, bool):
            raise HTTPException(
                status_code=422,
                detail=(
                    f"declarations.{flag} es obligatorio (bool) antes de "
                    "enviar a TRACES NT (EUDR Art. 3.a / 2.7)."
                ),
            )

    meta = dds.get("tracelog_metadata") or {}
    commodity_type = (meta.get("commodity_type") or "").lower() or None

    for commodity in dds.get("commodities") or []:
        hs_heading = (commodity.get("hsHeading") or "").strip()
        if hs_heading in EUDR_CORE_HS_HEADINGS and not commodity.get("scientificName"):
            raise HTTPException(
                status_code=422,
                detail=(
                    f"commodities[].scientificName es obligatorio para HS "
                    f"heading {hs_heading} (EUDR Art. 9(1)(a))."
                ),
            )

        # Cacao: cadmio lab test obligatorio y debe estar en compliance-range.
        is_cacao = commodity_type == "cacao" or hs_heading.startswith("18")
        if is_cacao:
            if meta.get("cadmium_eu_compliant") is not True:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "Cadmio no validado o supera 0.6 mg/kg (EU 2023/915). "
                        "Registrar lab test en /records/{id}/cadmium-test antes "
                        "de someter el DDS."
                    ),
                )

        # Palma: RSPO chain-of-custody model requerido.
        is_palm = commodity_type == "palm" or hs_heading[:2] in {"15", "38"}
        if is_palm and not meta.get("rspo_trace_model"):
            raise HTTPException(
                status_code=422,
                detail=(
                    "RSPO trace_model requerido para palma "
                    "(mass_balance|segregated|identity_preserved)."
                ),
            )

        # Scientific name debe coincidir con la lista aceptada por commodity.
        sci = (commodity.get("scientificName") or "").strip()
        if sci and commodity_type in ACCEPTED_SCIENTIFIC_NAMES:
            if sci not in ACCEPTED_SCIENTIFIC_NAMES[commodity_type]:
                accepted = ", ".join(sorted(ACCEPTED_SCIENTIFIC_NAMES[commodity_type]))
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"scientificName '{sci}' no aceptado para commodity "
                        f"'{commodity_type}'. Valores permitidos: {accepted}."
                    ),
                )


def build_soap_envelope(
    dds: dict,
    username: str,
    auth_key: str,
    client_id: str = "eudr-test",
) -> str:
    """Build SOAP XML envelope for TRACES NT submission with WS-Security."""
    _validate_dds_for_submission(dds)
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
    common_name_xml = (
        f"<eudr:commonName>{_xe(commodity.get('commonName'))}</eudr:commonName>"
        if commodity.get("commonName")
        else ""
    )
    eori_xml = (
        f"<eudr:eoriNumber>{_xe(dds['operator']['eoriNumber'])}</eudr:eoriNumber>"
        if dds["operator"].get("eoriNumber")
        else ""
    )

    # Producers nested per commodity. IMPORTANTE: el schema TRACES NT (verificado
    # contra eudr-api.eu, mfrntic/eudr-api-client y la spec ATIBT) acepta SOLO
    # name y country dentro de <eudr:producer>. Cualquier sub-elemento extra
    # (nationalIdentifier, legalOwner, cadastralReference, landUseRight,
    # indigenousTerritory, geometryReference) es ignorado o causa fault del
    # validador XSD. La data de tenencia/cadastro/owner se transmite al EU via
    # additionalInformation (campo libre, ver build_dds_payload).
    producers_xml_parts = []
    for p in commodity.get("producers") or []:
        producers_xml_parts.append(
            "<eudr:producer>"
            f"<eudr:name>{_xe(p.get('name'))}</eudr:name>"
            f"<eudr:country>{_xe(p.get('country'))}</eudr:country>"
            "</eudr:producer>"
        )
    producers_xml = "".join(producers_xml_parts)

    # Reference documentation (Art. 9.4 evidence)
    ref_docs_xml_parts = []
    for d in dds.get("referenceDocumentation") or []:
        ref_docs_xml_parts.append(
            "<eudr:referenceDocument>"
            f"<eudr:documentType>{_xe(d.get('documentType'))}</eudr:documentType>"
            f"<eudr:referenceNumber>{_xe(d.get('referenceNumber'))}</eudr:referenceNumber>"
            f"<eudr:filename>{_xe(d.get('filename'))}</eudr:filename>"
            f"<eudr:fileHash>{_xe(d.get('fileHash'))}</eudr:fileHash>"
            f"<eudr:description>{_xe(d.get('description'))}</eudr:description>"
            f"<eudr:uploadedAt>{_xe(d.get('uploadedAt'))}</eudr:uploadedAt>"
            + (f"<eudr:plotCode>{_xe(d.get('plotCode'))}</eudr:plotCode>" if d.get("plotCode") else "")
            + "</eudr:referenceDocument>"
        )
    ref_docs_xml = (
        f"<eudr:referenceDocumentation>{''.join(ref_docs_xml_parts)}</eudr:referenceDocumentation>"
        if ref_docs_xml_parts
        else ""
    )

    # Associated DDS statements (downstream/upstream chain refs)
    assoc_xml_parts = []
    for ref in dds.get("associatedStatements") or []:
        if isinstance(ref, dict):
            assoc_xml_parts.append(
                "<eudr:associatedStatement>"
                f"<eudr:referenceNumber>{_xe(ref.get('referenceNumber') or ref.get('reference'))}</eudr:referenceNumber>"
                f"<eudr:verificationNumber>{_xe(ref.get('verificationNumber') or '')}</eudr:verificationNumber>"
                "</eudr:associatedStatement>"
            )
        else:
            assoc_xml_parts.append(
                f"<eudr:associatedStatement><eudr:referenceNumber>{_xe(ref)}</eudr:referenceNumber></eudr:associatedStatement>"
            )
    assoc_xml = (
        f"<eudr:associatedStatements>{''.join(assoc_xml_parts)}</eudr:associatedStatements>"
        if assoc_xml_parts
        else ""
    )

    additional_info_xml = (
        f"<eudr:additionalInformation>{_xe(dds.get('additionalInformation'))}</eudr:additionalInformation>"
        if dds.get("additionalInformation")
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
        <eudr:country>{_xe(dds['operator'].get('country', 'CO'))}</eudr:country>
        {eori_xml}
      </eudr:operator>
      <eudr:commodity>
        <eudr:hsHeading>{_xe(commodity['hsHeading'])}</eudr:hsHeading>
        <eudr:hsCode>{_xe(commodity['hsCode'])}</eudr:hsCode>
        <eudr:description>{_xe(commodity['description'])}</eudr:description>
        {sci_name_xml}
        {common_name_xml}
        <eudr:netMass>{_xe(commodity['quantity']['netMass'])}</eudr:netMass>
        <eudr:netMassUnit>KGM</eudr:netMassUnit>
        <eudr:countryOfProduction>{_xe(commodity['countryOfProduction'])}</eudr:countryOfProduction>
        {producers_xml}
      </eudr:commodity>
      <eudr:geometryGeojson>{_xe(dds['geometryGeojson'])}</eudr:geometryGeojson>
      <eudr:geoLocationConfidential>{str(dds['geoLocationConfidential']).lower()}</eudr:geoLocationConfidential>
      <eudr:productionPeriodStart>{_xe(dds['productionPeriod']['start'])}</eudr:productionPeriodStart>
      <eudr:productionPeriodEnd>{_xe(dds['productionPeriod']['end'])}</eudr:productionPeriodEnd>
      <eudr:supplier>
        <eudr:name>{_xe(dds['supplier']['name'])}</eudr:name>
        <eudr:address>{_xe(dds['supplier']['address'])}</eudr:address>
        <eudr:email>{_xe(dds['supplier']['email'])}</eudr:email>
        <eudr:country>{_xe(dds['supplier'].get('country', 'CO'))}</eudr:country>
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
      {assoc_xml}
      {ref_docs_xml}
      {additional_info_xml}
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
