"""Workflow engine configuration endpoints."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_tenant_id
from app.db.session import get_db_session
from app.domain.schemas import (
    AvailableActionResponse,
    INDUSTRY_PRESETS,
    WorkflowStateCreate,
    WorkflowStateUpdate,
    WorkflowStateResponse,
    WorkflowStateReorderRequest,
    WorkflowTransitionCreate,
    WorkflowTransitionResponse,
    WorkflowEventTypeCreate,
    WorkflowEventTypeUpdate,
    WorkflowEventTypeResponse,
)
from app.services.workflow_service import WorkflowService

router = APIRouter(prefix="/config/workflow", tags=["workflow"])


def _get_service(
    session: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> WorkflowService:
    return WorkflowService(session, tenant_id)


# ─── States ────────────────────────────────────────────────────────────────────

@router.get("/states", response_model=list[WorkflowStateResponse])
async def list_states(svc: WorkflowService = Depends(_get_service)):
    return await svc.list_states()


@router.post("/states", response_model=WorkflowStateResponse, status_code=201)
async def create_state(
    body: WorkflowStateCreate,
    svc: WorkflowService = Depends(_get_service),
):
    return await svc.create_state(**body.model_dump())


@router.patch("/states/{state_id}", response_model=WorkflowStateResponse)
async def update_state(
    state_id: uuid.UUID,
    body: WorkflowStateUpdate,
    svc: WorkflowService = Depends(_get_service),
):
    return await svc.update_state(state_id, **body.model_dump(exclude_unset=True))


@router.delete("/states/{state_id}", status_code=204)
async def delete_state(
    state_id: uuid.UUID,
    svc: WorkflowService = Depends(_get_service),
):
    await svc.delete_state(state_id)
    return Response(status_code=204)


@router.post("/states/reorder", response_model=list[WorkflowStateResponse])
async def reorder_states(
    body: WorkflowStateReorderRequest,
    svc: WorkflowService = Depends(_get_service),
):
    return await svc.reorder_states(body.state_ids)


@router.get(
    "/states/{state_slug}/actions",
    response_model=list[AvailableActionResponse],
    summary="Available actions from a given state (for dynamic UI buttons)",
)
async def get_available_actions(
    state_slug: str,
    svc: WorkflowService = Depends(_get_service),
):
    return await svc.get_available_actions(state_slug)


# ─── Transitions ───────────────────────────────────────────────────────────────

@router.get("/transitions", response_model=list[WorkflowTransitionResponse])
async def list_transitions(svc: WorkflowService = Depends(_get_service)):
    return await svc.list_transitions()


@router.post("/transitions", response_model=WorkflowTransitionResponse, status_code=201)
async def create_transition(
    body: WorkflowTransitionCreate,
    svc: WorkflowService = Depends(_get_service),
):
    return await svc.create_transition(**body.model_dump())


@router.delete("/transitions/{transition_id}", status_code=204)
async def delete_transition(
    transition_id: uuid.UUID,
    svc: WorkflowService = Depends(_get_service),
):
    await svc.delete_transition(transition_id)
    return Response(status_code=204)


# ─── Event Types ───────────────────────────────────────────────────────────────

@router.get("/event-types", response_model=list[WorkflowEventTypeResponse])
async def list_event_types(
    active_only: bool = True,
    svc: WorkflowService = Depends(_get_service),
):
    return await svc.list_event_types(active_only)


@router.post("/event-types", response_model=WorkflowEventTypeResponse, status_code=201)
async def create_event_type(
    body: WorkflowEventTypeCreate,
    svc: WorkflowService = Depends(_get_service),
):
    return await svc.create_event_type(**body.model_dump())


@router.patch("/event-types/{et_id}", response_model=WorkflowEventTypeResponse)
async def update_event_type(
    et_id: uuid.UUID,
    body: WorkflowEventTypeUpdate,
    svc: WorkflowService = Depends(_get_service),
):
    return await svc.update_event_type(et_id, **body.model_dump(exclude_unset=True))


@router.delete("/event-types/{et_id}", status_code=204)
async def delete_event_type(
    et_id: uuid.UUID,
    svc: WorkflowService = Depends(_get_service),
):
    await svc.delete_event_type(et_id)
    return Response(status_code=204)


# ─── Industry Presets ──────────────────────────────────────────────────────────

@router.get("/presets")
async def list_presets():
    """List available industry presets."""
    return {
        name: {
            "states": len(p["states"]),
            "transitions": len(p.get("transitions", [])),
            "event_types": len(p.get("event_types", [])),
        }
        for name, p in INDUSTRY_PRESETS.items()
    }


@router.post("/seed/{preset_name}", status_code=201)
async def seed_preset(
    preset_name: str,
    svc: WorkflowService = Depends(_get_service),
):
    return await svc.seed_preset(preset_name)
