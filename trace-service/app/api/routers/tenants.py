"""Tenants router — multi-tenancy management + Merkle tree provisioning."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from fastapi.responses import ORJSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_tenant_id
from app.core.logging import get_logger
from app.db.session import get_db_session
from app.domain.schemas import MerkleTreeResponse, TenantCreate, TenantResponse
from app.services.tenant_service import TenantService

log = get_logger(__name__)
router = APIRouter(prefix="/tenants", tags=["tenants"])


def _tenant_dict(tenant) -> dict:
    return TenantResponse.model_validate(tenant).model_dump(mode="json")


def _tree_dict(tree) -> dict:
    return MerkleTreeResponse.model_validate(tree).model_dump(mode="json")


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new tenant",
)
async def create_tenant(
    body: TenantCreate,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = TenantService(db)
    tenant = await svc.create_tenant(name=body.name, slug=body.slug)
    await db.commit()
    return ORJSONResponse(status_code=status.HTTP_201_CREATED, content=_tenant_dict(tenant))


@router.get(
    "",
    summary="List all tenants",
)
async def list_tenants(
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = TenantService(db)
    tenants = await svc.list_tenants()
    return ORJSONResponse(content=[_tenant_dict(t) for t in tenants])


@router.get(
    "/{tenant_id}",
    summary="Get tenant by ID",
)
async def get_tenant(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = TenantService(db)
    tenant = await svc.get_tenant(tenant_id)
    return ORJSONResponse(content=_tenant_dict(tenant))


@router.post(
    "/{tenant_id}/provision-tree",
    status_code=status.HTTP_201_CREATED,
    summary="Provision a Merkle tree for a tenant",
)
async def provision_tree(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = TenantService(db)
    tree = await svc.provision_merkle_tree(tenant_id)
    await db.commit()
    return ORJSONResponse(status_code=status.HTTP_201_CREATED, content=_tree_dict(tree))


@router.get(
    "/{tenant_id}/tree",
    summary="Get Merkle tree status for a tenant",
)
async def get_tree(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    svc = TenantService(db)
    tree = await svc.get_merkle_tree(tenant_id)
    return ORJSONResponse(content=_tree_dict(tree))


@router.get(
    "/assets/{asset_id}/blockchain",
    summary="Verify on-chain state of an asset",
)
async def get_asset_blockchain(
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> ORJSONResponse:
    from app.clients.provider_factory import get_blockchain_provider
    from app.core.errors import NotFoundError
    from app.repositories.custody_repo import AssetRepository
    from app.services.blockchain_service import BlockchainService

    # Tenant isolation check
    asset_repo = AssetRepository(db)
    asset = await asset_repo.get_by_id(asset_id)
    if asset is None or asset.tenant_id != tenant_id:
        raise NotFoundError(f"Asset '{asset_id}' not found")

    provider = get_blockchain_provider()
    svc = BlockchainService(db, provider)
    result = await svc.verify_asset_onchain(asset_id)

    if result is None:
        return ORJSONResponse(content={"message": "No blockchain data available for this asset"})

    return ORJSONResponse(content={
        "asset_id": result.asset_id,
        "owner": result.owner,
        "tree_address": result.tree_address,
        "leaf_index": result.leaf_index,
        "confirmed": result.confirmed,
    })
