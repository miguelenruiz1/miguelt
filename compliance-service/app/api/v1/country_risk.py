"""Router for country risk benchmarks."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ModuleUser
from app.core.errors import NotFoundError
from app.db.session import get_db_session
from app.models.country_risk import CountryRiskBenchmark
from app.schemas.country_risk import (
    CountryRiskBenchmarkResponse,
    CountryRiskBenchmarkUpdate,
)

router = APIRouter(
    prefix="/api/v1/compliance/country-risk",
    tags=["country-risk"],
)


@router.get("/", response_model=list[CountryRiskBenchmarkResponse])
async def list_benchmarks(
    _: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
    only_current: bool = Query(True),
):
    q = select(CountryRiskBenchmark)
    if only_current:
        q = q.where(CountryRiskBenchmark.is_current.is_(True))
    q = q.order_by(CountryRiskBenchmark.country_code)
    return (await db.execute(q)).scalars().all()


@router.get("/{code}", response_model=CountryRiskBenchmarkResponse)
async def get_benchmark(
    code: str,
    _: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    code = code.upper()
    row = (
        await db.execute(
            select(CountryRiskBenchmark)
            .where(
                CountryRiskBenchmark.country_code == code,
                CountryRiskBenchmark.is_current.is_(True),
            )
            .order_by(CountryRiskBenchmark.as_of_date.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if row is None:
        raise NotFoundError(f"No current benchmark for country '{code}'")
    return row


@router.post("/{code}", response_model=CountryRiskBenchmarkResponse)
async def upsert_benchmark(
    code: str,
    body: CountryRiskBenchmarkUpdate,
    user: ModuleUser,
    db: AsyncSession = Depends(get_db_session),
):
    if not user.get("is_superuser"):
        raise HTTPException(status_code=403, detail="admin required")

    code = code.upper()
    # Mark existing "current" rows as not current for this country
    await db.execute(
        update(CountryRiskBenchmark)
        .where(
            CountryRiskBenchmark.country_code == code,
            CountryRiskBenchmark.is_current.is_(True),
        )
        .values(is_current=False)
    )
    row = CountryRiskBenchmark(
        country_code=code,
        risk_level=body.risk_level,
        cpi_score=body.cpi_score,
        cpi_rank=body.cpi_rank,
        conflict_flag=body.conflict_flag,
        deforestation_prevalence=body.deforestation_prevalence,
        indigenous_risk_flag=body.indigenous_risk_flag,
        notes=body.notes,
        source=body.source,
        as_of_date=body.as_of_date,
        is_current=True,
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return row
