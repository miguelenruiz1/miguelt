"""Repository: assets + custody_events tables."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Asset, CustodyEvent
from app.domain.types import AssetState


# Sentinel for "field not provided" — distinguishes from explicit None.
class _Unset:
    """Marker class for unset parameters; allows clearing a column to NULL explicitly."""
    pass


_UNSET = _Unset()


class AssetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def create(
        self,
        asset_mint: str,
        product_type: str,
        metadata: dict[str, Any],
        initial_custodian_wallet: str,
        state: AssetState | str,
        last_event_hash: str | None = None,
        tenant_id: uuid.UUID | None = None,
        blockchain_status: str = "SKIPPED",
        workflow_state_id: uuid.UUID | None = None,
    ) -> Asset:
        now = datetime.now(tz=timezone.utc)
        asset = Asset(
            id=uuid.uuid4(),
            asset_mint=asset_mint,
            product_type=product_type,
            metadata_=metadata,
            current_custodian_wallet=initial_custodian_wallet,
            state=state,
            last_event_hash=last_event_hash,
            tenant_id=tenant_id or uuid.UUID("00000000-0000-0000-0000-000000000001"),
            blockchain_status=blockchain_status,
            is_compressed=False,
            workflow_state_id=workflow_state_id,
            created_at=now,
            updated_at=now,
        )
        self._db.add(asset)
        await self._db.flush()
        return asset

    async def get_by_id(self, asset_id: uuid.UUID) -> Asset | None:
        result = await self._db.execute(
            select(Asset).where(Asset.id == asset_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_for_update(self, asset_id: uuid.UUID) -> Asset | None:
        """SELECT FOR UPDATE — prevents concurrent handoffs."""
        result = await self._db.execute(
            select(Asset).where(Asset.id == asset_id).with_for_update()
        )
        return result.scalar_one_or_none()

    async def get_by_mint(self, asset_mint: str) -> Asset | None:
        result = await self._db.execute(
            select(Asset).where(Asset.asset_mint == asset_mint)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        product_type: str | None = None,
        custodian: str | None = None,
        state: str | None = None,
        tenant_id: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[Asset], int]:
        q = select(Asset)
        count_q = select(func.count(Asset.id))

        if tenant_id is not None:
            q = q.where(Asset.tenant_id == tenant_id)
            count_q = count_q.where(Asset.tenant_id == tenant_id)
        if product_type:
            q = q.where(Asset.product_type == product_type)
            count_q = count_q.where(Asset.product_type == product_type)
        if custodian:
            q = q.where(Asset.current_custodian_wallet == custodian)
            count_q = count_q.where(Asset.current_custodian_wallet == custodian)
        if state:
            q = q.where(Asset.state == state)
            count_q = count_q.where(Asset.state == state)

        total = (await self._db.execute(count_q)).scalar_one()
        rows = (await self._db.execute(q.offset(offset).limit(limit))).scalars().all()
        return list(rows), total

    async def update_blockchain_fields(
        self,
        asset_id: uuid.UUID,
        blockchain_asset_id: str | None = None,
        blockchain_tree_address: str | None = None,
        blockchain_tx_signature: str | None = None,
        blockchain_status: str | None = None,
        blockchain_error: str | None | _Unset = _UNSET,
        is_compressed: bool | None = None,
    ) -> None:
        """Update only blockchain_* fields on an Asset.

        `blockchain_error` uses a sentinel: pass `None` explicitly to clear it,
        or omit it (`_UNSET`) to leave it unchanged. This lets a successful
        retry mint clear a stale error message.
        """
        updates: dict[str, Any] = {}
        if blockchain_asset_id is not None:
            updates["blockchain_asset_id"] = blockchain_asset_id
            # Also update asset_mint from placeholder to real blockchain address
            updates["asset_mint"] = blockchain_asset_id
        if blockchain_tree_address is not None:
            updates["blockchain_tree_address"] = blockchain_tree_address
        if blockchain_tx_signature is not None:
            updates["blockchain_tx_signature"] = blockchain_tx_signature
        if blockchain_status is not None:
            updates["blockchain_status"] = blockchain_status
        if is_compressed is not None:
            updates["is_compressed"] = is_compressed
        if blockchain_error is not _UNSET:
            updates["blockchain_error"] = blockchain_error
        if updates:
            await self._db.execute(
                update(Asset)
                .where(Asset.id == asset_id)
                .values(**updates)
                .execution_options(synchronize_session="fetch")
            )
            await self._db.flush()

    async def update_after_event(
        self,
        asset_id: uuid.UUID,
        new_state: AssetState | str,
        new_custodian: str | None,
        last_event_hash: str,
        workflow_state_id: uuid.UUID | None = None,
    ) -> None:
        values: dict = {
            "state": new_state,
            "last_event_hash": last_event_hash,
            "updated_at": datetime.now(tz=timezone.utc),
        }
        if new_custodian is not None:
            values["current_custodian_wallet"] = new_custodian
        if workflow_state_id is not None:
            values["workflow_state_id"] = workflow_state_id
        await self._db.execute(
            update(Asset).where(Asset.id == asset_id).values(**values)
        )
        await self._db.flush()


class CustodyEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def create(
        self,
        asset_id: uuid.UUID,
        event_type: str,
        from_wallet: str | None,
        to_wallet: str | None,
        timestamp: datetime,
        location: dict[str, Any] | None,
        data: dict[str, Any],
        prev_event_hash: str | None,
        event_hash: str,
        tenant_id: uuid.UUID | None = None,
        parent_event_id: uuid.UUID | None = None,
    ) -> CustodyEvent:
        now = datetime.now(tz=timezone.utc)
        event = CustodyEvent(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            asset_id=asset_id,
            event_type=event_type,
            from_wallet=from_wallet,
            to_wallet=to_wallet,
            timestamp=timestamp,
            location=location,
            data=data,
            prev_event_hash=prev_event_hash,
            event_hash=event_hash,
            anchored=False,
            anchor_attempts=0,
            created_at=now,
            parent_event_id=parent_event_id,
        )
        self._db.add(event)
        await self._db.flush()
        return event

    async def get_last_root_event(
        self, asset_id: uuid.UUID
    ) -> CustodyEvent | None:
        """Return the most recent ROOT event for the asset (parent_event_id IS NULL).

        Used to auto-link informational events as children of the most recent
        state transition.
        """
        result = await self._db.execute(
            select(CustodyEvent)
            .where(
                CustodyEvent.asset_id == asset_id,
                CustodyEvent.parent_event_id.is_(None),
            )
            .order_by(CustodyEvent.timestamp.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, event_id: uuid.UUID) -> CustodyEvent | None:
        result = await self._db.execute(
            select(CustodyEvent).where(CustodyEvent.id == event_id)
        )
        return result.scalar_one_or_none()

    async def get_by_asset(
        self, asset_id: uuid.UUID, offset: int = 0, limit: int = 100
    ) -> tuple[list[CustodyEvent], int]:
        q = (
            select(CustodyEvent)
            .where(CustodyEvent.asset_id == asset_id)
            .order_by(CustodyEvent.timestamp.desc())
        )
        count_q = select(func.count(CustodyEvent.id)).where(CustodyEvent.asset_id == asset_id)
        total = (await self._db.execute(count_q)).scalar_one()
        rows = (await self._db.execute(q.offset(offset).limit(limit))).scalars().all()
        return list(rows), total

    async def get_pending_anchor(self, limit: int = 50) -> list[CustodyEvent]:
        result = await self._db.execute(
            select(CustodyEvent)
            .where(CustodyEvent.anchored.is_(False))
            .order_by(CustodyEvent.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def mark_anchored(self, event_id: uuid.UUID, tx_sig: str) -> None:
        await self._db.execute(
            update(CustodyEvent)
            .where(CustodyEvent.id == event_id)
            .values(anchored=True, solana_tx_sig=tx_sig, anchor_last_error=None)
        )
        await self._db.flush()

    async def increment_anchor_attempt(
        self, event_id: uuid.UUID, error: str | None = None
    ) -> None:
        """Atomic increment to avoid lost updates under concurrent retries."""
        await self._db.execute(
            update(CustodyEvent)
            .where(CustodyEvent.id == event_id)
            .values(
                anchor_attempts=CustodyEvent.anchor_attempts + 1,
                anchor_last_error=error,
            )
        )
        await self._db.flush()
