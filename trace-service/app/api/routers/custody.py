"""Custody router — assets and custody events."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Header, Query, Request, UploadFile, status
from fastapi.responses import ORJSONResponse
from starlette.responses import Response
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
    GenericEventRequest,
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


# ─── Public metadata endpoint (no auth) — used as NFT metadata URI ───────────

@router.get(
    "/{asset_id}/metadata.json",
    summary="Public NFT metadata in Metaplex standard format",
    tags=["public"],
)
async def get_nft_metadata(
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    """Returns Metaplex-compatible metadata JSON for on-chain NFTs."""
    from app.core.settings import get_settings
    from app.repositories.custody_repo import AssetRepository

    repo = AssetRepository(db)
    asset = await repo.get_by_id(asset_id)
    if not asset:
        return ORJSONResponse(status_code=404, content={"error": "Asset not found"})

    meta = asset.metadata_ or {}
    settings = get_settings()
    base_url = settings.PUBLIC_BASE_URL.rstrip("/")

    # Build Metaplex-standard metadata
    # Image: user-provided or DiceBear generated
    image = meta.get("image_url") or (
        f"https://api.dicebear.com/9.x/shapes/svg"
        f"?seed={asset_id}&backgroundColor=6366f1,3b82f6,22c55e,f59e0b,ef4444"
    )

    # Attributes in Metaplex format
    skip = {"name", "description", "symbol", "image_url", "external_url"}
    field_labels = {
        "product_type": "Tipo de Producto", "weight": "Peso",
        "weight_unit": "Unidad de Peso", "quality_grade": "Calidad",
        "origin": "Origen", "metadata_hash": "Hash de Integridad",
        "batch_number": "Número de Lote", "supplier": "Proveedor",
        "variety": "Variedad", "humidity": "Humedad",
    }
    attributes = [{"trait_type": "Tipo de Producto", "value": asset.product_type}]
    for key, val in meta.items():
        if key in skip or val is None or val == "":
            continue
        label = field_labels.get(key, key.replace("_", " ").title())
        attributes.append({"trait_type": label, "value": str(val)})

    return ORJSONResponse(content={
        "name": meta.get("name", asset.product_type),
        "symbol": "TRC",
        "description": meta.get("description", f"Carga trazable: {asset.product_type}"),
        "image": image,
        "external_url": f"{base_url}/api/v1/assets/{asset_id}/metadata.json",
        "attributes": attributes,
        "properties": {
            "category": "logistics",
            "creators": [],
            "files": [{"uri": image, "type": "image/svg+xml"}],
        },
    })


def _asset_resp(asset) -> dict:
    return AssetResponse.model_validate(asset).model_dump(mode="json")


def _event_resp(event) -> dict:
    return CustodyEventResponse.model_validate(event).model_dump(mode="json")


# Module-level Redis client — singleton, reused across requests, avoids
# the TIME_WAIT churn that came from creating/closing per request.
_idempotency_redis = None


async def _get_idempotency_redis():
    global _idempotency_redis
    if _idempotency_redis is None:
        import redis.asyncio as aioredis
        from app.core.settings import get_settings
        _idempotency_redis = aioredis.from_url(get_settings().REDIS_URL)
    return _idempotency_redis


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

    from app.utils.idempotency import IdempotencyStore

    redis_client = await _get_idempotency_redis()
    store = IdempotencyStore(redis_client)

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

        # Mint cNFT AFTER commit so the blockchain session can see the asset
        try:
            from app.services.blockchain_service import BlockchainService
            from app.clients.provider_factory import get_blockchain_provider
            from app.db.session import get_db

            async with get_db() as mint_session:
                mint_svc = BlockchainService(
                    session=mint_session,
                    provider=get_blockchain_provider(),
                )
                await mint_svc.mint_asset_onchain(
                    asset_id=asset.id,
                    tenant_id=tenant_id,
                    product_type=body.product_type,
                    metadata=body.metadata,
                    owner_pubkey=body.initial_custodian_wallet,
                )
        except Exception as exc:
            log.warning("cnft_mint_post_commit_failed", asset_id=str(asset.id), exc=str(exc))
            # Mark asset as FAILED so the retry worker / UI can detect the inconsistency.
            try:
                async with get_db() as fail_session:
                    from app.repositories.custody_repo import AssetRepository
                    repo = AssetRepository(fail_session)
                    await repo.update_blockchain_fields(
                        asset_id=asset.id,
                        blockchain_status="FAILED",
                        blockchain_error=str(exc)[:500],
                    )
                    await fail_session.commit()
            except Exception as inner_exc:
                log.error("mint_failed_status_update_error", asset_id=str(asset.id), exc=str(inner_exc))

        # Re-read asset from a fresh session to get updated blockchain fields
        async with get_db() as read_session:
            from app.repositories.custody_repo import AssetRepository
            fresh_asset = await AssetRepository(read_session).get_by_id(asset.id)
            if fresh_asset:
                return {"asset": _asset_resp(fresh_asset), "event": _event_resp(event)}
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
    x_user_id: str = Header(..., alias="X-User-Id", description="User ID"),
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> ORJSONResponse:
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
    x_user_id: str = Header(..., alias="X-User-Id", description="User ID"),
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> ORJSONResponse:
    # Auth: any authenticated user can perform custody events

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
    x_user_id: str = Header(..., alias="X-User-Id", description="User ID"),
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> ORJSONResponse:
    # Auth: any authenticated user can perform custody events

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
    x_user_id: str = Header(..., alias="X-User-Id", description="User ID"),
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> ORJSONResponse:
    # Auth: any authenticated user can perform custody events

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
    x_user_id: str = Header(..., alias="X-User-Id", description="User ID"),
    x_admin_key: str | None = Header(None, alias="X-Admin-Key", description="Admin secret key"),
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> ORJSONResponse:
    import secrets as _secrets
    from app.core.errors import ForbiddenError
    from app.core.settings import get_settings
    if not _secrets.compare_digest(x_admin_key or "", get_settings().TRACE_ADMIN_KEY):
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
    x_user_id: str = Header(..., alias="X-User-Id", description="User ID"),
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> ORJSONResponse:

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
        # Auto-generate EUDR compliance certificate if a ready record exists
        await _try_auto_certificate(asset_id, tenant_id)

    code = status.HTTP_200_OK if was_cached else status.HTTP_201_CREATED
    return ORJSONResponse(status_code=code, content=result)


async def _try_auto_certificate(asset_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
    """Fire-and-forget: check compliance-service for a ready record and auto-generate certificate."""
    try:
        import httpx
        from app.core.settings import get_settings
        settings = get_settings()
        base = settings.COMPLIANCE_SERVICE_URL.rstrip("/")

        async with httpx.AsyncClient(timeout=15.0) as http:
            # 1. Get compliance records for this asset
            resp = await http.get(
                f"{base}/api/v1/compliance/assets/{asset_id}",
                headers={"X-Tenant-Id": str(tenant_id), "X-Service-Token": settings.S2S_SERVICE_TOKEN},
            )
            if resp.status_code != 200:
                return

            records = resp.json()
            if not records:
                return

            for record in records:
                rid = record.get("id")
                status_val = record.get("compliance_status", "")

                # 2. Validate the record first (this persists the status)
                await http.get(
                    f"{base}/api/v1/compliance/records/{rid}/validate",
                    headers={"X-Tenant-Id": str(tenant_id), "X-Service-Token": settings.S2S_SERVICE_TOKEN},
                )

                # 3. Re-check status
                rec_resp = await http.get(
                    f"{base}/api/v1/compliance/records/{rid}",
                    headers={"X-Tenant-Id": str(tenant_id), "X-Service-Token": settings.S2S_SERVICE_TOKEN},
                )
                if rec_resp.status_code != 200:
                    continue
                updated = rec_resp.json()
                status_val = updated.get("compliance_status", "")

                if status_val not in ("ready", "declared", "compliant"):
                    log.info("auto_cert_skipped", asset_id=str(asset_id), record_id=rid, status=status_val)
                    continue

                # 4. Check if certificate already exists
                cert_resp = await http.get(
                    f"{base}/api/v1/compliance/records/{rid}/certificate",
                    headers={"X-Tenant-Id": str(tenant_id), "X-Service-Token": settings.S2S_SERVICE_TOKEN},
                )
                if cert_resp.status_code == 200:
                    existing = cert_resp.json()
                    if existing.get("status") == "active":
                        log.info("auto_cert_exists", asset_id=str(asset_id), cert=existing.get("certificate_number"))
                        continue

                # 5. Generate certificate
                gen_resp = await http.post(
                    f"{base}/api/v1/compliance/records/{rid}/certificate",
                    headers={"X-Tenant-Id": str(tenant_id), "X-Service-Token": settings.S2S_SERVICE_TOKEN},
                )
                if gen_resp.status_code in (200, 201):
                    cert_data = gen_resp.json()
                    log.info(
                        "auto_cert_generated",
                        asset_id=str(asset_id),
                        record_id=rid,
                        certificate_number=cert_data.get("certificate_number"),
                    )
                else:
                    log.warning("auto_cert_failed", asset_id=str(asset_id), record_id=rid, status=gen_resp.status_code, body=gen_resp.text[:200])

    except Exception as exc:
        log.warning("auto_cert_error", asset_id=str(asset_id), exc=str(exc))


# ─── Generic Event Endpoint (Phase 1A) ────────────────────────────────────────

@router.post(
    "/{asset_id}/events",
    status_code=status.HTTP_201_CREATED,
    summary="Record any custody event (generic endpoint for all event types)",
)
async def record_event(
    request: Request,
    asset_id: uuid.UUID,
    body: GenericEventRequest,
    x_user_id: str = Header(..., alias="X-User-Id", description="User ID"),
    x_admin_key: str | None = Header(None, alias="X-Admin-Key", description="Admin key for sensitive events"),
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> ORJSONResponse:
    idempotency_key = getattr(request.state, "idempotency_key", None)
    svc = CustodyService(db, tenant_id=tenant_id)

    location = body.location.model_dump() if body.location else None

    async def _handler():
        asset, event = await svc.record_event(
            asset_id=asset_id,
            event_type_slug=str(body.event_type),
            to_wallet=body.to_wallet,
            location=location,
            data=body.data,
            notes=body.notes,
            result=body.result,
            reason=body.reason,
            admin_key=x_admin_key,
        )
        await db.commit()
        await enqueue_anchor(event.id)
        return {"asset": _asset_resp(asset), "event": _event_resp(event)}

    was_cached, result = await _idempotent_post(
        idempotency_key, f"event:{asset_id}:{body.event_type}", _handler
    )
    if not was_cached:
        log.info(
            "custody_event",
            action=str(body.event_type),
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


@router.post(
    "/{asset_id}/remint",
    summary="Re-mint blockchain cNFT for an asset stuck in pending_* state",
)
async def remint_asset(
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> ORJSONResponse:
    """Re-trigger blockchain minting for assets that failed or are stuck."""
    svc = CustodyService(db, tenant_id=tenant_id)
    asset = await svc.get_asset(asset_id)

    try:
        from app.services.blockchain_service import BlockchainService
        from app.clients.provider_factory import get_blockchain_provider
        from app.db.session import get_db

        async with get_db() as mint_session:
            mint_svc = BlockchainService(
                session=mint_session,
                provider=get_blockchain_provider(),
            )
            await mint_svc.mint_asset_onchain(
                asset_id=asset.id,
                tenant_id=tenant_id,
                product_type=asset.product_type,
                metadata=asset.metadata_,
                owner_pubkey=asset.current_custodian_wallet,
            )

        async with get_db() as read_session:
            from app.repositories.custody_repo import AssetRepository
            fresh = await AssetRepository(read_session).get_by_id(asset.id)
            if fresh:
                return ORJSONResponse(content=_asset_resp(fresh))
    except Exception as exc:
        log.error("remint_failed", asset_id=str(asset_id), exc=str(exc))
        return ORJSONResponse(
            status_code=500,
            content={"detail": f"Remint failed: {exc}"},
        )
    return ORJSONResponse(content=_asset_resp(asset))


@router.post("/assets/{asset_id}/events/{event_id}/evidence")
async def upload_evidence(
    asset_id: uuid.UUID,
    event_id: uuid.UUID,
    file: UploadFile = File(...),
    evidence_type: str = Query("photo", pattern="^(photo|signature|document)$"),
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> ORJSONResponse:
    """Upload proof-of-delivery evidence via media-service and store reference."""
    import hashlib
    from app.clients.media_client import upload_file as media_upload

    svc = CustodyService(db, tenant_id=tenant_id)
    await svc.get_event(asset_id, event_id)

    content = await file.read()
    evidence_hash = hashlib.sha256(content).hexdigest()

    # Upload to media-service
    media_file = await media_upload(
        tenant_id=str(tenant_id),
        file_bytes=content,
        filename=file.filename or f"evidence-{event_id}.bin",
        content_type=file.content_type or "application/octet-stream",
        category="custody_proof",
        document_type=evidence_type,
        title=f"Evidencia {evidence_type} — evento {str(event_id)[:8]}",
    )

    evidence_url = media_file["url"] if media_file else None
    media_file_id = media_file["id"] if media_file else None

    # Update event with media reference
    from sqlalchemy import update as sa_update
    from app.db.models import CustodyEvent
    await db.execute(
        sa_update(CustodyEvent)
        .where(CustodyEvent.id == event_id)
        .values(
            evidence_url=evidence_url,
            evidence_hash=evidence_hash,
            evidence_type=evidence_type,
        )
    )
    await db.commit()

    return ORJSONResponse(content={
        "event_id": str(event_id),
        "media_file_id": media_file_id,
        "evidence_url": evidence_url,
        "evidence_hash": evidence_hash,
        "evidence_type": evidence_type,
    })


# ─── Event Documents (upload + link media to events) ────────────────────────


@router.post(
    "/assets/{asset_id}/events/{event_id}/documents",
    status_code=status.HTTP_201_CREATED,
)
async def upload_and_link_documents(
    asset_id: uuid.UUID,
    event_id: uuid.UUID,
    files: list[UploadFile] = File(...),
    document_type: str = Query(..., min_length=1, max_length=100),
    title: str | None = Query(None, max_length=200),
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    x_user_id: str = Header("1", alias="X-User-Id"),
) -> ORJSONResponse:
    """Upload files to media library AND link them to a custody event."""
    from app.services.document_service import MediaService, DocumentLinkService

    svc = CustodyService(db, tenant_id=tenant_id)
    event = await svc.get_event(asset_id, event_id)

    media_svc = MediaService(db, tenant_id)
    link_svc = DocumentLinkService(db, tenant_id)
    results = []
    for f in files:
        mf = await media_svc.upload_file(
            file=f,
            category="event_document",
            document_type=document_type,
            title=title,
            uploaded_by=x_user_id,
        )
        link = await link_svc.link_file_to_event(
            event_id=event_id,
            asset_id=asset_id,
            media_file_id=mf.id,
            document_type=document_type,
            linked_by=x_user_id,
        )
        results.append(_link_resp(link, mf))

    await db.commit()
    return ORJSONResponse(content={"documents": results}, status_code=201)


@router.post(
    "/assets/{asset_id}/events/{event_id}/documents/link",
    status_code=status.HTTP_201_CREATED,
)
async def link_existing_media(
    asset_id: uuid.UUID,
    event_id: uuid.UUID,
    media_file_id: uuid.UUID = Query(...),
    document_type: str = Query(..., min_length=1, max_length=100),
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    x_user_id: str = Header("1", alias="X-User-Id"),
) -> ORJSONResponse:
    """Link an existing media file to a custody event (no upload needed)."""
    from app.services.document_service import MediaService, DocumentLinkService
    from fastapi import HTTPException

    svc = CustodyService(db, tenant_id=tenant_id)
    await svc.get_event(asset_id, event_id)

    media_svc = MediaService(db, tenant_id)
    mf = await media_svc.get_file(media_file_id)
    if not mf:
        raise HTTPException(status_code=404, detail="Media file not found")

    link_svc = DocumentLinkService(db, tenant_id)
    link = await link_svc.link_file_to_event(
        event_id=event_id,
        asset_id=asset_id,
        media_file_id=mf.id,
        document_type=document_type,
        linked_by=x_user_id,
    )
    await db.commit()
    return ORJSONResponse(content=_link_resp(link, mf), status_code=201)


@router.get("/assets/{asset_id}/events/{event_id}/documents")
async def list_event_documents(
    asset_id: uuid.UUID,
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> ORJSONResponse:
    """List all documents linked to a custody event with completeness status."""
    from app.services.document_service import DocumentLinkService

    svc = CustodyService(db, tenant_id=tenant_id)
    event = await svc.get_event(asset_id, event_id)

    link_svc = DocumentLinkService(db, tenant_id)
    links = await link_svc.list_event_documents(event_id)

    compliance_active = await _is_compliance_active(tenant_id)
    completeness = await link_svc.check_completeness(event_id, event.event_type, compliance_active)

    return ORJSONResponse(content={
        "documents": [_link_resp(link, link.media_file) for link in links],
        "completeness": completeness,
    })


@router.delete(
    "/assets/{asset_id}/events/{event_id}/documents/{link_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def unlink_event_document(
    asset_id: uuid.UUID,
    event_id: uuid.UUID,
    link_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """Unlink a document from a custody event (does NOT delete the media file)."""
    from app.services.document_service import DocumentLinkService
    from fastapi import HTTPException

    link_svc = DocumentLinkService(db, tenant_id)
    deleted = await link_svc.unlink(link_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document link not found")
    await db.commit()
    return Response(status_code=204)


@router.get("/assets/{asset_id}/document-requirements")
async def get_document_requirements(
    asset_id: uuid.UUID,
    event_type: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> ORJSONResponse:
    """Get merged document requirements for an event type (base + compliance if active)."""
    from app.services.document_service import DocumentLinkService

    compliance_active = await _is_compliance_active(tenant_id)
    link_svc = DocumentLinkService(db, tenant_id)
    reqs = await link_svc.get_merged_requirements(event_type, compliance_active)

    return ORJSONResponse(content=reqs)


def _link_resp(link, media_file) -> dict:
    """Build response dict for an event document link + its media file."""
    return {
        "id": str(link.id),
        "event_id": str(link.event_id),
        "asset_id": str(link.asset_id),
        "media_file_id": str(link.media_file_id),
        "document_type": link.document_type,
        "is_required": link.is_required,
        "compliance_source": link.compliance_source,
        "linked_by": link.linked_by,
        "created_at": link.created_at.isoformat(),
        # Embedded media file info
        "file": {
            "id": str(media_file.id),
            "filename": media_file.filename,
            "original_filename": media_file.original_filename,
            "content_type": media_file.content_type,
            "file_size": media_file.file_size,
            "file_hash": media_file.file_hash,
            "url": media_file.url,
            "title": media_file.title,
            "category": media_file.category,
            "storage_backend": media_file.storage_backend,
        },
    }


async def _is_compliance_active(tenant_id: uuid.UUID) -> bool:
    """Check if compliance module is active for tenant (cached via Redis)."""
    import redis.asyncio as aioredis
    from app.core.settings import get_settings

    settings = get_settings()
    cache_key = f"module:{tenant_id}:compliance"

    try:
        redis = aioredis.from_url(settings.REDIS_URL, socket_timeout=2)
        cached = await redis.get(cache_key)
        await redis.aclose()
        if cached is not None:
            return cached == b"1"
    except Exception:
        pass

    import httpx
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{settings.SUBSCRIPTION_SERVICE_URL}/api/v1/modules/{tenant_id}/compliance"
            )
            if resp.status_code == 200:
                is_active = resp.json().get("is_active", False)
                try:
                    redis = aioredis.from_url(settings.REDIS_URL, socket_timeout=2)
                    await redis.setex(cache_key, settings.MODULE_CACHE_TTL, "1" if is_active else "0")
                    await redis.aclose()
                except Exception:
                    pass
                return is_active
    except Exception:
        pass

    return False
