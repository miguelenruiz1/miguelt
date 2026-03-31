"""Router for compliance risk assessments — EUDR Art. 10-11."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.logging import get_logger
from app.db.session import get_db_session
from app.models.record import ComplianceRecord
from app.models.risk_assessment import ComplianceRiskAssessment
from app.schemas.risk_assessment import (
    RiskAssessmentCreate,
    RiskAssessmentResponse,
    RiskAssessmentUpdate,
)

log = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/compliance/risk-assessments",
    tags=["risk-assessments"],
)


def _tenant_id(user: dict) -> uuid.UUID:
    raw = str(user.get("tenant_id", "00000000-0000-0000-0000-000000000001"))
    try:
        return uuid.UUID(raw)
    except ValueError:
        return uuid.UUID("00000000-0000-0000-0000-000000000001")


@router.post("/", response_model=RiskAssessmentResponse, status_code=status.HTTP_201_CREATED)
async def create_risk_assessment(
    body: RiskAssessmentCreate,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    tid = _tenant_id(user)

    # Verify record exists
    record = (
        await db.execute(
            select(ComplianceRecord).where(
                ComplianceRecord.id == body.record_id,
                ComplianceRecord.tenant_id == tid,
            )
        )
    ).scalar_one_or_none()
    if record is None:
        raise NotFoundError(f"Record '{body.record_id}' not found")

    # Return existing if already created (idempotent)
    existing = (
        await db.execute(
            select(ComplianceRiskAssessment).where(
                ComplianceRiskAssessment.tenant_id == tid,
                ComplianceRiskAssessment.record_id == body.record_id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    data = body.model_dump(exclude_unset=True)
    assessment = ComplianceRiskAssessment(tenant_id=tid, **data)
    db.add(assessment)
    await db.flush()
    await db.refresh(assessment)
    return assessment


@router.get("/by-record/{record_id}", response_model=RiskAssessmentResponse)
async def get_by_record(
    record_id: uuid.UUID,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    tid = _tenant_id(user)
    assessment = (
        await db.execute(
            select(ComplianceRiskAssessment).where(
                ComplianceRiskAssessment.record_id == record_id,
                ComplianceRiskAssessment.tenant_id == tid,
            )
        )
    ).scalar_one_or_none()
    if assessment is None:
        raise NotFoundError(f"Risk assessment for record '{record_id}' not found")
    return assessment


@router.get("/{assessment_id}", response_model=RiskAssessmentResponse)
async def get_risk_assessment(
    assessment_id: uuid.UUID,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    tid = _tenant_id(user)
    assessment = (
        await db.execute(
            select(ComplianceRiskAssessment).where(
                ComplianceRiskAssessment.id == assessment_id,
                ComplianceRiskAssessment.tenant_id == tid,
            )
        )
    ).scalar_one_or_none()
    if assessment is None:
        raise NotFoundError(f"Risk assessment '{assessment_id}' not found")
    return assessment


@router.patch("/{assessment_id}", response_model=RiskAssessmentResponse)
async def update_risk_assessment(
    assessment_id: uuid.UUID,
    body: RiskAssessmentUpdate,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    tid = _tenant_id(user)
    assessment = (
        await db.execute(
            select(ComplianceRiskAssessment).where(
                ComplianceRiskAssessment.id == assessment_id,
                ComplianceRiskAssessment.tenant_id == tid,
            )
        )
    ).scalar_one_or_none()
    if assessment is None:
        raise NotFoundError(f"Risk assessment '{assessment_id}' not found")

    if assessment.status == "completed":
        raise ValidationError("Cannot update a completed risk assessment. Create a new one.")

    update_data = body.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        setattr(assessment, key, val)

    await db.flush()
    await db.refresh(assessment)
    return assessment


@router.post("/{assessment_id}/complete", response_model=RiskAssessmentResponse)
async def complete_risk_assessment(
    assessment_id: uuid.UUID,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    """Mark a risk assessment as completed. Validates all 3 steps are filled."""
    tid = _tenant_id(user)
    assessment = (
        await db.execute(
            select(ComplianceRiskAssessment).where(
                ComplianceRiskAssessment.id == assessment_id,
                ComplianceRiskAssessment.tenant_id == tid,
            )
        )
    ).scalar_one_or_none()
    if assessment is None:
        raise NotFoundError(f"Risk assessment '{assessment_id}' not found")

    # Validate completeness
    errors: list[str] = []
    if not assessment.country_risk_level:
        errors.append("country_risk_level is required (Step 1)")
    if not assessment.supply_chain_risk_level:
        errors.append("supply_chain_risk_level is required (Step 2)")
    if not assessment.regional_risk_level:
        errors.append("regional_risk_level is required (Step 3)")
    if not assessment.overall_risk_level:
        errors.append("overall_risk_level is required (Conclusion)")
    if not assessment.conclusion:
        errors.append("conclusion is required (approved/conditional/rejected)")

    if errors:
        raise ValidationError(f"Incomplete risk assessment: {'; '.join(errors)}")

    now = datetime.now(tz=timezone.utc)
    assessment.status = "completed"
    assessment.assessed_at = now
    user_id = user.get("id")
    if user_id and user_id != "system":
        try:
            assessment.assessed_by = uuid.UUID(str(user_id))
        except ValueError:
            pass

    await db.flush()
    await db.refresh(assessment)
    return assessment


@router.delete("/{assessment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_risk_assessment(
    assessment_id: uuid.UUID,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    tid = _tenant_id(user)
    assessment = (
        await db.execute(
            select(ComplianceRiskAssessment).where(
                ComplianceRiskAssessment.id == assessment_id,
                ComplianceRiskAssessment.tenant_id == tid,
            )
        )
    ).scalar_one_or_none()
    if assessment is None:
        raise NotFoundError(f"Risk assessment '{assessment_id}' not found")

    await db.delete(assessment)
    await db.flush()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
