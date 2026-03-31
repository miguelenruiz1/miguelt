"""Media router — centralized file library management."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Header, Query, UploadFile, status
from fastapi.responses import ORJSONResponse
from starlette.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_tenant_id
from app.db.session import get_db_session

router = APIRouter(prefix="/media", tags=["media"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

def _media_resp(mf) -> dict:
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


# ─── Upload ───────────────────────────────────────────────────────────────────

@router.post("/files", status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    category: str = Query("general", max_length=50),
    document_type: str | None = Query(None, max_length=100),
    title: str | None = Query(None, max_length=200),
    description: str | None = Query(None, max_length=500),
    tags: str | None = Query(None, description="Comma-separated tags"),
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    x_user_id: str = Header("1", alias="X-User-Id"),
) -> ORJSONResponse:
    """Upload a file to the media library."""
    from app.services.document_service import MediaService
    from fastapi import HTTPException

    svc = MediaService(db, tenant_id)
    tag_list = [t.strip() for t in tags.split(",")] if tags else []

    try:
        mf = await svc.upload_file(
            file=file,
            category=category,
            document_type=document_type,
            title=title,
            description=description,
            tags=tag_list,
            uploaded_by=x_user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=413, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Upload failed: {exc}")

    await db.commit()
    return ORJSONResponse(content=_media_resp(mf), status_code=201)


@router.post("/files/batch", status_code=status.HTTP_201_CREATED)
async def upload_files_batch(
    files: list[UploadFile] = File(...),
    category: str = Query("general", max_length=50),
    document_type: str | None = Query(None, max_length=100),
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    x_user_id: str = Header("1", alias="X-User-Id"),
) -> ORJSONResponse:
    """Upload multiple files to the media library."""
    from app.services.document_service import MediaService

    svc = MediaService(db, tenant_id)
    results = []
    for f in files:
        mf = await svc.upload_file(
            file=f,
            category=category,
            document_type=document_type,
            uploaded_by=x_user_id,
        )
        results.append(_media_resp(mf))

    await db.commit()
    return ORJSONResponse(content={"files": results}, status_code=201)


# ─── List / Search ────────────────────────────────────────────────────────────

@router.get("/files")
async def list_files(
    category: str | None = Query(None),
    document_type: str | None = Query(None),
    search: str | None = Query(None, max_length=200),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> ORJSONResponse:
    """List media files with optional filtering."""
    from app.services.document_service import MediaService

    svc = MediaService(db, tenant_id)
    files, total = await svc.list_files(category, document_type, search, offset, limit)

    return ORJSONResponse(content={
        "items": [_media_resp(f) for f in files],
        "total": total,
        "offset": offset,
        "limit": limit,
    })


# ─── Detail ───────────────────────────────────────────────────────────────────

@router.get("/files/{file_id}")
async def get_file(
    file_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> ORJSONResponse:
    """Get a single media file."""
    from app.services.document_service import MediaService
    from fastapi import HTTPException

    svc = MediaService(db, tenant_id)
    mf = await svc.get_file(file_id)
    if not mf:
        raise HTTPException(status_code=404, detail="File not found")
    return ORJSONResponse(content=_media_resp(mf))


# ─── Update ───────────────────────────────────────────────────────────────────

@router.patch("/files/{file_id}")
async def update_file(
    file_id: uuid.UUID,
    title: str | None = Query(None, max_length=200),
    description: str | None = Query(None, max_length=500),
    category: str | None = Query(None, max_length=50),
    document_type: str | None = Query(None, max_length=100),
    tags: str | None = Query(None, description="Comma-separated tags"),
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> ORJSONResponse:
    """Update media file metadata."""
    from app.services.document_service import MediaService
    from fastapi import HTTPException

    svc = MediaService(db, tenant_id)
    tag_list = [t.strip() for t in tags.split(",")] if tags else None
    mf = await svc.update_file(file_id, title, description, category, document_type, tag_list)
    if not mf:
        raise HTTPException(status_code=404, detail="File not found")
    await db.commit()
    return ORJSONResponse(content=_media_resp(mf))


# ─── Reference counts (how many events link to each media file) ──────────────

@router.post("/files/reference-counts")
async def media_reference_counts(
    file_ids: list[str],
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
) -> ORJSONResponse:
    """Given a list of media file IDs, return how many event_document_links reference each."""
    from sqlalchemy import func, select
    from app.db.models import EventDocumentLink

    uuids = [uuid.UUID(fid) for fid in file_ids]
    rows = (
        await db.execute(
            select(
                EventDocumentLink.media_file_id,
                func.count(EventDocumentLink.id).label("count"),
            )
            .where(
                EventDocumentLink.media_file_id.in_(uuids),
                EventDocumentLink.tenant_id == tenant_id,
            )
            .group_by(EventDocumentLink.media_file_id)
        )
    ).all()
    counts = {str(r[0]): r[1] for r in rows}
    return ORJSONResponse(content={"counts": counts, "source": "trace"})


# ─── Delete ───────────────────────────────────────────────────────────────────

@router.delete("/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_file(
    file_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """Delete a media file and its storage."""
    from app.services.document_service import MediaService
    from fastapi import HTTPException

    svc = MediaService(db, tenant_id)
    deleted = await svc.delete_file(file_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="File not found")
    await db.commit()
    return Response(status_code=204)
