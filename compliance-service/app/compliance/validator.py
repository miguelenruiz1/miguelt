"""Generic compliance validator — reads rules from framework.validation_rules JSONB."""
from __future__ import annotations

from datetime import datetime, timezone

from app.models.framework import ComplianceFramework
from app.models.record import ComplianceRecord
from app.schemas.validation import ValidationResult


class ComplianceValidator:
    """Validate a ComplianceRecord against its framework's validation_rules.

    The validator is fully data-driven: no framework-specific logic is hardcoded.
    All required fields, export-conditional fields, commodity-specific fields,
    and plot requirements are read from ``framework.validation_rules`` JSONB.

    Expected ``validation_rules`` structure::

        {
            "required_fields": ["commodity_type", "hs_code", ...],
            "required_if_export_eu": ["operator_eori", ...],
            "min_plots": 1,
            "commodity_specific": {
                "coffee": {
                    "required_fields": ["scientific_name", ...]
                }
            }
        }
    """

    def validate(
        self,
        record: ComplianceRecord,
        framework: ComplianceFramework,
        plots_count: int,
        export_destinations: list[str] | None = None,
        plots: list | None = None,
    ) -> ValidationResult:
        rules: dict = framework.validation_rules or {}
        missing_fields: list[str] = []
        warnings: list[str] = []
        missing_plots = False

        # ------------------------------------------------------------------
        # 1. Base required fields
        # ------------------------------------------------------------------
        required_fields: list[str] = rules.get("required_fields", [])
        for field in required_fields:
            value = getattr(record, field, None)
            if value is None:
                missing_fields.append(field)

        # ------------------------------------------------------------------
        # 2. Export-conditional fields (e.g. required_if_export_eu)
        # ------------------------------------------------------------------
        if export_destinations:
            target_markets = set(framework.target_markets or [])
            export_set = set(export_destinations)
            if target_markets & export_set:
                export_fields: list[str] = rules.get("required_if_export_eu", [])
                for field in export_fields:
                    value = getattr(record, field, None)
                    if value is None:
                        missing_fields.append(field)

        # ------------------------------------------------------------------
        # 3. Geolocation / plots requirement
        # ------------------------------------------------------------------
        if framework.requires_geolocation:
            min_plots: int = rules.get("min_plots", 1)
            if plots_count < min_plots:
                missing_plots = True
                warnings.append(
                    f"At least {min_plots} plot(s) required; found {plots_count}"
                )

            # CRITICAL EUDR: every linked plot must be deforestation_free AND
            # cutoff_date_compliant. Previously only the count was checked, so
            # a record could be marked "ready" with a non-compliant plot, and
            # a falsified DDS could be exported to TRACES NT.
            if plots:
                for plot in plots:
                    pcode = getattr(plot, "plot_code", "?")
                    if not getattr(plot, "deforestation_free", False):
                        missing_fields.append(
                            f"plot {pcode}: deforestation_free=False (run GFW screening)"
                        )
                    if not getattr(plot, "cutoff_date_compliant", False):
                        missing_fields.append(
                            f"plot {pcode}: cutoff_date_compliant=False (post-2020-12-31 land use change)"
                        )
                    if not getattr(plot, "legal_land_use", False):
                        missing_fields.append(
                            f"plot {pcode}: legal_land_use=False"
                        )

        # ------------------------------------------------------------------
        # 4. Commodity-specific rules
        # ------------------------------------------------------------------
        commodity_rules: dict = rules.get("commodity_specific", {})
        if record.commodity_type and record.commodity_type in commodity_rules:
            commodity_req: dict = commodity_rules[record.commodity_type]
            extra_fields: list[str] = commodity_req.get("required_fields", [])
            for field in extra_fields:
                value = getattr(record, field, None)
                if value is None and field not in missing_fields:
                    missing_fields.append(field)

        # ------------------------------------------------------------------
        # 5. Determine compliance_status
        # ------------------------------------------------------------------
        # Preserve manually-set terminal statuses
        current_status = record.compliance_status
        if current_status in ("declared", "compliant", "non_compliant"):
            compliance_status = current_status
        elif missing_fields or missing_plots:
            compliance_status = "incomplete"
        else:
            compliance_status = "ready"

        valid = len(missing_fields) == 0 and not missing_plots

        return ValidationResult(
            valid=valid,
            compliance_status=compliance_status,
            missing_fields=missing_fields,
            missing_plots=missing_plots,
            warnings=warnings,
            framework=framework.slug,
            checked_at=datetime.now(tz=timezone.utc),
        )
