"""
Business logic for the per-tenant workflow engine.

Handles CRUD for workflow states, transitions, event types,
industry preset seeding, and transition validation.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError, AssetStateError, ForbiddenError
from app.core.logging import get_logger
from app.db.models import WorkflowState, WorkflowTransition, WorkflowEventType
from app.domain.schemas import INDUSTRY_PRESETS
from app.repositories.workflow_repo import (
    WorkflowStateRepository,
    WorkflowTransitionRepository,
    WorkflowEventTypeRepository,
)

log = get_logger(__name__)


class WorkflowService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._db = session
        self._tenant_id = tenant_id
        self._state_repo = WorkflowStateRepository(session)
        self._transition_repo = WorkflowTransitionRepository(session)
        self._event_type_repo = WorkflowEventTypeRepository(session)

    # ─── States ────────────────────────────────────────────────────────────────

    async def list_states(self) -> list[WorkflowState]:
        return await self._state_repo.list_by_tenant(self._tenant_id)

    async def get_state(self, state_id: uuid.UUID) -> WorkflowState:
        state = await self._state_repo.get_by_id(state_id)
        if state is None or state.tenant_id != self._tenant_id:
            raise NotFoundError(f"Workflow state '{state_id}' not found")
        return state

    async def get_state_by_slug(self, slug: str) -> WorkflowState | None:
        return await self._state_repo.get_by_slug(self._tenant_id, slug)

    async def get_initial_state(self) -> WorkflowState:
        state = await self._state_repo.get_initial_state(self._tenant_id)
        if state is None:
            raise AssetStateError("No initial workflow state configured for this tenant")
        return state

    async def create_state(
        self,
        slug: str,
        label: str,
        color: str = "#6366f1",
        icon: str | None = None,
        is_initial: bool = False,
        is_terminal: bool = False,
        sort_order: int = 0,
    ) -> WorkflowState:
        existing = await self._state_repo.get_by_slug(self._tenant_id, slug)
        if existing:
            raise ConflictError(f"Workflow state with slug '{slug}' already exists")
        return await self._state_repo.create(
            tenant_id=self._tenant_id,
            slug=slug,
            label=label,
            color=color,
            icon=icon,
            is_initial=is_initial,
            is_terminal=is_terminal,
            sort_order=sort_order,
        )

    async def update_state(self, state_id: uuid.UUID, **kwargs) -> WorkflowState:
        state = await self.get_state(state_id)
        filtered = {k: v for k, v in kwargs.items() if v is not None}
        if not filtered:
            return state
        result = await self._state_repo.update(state_id, **filtered)
        return result  # type: ignore

    async def delete_state(self, state_id: uuid.UUID) -> None:
        await self.get_state(state_id)  # validates tenant
        deleted = await self._state_repo.delete(state_id)
        if not deleted:
            raise NotFoundError(f"Workflow state '{state_id}' not found")

    async def reorder_states(self, state_ids: list[uuid.UUID]) -> list[WorkflowState]:
        await self._state_repo.reorder(self._tenant_id, state_ids)
        return await self.list_states()

    # ─── Transitions ───────────────────────────────────────────────────────────

    async def list_transitions(self) -> list[WorkflowTransition]:
        return await self._transition_repo.list_by_tenant(self._tenant_id)

    async def get_available_transitions(self, from_state_id: uuid.UUID) -> list[WorkflowTransition]:
        return await self._transition_repo.get_transitions_from(self._tenant_id, from_state_id)

    async def validate_transition(
        self, from_state_slug: str, to_state_slug: str
    ) -> bool:
        from_state = await self._state_repo.get_by_slug(self._tenant_id, from_state_slug)
        to_state = await self._state_repo.get_by_slug(self._tenant_id, to_state_slug)
        if not from_state or not to_state:
            return False
        if from_state.is_terminal:
            return False
        return await self._transition_repo.is_valid_transition(
            self._tenant_id, from_state.id, to_state.id
        )

    async def create_transition(
        self,
        from_state_id: uuid.UUID | None,
        to_state_id: uuid.UUID,
        event_type_slug: str | None = None,
        label: str | None = None,
        requires_data: dict[str, Any] | None = None,
    ) -> WorkflowTransition:
        # Validate state IDs belong to tenant
        if from_state_id:
            await self.get_state(from_state_id)
        to_state = await self.get_state(to_state_id)
        return await self._transition_repo.create(
            tenant_id=self._tenant_id,
            from_state_id=from_state_id,
            to_state_id=to_state_id,
            event_type_slug=event_type_slug,
            label=label,
            requires_data=requires_data,
        )

    async def delete_transition(self, transition_id: uuid.UUID) -> None:
        deleted = await self._transition_repo.delete(transition_id)
        if not deleted:
            raise NotFoundError(f"Workflow transition '{transition_id}' not found")

    # ─── Event Types ───────────────────────────────────────────────────────────

    async def list_event_types(self, active_only: bool = True) -> list[WorkflowEventType]:
        return await self._event_type_repo.list_by_tenant(self._tenant_id, active_only)

    async def get_event_type(self, et_id: uuid.UUID) -> WorkflowEventType:
        et = await self._event_type_repo.get_by_id(et_id)
        if et is None or et.tenant_id != self._tenant_id:
            raise NotFoundError(f"Workflow event type '{et_id}' not found")
        return et

    async def get_event_type_by_slug(self, slug: str) -> WorkflowEventType | None:
        return await self._event_type_repo.get_by_slug(self._tenant_id, slug)

    async def create_event_type(self, **kwargs) -> WorkflowEventType:
        slug = kwargs.get("slug", "")
        existing = await self._event_type_repo.get_by_slug(self._tenant_id, slug)
        if existing:
            raise ConflictError(f"Event type with slug '{slug}' already exists")
        return await self._event_type_repo.create(tenant_id=self._tenant_id, **kwargs)

    async def update_event_type(self, et_id: uuid.UUID, **kwargs) -> WorkflowEventType:
        await self.get_event_type(et_id)
        filtered = {k: v for k, v in kwargs.items() if v is not None}
        if not filtered:
            et = await self._event_type_repo.get_by_id(et_id)
            return et  # type: ignore
        result = await self._event_type_repo.update(et_id, **filtered)
        return result  # type: ignore

    async def delete_event_type(self, et_id: uuid.UUID) -> None:
        await self.get_event_type(et_id)
        deleted = await self._event_type_repo.delete(et_id)
        if not deleted:
            raise NotFoundError(f"Workflow event type '{et_id}' not found")

    # ─── Industry Preset Seeding ───────────────────────────────────────────────

    async def seed_preset(self, preset_name: str) -> dict[str, Any]:
        preset = INDUSTRY_PRESETS.get(preset_name)
        if not preset:
            valid = ", ".join(sorted(INDUSTRY_PRESETS.keys()))
            raise NotFoundError(f"Unknown preset '{preset_name}'. Valid: {valid}")

        # Check if tenant already has states (avoid double-seed)
        count = await self._state_repo.count_by_tenant(self._tenant_id)
        if count > 0:
            raise ConflictError(
                "Tenant already has workflow states. Delete existing states before seeding."
            )

        # 1. Create states
        slug_to_state: dict[str, WorkflowState] = {}
        for s in preset["states"]:
            state = await self._state_repo.create(
                tenant_id=self._tenant_id,
                slug=s["slug"],
                label=s["label"],
                color=s.get("color", "#6366f1"),
                icon=s.get("icon"),
                is_initial=s.get("is_initial", False),
                is_terminal=s.get("is_terminal", False),
                sort_order=s.get("sort_order", 0),
            )
            slug_to_state[s["slug"]] = state

        # 2. Create transitions
        transitions_created = []
        for t in preset.get("transitions", []):
            from_state = slug_to_state.get(t["from"])
            to_state = slug_to_state.get(t["to"])
            if from_state and to_state:
                tr = await self._transition_repo.create(
                    tenant_id=self._tenant_id,
                    from_state_id=from_state.id,
                    to_state_id=to_state.id,
                    event_type_slug=t.get("event_type_slug"),
                    label=t.get("label"),
                )
                transitions_created.append(tr)

        # 3. Create event types
        event_types_created = []
        for et in preset.get("event_types", []):
            evt = await self._event_type_repo.create(
                tenant_id=self._tenant_id,
                slug=et["slug"],
                name=et["name"],
                icon=et.get("icon", "circle"),
                color=et.get("color", "#6366f1"),
                is_informational=et.get("is_informational", False),
                requires_wallet=et.get("requires_wallet", False),
                requires_notes=et.get("requires_notes", False),
                requires_reason=et.get("requires_reason", False),
                requires_admin=et.get("requires_admin", False),
                required_documents=et.get("required_documents"),
                compliance_required_documents=et.get("compliance_required_documents"),
            )
            event_types_created.append(evt)

        log.info(
            "workflow_preset_seeded",
            tenant_id=str(self._tenant_id),
            preset=preset_name,
            states=len(slug_to_state),
            transitions=len(transitions_created),
            event_types=len(event_types_created),
        )

        return {
            "preset": preset_name,
            "states_created": len(slug_to_state),
            "transitions_created": len(transitions_created),
            "event_types_created": len(event_types_created),
        }

    # ─── Transition Validation (used by custody_service) ───────────────────────

    async def assert_valid_workflow_transition(
        self, current_state_slug: str, target_state_slug: str
    ) -> WorkflowState:
        """
        Validate that transitioning from current_state_slug to target_state_slug
        is allowed by the tenant's workflow config. Returns the target WorkflowState.
        Raises AssetStateError if not valid.
        """
        current = await self._state_repo.get_by_slug(self._tenant_id, current_state_slug)
        if not current:
            raise AssetStateError(f"Unknown workflow state: '{current_state_slug}'")

        if current.is_terminal:
            raise AssetStateError(
                f"Asset is in terminal state '{current.label}' — no further transitions allowed"
            )

        target = await self._state_repo.get_by_slug(self._tenant_id, target_state_slug)
        if not target:
            raise AssetStateError(f"Unknown target workflow state: '{target_state_slug}'")

        is_valid = await self._transition_repo.is_valid_transition(
            self._tenant_id, current.id, target.id
        )
        if not is_valid:
            raise AssetStateError(
                f"Transition from '{current.label}' to '{target.label}' is not allowed"
            )

        return target

    async def find_transition_for_event(
        self,
        from_state_slug: str,
        event_type_slug: str,
        qc_result: str | None = None,
    ) -> tuple[WorkflowTransition, WorkflowState] | None:
        """
        Given a current state and an event type, find the matching transition
        and return (transition, target_state).

        For QC events, qc_result ('pass'/'fail') selects the correct target.
        Returns None if no matching transition exists in the workflow tables.
        """
        from_state = await self._state_repo.get_by_slug(self._tenant_id, from_state_slug)
        if not from_state:
            return None

        if from_state.is_terminal:
            raise AssetStateError(
                f"Asset is in terminal state '{from_state.label}' — no further transitions allowed"
            )

        transitions = await self._transition_repo.find_by_event(
            self._tenant_id, from_state.id, event_type_slug
        )
        if not transitions:
            # Fallback: look for transitions with NULL event_type_slug
            # Match by label (synthetic slug = LABEL.upper().replace(" ","_"))
            all_from = await self._transition_repo.get_transitions_from(
                self._tenant_id, from_state.id
            )
            null_transitions = [t for t in all_from if t.event_type_slug is None]

            # Try matching by synthetic slug (label-based)
            for t in null_transitions:
                synthetic = (t.label or "").upper().replace(" ", "_")
                if synthetic and synthetic == event_type_slug.upper():
                    return t, t.to_state

            # Try matching by transition ID (frontend sends transition_id as event_type)
            try:
                evt_uuid = uuid.UUID(event_type_slug)
                for t in null_transitions:
                    if t.id == evt_uuid:
                        return t, t.to_state
            except (ValueError, AttributeError):
                pass

            if len(null_transitions) == 1:
                transitions = null_transitions
            elif null_transitions:
                transitions = null_transitions
            else:
                return None

        # Multiple transitions with same event_type_slug (e.g., QC → pass/fail).
        # Match against canonical slugs at word boundaries to avoid e.g.
        # "pasado_inspeccion" colliding with the substring "pass".
        if qc_result and len(transitions) > 1:
            import re as _re
            result_lower = qc_result.lower()
            PASS_RE = _re.compile(r"(?:^|[_-])(pass|passed|aprobad[oa]|ok|qc[_-]?passed)(?:$|[_-])")
            FAIL_RE = _re.compile(r"(?:^|[_-])(fail|failed|fallid[oa]|rechaz[oa]|qc[_-]?failed)(?:$|[_-])")
            for t in transitions:
                slug = (t.to_state.slug if t.to_state else "").lower()
                if result_lower == "pass" and PASS_RE.search(slug):
                    return t, t.to_state
                if result_lower == "fail" and FAIL_RE.search(slug):
                    return t, t.to_state
            # Fall through to first match

        t = transitions[0]
        return t, t.to_state

    async def get_available_actions(
        self, from_state_slug: str
    ) -> list[dict[str, Any]]:
        """
        Return all available actions (transitions + event type metadata) from a state.
        Used by the frontend to render dynamic action buttons.
        Accepts a state slug OR a workflow_state_id UUID string.
        """
        from_state = await self._state_repo.get_by_slug(self._tenant_id, from_state_slug)
        # If slug not found, try as UUID (workflow_state_id)
        if not from_state:
            try:
                state_uuid = uuid.UUID(from_state_slug)
                ws = await self._state_repo.get_by_id(state_uuid)
                if ws and ws.tenant_id == self._tenant_id:
                    from_state = ws
            except (ValueError, AttributeError):
                pass
        if not from_state:
            return []

        if from_state.is_terminal:
            return []

        transitions = await self._transition_repo.get_transitions_from(
            self._tenant_id, from_state.id
        )

        # Bucket transitions by event_type_slug so we can expose ALL outputs
        # (not just the first) when an event has multiple outcomes (pass/fail/hold).
        # Transitions WITHOUT event_type_slug are treated individually (each is its own action).
        outputs_by_slug: dict[str, list[Any]] = {}
        for t in transitions:
            if t.event_type_slug:
                outputs_by_slug.setdefault(t.event_type_slug, []).append(t)

        seen_events: set[str] = set()
        actions: list[dict[str, Any]] = []

        for t in transitions:
            evt_slug = t.event_type_slug

            # ── Transitions WITHOUT event_type: each is an independent action ──
            if not evt_slug:
                # Use the transition label as a synthetic event slug
                synthetic_slug = (t.label or "").upper().replace(" ", "_") or f"TRANSITION_{t.id}"
                to_state_info = {
                    "slug": t.to_state.slug,
                    "label": t.to_state.label,
                    "color": t.to_state.color,
                    "icon": t.to_state.icon,
                    "is_terminal": t.to_state.is_terminal,
                } if t.to_state else None
                actions.append({
                    "transition_id": str(t.id),
                    "to_state": to_state_info,
                    "event_type_slug": synthetic_slug,
                    "label": t.label or (t.to_state.label if t.to_state else "Acción"),
                    "event_type": {
                        "slug": synthetic_slug,
                        "name": t.label or (t.to_state.label if t.to_state else "Acción"),
                        "description": None,
                        "icon": t.to_state.icon if t.to_state else None,
                        "color": t.to_state.color if t.to_state else "#6366f1",
                        "is_informational": False,
                        "requires_wallet": False,
                        "requires_notes": False,
                        "requires_reason": False,
                        "requires_admin": False,
                    },
                    "has_pass_fail": False,
                    "outputs": [
                        {
                            "transition_id": str(t.id),
                            "slug": t.to_state.slug if t.to_state else None,
                            "label": t.to_state.label if t.to_state else None,
                            "color": t.to_state.color if t.to_state else None,
                            "icon": t.to_state.icon if t.to_state else None,
                            "is_terminal": t.to_state.is_terminal if t.to_state else False,
                        }
                    ],
                })
                continue

            # ── Transitions WITH event_type: group by slug ─────────────────
            if evt_slug in seen_events:
                continue
            seen_events.add(evt_slug)

            # Look up event type metadata
            event_type = None
            et = await self._event_type_repo.get_by_slug(self._tenant_id, evt_slug)
            if et and not et.is_active:
                continue  # Skip disabled event types
            if et:
                event_type = {
                    "slug": et.slug,
                    "name": et.name,
                    "description": et.description,
                    "icon": et.icon,
                    "color": et.color,
                    "is_informational": et.is_informational,
                    "requires_wallet": et.requires_wallet,
                    "requires_notes": et.requires_notes,
                    "requires_reason": et.requires_reason,
                    "requires_admin": et.requires_admin,
                }

            slug_outputs = outputs_by_slug.get(evt_slug, [t])
            outputs = [
                {
                    "transition_id": str(out.id),
                    "slug": out.to_state.slug if out.to_state else None,
                    "label": out.to_state.label if out.to_state else None,
                    "color": out.to_state.color if out.to_state else None,
                    "icon": out.to_state.icon if out.to_state else None,
                    "is_terminal": out.to_state.is_terminal if out.to_state else False,
                }
                for out in slug_outputs
            ]

            actions.append({
                "transition_id": str(t.id),
                "to_state": {
                    "slug": t.to_state.slug,
                    "label": t.to_state.label,
                    "color": t.to_state.color,
                    "icon": t.to_state.icon,
                    "is_terminal": t.to_state.is_terminal,
                } if t.to_state else None,
                "event_type_slug": evt_slug,
                "label": t.label,
                "event_type": event_type,
                "has_pass_fail": len(slug_outputs) > 1,
                "outputs": outputs,
            })

        # ── Append free moves to ALL other states not already covered ────────
        # Users can move cargo to any state, not just predefined transitions.
        covered_to_slugs = {a["to_state"]["slug"] for a in actions if a.get("to_state")}
        if from_state:
            covered_to_slugs.add(from_state.slug)  # exclude current state
        all_states = await self._state_repo.list_by_tenant(self._tenant_id)
        for s in all_states:
            if s.slug in covered_to_slugs:
                continue
            actions.append({
                "transition_id": f"free_{s.slug}",
                "to_state": {
                    "slug": s.slug,
                    "label": s.label,
                    "color": s.color,
                    "icon": s.icon,
                    "is_terminal": s.is_terminal,
                },
                "event_type_slug": f"MOVE_TO_{s.slug.upper()}",
                "label": f"Mover a {s.label}",
                "event_type": {
                    "slug": f"MOVE_TO_{s.slug.upper()}",
                    "name": f"Mover a {s.label}",
                    "description": None,
                    "icon": s.icon,
                    "color": s.color,
                    "is_informational": False,
                    "requires_wallet": False,
                    "requires_notes": False,
                    "requires_reason": False,
                    "requires_admin": False,
                },
                "has_pass_fail": False,
                "outputs": [{
                    "transition_id": f"free_{s.slug}",
                    "slug": s.slug,
                    "label": s.label,
                    "color": s.color,
                    "icon": s.icon,
                    "is_terminal": s.is_terminal,
                }],
            })

        # ── Append ALL other active event types not already in actions ────
        # This lets users record any event (informational, fortuito, etc.)
        used_slugs = {a.get("event_type_slug") for a in actions}
        all_event_types = await self._event_type_repo.list_by_tenant(self._tenant_id, active_only=True)
        for et in all_event_types:
            if et.slug in used_slugs:
                continue
            actions.append({
                "transition_id": f"evt_{et.slug}",
                "to_state": None,
                "event_type_slug": et.slug,
                "label": et.name,
                "event_type": {
                    "slug": et.slug,
                    "name": et.name,
                    "description": et.description,
                    "icon": et.icon,
                    "color": et.color,
                    "is_informational": et.is_informational,
                    "requires_wallet": et.requires_wallet,
                    "requires_notes": et.requires_notes,
                    "requires_reason": et.requires_reason,
                    "requires_admin": et.requires_admin,
                },
                "has_pass_fail": False,
                "outputs": [],
            })

        return actions

    async def resolve_state_slug(self, slug_or_legacy: str) -> WorkflowState | None:
        """
        Resolve a state slug to a WorkflowState. Supports both new workflow slugs
        and legacy hardcoded slugs (for backward compatibility during migration).
        """
        return await self._state_repo.get_by_slug(self._tenant_id, slug_or_legacy)
