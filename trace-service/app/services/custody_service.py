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
    NotFoundError,
)
from app.core.logging import get_logger
from app.core.settings import get_settings
from app.db.models import Asset, CustodyEvent
from app.domain.types import EventType
from app.domain.schemas import (
    ArrivedRequest,
    HandoffRequest,
    LoadedRequest,
    QCRequest,
    ReleaseRequest,
    BurnRequest,
)
from app.repositories.custody_repo import AssetRepository, CustodyEventRepository
from app.repositories.registry_repo import RegistryRepository
from app.repositories.workflow_repo import WorkflowStateRepository
from app.services.anchor_service import enqueue_anchor
from app.services.workflow_service import WorkflowService
from app.utils.hashing import compute_event_hash

log = get_logger(__name__)


_DEFAULT_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


class CustodyService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID | None = None, current_user: dict | None = None) -> None:
        self._db = session
        self._tenant_id = tenant_id or _DEFAULT_TENANT_ID
        self._current_user = current_user
        self._asset_repo = AssetRepository(session)
        self._event_repo = CustodyEventRepository(session)
        self._registry_repo = RegistryRepository(session)
        self._workflow_svc = WorkflowService(session, self._tenant_id)
        self._state_repo = WorkflowStateRepository(session)

    # ─── Internal helpers ─────────────────────────────────────────────────────

    async def _get_effective_state_slug(self, asset: Asset) -> str:
        """
        Resolve the effective workflow state slug for an asset.
        Uses workflow_state_id first (reliable FK), then falls back to asset.state string.
        """
        if asset.workflow_state_id:
            ws = await self._state_repo.get_by_id(asset.workflow_state_id)
            if ws and ws.tenant_id == self._tenant_id:
                return ws.slug
        return asset.state

    async def _assert_valid_transition(
        self, asset: Asset, event_type: str, qc_result: str | None = None
    ) -> str:
        """
        Validate transition using the workflow engine. Returns the target state slug.
        No hardcoded fallback — workflow must be configured.
        """
        event_type_slug = event_type if isinstance(event_type, str) else str(event_type)
        effective_slug = await self._get_effective_state_slug(asset)

        result = await self._workflow_svc.find_transition_for_event(
            effective_slug, event_type_slug, qc_result=qc_result
        )
        if result:
            _transition, target_state = result
            return target_state.slug

        raise AssetStateError(
            f"No workflow transition found for event '{event_type_slug}' "
            f"from state '{effective_slug}'. Configure transitions in the workflow engine."
        )

    async def _assert_active_wallet(self, pubkey: str) -> None:
        from app.core.errors import WalletNotAllowlistedError
        wallet = await self._registry_repo.get_by_pubkey(pubkey)
        if not wallet or wallet.status != "active" or wallet.tenant_id != self._tenant_id:
            raise WalletNotAllowlistedError(
                f"Wallet '{pubkey}' is not in the active allowlist",
                wallet_pubkey=pubkey,
            )

    async def _assert_current_wallet_active(self, asset: Asset) -> None:
        """Reject events when the asset's current custodian wallet was revoked.

        Used by ALL state-changing methods (handoff/arrived/loaded/qc/release/burn
        and the generic record_event) so behavior is consistent.
        """
        if not asset.current_custodian_wallet:
            return
        current = await self._registry_repo.get_by_pubkey(asset.current_custodian_wallet)
        if (
            current is None
            or current.tenant_id != self._tenant_id
            or current.status != "active"
        ):
            raise AssetStateError(
                f"Current custodian wallet '{asset.current_custodian_wallet}' "
                f"is no longer active. Re-assign the asset before recording new events."
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
        new_state: str,
        new_custodian: str | None = None,
        timestamp: datetime | None = None,
        parent_event_id: uuid.UUID | None = None,
        custody_mode: str | None = None,
    ) -> CustodyEvent:
        ts = timestamp or datetime.now(tz=timezone.utc)

        # Resolve custody_mode: explicit > last event's mode > "segregated"
        # This is shared across typed endpoints (handoff/arrived/loaded/qc/
        # release/burn) and the generic record_event path, so all events
        # for the same asset keep a consistent custody mode unless the
        # caller explicitly changes it.
        resolved_mode = custody_mode
        if resolved_mode is None:
            prior = await self._event_repo.get_last_event_mode(asset.id)
            resolved_mode = prior or "segregated"

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
            tenant_id=self._tenant_id,
            parent_event_id=parent_event_id,
            custody_mode=resolved_mode,
        )

        # Resolve workflow_state_id from the new state slug
        workflow_state_id = None
        ws = await self._workflow_svc.resolve_state_slug(
            str(new_state)
        )
        if ws:
            workflow_state_id = ws.id

        await self._asset_repo.update_after_event(
            asset_id=asset.id,
            new_state=new_state,
            new_custodian=new_custodian or asset.current_custodian_wallet,
            last_event_hash=event_hash,
            workflow_state_id=workflow_state_id,
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

        # Resolve initial state from workflow engine
        ws = await self._workflow_svc.get_initial_state()
        initial_state = ws.slug
        workflow_state_id = ws.id

        now = datetime.now(tz=timezone.utc)

        asset = await self._asset_repo.create(
            asset_mint=asset_mint,
            product_type=product_type,
            metadata=metadata,
            initial_custodian_wallet=initial_custodian_wallet,
            state=initial_state,
            last_event_hash=None,
            tenant_id=self._tenant_id,
            workflow_state_id=workflow_state_id,
        )

        event = await self._create_event(
            asset=asset,
            event_type="CREATED",
            from_wallet=None,
            to_wallet=initial_custodian_wallet,
            location=None,
            data={},
            new_state=initial_state,
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

        # Resolve initial state from workflow engine
        ws = await self._workflow_svc.get_initial_state()
        initial_state = ws.slug
        workflow_state_id = ws.id

        # 2. Create asset record in DB with PENDING status — blockchain is eventual
        import uuid as _uuid
        placeholder_mint = "pending_" + _uuid.uuid4().hex
        asset = await self._asset_repo.create(
            asset_mint=placeholder_mint,
            product_type=product_type,
            metadata=metadata,
            initial_custodian_wallet=initial_custodian_wallet,
            state=initial_state,
            last_event_hash=None,
            tenant_id=self._tenant_id,
            blockchain_status="PENDING",
            workflow_state_id=workflow_state_id,
        )
        event = await self._create_event(
            asset=asset,
            event_type="CREATED",
            from_wallet=None,
            to_wallet=initial_custodian_wallet,
            location=None,
            data={},
            new_state=initial_state,
            new_custodian=initial_custodian_wallet,
        )

        log.info(
            "asset_pending_mint",
            asset_id=str(asset.id),
            product_type=product_type,
            custodian=initial_custodian_wallet,
        )

        # cNFT minting is handled by the router AFTER db.commit()
        # so the blockchain session can see the committed asset.

        return asset, event

    # ─── Handoff ──────────────────────────────────────────────────────────────

    async def handoff(
        self, asset_id: uuid.UUID, req: HandoffRequest
    ) -> tuple[Asset, CustodyEvent]:
        asset = await self._get_asset_locked(asset_id)
        await self._assert_current_wallet_active(asset)
        target_state = await self._assert_valid_transition(asset, "HANDOFF")
        await self._assert_active_wallet(req.to_wallet)

        location = req.location.model_dump() if req.location else None
        event = await self._create_event(
            asset=asset,
            event_type="HANDOFF",
            from_wallet=asset.current_custodian_wallet,
            to_wallet=req.to_wallet,
            location=location,
            data=req.data,
            new_state=target_state,
            new_custodian=req.to_wallet,
        )

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
        asset = await self._get_asset_locked(asset_id)
        await self._assert_current_wallet_active(asset)
        target_state = await self._assert_valid_transition(asset, "ARRIVED")

        location = req.location.model_dump() if req.location else None
        event = await self._create_event(
            asset=asset,
            event_type="ARRIVED",
            from_wallet=asset.current_custodian_wallet,
            to_wallet=asset.current_custodian_wallet,
            location=location,
            data=req.data,
            new_state=target_state,
        )

        updated_asset = await self._asset_repo.get_by_id(asset_id)
        log.info("arrived_recorded", asset_id=str(asset_id), event_hash=event.event_hash)
        return updated_asset, event  # type: ignore

    # ─── Loaded ───────────────────────────────────────────────────────────────

    async def loaded(
        self, asset_id: uuid.UUID, req: LoadedRequest
    ) -> tuple[Asset, CustodyEvent]:
        asset = await self._get_asset_locked(asset_id)
        await self._assert_current_wallet_active(asset)
        target_state = await self._assert_valid_transition(asset, "LOADED")

        location = req.location.model_dump() if req.location else None
        event = await self._create_event(
            asset=asset,
            event_type="LOADED",
            from_wallet=asset.current_custodian_wallet,
            to_wallet=None,
            location=location,
            data=req.data,
            new_state=target_state,
        )

        updated_asset = await self._asset_repo.get_by_id(asset_id)
        log.info("loaded_recorded", asset_id=str(asset_id), event_hash=event.event_hash)
        return updated_asset, event  # type: ignore

    # ─── QC ───────────────────────────────────────────────────────────────────

    async def qc(
        self, asset_id: uuid.UUID, req: QCRequest
    ) -> tuple[Asset, CustodyEvent]:
        asset = await self._get_asset_locked(asset_id)
        await self._assert_current_wallet_active(asset)

        result = req.result.lower()
        target_state = await self._assert_valid_transition(
            asset, "QC", qc_result=result
        )

        data = {**req.data, "qc_result": result}
        if req.notes:
            data["notes"] = req.notes

        event = await self._create_event(
            asset=asset,
            event_type="QC",
            from_wallet=asset.current_custodian_wallet,
            to_wallet=None,
            location=None,
            data=data,
            new_state=target_state,
        )

        updated_asset = await self._asset_repo.get_by_id(asset_id)
        log.info("qc_recorded", asset_id=str(asset_id), result=result, event_hash=event.event_hash)
        return updated_asset, event  # type: ignore

    # ─── Release ──────────────────────────────────────────────────────────────

    async def release(
        self, asset_id: uuid.UUID, req: ReleaseRequest, admin_key: str
    ) -> tuple[Asset, CustodyEvent]:
        import secrets as _secrets
        settings = get_settings()
        if not _secrets.compare_digest(admin_key or "", settings.TRACE_ADMIN_KEY):
            raise ForbiddenError("Invalid admin key")

        asset = await self._get_asset_locked(asset_id)
        await self._assert_current_wallet_active(asset)
        target_state = await self._assert_valid_transition(asset, "RELEASED")

        event = await self._create_event(
            asset=asset,
            event_type="RELEASED",
            from_wallet=asset.current_custodian_wallet,
            to_wallet=req.external_wallet,
            location=None,
            data={**req.data, "reason": req.reason},
            new_state=target_state,
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
        await self._assert_current_wallet_active(asset)
        target_state = await self._assert_valid_transition(asset, "BURN")

        event = await self._create_event(
            asset=asset,
            event_type="BURN",
            from_wallet=asset.current_custodian_wallet,
            to_wallet=None,
            location=None,
            data={**req.data, "reason": req.reason},
            new_state=target_state,
        )

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
        admin_key: str | None = None,
        parent_event_id: uuid.UUID | None = None,
        custody_mode: str | None = None,
    ) -> tuple[Asset, CustodyEvent]:
        """
        Generic event recorder — workflow engine is the primary source of truth.
        1. Looks up WorkflowEventType for metadata (requires_wallet, etc.)
        2. Uses find_transition_for_event() to resolve target state
        3. Falls back to hardcoded types.py only when no workflow data exists

        Sensitive events (HANDOFF, RELEASED, BURN, LOADED, QC) always take a
        SELECT FOR UPDATE lock to prevent concurrent double-writes that would
        break the hash chain.
        """
        event_data = dict(data or {})

        # Normalize the slug to uppercase. Both `EventType` enum values and
        # `WorkflowEventType.slug` are constrained to `^[A-Z0-9_]+$` by the
        # schema, so a client sending "note" used to silently become a
        # state-changing event because the INFORMATIONAL_EVENTS check is
        # case-sensitive. Normalizing here fixes every downstream check.
        if isinstance(event_type_slug, str):
            event_type_slug = event_type_slug.upper()

        # ── 1. Load event type metadata from workflow engine ──────────────────
        wf_event = await self._workflow_svc.get_event_type_by_slug(event_type_slug)

        # Fallback: check INFORMATIONAL_EVENTS set when no DB record exists
        # (e.g. COMPLIANCE_VERIFIED added to enum but not yet seeded in workflow DB)
        from app.domain.types import INFORMATIONAL_EVENTS, EventType as _ET
        _is_info_enum = event_type_slug in {e.value for e in INFORMATIONAL_EVENTS}
        is_informational = wf_event.is_informational if wf_event else _is_info_enum
        needs_wallet = wf_event.requires_wallet if wf_event else False
        needs_lock = (wf_event.requires_admin or wf_event.requires_reason) if wf_event else False

        # Always lock for ANY state-changing event (informational events skip the lock).
        # This covers custom event types not in SENSITIVE_EVENTS too.
        if not is_informational:
            needs_lock = True

        if wf_event and not wf_event.is_active:
            raise AssetStateError(f"Event type '{event_type_slug}' is disabled")

        # ── 1b. Admin key check for events flagged requires_admin ─────────────
        #   Accepts EITHER a valid X-Admin-Key OR the request coming from a
        #   tenant admin / superuser (checked via current_user dict).
        if wf_event and wf_event.requires_admin:
            import secrets as _secrets
            settings = get_settings()
            has_valid_key = bool(admin_key) and _secrets.compare_digest(admin_key, settings.TRACE_ADMIN_KEY)
            caller = getattr(self, '_current_user', None) or {}
            user_perms = caller.get('permissions') or []
            is_admin_user = caller.get('is_superuser') or 'logistics.manage' in user_perms or 'logistics.admin' in user_perms
            if not (has_valid_key or is_admin_user):
                raise ForbiddenError(
                    f"Event '{event_type_slug}' requires admin privileges or a valid X-Admin-Key header"
                )

        # ── 1c. Reason required when flagged ──────────────────────────────────
        if wf_event and wf_event.requires_reason and not reason:
            raise AssetStateError(
                f"Event '{event_type_slug}' requires a non-empty reason"
            )

        # ── 1d. Notes required when flagged ───────────────────────────────────
        if wf_event and getattr(wf_event, "requires_notes", False) and not notes:
            raise AssetStateError(
                f"Event '{event_type_slug}' requires non-empty notes"
            )

        # ── 2. Wallet validation ──────────────────────────────────────────────
        # Skip allowlist check for RELEASED so external (non-allowlisted) wallets work.
        if to_wallet and event_type_slug.upper() != "RELEASED":
            await self._assert_active_wallet(to_wallet)

        # ── 3. Load asset ─────────────────────────────────────────────────────
        if needs_lock:
            asset = await self._get_asset_locked(asset_id)
        else:
            asset = await self._get_asset_or_404(asset_id)

        # ── 3b. Reject events when current custodian wallet was revoked ──────
        # Applies to ALL events, including informational — a revoked wallet must
        # not be able to log anything (photos, comments, etc.) against the asset.
        await self._assert_current_wallet_active(asset)

        # ── 4. Resolve target state via workflow engine ───────────────────────
        if is_informational:
            new_state = asset.state
        else:
            # Try to find a matching transition; if none exists, record the
            # event without changing state (free/fortuitous event).
            effective_slug = await self._get_effective_state_slug(asset)
            result_transition = await self._workflow_svc.find_transition_for_event(
                effective_slug, event_type_slug, qc_result=result
            )
            if result_transition:
                _transition, target_state = result_transition
                new_state = target_state.slug
            else:
                # Check for free move (MOVE_TO_<state_slug>)
                if event_type_slug.upper().startswith("MOVE_TO_"):
                    target_slug = event_type_slug[8:].lower()  # strip "MOVE_TO_"
                    target_ws = await self._workflow_svc.resolve_state_slug(target_slug)
                    if target_ws and target_ws.tenant_id == self._tenant_id:
                        new_state = target_ws.slug
                    else:
                        raise AssetStateError(f"State '{target_slug}' not found in workflow")
                else:
                    # No transition found — record event without state change
                    new_state = asset.state

        # ── 5. Enrich event data ──────────────────────────────────────────────
        if notes:
            event_data["notes"] = notes
        if reason:
            event_data["reason"] = reason
        if result:
            event_data["result"] = result

        # ── 6. Resolve parent_event_id (hierarchical timeline) ────────────────
        # Informational events (NOTE, INSPECTION, COMPLIANCE_VERIFIED, etc.)
        # auto-link as children of the most recent ROOT event for this asset.
        # Caller can override by passing parent_event_id explicitly. State
        # transitions are always roots and ignore the field.
        resolved_parent_id = None
        if is_informational:
            if parent_event_id is not None:
                resolved_parent_id = parent_event_id
            else:
                last_root = await self._event_repo.get_last_root_event(asset_id)
                if last_root is not None:
                    resolved_parent_id = last_root.id

        # ── 7. Create event ───────────────────────────────────────────────────
        # custody_mode is resolved inside _create_event (explicit > prior > 'segregated')
        from_wallet = asset.current_custodian_wallet
        new_custodian = to_wallet if to_wallet else None

        event = await self._create_event(
            asset=asset,
            event_type=event_type_slug,
            from_wallet=from_wallet,
            to_wallet=to_wallet,
            location=location,
            data=event_data,
            new_state=new_state,
            new_custodian=new_custodian,
            parent_event_id=resolved_parent_id,
            custody_mode=custody_mode,
        )

        updated_asset = await self._asset_repo.get_by_id(asset_id)
        log.info(
            "event_recorded",
            asset_id=str(asset_id),
            event_type=event_type_slug,
            new_state=new_state,
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
