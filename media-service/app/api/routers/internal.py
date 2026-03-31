"""Internal S2S router — for other microservices to upload/query media."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import ORJSONResponse
from starlette.responses import Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import verify_service_token
from app.db.session import get_db_session

router = APIRouter(
    prefix="/internal/media",
    tags=["internal"],
    dependencies=[Depends(verify_service_token)],
)


def _resolve_tenant(tenant_id: str) -> uuid.UUID:
    """Resolve tenant_id string to UUID. Accepts UUID or slug 'default'."""
    try:
        return uuid.UUID(tenant_id)
    except ValueError:
        if tenant_id == "default":
            return uuid.UUID("00000000-0000-0000-0000-000000000001")
        raise HTTPException(status_code=400, detail=f"Cannot resolve tenant: {tenant_id}")


def _file_resp(mf) -> dict:
    return {
        "id": str(mf.id),
        "tenant_id": str(mf.tenant_id),
        "filename": mf.filename,
        "original_filename": mf.original_filename,
        "content_type": mf.content_type,
        "file_size": mf.file_size,
        "file_hash": mf.file_hash,
        "storage_backend": mf.storage_backend,
        "url": mf.url,
        "category": mf.category,
        "document_type": mf.document_type,
        "title": mf.title,
        "description": mf.description,
        "tags": mf.tags,
        "uploaded_by": mf.uploaded_by,
        "created_at": mf.created_at.isoformat(),
        "updated_at": mf.updated_at.isoformat(),
    }


@router.post("/files", status_code=status.HTTP_201_CREATED)
async def s2s_upload_file(
    file: UploadFile = File(...),
    tenant_id: str = Query(...),
    category: str = Query("general"),
    document_type: str | None = Query(None),
    title: str | None = Query(None),
    uploaded_by: str | None = Query(None),
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    """Upload a file on behalf of another service."""
    from app.services.media_service import MediaService

    tid = _resolve_tenant(tenant_id)
    svc = MediaService(db, tid)
    try:
        mf = await svc.upload_file(
            file=file, category=category, document_type=document_type,
            title=title, uploaded_by=uploaded_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=413, detail=str(exc))
    await db.commit()
    return ORJSONResponse(content=_file_resp(mf), status_code=201)


@router.get("/files")
async def s2s_list_files(
    tenant_id: str = Query(...),
    category: str | None = Query(None),
    document_type: str | None = Query(None),
    search: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    from app.services.media_service import MediaService

    tid = _resolve_tenant(tenant_id)
    files, total = await MediaService(db, tid).list_files(category, document_type, search, offset, limit)
    return ORJSONResponse(content={"items": [_file_resp(f) for f in files], "total": total})


@router.get("/files/{file_id}")
async def s2s_get_file(
    file_id: uuid.UUID,
    tenant_id: str = Query(...),
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    from app.services.media_service import MediaService

    mf = await MediaService(db, _resolve_tenant(tenant_id)).get_file(file_id)
    if not mf:
        raise HTTPException(status_code=404, detail="File not found")
    return ORJSONResponse(content=_file_resp(mf))


@router.delete("/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def s2s_delete_file(
    file_id: uuid.UUID,
    tenant_id: str = Query(...),
    db: AsyncSession = Depends(get_db_session),
):
    from app.services.media_service import MediaService

    if not await MediaService(db, _resolve_tenant(tenant_id)).delete_file(file_id):
        raise HTTPException(status_code=404, detail="File not found")
    await db.commit()
    return Response(status_code=204)


class ValidateRequest(BaseModel):
    tenant_id: str
    file_ids: list[str]


@router.post("/files/validate")
async def s2s_validate_file_ids(
    body: ValidateRequest,
    db: AsyncSession = Depends(get_db_session),
) -> ORJSONResponse:
    """Check which file IDs exist for a tenant. Returns valid IDs."""
    from app.services.media_service import MediaService

    tid = uuid.UUID(body.tenant_id)
    ids = [uuid.UUID(fid) for fid in body.file_ids]
    valid = await MediaService(db, tid).validate_ids(ids)
    return ORJSONResponse(content={"valid_ids": valid})
