"""Repository for AnchorRequest CRUD."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AnchorRequest


class AnchorRequestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        tenant_id: uuid.UUID,
        source_service: str,
        source_entity_type: str,
        source_entity_id: str,
        payload_hash: str,
        callback_url: str | None = None,
        metadata: dict | None = None,
    ) -> AnchorRequest:
        ar = AnchorRequest(
            tenant_id=tenant_id,
            source_service=source_service,
            source_entity_type=source_entity_type,
            source_entity_id=source_entity_id,
            payload_hash=payload_hash,
            anchor_status="pending",
            callback_url=callback_url,
            metadata_=metadata or {},
        )
        self._session.add(ar)
        await self._session.flush()
        return ar

    async def get_by_id(self, anchor_id: uuid.UUID) -> AnchorRequest | None:
        return await self._session.get(AnchorRequest, anchor_id)

    async def get_by_hash(self, payload_hash: str) -> AnchorRequest | None:
        stmt = select(AnchorRequest).where(AnchorRequest.payload_hash == payload_hash)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_source(
        self,
        source_service: str,
        source_entity_type: str,
        source_entity_id: str,
    ) -> AnchorRequest | None:
        stmt = select(AnchorRequest).where(
            AnchorRequest.source_service == source_service,
            AnchorRequest.source_entity_type == source_entity_type,
            AnchorRequest.source_entity_id == source_entity_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_anchored(self, anchor_id: uuid.UUID, tx_sig: str) -> None:
        now = datetime.now(tz=timezone.utc)
        stmt = (
            update(AnchorRequest)
            .where(AnchorRequest.id == anchor_id)
            .values(
                anchor_status="anchored",
                solana_tx_sig=tx_sig,
                anchored_at=now,
                updated_at=now,
            )
        )
        await self._session.execute(stmt)

    async def increment_attempt(self, anchor_id: uuid.UUID, error: str) -> None:
        ar = await self.get_by_id(anchor_id)
        if ar:
            ar.attempts += 1
            ar.last_error = error[:500]
            ar.updated_at = datetime.now(tz=timezone.utc)

    async def mark_failed(self, anchor_id: uuid.UUID, error: str) -> None:
        stmt = (
            update(AnchorRequest)
            .where(AnchorRequest.id == anchor_id)
            .values(
                anchor_status="failed",
                last_error=error[:500],
                updated_at=datetime.now(tz=timezone.utc),
            )
        )
        await self._session.execute(stmt)

    async def get_pending(self, limit: int = 100) -> Sequence[AnchorRequest]:
        stmt = (
            select(AnchorRequest)
            .where(AnchorRequest.anchor_status == "pending")
            .order_by(AnchorRequest.created_at)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()
