"""Router for national platform adapters."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import ModuleUser
from app.services.national_platforms import (
    NationalPlatformMetadata,
    get_adapter,
    list_adapters,
)


router = APIRouter(
    prefix="/api/v1/compliance/national-platforms",
    tags=["national-platforms"],
)


class LookupRequest(BaseModel):
    reference_id: str


@router.get("/")
async def list_national_platforms(_: ModuleUser) -> list[dict]:
    return [_metadata_to_dict(m) for m in list_adapters()]


@router.get("/{slug}")
async def get_national_platform(slug: str, _: ModuleUser) -> dict:
    adapter = get_adapter(slug)
    if adapter is None:
        raise HTTPException(status_code=404, detail=f"Platform '{slug}' not registered")
    return _metadata_to_dict(adapter.metadata)


@router.post("/{slug}/lookup")
async def lookup(
    slug: str,
    body: LookupRequest,
    user: ModuleUser,
) -> dict:
    adapter = get_adapter(slug)
    if adapter is None:
        raise HTTPException(status_code=404, detail=f"Platform '{slug}' not registered")
    result = await adapter.lookup_producer(
        body.reference_id,
        tenant_id=str(user.get("tenant_id")) if user.get("tenant_id") else None,
    )
    return {
        "platform": adapter.metadata.slug,
        "available": adapter.is_available(),
        "result": result.to_dict(),
    }


def _metadata_to_dict(m: NationalPlatformMetadata) -> dict:
    return {
        "slug": m.slug,
        "name": m.name,
        "country": m.country,
        "description": m.description,
        "reference_url": m.reference_url,
        "supports": m.supports,
        "available": m.available,
    }
