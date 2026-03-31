"""Public media router — file library management (frontend-facing)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, UploadFile, status
from fastapi.responses import ORJSONResponse
from starlette.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_tenant_id
from app.db.session import get_db_session

router = APIRouter(prefix="/media", tags=["media"])


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
async def upload_file(
    file: UploadFile = File(...),
    category: str = Query("general", max_length=50),
    document_type: str | None = Query(None, max_length=100),
    title: str | None = Query(None, max_length=200),
    description: str | None = Query(None, max_length=500),
    tags: str | None = Query(None),
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    x_user_id: str = Header("1", alias="X-User-Id"),
) -> ORJSONResponse:
    from app.services.media_service import MediaService

    svc = MediaService(db, tenant_id)
    tag_list = [t.strip() for t in tags.split(",")] if tags else []
    try:
        mf = await svc.upload_file(
            file=file, category=category, document_type=document_type,
            title=title, description=description, tags=tag_list, uploaded_by=x_user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=413, detail=str(exc))
    await db.commit()
    return ORJSONResponse(content=_file_resp(mf), status_code=201)


@router.post("/files/batch", status_code=status.HTTP_201_CREATED)
async def upload_files_batch(
    files: list[UploadFile] = File(...),
    category: str = Query("general", max_length=50),
    document_type: str | None = Query(None, max_length=100),
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    x_user_id: str = Header("1", alias="X-User-Id"),
) -> ORJSONResponse:
    from app.services.media_service import MediaService

    svc = MediaService(db, tenant_id)
    results = []
    for f in files:
        try:
            mf = await svc.upload_file(file=f, category=category, document_type=document_type, uploaded_by=x_user_id)
            results.append(_file_resp(mf))
        except ValueError as exc:
            raise HTTPException(status_code=413, detail=str(exc))
    await db.commit()
    return ORJSONResponse(content={"files": results}, status_code=201)


@router.get("/files")
async def list_files(
    category: str | None = Query(None), document_type: str | None = Query(None),
    search: str | None = Query(None, max_length=200),
    offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session), tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> ORJSONResponse:
    from app.services.media_service import MediaService

    svc = MediaService(db, tenant_id)
    files, total = await svc.list_files(category, document_type, search, offset, limit)
    return ORJSONResponse(content={"items": [_file_resp(f) for f in files], "total": total, "offset": offset, "limit": limit})


@router.get("/files/{file_id}")
async def get_file(
    file_id: uuid.UUID, db: AsyncSession = Depends(get_db_session), tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> ORJSONResponse:
    from app.services.media_service import MediaService

    mf = await MediaService(db, tenant_id).get_file(file_id)
    if not mf:
        raise HTTPException(status_code=404, detail="File not found")
    return ORJSONResponse(content=_file_resp(mf))


@router.patch("/files/{file_id}")
async def update_file(
    file_id: uuid.UUID,
    title: str | None = Query(None, max_length=200), description: str | None = Query(None, max_length=500),
    category: str | None = Query(None, max_length=50), document_type: str | None = Query(None, max_length=100),
    tags: str | None = Query(None),
    db: AsyncSession = Depends(get_db_session), tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> ORJSONResponse:
    from app.services.media_service import MediaService

    tag_list = [t.strip() for t in tags.split(",")] if tags else None
    mf = await MediaService(db, tenant_id).update_file(file_id, title=title, description=description, category=category, document_type=document_type, tags=tag_list)
    if not mf:
        raise HTTPException(status_code=404, detail="File not found")
    await db.commit()
    return ORJSONResponse(content=_file_resp(mf))


@router.delete("/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_file(
    file_id: uuid.UUID, db: AsyncSession = Depends(get_db_session), tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    from app.services.media_service import MediaService

    if not await MediaService(db, tenant_id).delete_file(file_id):
        raise HTTPException(status_code=404, detail="File not found")
    await db.commit()
    return Response(status_code=204)
