"""Custody router — assets and custody events."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, Query, Request, status
from fastapi.responses import ORJSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError
from app.core.logging import get_logger
from app.db.session import get_db_session
from app.domain.schemas import (
    ArrivedRequest,
    AssetCreate,
    AssetMintRequest,
    AssetListResponse,
    AssetResponse,
    CustodyEventListResponse,
    CustodyEventResponse,
    HandoffRequest,
    LoadedRequest,
    QCRequest,
    ReleaseRequest,
    BurnRequest,
)
from app.api.deps import get_tenant_id
from app.services.anchor_service import enqueue_anchor
from app.services.custody_service import CustodyService

log = get_logger(__name__)
router = APIRouter(prefix="/assets", tags=["custody"])


def _asset_resp(asset) -> dict:
    return AssetResponse.model_validate(asset).model_dump(mode="json")


def _event_resp(event) -> dict:
    return CustodyEventResponse.model_validate(event).model_dump(mode="json")


async def _idempotent_post(
    idempotency_key: str | None,
    namespace: str,
    handler,
) -> tuple[bool, dict]:
    """
    Returns (was_cached, result_dict).
    Handles idempotency bookkeeping around `handler` coroutine.
    `handler` must be a zero-arg coroutine that returns a dict.
    """
    if not idempotency_key:
        result = await handler()
        return False, result

    import redis.asyncio as aioredis
    from app.core.settings import get_settings
    from app.utils.idempotency import IdempotencyStore

    redis_client = aioredis.from_url(get_settings().REDIS_URL)
    store = IdempotencyStore(redis_client)

    try:
        cached = await store.get_cached_response(idempotency_key, namespace=namespace)
        if cached:
            if cached.get("__processing__"):
                raise ConflictError("Request is still being processed")
            return True, cached

        acquired = await store.mark_processing(idempotency_key, namespace=namespace)
        if not acquired:
            raise ConflictError("Concurrent duplicate request in progress")

        try:
            result = await handler()
            await store.save_response(idempotency_key, namespace=namespace, response=result)
            return False, result
        except Exception:
            await store.delete(idempotency_key, namespace=namespace)
            raise
    finally:
        await redis_client.aclose()


# ─── Assets ───────────────────────────────────────────────────────────────────

@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new asset and genesis custody event",
)
async def create_asset(
    request: Request,
    body: AssetCreate,
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> ORJSONResponse:
    idempotency_key = getattr(request.state, "idempotency_key", None)
    svc = CustodyService(db, tenant_id=tenant_id)

    async def _handler():
        asset, event = await svc.create_asset(
            asset_mint=body.asset_mint,
            product_type=body.product_type,
            metadata=body.metadata,
            initial_custodian_wallet=body.initial_custodian_wallet,
        )
        await db.commit()
        await enqueue_anchor(event.id)
        return {"asset": _asset_resp(asset), "event": _event_resp(event)}

    was_cached, result = await _idempotent_post(idempotency_key, "create_asset", _handler)
    if not was_cached:
        log.info(
            "custody_event",
            action="create",
            asset_id=result["asset"]["id"],
            user_id=request.headers.get("X-User-Id", "unknown"),
            tenant_id=str(tenant_id),
        )
    code = status.HTTP_200_OK if was_cached else status.HTTP_201_CREATED
    return ORJSONResponse(status_code=code, content=result)


@router.post(
    "/mint",
    status_code=status.HTTP_201_CREATED,
    summary="Mint a new NFT representing a logistics load",
)
async def mint_asset(
    request: Request,
    body: AssetMintRequest,
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> ORJSONResponse:
    idempotency_key = getattr(request.state, "idempotency_key", None)
    svc = CustodyService(db, tenant_id=tenant_id)

    async def _handler():
        asset, event = await svc.mint_asset(
            product_type=body.product_type,
            metadata=body.metadata,
            initial_custodian_wallet=body.initial_custodian_wallet,
        )
        await db.commit()
        await enqueue_anchor(event.id)
        return {"asset": _asset_resp(asset), "event": _event_resp(event)}

    was_cached, result = await _idempotent_post(idempotency_key, "mint_asset", _handler)
    if not was_cached:
        log.info(
            "custody_event",
            action="mint",
            asset_id=result["asset"]["id"],
            user_id=request.headers.get("X-User-Id", "unknown"),
            tenant_id=str(tenant_id),
        )
    code = status.HTTP_200_OK if was_cached else status.HTTP_201_CREATED
    return ORJSONResponse(status_code=code, content=result)


@router.get("", summary="List assets with optional filters")
async def list_assets(
    product_type: str | None = Query(None),
    custodian: str | None = Query(None),
    state: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> ORJSONResponse:
    svc = CustodyService(db, tenant_id=tenant_id)
    assets, total = await svc.list_assets(
        product_type=product_type, custodian=custodian, state=state, offset=offset, limit=limit
    )
    items = [_asset_resp(a) for a in assets]
    return ORJSONResponse(content={"items": items, "total": total})


@router.get("/{asset_id}", summary="Get asset by ID")
async def get_asset(
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> ORJSONResponse:
    svc = CustodyService(db, tenant_id=tenant_id)
    asset = await svc.get_asset(asset_id)
    return ORJSONResponse(content=_asset_resp(asset))


@router.get("/{asset_id}/events", summary="List custody events for asset")
async def get_events(
    asset_id: uuid.UUID,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> ORJSONResponse:
    svc = CustodyService(db, tenant_id=tenant_id)
    events, total = await svc.get_asset_events(asset_id, offset=offset, limit=limit)
    items = [_event_resp(e) for e in events]
    return ORJSONResponse(content={"items": items, "total": total})


# ─── Custody Events ───────────────────────────────────────────────────────────

@router.post("/{asset_id}/events/handoff", status_code=status.HTTP_201_CREATED, summary="Handoff asset to another wallet")
async def handoff(
    request: Request,
    asset_id: uuid.UUID,
    body: HandoffRequest,
    x_user_id: int = Header(..., alias="X-User-Id", description="User ID (Master = 1)"),
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> ORJSONResponse:
    from app.core.errors import ForbiddenError
    if x_user_id != 1:
        raise ForbiddenError("Only Master Account (ID 1) can authorize transfers")

    idempotency_key = getattr(request.state, "idempotency_key", None)
    svc = CustodyService(db, tenant_id=tenant_id)

    async def _handler():
        asset, event = await svc.handoff(asset_id, body)
        await db.commit()
        await enqueue_anchor(event.id)
        return {"asset": _asset_resp(asset), "event": _event_resp(event)}

    was_cached, result = await _idempotent_post(
        idempotency_key, f"handoff:{asset_id}", _handler
    )
    if not was_cached:
        log.info(
            "custody_event",
            action="handoff",
            asset_id=str(asset_id),
            user_id=request.headers.get("X-User-Id", "unknown"),
            tenant_id=str(tenant_id),
        )
    code = status.HTTP_200_OK if was_cached else status.HTTP_201_CREATED
    return ORJSONResponse(status_code=code, content=result)


@router.post("/{asset_id}/events/arrived", status_code=status.HTTP_201_CREATED, summary="Mark asset as arrived")
async def arrived(
    asset_id: uuid.UUID,
    body: ArrivedRequest,
    x_user_id: int = Header(..., alias="X-User-Id", description="User ID (Master = 1)"),
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> ORJSONResponse:
    from app.core.errors import ForbiddenError
    if x_user_id != 1:
        raise ForbiddenError("Only Master Account (ID 1) can authorize transfers")

    svc = CustodyService(db, tenant_id=tenant_id)
    asset, event = await svc.arrived(asset_id, body)
    await db.commit()
    await enqueue_anchor(event.id)
    log.info(
        "custody_event",
        action="arrived",
        asset_id=str(asset_id),
        user_id=str(x_user_id),
        tenant_id=str(tenant_id),
    )
    return ORJSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"asset": _asset_resp(asset), "event": _event_resp(event)},
    )


@router.post("/{asset_id}/events/loaded", status_code=status.HTTP_201_CREATED, summary="Mark asset as loaded")
async def loaded(
    asset_id: uuid.UUID,
    body: LoadedRequest,
    x_user_id: int = Header(..., alias="X-User-Id", description="User ID (Master = 1)"),
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> ORJSONResponse:
    from app.core.errors import ForbiddenError
    if x_user_id != 1:
        raise ForbiddenError("Only Master Account (ID 1) can authorize transfers")

    svc = CustodyService(db, tenant_id=tenant_id)
    asset, event = await svc.loaded(asset_id, body)
    await db.commit()
    await enqueue_anchor(event.id)
    log.info(
        "custody_event",
        action="loaded",
        asset_id=str(asset_id),
        user_id=str(x_user_id),
        tenant_id=str(tenant_id),
    )
    return ORJSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"asset": _asset_resp(asset), "event": _event_resp(event)},
    )


@router.post("/{asset_id}/events/qc", status_code=status.HTTP_201_CREATED, summary="Record QC result")
async def qc(
    asset_id: uuid.UUID,
    body: QCRequest,
    x_user_id: int = Header(..., alias="X-User-Id", description="User ID (Master = 1)"),
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> ORJSONResponse:
    from app.core.errors import ForbiddenError
    if x_user_id != 1:
        raise ForbiddenError("Only Master Account (ID 1) can authorize transfers")

    svc = CustodyService(db, tenant_id=tenant_id)
    asset, event = await svc.qc(asset_id, body)
    await db.commit()
    await enqueue_anchor(event.id)
    log.info(
        "custody_event",
        action="qc",
        asset_id=str(asset_id),
        user_id=str(x_user_id),
        tenant_id=str(tenant_id),
    )
    return ORJSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"asset": _asset_resp(asset), "event": _event_resp(event)},
    )


@router.post(
    "/{asset_id}/events/release",
    status_code=status.HTTP_201_CREATED,
    summary="Release asset to external wallet (admin only)",
)
async def release(
    request: Request,
    asset_id: uuid.UUID,
    body: ReleaseRequest,
    x_user_id: int = Header(..., alias="X-User-Id", description="User ID (Master = 1)"),
    x_admin_key: str | None = Header(None, alias="X-Admin-Key", description="Admin secret key"),
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> ORJSONResponse:
    from app.core.errors import ForbiddenError
    from app.core.settings import get_settings
    if x_user_id != 1:
        raise ForbiddenError("Only Master Account (ID 1) can authorize transfers")
    if x_admin_key != get_settings().TRACE_ADMIN_KEY:
        raise ForbiddenError("Invalid admin key")

    idempotency_key = getattr(request.state, "idempotency_key", None)
    svc = CustodyService(db, tenant_id=tenant_id)

    async def _handler():
        from app.core.settings import get_settings
        asset, event = await svc.release(asset_id, body, admin_key=get_settings().TRACE_ADMIN_KEY)
        await db.commit()
        await enqueue_anchor(event.id)
        return {"asset": _asset_resp(asset), "event": _event_resp(event)}

    was_cached, result = await _idempotent_post(
        idempotency_key, f"release:{asset_id}", _handler
    )
    if not was_cached:
        log.info(
            "custody_event",
            action="release",
            asset_id=str(asset_id),
            user_id=request.headers.get("X-User-Id", "unknown"),
            tenant_id=str(tenant_id),
        )
    code = status.HTTP_200_OK if was_cached else status.HTTP_201_CREATED
    return ORJSONResponse(status_code=code, content=result)


@router.post(
    "/{asset_id}/events/burn",
    status_code=status.HTTP_201_CREATED,
    summary="Burn asset (mark as consumed/final destination)",
)
async def burn(
    request: Request,
    asset_id: uuid.UUID,
    body: BurnRequest,
    x_user_id: int = Header(..., alias="X-User-Id", description="User ID (Master = 1)"),
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> ORJSONResponse:
    from app.core.errors import ForbiddenError
    if x_user_id != 1:
        raise ForbiddenError("Only Master Account (ID 1) can authorize transfers/burns")

    idempotency_key = getattr(request.state, "idempotency_key", None)
    svc = CustodyService(db, tenant_id=tenant_id)

    async def _handler():
        asset, event = await svc.burn(asset_id, body)
        await db.commit()
        await enqueue_anchor(event.id)
        return {"asset": _asset_resp(asset), "event": _event_resp(event)}

    was_cached, result = await _idempotent_post(
        idempotency_key, f"burn:{asset_id}", _handler
    )
    if not was_cached:
        log.info(
            "custody_event",
            action="burn",
            asset_id=str(asset_id),
            user_id=request.headers.get("X-User-Id", "unknown"),
            tenant_id=str(tenant_id),
        )
    code = status.HTTP_200_OK if was_cached else status.HTTP_201_CREATED
    return ORJSONResponse(status_code=code, content=result)


@router.post(
    "/{asset_id}/events/{event_id}/anchor",
    summary="Manually trigger Solana anchoring for a specific event",
)
async def anchor_event(
    asset_id: uuid.UUID,
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> ORJSONResponse:
    svc = CustodyService(db, tenant_id=tenant_id)
    event = await svc.trigger_anchor(asset_id, event_id)
    return ORJSONResponse(content=_event_resp(event))
