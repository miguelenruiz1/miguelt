"""Unit tests for TRACES NT SOAP envelope + retrieve response parsing.

These tests cover the pure functions (envelope builders, payload builder,
response parser) — no DB, no network. End-to-end verification against the
real TRACES NT acceptance environment requires production-grade credentials
and is out of scope here.
"""
from __future__ import annotations

import base64
import re
from datetime import date
from pathlib import Path

import pytest

from app.services.traces_service import (
    build_dds_payload,
    build_retrieve_envelope,
    build_soap_envelope,
    parse_retrieve_response,
)


# ─── Fixtures ────────────────────────────────────────────────────────────────

def _minimal_record(**overrides):
    base = {
        "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "framework_slug": "eudr",
        "hs_code": "0901",
        "commodity_type": "coffee",
        "product_description": "Green coffee beans",
        "scientific_name": "Coffea arabica L.",
        "quantity_kg": 12500,
        "country_of_production": "CO",
        "production_period_start": "2026-01-01",
        "production_period_end": "2026-02-28",
        "supplier_name": "Coop Los Andes",
        "supplier_address": "Huila, CO",
        "supplier_email": "ops@coop.example",
        "buyer_name": "Barry Callebaut EU",
        "buyer_address": "Lebbeke, BE",
        "buyer_email": "eudr@bc.example",
        "operator_eori": "BE1234567890",
        "activity_type": "export",
        "deforestation_free_declaration": True,
        "legal_compliance_declaration": True,
        "signatory_name": "Jane Compliance",
        "signatory_role": "Head of Sustainability",
        "signatory_date": "2026-03-10",
    }
    base.update(overrides)
    return base


def _plot(code: str, lat: float, lng: float, **extra):
    base = {
        "plot_code": code,
        "lat": lat,
        "lng": lng,
        "country_code": "CO",
        "producer_name": "Finca " + code,
        "plot_area_ha": 2.5,
        "geojson_data": {
            "type": "Polygon",
            "coordinates": [[
                [lng, lat],
                [lng + 0.001, lat],
                [lng + 0.001, lat + 0.001],
                [lng, lat + 0.001],
                [lng, lat],
            ]],
        },
    }
    base.update(extra)
    return base


# ─── 1) SOAP envelope structure ──────────────────────────────────────────────

def test_build_soap_envelope_structure():
    """WS-Security header must contain Nonce (base64), Created (ISO-Z), and
    PasswordDigest computed with SHA1(nonce + created + authkey)."""
    rec = _minimal_record()
    plots = [_plot("P001", 4.5, -75.5)]
    dds = build_dds_payload(rec, plots)

    xml = build_soap_envelope(
        dds, username="tenant1", auth_key="supersecret", client_id="eudr-test"
    )

    # Top-level envelope
    assert xml.startswith("<?xml version=\"1.0\" encoding=\"UTF-8\"?>")
    assert "<soap:Envelope" in xml
    assert "<eudr:submitDds>" in xml and "</eudr:submitDds>" in xml

    # WS-Security block
    assert "<wsse:Security" in xml
    assert "<wsse:UsernameToken>" in xml
    assert "<wsse:Username>tenant1</wsse:Username>" in xml

    # PasswordDigest type
    assert "#PasswordDigest" in xml

    # Nonce is valid base64 (16 raw bytes → 24 chars b64).
    m = re.search(r"<wsse:Nonce[^>]*>([^<]+)</wsse:Nonce>", xml)
    assert m, "Nonce missing"
    nonce = m.group(1)
    assert len(nonce) >= 20
    # Decodes cleanly
    base64.b64decode(nonce)

    # Created is ISO-8601 UTC with millisecond ".000Z" suffix
    m = re.search(
        r"<wsu:Created>(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.000Z)</wsu:Created>",
        xml,
    )
    assert m, "Created timestamp missing/malformed"

    # webServiceClientId propagated
    assert "<eudr:webServiceClientId>eudr-test</eudr:webServiceClientId>" in xml

    # Commodity + country of activity rendered
    assert "<eudr:hsHeading>0901</eudr:hsHeading>" in xml
    assert "<eudr:countryOfActivity>CO</eudr:countryOfActivity>" in xml


# ─── 2) DDS payload with full plots ──────────────────────────────────────────

def test_build_dds_payload_full_plots():
    """Record + 3 plots → payload has expected structural keys and
    FeatureCollection embedded in geometryGeojson."""
    rec = _minimal_record()
    plots = [
        _plot("P001", 4.500000, -75.500000),
        _plot("P002", 4.501000, -75.501000),
        _plot("P003", 4.502000, -75.502000),
    ]
    dds = build_dds_payload(rec, plots)

    for key in (
        "internalReferenceNumber",
        "activityType",
        "operatorType",
        "countryOfActivity",
        "operator",
        "commodities",
        "geometryGeojson",
        "productionPeriod",
        "supplier",
        "declarations",
        "signatory",
    ):
        assert key in dds, f"Missing top-level key {key!r}"

    assert dds["activityType"] == "EXPORT"
    assert dds["countryOfActivity"] == "CO"
    assert dds["operator"]["name"] == "Barry Callebaut EU"
    assert dds["operator"]["eoriNumber"] == "BE1234567890"

    assert len(dds["commodities"]) == 1
    commodity = dds["commodities"][0]
    assert commodity["hsHeading"] == "0901"
    assert commodity["scientificName"] == "Coffea arabica L."
    assert commodity["quantity"]["netMass"] == 12500
    assert commodity["quantity"]["unit"] == "KGM"
    assert len(commodity["producers"]) == 3

    # geometryGeojson is base64(FeatureCollection with 3 features)
    decoded = base64.b64decode(dds["geometryGeojson"]).decode("utf-8")
    assert '"type":"FeatureCollection"' in decoded
    assert decoded.count('"Feature"') >= 3
    # 6-decimal padding enforced
    assert re.search(r"-75\.\d{6,}", decoded)


# ─── 3) retrieve response parsing ────────────────────────────────────────────

def test_retrieve_dds_info_parsing_validated():
    xml = """<?xml version="1.0"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <eudr:retrieveDdsInfoByReferencesResponse xmlns:eudr="http://ec.europa.eu/tracesnt/eudr">
      <eudr:dds>
        <eudr:referenceNumber>25EUDR00123ABC</eudr:referenceNumber>
        <eudr:status>AVAILABLE</eudr:status>
        <eudr:validatedAt>2026-04-10T12:34:56Z</eudr:validatedAt>
      </eudr:dds>
    </eudr:retrieveDdsInfoByReferencesResponse>
  </soap:Body>
</soap:Envelope>"""
    parsed = parse_retrieve_response(xml, "25EUDR00123ABC")
    assert parsed["status"] == "validated"
    assert parsed["raw_status"] == "AVAILABLE"
    assert parsed["validated_at"] == "2026-04-10T12:34:56Z"
    assert parsed["rejection_reason"] is None
    assert parsed["reference_number"] == "25EUDR00123ABC"


def test_retrieve_dds_info_parsing_rejected():
    xml = """<?xml version="1.0"?>
<Envelope><Body>
  <retrieveDdsInfoByReferencesResponse>
    <dds>
      <referenceNumber>25EUDR00999XYZ</referenceNumber>
      <status>REJECTED</status>
      <rejectionReason>GeoJSON fuera del pais declarado</rejectionReason>
    </dds>
  </retrieveDdsInfoByReferencesResponse>
</Body></Envelope>"""
    parsed = parse_retrieve_response(xml, "25EUDR00999XYZ")
    assert parsed["status"] == "rejected"
    assert parsed["raw_status"] == "REJECTED"
    assert parsed["rejection_reason"] == "GeoJSON fuera del pais declarado"


def test_retrieve_dds_info_parsing_unknown_without_ref():
    """Response without status AND without the reference -> 'unknown'."""
    xml = "<Envelope><Body><empty/></Body></Envelope>"
    parsed = parse_retrieve_response(xml, "NOTFOUND-REF")
    assert parsed["status"] == "unknown"


def test_retrieve_dds_info_parsing_submitted_fallback():
    """Response carries only the reference (no status tag) -> assume
    'submitted' (still in EU validation queue)."""
    xml = "<Envelope><Body><ref>25EUDR00777MMM</ref></Body></Envelope>"
    parsed = parse_retrieve_response(xml, "25EUDR00777MMM")
    assert parsed["status"] == "submitted"


# ─── 4) retrieve envelope structure ──────────────────────────────────────────

def test_retrieve_envelope_structure():
    xml = build_retrieve_envelope(
        reference_number="25EUDR00123ABC",
        username="tenant1",
        auth_key="supersecret",
        client_id="eudr-test",
    )
    assert "<eudr:retrieveDdsInfoByReferences>" in xml
    assert "<eudr:referenceNumber>25EUDR00123ABC</eudr:referenceNumber>" in xml
    assert "<wsse:UsernameToken>" in xml
    assert "#PasswordDigest" in xml
    # Same WS-Security shape as submit — nonce base64 decodable.
    m = re.search(r"<wsse:Nonce[^>]*>([^<]+)</wsse:Nonce>", xml)
    assert m and base64.b64decode(m.group(1))


# ─── 5) Snapshot of envelope skeleton ────────────────────────────────────────

def test_soap_envelope_snapshot_stable_fields():
    """Detects accidental drift in the envelope scaffolding.

    We don't snapshot the full XML (timestamps/nonce change every call).
    Instead we assert that the skeleton contains every tag the TRACES NT
    XSD expects — if someone renames one, this test catches it.
    """
    rec = _minimal_record()
    plots = [_plot("P001", 4.5, -75.5)]
    dds = build_dds_payload(rec, plots)
    xml = build_soap_envelope(dds, "u", "k", client_id="eudr-test")

    expected_tags = [
        "<eudr:submitDds>",
        "<eudr:internalReferenceNumber>",
        "<eudr:operatorType>",
        "<eudr:activityType>",
        "<eudr:countryOfActivity>",
        "<eudr:operator>",
        "<eudr:commodity>",
        "<eudr:hsHeading>",
        "<eudr:hsCode>",
        "<eudr:netMass>",
        "<eudr:netMassUnit>",
        "<eudr:countryOfProduction>",
        "<eudr:producer>",
        "<eudr:geometryGeojson>",
        "<eudr:geoLocationConfidential>",
        "<eudr:productionPeriodStart>",
        "<eudr:productionPeriodEnd>",
        "<eudr:supplier>",
        "<eudr:declarations>",
        "<eudr:deforestationFree>",
        "<eudr:degradationFree>",
        "<eudr:legalCompliance>",
        "<eudr:signatory>",
    ]
    missing = [t for t in expected_tags if t not in xml]
    assert not missing, f"Missing tags in SOAP envelope: {missing}"
