"""Unit tests for ComplianceValidator — no DB needed."""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from app.compliance.validator import ComplianceValidator


class _Obj(SimpleNamespace):
    """SimpleNamespace that returns None for missing attributes (like a DB row)."""
    def __getattr__(self, name):
        return None


def _make_framework(
    slug="eudr",
    requires_geolocation=True,
    target_markets=None,
    validation_rules=None,
):
    return _Obj(
        slug=slug,
        requires_geolocation=requires_geolocation,
        target_markets=target_markets or ["EU"],
        validation_rules=validation_rules or {
        "required_fields": [
            "hs_code", "commodity_type", "quantity_kg",
            "country_of_production", "supplier_name",
            "deforestation_free_declaration", "legal_compliance_declaration",
        ],
        "required_if_export_eu": ["operator_eori"],
        "min_plots": 1,
        "commodity_specific": {
            "madera": {"required_fields": ["scientific_name"]},
        },
    },
    )


def _make_record(**overrides):
    defaults = {
        "hs_code": "0901",
        "commodity_type": "cafe",
        "quantity_kg": 2500.0,
        "country_of_production": "CO",
        "supplier_name": "Coop Huila",
        "deforestation_free_declaration": True,
        "legal_compliance_declaration": True,
        "operator_eori": "EU12345",
        "scientific_name": None,
        "compliance_status": "incomplete",
    }
    defaults.update(overrides)
    return _Obj(**defaults)


class TestValidatorRequiredFields:
    def test_all_fields_present_returns_ready(self):
        v = ComplianceValidator()
        result = v.validate(
            record=_make_record(),
            framework=_make_framework(),
            plots_count=1,
        )
        assert result.valid is True
        assert result.compliance_status == "ready"
        assert result.missing_fields == []

    def test_missing_hs_code_returns_incomplete(self):
        v = ComplianceValidator()
        result = v.validate(
            record=_make_record(hs_code=None),
            framework=_make_framework(),
            plots_count=1,
        )
        assert result.valid is False
        assert result.compliance_status == "incomplete"
        assert "hs_code" in result.missing_fields

    def test_multiple_missing_fields(self):
        v = ComplianceValidator()
        result = v.validate(
            record=_make_record(hs_code=None, supplier_name=None),
            framework=_make_framework(),
            plots_count=1,
        )
        assert result.valid is False
        assert "hs_code" in result.missing_fields
        assert "supplier_name" in result.missing_fields


class TestValidatorExportConditional:
    def test_eu_export_requires_eori(self):
        v = ComplianceValidator()
        result = v.validate(
            record=_make_record(operator_eori=None),
            framework=_make_framework(),
            plots_count=1,
            export_destinations=["EU"],
        )
        assert result.valid is False
        assert "operator_eori" in result.missing_fields

    def test_no_export_destination_skips_eori(self):
        v = ComplianceValidator()
        result = v.validate(
            record=_make_record(operator_eori=None),
            framework=_make_framework(),
            plots_count=1,
            export_destinations=None,
        )
        assert result.valid is True
        assert "operator_eori" not in result.missing_fields

    def test_non_matching_export_skips_eori(self):
        v = ComplianceValidator()
        result = v.validate(
            record=_make_record(operator_eori=None),
            framework=_make_framework(),
            plots_count=1,
            export_destinations=["US"],
        )
        assert result.valid is True
        assert "operator_eori" not in result.missing_fields


class TestValidatorPlots:
    def test_missing_plots_returns_incomplete(self):
        v = ComplianceValidator()
        result = v.validate(
            record=_make_record(),
            framework=_make_framework(requires_geolocation=True),
            plots_count=0,
        )
        assert result.valid is False
        assert result.missing_plots is True
        assert len(result.warnings) > 0

    def test_sufficient_plots_passes(self):
        v = ComplianceValidator()
        result = v.validate(
            record=_make_record(),
            framework=_make_framework(requires_geolocation=True),
            plots_count=3,
        )
        assert result.missing_plots is False

    def test_no_geolocation_requirement_ignores_plots(self):
        v = ComplianceValidator()
        result = v.validate(
            record=_make_record(),
            framework=_make_framework(requires_geolocation=False),
            plots_count=0,
        )
        assert result.missing_plots is False


class TestValidatorCommoditySpecific:
    def test_madera_requires_scientific_name(self):
        v = ComplianceValidator()
        result = v.validate(
            record=_make_record(commodity_type="madera", scientific_name=None),
            framework=_make_framework(),
            plots_count=1,
        )
        assert "scientific_name" in result.missing_fields

    def test_madera_with_scientific_name_passes(self):
        v = ComplianceValidator()
        result = v.validate(
            record=_make_record(commodity_type="madera", scientific_name="Swietenia macrophylla"),
            framework=_make_framework(),
            plots_count=1,
        )
        assert "scientific_name" not in result.missing_fields

    def test_cafe_does_not_require_scientific_name(self):
        v = ComplianceValidator()
        result = v.validate(
            record=_make_record(commodity_type="cafe", scientific_name=None),
            framework=_make_framework(),
            plots_count=1,
        )
        assert "scientific_name" not in result.missing_fields


class TestValidatorStatusPreservation:
    def test_declared_status_preserved(self):
        v = ComplianceValidator()
        result = v.validate(
            record=_make_record(compliance_status="declared", hs_code=None),
            framework=_make_framework(),
            plots_count=1,
        )
        assert result.compliance_status == "declared"
        assert result.valid is False  # still invalid, but status preserved

    def test_compliant_status_preserved(self):
        v = ComplianceValidator()
        result = v.validate(
            record=_make_record(compliance_status="compliant"),
            framework=_make_framework(),
            plots_count=1,
        )
        assert result.compliance_status == "compliant"

    def test_non_compliant_preserved(self):
        v = ComplianceValidator()
        result = v.validate(
            record=_make_record(compliance_status="non_compliant"),
            framework=_make_framework(),
            plots_count=1,
        )
        assert result.compliance_status == "non_compliant"


class TestValidatorEmptyRules:
    def test_empty_rules_always_ready(self):
        v = ComplianceValidator()
        result = v.validate(
            record=_make_record(),
            framework=_make_framework(
                validation_rules={},
                requires_geolocation=False,
            ),
            plots_count=0,
        )
        assert result.valid is True
        assert result.compliance_status == "ready"
