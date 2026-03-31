"""Repository: workflow engine tables (states, transitions, event_types)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models import WorkflowState, WorkflowTransition, WorkflowEventType


class WorkflowStateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def list_by_tenant(self, tenant_id: uuid.UUID) -> list[WorkflowState]:
        result = await self._db.execute(
            select(WorkflowState)
            .where(WorkflowState.tenant_id == tenant_id)
            .order_by(WorkflowState.sort_order)
        )
        return list(result.scalars().all())

    async def get_by_id(self, state_id: uuid.UUID) -> WorkflowState | None:
        result = await self._db.execute(
            select(WorkflowState).where(WorkflowState.id == state_id)
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, tenant_id: uuid.UUID, slug: str) -> WorkflowState | None:
        result = await self._db.execute(
            select(WorkflowState).where(
                WorkflowState.tenant_id == tenant_id,
                WorkflowState.slug == slug,
            )
        )
        return result.scalar_one_or_none()

    async def get_initial_state(self, tenant_id: uuid.UUID) -> WorkflowState | None:
        result = await self._db.execute(
            select(WorkflowState).where(
                WorkflowState.tenant_id == tenant_id,
                WorkflowState.is_initial.is_(True),
            ).limit(1)
        )
        return result.scalar_one_or_none()

    async def create(self, tenant_id: uuid.UUID, **kwargs) -> WorkflowState:
        now = datetime.now(tz=timezone.utc)
        state = WorkflowState(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            created_at=now,
            updated_at=now,
            **kwargs,
        )
        self._db.add(state)
        await self._db.flush()
        return state

    async def update(self, state_id: uuid.UUID, **kwargs) -> WorkflowState | None:
        state = await self.get_by_id(state_id)
        if state is None:
            return None
        kwargs["updated_at"] = datetime.now(tz=timezone.utc)
        for k, v in kwargs.items():
            if v is not None:
                setattr(state, k, v)
        await self._db.flush()
        return state

    async def delete(self, state_id: uuid.UUID) -> bool:
        result = await self._db.execute(
            delete(WorkflowState).where(WorkflowState.id == state_id)
        )
        await self._db.flush()
        return result.rowcount > 0

    async def reorder(self, tenant_id: uuid.UUID, state_ids: list[uuid.UUID]) -> None:
        for idx, sid in enumerate(state_ids):
            await self._db.execute(
                update(WorkflowState)
                .where(WorkflowState.id == sid, WorkflowState.tenant_id == tenant_id)
                .values(sort_order=idx)
            )
        await self._db.flush()

    async def count_by_tenant(self, tenant_id: uuid.UUID) -> int:
        result = await self._db.execute(
            select(func.count(WorkflowState.id)).where(WorkflowState.tenant_id == tenant_id)
        )
        return result.scalar_one()


class WorkflowTransitionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def list_by_tenant(self, tenant_id: uuid.UUID) -> list[WorkflowTransition]:
        result = await self._db.execute(
            select(WorkflowTransition)
            .where(WorkflowTransition.tenant_id == tenant_id)
            .options(
                joinedload(WorkflowTransition.from_state),
                joinedload(WorkflowTransition.to_state),
            )
        )
        return list(result.unique().scalars().all())

    async def get_transitions_from(
        self, tenant_id: uuid.UUID, from_state_id: uuid.UUID
    ) -> list[WorkflowTransition]:
        """Get transitions from a specific state (including wildcards where from_state_id is NULL)."""
        result = await self._db.execute(
            select(WorkflowTransition)
            .where(
                WorkflowTransition.tenant_id == tenant_id,
                (WorkflowTransition.from_state_id == from_state_id)
                | (WorkflowTransition.from_state_id.is_(None)),
            )
            .options(
                joinedload(WorkflowTransition.from_state),
                joinedload(WorkflowTransition.to_state),
            )
        )
        return list(result.unique().scalars().all())

    async def find_by_event(
        self,
        tenant_id: uuid.UUID,
        from_state_id: uuid.UUID,
        event_type_slug: str,
    ) -> list[WorkflowTransition]:
        """Find transitions from a state triggered by a specific event type."""
        result = await self._db.execute(
            select(WorkflowTransition)
            .where(
                WorkflowTransition.tenant_id == tenant_id,
                (
                    (WorkflowTransition.from_state_id == from_state_id)
                    | (WorkflowTransition.from_state_id.is_(None))
                ),
                WorkflowTransition.event_type_slug == event_type_slug,
            )
            .options(
                joinedload(WorkflowTransition.from_state),
                joinedload(WorkflowTransition.to_state),
            )
        )
        return list(result.unique().scalars().all())

    async def is_valid_transition(
        self, tenant_id: uuid.UUID, from_state_id: uuid.UUID, to_state_id: uuid.UUID
    ) -> bool:
        result = await self._db.execute(
            select(func.count(WorkflowTransition.id)).where(
                WorkflowTransition.tenant_id == tenant_id,
                (
                    (WorkflowTransition.from_state_id == from_state_id)
                    | (WorkflowTransition.from_state_id.is_(None))
                ),
                WorkflowTransition.to_state_id == to_state_id,
            )
        )
        return result.scalar_one() > 0

    async def create(self, tenant_id: uuid.UUID, **kwargs) -> WorkflowTransition:
        transition = WorkflowTransition(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            created_at=datetime.now(tz=timezone.utc),
            **kwargs,
        )
        self._db.add(transition)
        await self._db.flush()
        # Reload with relationships
        result = await self._db.execute(
            select(WorkflowTransition)
            .where(WorkflowTransition.id == transition.id)
            .options(
                joinedload(WorkflowTransition.from_state),
                joinedload(WorkflowTransition.to_state),
            )
        )
        return result.unique().scalar_one()

    async def delete(self, transition_id: uuid.UUID) -> bool:
        result = await self._db.execute(
            delete(WorkflowTransition).where(WorkflowTransition.id == transition_id)
        )
        await self._db.flush()
        return result.rowcount > 0


class WorkflowEventTypeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def list_by_tenant(
        self, tenant_id: uuid.UUID, active_only: bool = True
    ) -> list[WorkflowEventType]:
        q = select(WorkflowEventType).where(WorkflowEventType.tenant_id == tenant_id)
        if active_only:
            q = q.where(WorkflowEventType.is_active.is_(True))
        result = await self._db.execute(q.order_by(WorkflowEventType.sort_order))
        return list(result.scalars().all())

    async def get_by_id(self, et_id: uuid.UUID) -> WorkflowEventType | None:
        result = await self._db.execute(
            select(WorkflowEventType).where(WorkflowEventType.id == et_id)
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, tenant_id: uuid.UUID, slug: str) -> WorkflowEventType | None:
        result = await self._db.execute(
            select(WorkflowEventType).where(
                WorkflowEventType.tenant_id == tenant_id,
                WorkflowEventType.slug == slug,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, tenant_id: uuid.UUID, **kwargs) -> WorkflowEventType:
        now = datetime.now(tz=timezone.utc)
        et = WorkflowEventType(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            created_at=now,
            updated_at=now,
            **kwargs,
        )
        self._db.add(et)
        await self._db.flush()
        return et

    async def update(self, et_id: uuid.UUID, **kwargs) -> WorkflowEventType | None:
        et = await self.get_by_id(et_id)
        if et is None:
            return None
        kwargs["updated_at"] = datetime.now(tz=timezone.utc)
        for k, v in kwargs.items():
            if v is not None:
                setattr(et, k, v)
        await self._db.flush()
        return et

    async def delete(self, et_id: uuid.UUID) -> bool:
        result = await self._db.execute(
            delete(WorkflowEventType).where(WorkflowEventType.id == et_id)
        )
        await self._db.flush()
        return result.rowcount > 0
