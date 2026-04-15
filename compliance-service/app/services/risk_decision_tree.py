"""Composite risk decision-tree service.

Applies a cascade of rules over the data Trace already has for a plot, and
returns a single final risk label plus the drivers that contributed. The
goal, per MITECO webinar 3, is to move past "one map says X" into a
defendable "N sources agree, and here is why we chose this label".

Inputs combined:
  1. Multi-source satellite screening (JRC + Hansen + GFW alerts + WDPA)
  2. Convergence score (0-5)
  3. Country risk benchmark (CPI, deforestation prevalence, conflict)
  4. Legal compliance status (blocking_missing from plot_legal_compliance)
  5. Producer scale (smallholder vs industrial)
  6. WDPA / protected area flag
  7. Tenure type (indigenous / sharecropped reinforce due diligence)
  8. Capture metadata (accuracy, method)
"""
from __future__ import annotations

from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.country_risk import CountryRiskBenchmark
from app.models.legal_catalog import (
    LegalRequirement,
    LegalRequirementCatalog,
    PlotLegalCompliance,
)
from app.models.plot import CompliancePlot


FinalRisk = Literal["low", "medium", "high", "critical", "requires_field_visit"]


class RiskDecisionTree:
    """Compose satellite + legal + country risk into one label."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def decide(self, plot: CompliancePlot) -> dict[str, Any]:
        drivers: list[str] = []
        warnings: list[str] = []
        positives: list[str] = []

        # --- 1. Screening metadata ---------------------------------------------
        meta = plot.metadata_ or {}
        full = meta.get("eudr_full_screening") or {}
        convergence_score = full.get("convergence_score")
        convergence_level = full.get("convergence_level")
        eudr_risk = full.get("eudr_risk")
        inside_wdpa = full.get("inside_protected_area")

        if eudr_risk in ("high", "critical"):
            drivers.append(f"Riesgo satelital {eudr_risk}")
        elif eudr_risk == "low":
            positives.append("Screening satelital sin alertas post-2020")
        elif eudr_risk == "medium":
            warnings.append("Screening satelital con riesgo medio")
        elif eudr_risk is None:
            warnings.append("Screening satelital no ejecutado")

        if convergence_level == "low":
            warnings.append(
                f"Convergencia de evidencia BAJA ({convergence_score}/5) — "
                "menos de 2 fuentes respondieron correctamente"
            )
        elif convergence_level == "high":
            positives.append(
                f"Convergencia de evidencia ALTA ({convergence_score}/5)"
            )

        if inside_wdpa is True:
            drivers.append("Parcela dentro de area protegida WDPA")

        # --- 2. Country risk benchmark ------------------------------------------
        country = plot.country_code
        bench = (
            await self._db.execute(
                select(CountryRiskBenchmark)
                .where(
                    CountryRiskBenchmark.country_code == country,
                    CountryRiskBenchmark.is_current.is_(True),
                )
                .order_by(CountryRiskBenchmark.as_of_date.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

        country_risk_snapshot: dict[str, Any] | None = None
        if bench:
            country_risk_snapshot = {
                "country_code": bench.country_code,
                "risk_level": bench.risk_level,
                "cpi_score": bench.cpi_score,
                "cpi_rank": bench.cpi_rank,
                "conflict_flag": bench.conflict_flag,
                "deforestation_prevalence": bench.deforestation_prevalence,
                "indigenous_risk_flag": bench.indigenous_risk_flag,
                "as_of_date": bench.as_of_date.isoformat(),
            }
            if bench.risk_level in ("high", "critical"):
                drivers.append(
                    f"Pais {country}: riesgo {bench.risk_level} "
                    f"(CPI {bench.cpi_score}, deforestacion "
                    f"{bench.deforestation_prevalence})"
                )
            if bench.conflict_flag:
                warnings.append(f"{country} en zona con conflicto activo (ACLED)")
            if bench.indigenous_risk_flag and plot.indigenous_territory_flag:
                drivers.append(
                    f"{country}: superposicion con territorios indigenas "
                    "con alto riesgo reconocido"
                )
        else:
            warnings.append(f"No hay benchmark de pais para {country}")

        # --- 3. Legal compliance checklist --------------------------------------
        legal_summary = await self._legal_status(plot)
        if legal_summary:
            if legal_summary["blocking_missing"] > 0:
                drivers.append(
                    f"Legalidad: {legal_summary['blocking_missing']} "
                    "requisito(s) bloqueantes no cumplidos"
                )
            elif legal_summary["missing"] > 0:
                warnings.append(
                    f"Legalidad: {legal_summary['missing']} "
                    "requisito(s) no cumplidos (no bloqueantes)"
                )
            elif legal_summary["applicable"] > 0 and (
                legal_summary["satisfied"] / legal_summary["applicable"]
            ) >= 0.8:
                positives.append(
                    f"Legalidad: {legal_summary['satisfied']}/"
                    f"{legal_summary['applicable']} requisitos cumplidos"
                )
            # Sworn affidavits — advertencia si mas del 30% de satisfied
            # se apoya solo en declaracion jurada.
            sat = legal_summary.get("satisfied", 0)
            aff = legal_summary.get("affidavit_only", 0)
            if sat > 0 and (aff / sat) > 0.3:
                warnings.append(
                    f"Legalidad: {aff}/{sat} items satisfechos se apoyan "
                    "unicamente en declaracion jurada — requiere corroboracion "
                    "documental cruzada"
                )

        # --- 4. Producer scale / tenure reinforcements --------------------------
        if plot.producer_scale == "industrial":
            warnings.append(
                "Produccion industrial — requisitos reforzados (EIA, contratos, FPIC)"
            )
        if plot.tenure_type in ("indigenous_collective", "afro_collective"):
            warnings.append(
                f"Tenencia colectiva ({plot.tenure_type}) — FPIC obligatorio"
            )
        if plot.tenure_type == "occupation":
            drivers.append("Tenencia por ocupacion sin titulo — riesgo de legalidad")

        # --- 5. Capture metadata ------------------------------------------------
        if plot.gps_accuracy_m is not None and float(plot.gps_accuracy_m) > 10:
            warnings.append(
                f"Exactitud GPS baja ({plot.gps_accuracy_m} m) — "
                "considerar recaptura en campo"
            )
        if plot.capture_method in (None, "unknown"):
            warnings.append(
                "Metodo de captura no documentado — SOP de campo no trazable"
            )

        # --- 6. Final label -----------------------------------------------------
        final_risk: FinalRisk
        recommended_action: str

        # Hard blockers (drivers) escalate straight to high / critical.
        if len(drivers) >= 2:
            final_risk = "critical"
            recommended_action = (
                "NO comercializar. Se requiere verificacion en terreno y "
                "resolucion de todos los drivers antes de proceder."
            )
        elif len(drivers) == 1:
            final_risk = "high"
            recommended_action = (
                "Due diligence reforzado obligatorio. Revisar el driver y "
                "documentar mitigacion antes de exportar."
            )
        elif len(warnings) >= 3:
            final_risk = "requires_field_visit"
            recommended_action = (
                "Multiples advertencias. Se recomienda visita en terreno "
                "para aumentar la convergencia de evidencia antes de declarar."
            )
        elif len(warnings) >= 1:
            final_risk = "medium"
            recommended_action = (
                "Completar los items de advertencia y re-ejecutar el screening "
                "para mover a riesgo bajo."
            )
        else:
            final_risk = "low"
            recommended_action = (
                "Cumplimiento aceptable. Mantener evidencia, re-ejecutar "
                "screening cada 6 meses."
            )

        # EUDR Art. 10 — la convergencia (numero de fuentes que respondieron)
        # es informacion sobre el screening, NO un downgrade del riesgo
        # normativo. Si la regla normativa marca high, NO permitimos que la
        # baja convergencia lo baje a medium. Marcamos la advertencia como
        # informacion separada.
        convergence_warning = convergence_level == "low"
        if eudr_risk in ("high", "critical") and final_risk in ("low", "medium"):
            final_risk = "high"
            recommended_action = (
                "Riesgo satelital alto detectado: due diligence reforzado "
                "obligatorio. La baja convergencia de evidencia es informativa "
                "y no permite degradar el riesgo normativo."
            )

        return {
            "final_risk": final_risk,
            "drivers": drivers,
            "warnings": warnings,
            "positives": positives,
            "convergence_warning": convergence_warning,
            "recommended_action": recommended_action,
            "inputs": {
                "eudr_risk": eudr_risk,
                "convergence_score": convergence_score,
                "convergence_level": convergence_level,
                "inside_protected_area": inside_wdpa,
                "country_risk": country_risk_snapshot,
                "legal_summary": legal_summary,
                "producer_scale": plot.producer_scale,
                "tenure_type": plot.tenure_type,
                "gps_accuracy_m": (
                    float(plot.gps_accuracy_m)
                    if plot.gps_accuracy_m is not None
                    else None
                ),
                "capture_method": plot.capture_method,
            },
        }

    async def _legal_status(
        self, plot: CompliancePlot
    ) -> dict[str, int] | None:
        """Return a compact legal compliance summary for the plot."""
        commodity = (plot.crop_type or "").lower() or None
        q = select(LegalRequirementCatalog).where(
            LegalRequirementCatalog.country_code == plot.country_code,
            LegalRequirementCatalog.is_active.is_(True),
        )
        if commodity:
            q = q.where(LegalRequirementCatalog.commodity == commodity)
        q = q.order_by(LegalRequirementCatalog.version.desc())
        cat = (await self._db.execute(q)).scalars().first()
        if cat is None:
            return None

        reqs = (
            await self._db.execute(
                select(LegalRequirement).where(LegalRequirement.catalog_id == cat.id)
            )
        ).scalars().all()
        if not reqs:
            return None

        statuses = (
            await self._db.execute(
                select(PlotLegalCompliance).where(
                    PlotLegalCompliance.plot_id == plot.id
                )
            )
        ).scalars().all()
        by_req = {s.requirement_id: s for s in statuses}

        satisfied = missing = blocking_missing = applicable = 0
        affidavit_only = 0
        scale = plot.producer_scale
        for r in reqs:
            applies = r.applies_to_scale == "all" or (
                scale is not None
                and (
                    r.applies_to_scale == scale
                    or (
                        r.applies_to_scale == "medium_or_industrial"
                        and scale in ("medium", "industrial")
                    )
                )
            )
            if not applies:
                continue
            applicable += 1
            s = by_req.get(r.id)
            status = s.status if s else "pending"
            if status == "satisfied":
                satisfied += 1
                if s is not None and getattr(s, "evidence_weight", "primary") == "affidavit":
                    affidavit_only += 1
            elif status == "missing":
                missing += 1
                if r.is_blocking:
                    blocking_missing += 1
        return {
            "satisfied": satisfied,
            "missing": missing,
            "blocking_missing": blocking_missing,
            "applicable": applicable,
            "affidavit_only": affidavit_only,
        }
