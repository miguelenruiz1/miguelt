"""Taxonomy router — custodian types and organizations."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import ORJSONResponse
from starlette.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_tenant_id
from app.core.logging import get_logger
from app.db.session import get_db_session
from app.domain.schemas import (
    AssetListResponse,
    AssetResponse,
    CustodianTypeCreate,
    CustodianTypeResponse,
    CustodianTypeUpdate,
    OrganizationCreate,
    OrganizationListResponse,
    OrganizationResponse,
    OrganizationUpdate,
    WalletListResponse,
    WalletResponse,
)
from app.services.taxonomy_service import TaxonomyService

log = get_logger(__name__)
router = APIRouter(prefix="/taxonomy", tags=["taxonomy"])


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _type_dict(ct) -> dict:
    return CustodianTypeResponse.model_validate(ct).model_dump(mode="json")


async def _org_dict(svc: TaxonomyService, org) -> dict:
    wallet_count = await svc.wallet_count_for_org(org.id)
    d = OrganizationResponse.model_validate(org).model_dump(mode="json")
    d["wallet_count"] = wallet_count
    return d


# ─── Custodian Types ──────────────────────────────────────────────────────────

@router.get(
    "/custodian-types",
    response_model=list[CustodianTypeResponse],
    summary="List all custodian types",
)
async def list_custodian_types(
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> ORJSONResponse:
    svc = TaxonomyService(db, tenant_id=tenant_id)
    types = await svc.list_types()
    return ORJSONResponse(content=[_type_dict(t) for t in types])


@router.post(
    "/custodian-types",
    response_model=CustodianTypeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a custodian type",
)
async def create_custodian_type(
    body: CustodianTypeCreate,
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> ORJSONResponse:
    svc = TaxonomyService(db, tenant_id=tenant_id)
    ct = await svc.create_type(
        name=body.name,
        slug=body.slug,
        color=body.color,
        icon=body.icon,
        description=body.description,
        sort_order=body.sort_order,
    )
    await db.commit()
    return ORJSONResponse(status_code=status.HTTP_201_CREATED, content=_type_dict(ct))


@router.get(
    "/custodian-types/{type_id}",
    response_model=CustodianTypeResponse,
    summary="Get a custodian type by ID",
)
async def get_custodian_type(
    type_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> ORJSONResponse:
    svc = TaxonomyService(db, tenant_id=tenant_id)
    ct = await svc.get_type(type_id)
    return ORJSONResponse(content=_type_dict(ct))


@router.patch(
    "/custodian-types/{type_id}",
    response_model=CustodianTypeResponse,
    summary="Update a custodian type",
)
async def update_custodian_type(
    type_id: uuid.UUID,
    body: CustodianTypeUpdate,
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> ORJSONResponse:
    svc = TaxonomyService(db, tenant_id=tenant_id)
    values = body.model_dump(exclude_none=True)
    ct = await svc.update_type(type_id, **values)
    await db.commit()
    return ORJSONResponse(content=_type_dict(ct))


@router.delete(
    "/custodian-types/{type_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a custodian type (only if no organizations are linked)",
    response_class=Response,
)
async def delete_custodian_type(
    type_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = TaxonomyService(db, tenant_id=tenant_id)
    await svc.delete_type(type_id)
    await db.commit()
    return Response(status_code=204)


# ─── Organizations ────────────────────────────────────────────────────────────

@router.get(
    "/organizations",
    response_model=OrganizationListResponse,
    summary="List organizations with optional filters",
)
async def list_organizations(
    custodian_type_id: uuid.UUID | None = Query(None),
    status: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> ORJSONResponse:
    svc = TaxonomyService(db, tenant_id=tenant_id)
    orgs, total = await svc.list_orgs(
        custodian_type_id=custodian_type_id,
        status=status,
        offset=offset,
        limit=limit,
    )
    items = [await _org_dict(svc, o) for o in orgs]
    return ORJSONResponse(content={"items": items, "total": total})


@router.post(
    "/organizations",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an organization",
)
async def create_organization(
    body: OrganizationCreate,
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> ORJSONResponse:
    svc = TaxonomyService(db, tenant_id=tenant_id)
    org = await svc.create_org(
        name=body.name,
        custodian_type_id=body.custodian_type_id,
        description=body.description,
        tags=body.tags,
    )
    await db.commit()
    return ORJSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=await _org_dict(svc, org),
    )


@router.get(
    "/organizations/{org_id}",
    response_model=OrganizationResponse,
    summary="Get organization by ID",
)
async def get_organization(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> ORJSONResponse:
    svc = TaxonomyService(db, tenant_id=tenant_id)
    org = await svc.get_org(org_id)
    return ORJSONResponse(content=await _org_dict(svc, org))


@router.patch(
    "/organizations/{org_id}",
    response_model=OrganizationResponse,
    summary="Update an organization",
)
async def update_organization(
    org_id: uuid.UUID,
    body: OrganizationUpdate,
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> ORJSONResponse:
    svc = TaxonomyService(db, tenant_id=tenant_id)
    values = body.model_dump(exclude_none=True)
    org = await svc.update_org(org_id, **values)
    await db.commit()
    return ORJSONResponse(content=await _org_dict(svc, org))


@router.delete(
    "/organizations/{org_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an organization (only if no wallets are linked)",
    response_class=Response,
)
async def delete_organization(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = TaxonomyService(db, tenant_id=tenant_id)
    await svc.delete_org(org_id)
    await db.commit()
    return Response(status_code=204)


@router.get(
    "/organizations/{org_id}/wallets",
    response_model=WalletListResponse,
    summary="List wallets belonging to an organization",
)
async def get_org_wallets(
    org_id: uuid.UUID,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> ORJSONResponse:
    svc = TaxonomyService(db, tenant_id=tenant_id)
    wallets, total = await svc.get_org_wallets(org_id, offset=offset, limit=limit)
    items = [WalletResponse.model_validate(w).model_dump(mode="json") for w in wallets]
    return ORJSONResponse(content={"items": items, "total": total})


@router.get(
    "/organizations/{org_id}/assets",
    response_model=AssetListResponse,
    summary="List assets currently held by wallets of this organization",
)
async def get_org_assets(
    org_id: uuid.UUID,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> ORJSONResponse:
    svc = TaxonomyService(db, tenant_id=tenant_id)
    assets, total = await svc.get_org_assets(org_id, offset=offset, limit=limit)
    items = [AssetResponse.model_validate(a).model_dump(mode="json") for a in assets]
    return ORJSONResponse(content={"items": items, "total": total})
