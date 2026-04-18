"""Registry router — wallet allowlist management."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request, status

from fastapi.responses import ORJSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_tenant_id_enforced, get_tenant_id
from app.core.errors import ConflictError, IdempotencyConflictError
from app.core.logging import get_logger
from app.db.session import get_db_session
from app.domain.schemas import WalletCreate, WalletListResponse, WalletResponse, WalletUpdate, WalletGenerateRequest
from app.services.registry_service import RegistryService

log = get_logger(__name__)
router = APIRouter(prefix="/registry", tags=["registry"])


def _wallet_response(wallet) -> dict:
    return WalletResponse.model_validate(wallet).model_dump(mode="json")


@router.post(
    "/wallets",
    response_model=WalletResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a wallet in the allowlist",
)
async def register_wallet(
    request: Request,
    body: WalletCreate,
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id_enforced),
) -> ORJSONResponse:
    idempotency_key = getattr(request.state, "idempotency_key", None)

    # Idempotency check
    if idempotency_key:
        from app.utils.idempotency import IdempotencyStore
        import redis.asyncio as aioredis
        from app.core.settings import get_settings
        redis_client = aioredis.from_url(get_settings().REDIS_URL)
        store = IdempotencyStore(redis_client)

        cached = await store.get_cached_response(idempotency_key, namespace="register_wallet")
        if cached:
            if cached.get("__processing__"):
                raise ConflictError("Request is still being processed")
            await redis_client.aclose()
            return ORJSONResponse(status_code=status.HTTP_200_OK, content=cached)

        acquired = await store.mark_processing(idempotency_key, namespace="register_wallet")
        if not acquired:
            await redis_client.aclose()
            raise ConflictError("Concurrent duplicate request in progress")
    else:
        redis_client = None
        store = None

    try:
        svc = RegistryService(db, tenant_id=tenant_id)
        wallet = await svc.register_wallet(
            wallet_pubkey=body.wallet_pubkey,
            tags=body.tags,
            status=body.status,
            name=body.name,
            organization_id=body.organization_id,
        )
        await db.commit()
        result = _wallet_response(wallet)

        if idempotency_key and store and redis_client:
            await store.save_response(idempotency_key, namespace="register_wallet", response=result)
            await redis_client.aclose()

        return ORJSONResponse(status_code=status.HTTP_201_CREATED, content=result)
    except Exception:
        if idempotency_key and store and redis_client:
            await store.delete(idempotency_key, namespace="register_wallet")
            await redis_client.aclose()
        raise


@router.post(
    "/wallets/generate",
    response_model=WalletResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a new wallet and register it",
)
async def generate_wallet(
    body: WalletGenerateRequest,
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id_enforced),
) -> ORJSONResponse:
    svc = RegistryService(db, tenant_id=tenant_id)
    wallet, airdrop_info = await svc.generate_wallet(
        tags=body.tags,
        status=body.status,
        name=body.name,
        organization_id=body.organization_id,
    )
    await db.commit()
    result = _wallet_response(wallet)
    # Surface airdrop result so the UI can warn when devnet rate-limits us.
    result["airdrop"] = airdrop_info
    return ORJSONResponse(status_code=status.HTTP_201_CREATED, content=result)


@router.get(
    "/wallets",
    response_model=WalletListResponse,
    summary="List wallets with optional filters",
)
async def list_wallets(
    tag: str | None = Query(None),
    status: str | None = Query(None),
    organization_id: uuid.UUID | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id_enforced),
) -> ORJSONResponse:
    svc = RegistryService(db, tenant_id=tenant_id)
    wallets, total = await svc.list_wallets(tag=tag, status=status, organization_id=organization_id, offset=offset, limit=limit)
    items = [WalletResponse.model_validate(w).model_dump(mode="json") for w in wallets]
    return ORJSONResponse(content={"items": items, "total": total})


@router.get(
    "/wallets/{wallet_id}",
    response_model=WalletResponse,
    summary="Get wallet by ID",
)
async def get_wallet(
    wallet_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id_enforced),
) -> ORJSONResponse:
    svc = RegistryService(db, tenant_id=tenant_id)
    wallet = await svc.get_wallet(wallet_id)
    return ORJSONResponse(content=_wallet_response(wallet))


@router.patch(
    "/wallets/{wallet_id}",
    response_model=WalletResponse,
    summary="Update wallet tags or status",
)
async def update_wallet(
    wallet_id: uuid.UUID,
    body: WalletUpdate,
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id_enforced),
) -> ORJSONResponse:
    svc = RegistryService(db, tenant_id=tenant_id)
    wallet = await svc.update_wallet(
        wallet_id=wallet_id,
        tags=body.tags,
        status=body.status,
        name=body.name,
        organization_id=body.organization_id,
    )
    await db.commit()
    return ORJSONResponse(content=_wallet_response(wallet))
