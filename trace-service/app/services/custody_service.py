"""
Business logic for asset creation and custody event processing.

Design decisions:
- SELECT FOR UPDATE on asset during HANDOFF to prevent concurrent double-handoff.
- Event hash is computed BEFORE writing to DB for reproducibility.
- Anchor job is enqueued AFTER successful DB commit.
- All event creation goes through _create_event() for DRY hash-chain logic.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import (
    AssetStateError,
    ForbiddenError,
    InvalidCustodianError,
    NotFoundError,
)
from app.core.logging import get_logger
from app.core.settings import get_settings
from app.db.models import Asset, CustodyEvent
from app.domain.schemas import (
    ArrivedRequest,
    HandoffRequest,
    LoadedRequest,
    QCRequest,
    ReleaseRequest,
    BurnRequest,
)
from app.domain.types import (
    AssetState,
    EventType,
    EVENT_STATE_TRANSITIONS,
    INFORMATIONAL_EVENTS,
    TERMINAL_STATES,
    VALID_FROM_STATES,
)
from app.repositories.custody_repo import AssetRepository, CustodyEventRepository
from app.repositories.registry_repo import RegistryRepository
from app.services.anchor_service import enqueue_anchor
from app.utils.hashing import compute_event_hash

log = get_logger(__name__)


_DEFAULT_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


class CustodyService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID | None = None) -> None:
        self._db = session
        self._tenant_id = tenant_id or _DEFAULT_TENANT_ID
        self._asset_repo = AssetRepository(session)
        self._event_repo = CustodyEventRepository(session)
        self._registry_repo = RegistryRepository(session)

    # ─── Internal helpers ─────────────────────────────────────────────────────

    def _assert_valid_transition(self, asset: Asset, event_type: EventType) -> None:
        """Raise AssetStateError if the current asset state is not a valid origin for event_type."""
        current = AssetState(asset.state)
        allowed = VALID_FROM_STATES.get(event_type)
        if allowed is None:
            return  # CREATED is handled separately
        if current not in allowed:
            allowed_labels = ", ".join(sorted(s.value for s in allowed))
            raise AssetStateError(
                f"Cannot apply '{event_type}' to asset in state '{current}'. "
                f"Allowed states: [{allowed_labels}]"
            )

    async def _assert_active_wallet(self, pubkey: str) -> None:
        from app.core.errors import WalletNotAllowlistedError
        wallet = await self._registry_repo.get_by_pubkey(pubkey)
        if not wallet or wallet.status != "active" or wallet.tenant_id != self._tenant_id:
            raise WalletNotAllowlistedError(
                f"Wallet '{pubkey}' is not in the active allowlist",
                wallet_pubkey=pubkey,
            )

    async def _get_asset_or_404(self, asset_id: uuid.UUID) -> Asset:
        asset = await self._asset_repo.get_by_id(asset_id)
        if asset is None or asset.tenant_id != self._tenant_id:
            raise NotFoundError(f"Asset '{asset_id}' not found")
        return asset

    async def _get_asset_locked(self, asset_id: uuid.UUID) -> Asset:
        """SELECT FOR UPDATE – use inside a transaction for concurrency safety."""
        asset = await self._asset_repo.get_by_id_for_update(asset_id)
        if asset is None or asset.tenant_id != self._tenant_id:
            raise NotFoundError(f"Asset '{asset_id}' not found")
        return asset

    async def _create_event(
        self,
        asset: Asset,
        event_type: EventType | str,
        from_wallet: str | None,
        to_wallet: str | None,
        location: dict[str, Any] | None,
        data: dict[str, Any],
        new_state: AssetState,
        new_custodian: str | None = None,
        timestamp: datetime | None = None,
    ) -> CustodyEvent:
        ts = timestamp or datetime.now(tz=timezone.utc)

        event_hash = compute_event_hash(
            asset_id=asset.id,
            event_type=event_type,
            from_wallet=from_wallet,
            to_wallet=to_wallet,
            timestamp=ts,
            location=location,
            data=data,
            prev_event_hash=asset.last_event_hash,
        )

        event = await self._event_repo.create(
            asset_id=asset.id,
            event_type=event_type,
            from_wallet=from_wallet,
            to_wallet=to_wallet,
            timestamp=ts,
            location=location,
            data=data,
            prev_event_hash=asset.last_event_hash,
            event_hash=event_hash,
        )

        await self._asset_repo.update_after_event(
            asset_id=asset.id,
            new_state=new_state,
            new_custodian=new_custodian or asset.current_custodian_wallet,
            last_event_hash=event_hash,
        )

        return event

    # ─── Asset creation ───────────────────────────────────────────────────────

    async def create_asset(
        self,
        asset_mint: str,
        product_type: str,
        metadata: dict[str, Any],
        initial_custodian_wallet: str,
    ) -> tuple[Asset, CustodyEvent]:
        # Validate allowlist
        await self._assert_active_wallet(initial_custodian_wallet)

        # Check for duplicate mint
        existing = await self._asset_repo.get_by_mint(asset_mint)
        if existing is not None:
            from app.core.errors import ConflictError
            raise ConflictError(f"Asset with mint '{asset_mint}' already exists")

        now = datetime.now(tz=timezone.utc)

        # Create asset with placeholder last_event_hash (will be filled by event)
        asset = await self._asset_repo.create(
            asset_mint=asset_mint,
            product_type=product_type,
            metadata=metadata,
            initial_custodian_wallet=initial_custodian_wallet,
            state=AssetState.IN_CUSTODY,
            last_event_hash=None,
            tenant_id=self._tenant_id,
        )

        event = await self._create_event(
            asset=asset,
            event_type=EventType.CREATED,
            from_wallet=None,
            to_wallet=initial_custodian_wallet,
            location=None,
            data={},
            new_state=AssetState.IN_CUSTODY,
            new_custodian=initial_custodian_wallet,
            timestamp=now,
        )

        log.info(
            "asset_created",
            asset_id=str(asset.id),
            mint=asset_mint,
            custodian=initial_custodian_wallet,
            event_hash=event.event_hash,
        )
        return asset, event

    async def mint_asset(
        self,
        product_type: str,
        metadata: dict[str, Any],
        initial_custodian_wallet: str,
    ) -> tuple[Asset, CustodyEvent]:
        import asyncio

        # 1. Validate wallet
        wallet = await self._registry_repo.get_by_pubkey(initial_custodian_wallet)
        if not wallet or wallet.status != "active":
            from app.core.errors import WalletNotAllowlistedError
            raise WalletNotAllowlistedError(
                f"Wallet '{initial_custodian_wallet}' is not active or recorded",
                wallet_pubkey=initial_custodian_wallet,
            )

        # 2. Create asset record in DB with PENDING status — blockchain is eventual
        import uuid as _uuid
        placeholder_mint = "pending_" + _uuid.uuid4().hex
        asset = await self._asset_repo.create(
            asset_mint=placeholder_mint,
            product_type=product_type,
            metadata=metadata,
            initial_custodian_wallet=initial_custodian_wallet,
            state=AssetState.IN_CUSTODY,
            last_event_hash=None,
            tenant_id=self._tenant_id,
            blockchain_status="PENDING",
        )
        event = await self._create_event(
            asset=asset,
            event_type=EventType.CREATED,
            from_wallet=None,
            to_wallet=initial_custodian_wallet,
            location=None,
            data={},
            new_state=AssetState.IN_CUSTODY,
            new_custodian=initial_custodian_wallet,
        )

        log.info(
            "asset_pending_mint",
            asset_id=str(asset.id),
            product_type=product_type,
            custodian=initial_custodian_wallet,
        )

        # 3. Fire-and-forget blockchain mint — faults absorbed in BlockchainService
        from app.services.blockchain_service import BlockchainService
        from app.clients.provider_factory import get_blockchain_provider

        blockchain_svc = BlockchainService(
            session=self._db,
            provider=get_blockchain_provider(),
        )
        asyncio.create_task(
            blockchain_svc.mint_asset_onchain(
                asset_id=asset.id,
                tenant_id=self._tenant_id,
                product_type=product_type,
                metadata=metadata,
                owner_pubkey=wallet.wallet_pubkey,
            )
        )

        return asset, event

    # ─── Handoff ──────────────────────────────────────────────────────────────

    async def handoff(
        self, asset_id: uuid.UUID, req: HandoffRequest
    ) -> tuple[Asset, CustodyEvent]:
        # Lock asset row to prevent concurrent handoffs
        asset = await self._get_asset_locked(asset_id)

        self._assert_valid_transition(asset, EventType.HANDOFF)

        await self._assert_active_wallet(req.to_wallet)

        location = req.location.model_dump() if req.location else None
        event = await self._create_event(
            asset=asset,
            event_type=EventType.HANDOFF,
            from_wallet=asset.current_custodian_wallet,
            to_wallet=req.to_wallet,
            location=location,
            data=req.data,
            new_state=AssetState.IN_TRANSIT,
            new_custodian=req.to_wallet,
        )

        # Reload asset to get updated state
        updated_asset = await self._asset_repo.get_by_id(asset_id)
        log.info(
            "handoff_recorded",
            asset_id=str(asset_id),
            from_wallet=asset.current_custodian_wallet,
            to_wallet=req.to_wallet,
            event_hash=event.event_hash,
        )
        return updated_asset, event  # type: ignore

    # ─── Arrived ──────────────────────────────────────────────────────────────

    async def arrived(
        self, asset_id: uuid.UUID, req: ArrivedRequest
    ) -> tuple[Asset, CustodyEvent]:
        asset = await self._get_asset_or_404(asset_id)

        self._assert_valid_transition(asset, EventType.ARRIVED)

        location = req.location.model_dump() if req.location else None
        event = await self._create_event(
            asset=asset,
            event_type=EventType.ARRIVED,
            from_wallet=asset.current_custodian_wallet,
            to_wallet=asset.current_custodian_wallet,
            location=location,
            data=req.data,
            new_state=AssetState.IN_CUSTODY,
        )

        updated_asset = await self._asset_repo.get_by_id(asset_id)
        log.info("arrived_recorded", asset_id=str(asset_id), event_hash=event.event_hash)
        return updated_asset, event  # type: ignore

    # ─── Loaded ───────────────────────────────────────────────────────────────

    async def loaded(
        self, asset_id: uuid.UUID, req: LoadedRequest
    ) -> tuple[Asset, CustodyEvent]:
        asset = await self._get_asset_or_404(asset_id)

        self._assert_valid_transition(asset, EventType.LOADED)

        location = req.location.model_dump() if req.location else None
        event = await self._create_event(
            asset=asset,
            event_type=EventType.LOADED,
            from_wallet=asset.current_custodian_wallet,
            to_wallet=None,
            location=location,
            data=req.data,
            new_state=AssetState.LOADED,
        )

        updated_asset = await self._asset_repo.get_by_id(asset_id)
        log.info("loaded_recorded", asset_id=str(asset_id), event_hash=event.event_hash)
        return updated_asset, event  # type: ignore

    # ─── QC ───────────────────────────────────────────────────────────────────

    async def qc(
        self, asset_id: uuid.UUID, req: QCRequest
    ) -> tuple[Asset, CustodyEvent]:
        asset = await self._get_asset_or_404(asset_id)

        self._assert_valid_transition(asset, EventType.QC)

        result = req.result.lower()
        new_state = AssetState.QC_PASSED if result == "pass" else AssetState.QC_FAILED

        data = {**req.data, "qc_result": result}
        if req.notes:
            data["notes"] = req.notes

        event = await self._create_event(
            asset=asset,
            event_type=EventType.QC,
            from_wallet=asset.current_custodian_wallet,
            to_wallet=None,
            location=None,
            data=data,
            new_state=new_state,
        )

        updated_asset = await self._asset_repo.get_by_id(asset_id)
        log.info("qc_recorded", asset_id=str(asset_id), result=result, event_hash=event.event_hash)
        return updated_asset, event  # type: ignore

    # ─── Release ──────────────────────────────────────────────────────────────

    async def release(
        self, asset_id: uuid.UUID, req: ReleaseRequest, admin_key: str
    ) -> tuple[Asset, CustodyEvent]:
        settings = get_settings()
        if admin_key != settings.TRACE_ADMIN_KEY:
            raise ForbiddenError("Invalid admin key")

        asset = await self._get_asset_locked(asset_id)

        self._assert_valid_transition(asset, EventType.RELEASED)

        event = await self._create_event(
            asset=asset,
            event_type=EventType.RELEASED,
            from_wallet=asset.current_custodian_wallet,
            to_wallet=req.external_wallet,
            location=None,
            data={**req.data, "reason": req.reason},
            new_state=AssetState.RELEASED,
            new_custodian=req.external_wallet,
        )

        updated_asset = await self._asset_repo.get_by_id(asset_id)
        log.info(
            "asset_released",
            asset_id=str(asset_id),
            external_wallet=req.external_wallet,
            event_hash=event.event_hash,
        )
        return updated_asset, event  # type: ignore

    # ─── Burn ─────────────────────────────────────────────────────────────────

    async def burn(
        self, asset_id: uuid.UUID, req: BurnRequest
    ) -> tuple[Asset, CustodyEvent]:
        asset = await self._get_asset_locked(asset_id)

        self._assert_valid_transition(asset, EventType.BURN)

        event = await self._create_event(
            asset=asset,
            event_type=EventType.BURN,
            from_wallet=asset.current_custodian_wallet,
            to_wallet=None,
            location=None,
            data={**req.data, "reason": req.reason},
            new_state=AssetState.BURNED,
        )

        # Here we'd typically also instruct SolanaClient to burn the NFT on chain
        # client = get_solana_client()
        # await client.burn_logistics_asset(asset.asset_mint)

        updated_asset = await self._asset_repo.get_by_id(asset_id)
        log.info(
            "asset_burned",
            asset_id=str(asset_id),
            event_hash=event.event_hash,
        )
        return updated_asset, event  # type: ignore

    # ─── Generic event (DB-driven config) ─────────────────────────────────────

    async def record_event(
        self,
        asset_id: uuid.UUID,
        event_type_slug: str,
        to_wallet: str | None = None,
        location: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        notes: str | None = None,
        result: str | None = None,
        reason: str | None = None,
    ) -> tuple[Asset, CustodyEvent]:
        """
        Generic event recorder driven by EventTypeConfig from DB.
        Validates state transitions using the config's from_states/to_state.
        Informational events don't change state. Custom types fully supported.
        Falls back to hardcoded types.py for system events without DB config.
        """
        from app.repositories.event_type_repo import EventTypeConfigRepository

        event_data = dict(data or {})

        # ── Load event type config from DB ────────────────────────────────────
        etc_repo = EventTypeConfigRepository(self._db)
        config = await etc_repo.get_by_slug(self._tenant_id, event_type_slug)

        # ── Determine behavior from config or fallback to hardcoded ───────────
        if config:
            if not config.is_active:
                raise AssetStateError(f"Event type '{event_type_slug}' is disabled")
            is_informational = config.is_informational
            allowed_from = set(config.from_states) if config.from_states else None
            to_state_str = config.to_state
            needs_wallet = config.requires_wallet
            needs_lock = config.requires_admin or event_type_slug in {"HANDOFF", "RELEASED", "BURN", "DELIVERED", "DAMAGED"}
        else:
            # Fallback to hardcoded types.py for backward compatibility
            is_informational = event_type_slug in {e.value for e in INFORMATIONAL_EVENTS}
            et = EventType(event_type_slug)
            from_set = VALID_FROM_STATES.get(et)
            allowed_from = {s.value for s in from_set} if from_set else None
            to_state_str = EVENT_STATE_TRANSITIONS.get(et, AssetState(event_type_slug)).value if not is_informational else None
            needs_wallet = event_type_slug in {"HANDOFF", "PICKUP", "DELIVERED"}
            needs_lock = event_type_slug in {"HANDOFF", "RELEASED", "BURN", "DELIVERED", "DAMAGED"}

        # ── Wallet validation ─────────────────────────────────────────────────
        if needs_wallet and to_wallet:
            await self._assert_active_wallet(to_wallet)

        # ── Load asset (with lock if needed) ──────────────────────────────────
        if needs_lock:
            asset = await self._get_asset_locked(asset_id)
        else:
            asset = await self._get_asset_or_404(asset_id)

        # ── Validate state transition ─────────────────────────────────────────
        current_state = asset.state
        if allowed_from and current_state not in allowed_from:
            raise AssetStateError(
                f"Cannot apply '{event_type_slug}' to asset in state '{current_state}'. "
                f"Allowed: [{', '.join(sorted(allowed_from))}]"
            )

        # ── Determine new state ───────────────────────────────────────────────
        if is_informational or not to_state_str:
            new_state = AssetState(current_state)
        elif event_type_slug == "QC":
            qc_result = (result or "fail").lower()
            new_state = AssetState.QC_PASSED if qc_result == "pass" else AssetState.QC_FAILED
            event_data["qc_result"] = qc_result
        else:
            new_state = AssetState(to_state_str)

        # ── Enrich event data ─────────────────────────────────────────────────
        if notes:
            event_data["notes"] = notes
        if reason:
            event_data["reason"] = reason
        if result and event_type_slug != "QC":
            event_data["result"] = result

        # ── Determine wallets ─────────────────────────────────────────────────
        from_wallet = asset.current_custodian_wallet
        new_custodian = to_wallet if to_wallet else None

        # Use the slug as event_type string (works for both system and custom)
        event = await self._create_event(
            asset=asset,
            event_type=event_type_slug,
            from_wallet=from_wallet,
            to_wallet=to_wallet,
            location=location,
            data=event_data,
            new_state=new_state,
            new_custodian=new_custodian,
        )

        updated_asset = await self._asset_repo.get_by_id(asset_id)
        log.info(
            "event_recorded",
            asset_id=str(asset_id),
            event_type=event_type_slug,
            new_state=new_state.value,
            event_hash=event.event_hash,
        )
        return updated_asset, event  # type: ignore

    # ─── Query ────────────────────────────────────────────────────────────────

    async def get_asset(self, asset_id: uuid.UUID) -> Asset:
        return await self._get_asset_or_404(asset_id)

    async def list_assets(
        self,
        product_type: str | None = None,
        custodian: str | None = None,
        state: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[Asset], int]:
        return await self._asset_repo.list(
            product_type=product_type,
            custodian=custodian,
            state=state,
            tenant_id=self._tenant_id,
            offset=offset,
            limit=limit,
        )

    async def get_asset_events(
        self, asset_id: uuid.UUID, offset: int = 0, limit: int = 100
    ) -> tuple[list[CustodyEvent], int]:
        await self._get_asset_or_404(asset_id)
        return await self._event_repo.get_by_asset(asset_id, offset=offset, limit=limit)

    async def get_event(self, asset_id: uuid.UUID, event_id: uuid.UUID) -> CustodyEvent:
        await self._get_asset_or_404(asset_id)
        event = await self._event_repo.get_by_id(event_id)
        if event is None or event.asset_id != asset_id:
            raise NotFoundError(f"Event '{event_id}' not found for asset '{asset_id}'")
        return event

    async def trigger_anchor(self, asset_id: uuid.UUID, event_id: uuid.UUID) -> CustodyEvent:
        event = await self.get_event(asset_id, event_id)
        if event.anchored:
            log.info("anchor_already_done", event_id=str(event_id))
            return event
        await enqueue_anchor(event.id)
        log.info("anchor_manually_triggered", event_id=str(event_id))
        return event
