"""Onboarding endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.db.session import get_db_session
from app.repositories.user_repo import UserRepository

router = APIRouter(prefix="/api/v1/onboarding", tags=["onboarding"])


class OnboardingStatus(BaseModel):
    completed: bool
    step: str


class UpdateStepRequest(BaseModel):
    step: str = Field(max_length=50)


@router.get("/status", response_model=OnboardingStatus)
async def get_onboarding_status(current_user: CurrentUser) -> OnboardingStatus:
    return OnboardingStatus(
        completed=current_user.onboarding_completed,
        step=current_user.onboarding_step,
    )


@router.patch("/step", response_model=OnboardingStatus)
async def update_step(
    body: UpdateStepRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> OnboardingStatus:
    repo = UserRepository(db)
    await repo.update(current_user, onboarding_step=body.step)
    await db.commit()
    return OnboardingStatus(completed=current_user.onboarding_completed, step=body.step)


@router.patch("/complete", response_model=OnboardingStatus)
async def complete_onboarding(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> OnboardingStatus:
    repo = UserRepository(db)
    await repo.update(current_user, onboarding_completed=True, onboarding_step="complete")
    await db.commit()
    return OnboardingStatus(completed=True, step="complete")
