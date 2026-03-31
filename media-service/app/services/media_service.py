"""Service: media file management."""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import get_settings
from app.repositories.media_repo import MediaFileRepository
from app.storage.backend import get_storage
from app.db.models import MediaFile


class MediaService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._db = session
        self._tenant_id = tenant_id
        self._repo = MediaFileRepository(session)
        self._storage = get_storage()

    async def upload_file(
        self,
        file: UploadFile,
        category: str = "general",
        document_type: str | None = None,
        title: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
        uploaded_by: str | None = None,
    ) -> MediaFile:
        settings = get_settings()
        content = await file.read()

        max_bytes = settings.DOCUMENT_MAX_SIZE_MB * 1024 * 1024
        if len(content) > max_bytes:
            raise ValueError(f"File exceeds {settings.DOCUMENT_MAX_SIZE_MB}MB limit")

        file_hash = hashlib.sha256(content).hexdigest()
        original_filename = file.filename or "file"
        content_type = file.content_type or "application/octet-stream"

        storage_key, url = await self._storage.upload(
            tenant_id=str(self._tenant_id),
            filename=original_filename,
            data=content,
            content_type=content_type,
            category=category,
        )

        now = datetime.now(tz=timezone.utc)
        return await self._repo.create(
            id=uuid.uuid4(),
            tenant_id=self._tenant_id,
            filename=storage_key.split("/")[-1],
            original_filename=original_filename,
            content_type=content_type,
            file_size=len(content),
            file_hash=file_hash,
            storage_backend=self._storage.backend_name,
            storage_key=storage_key,
            url=url,
            category=category,
            document_type=document_type,
            title=title or original_filename,
            description=description,
            tags=tags or [],
            uploaded_by=uploaded_by,
            created_at=now,
            updated_at=now,
        )

    async def upload_bytes(
        self,
        data: bytes,
        filename: str,
        content_type: str,
        category: str = "general",
        document_type: str | None = None,
        title: str | None = None,
        uploaded_by: str | None = None,
    ) -> MediaFile:
        """Upload from raw bytes (used by S2S internal endpoint)."""
        settings = get_settings()
        max_bytes = settings.DOCUMENT_MAX_SIZE_MB * 1024 * 1024
        if len(data) > max_bytes:
            raise ValueError(f"File exceeds {settings.DOCUMENT_MAX_SIZE_MB}MB limit")

        file_hash = hashlib.sha256(data).hexdigest()
        storage_key, url = await self._storage.upload(
            tenant_id=str(self._tenant_id),
            filename=filename,
            data=data,
            content_type=content_type,
            category=category,
        )
        now = datetime.now(tz=timezone.utc)
        return await self._repo.create(
            id=uuid.uuid4(),
            tenant_id=self._tenant_id,
            filename=storage_key.split("/")[-1],
            original_filename=filename,
            content_type=content_type,
            file_size=len(data),
            file_hash=file_hash,
            storage_backend=self._storage.backend_name,
            storage_key=storage_key,
            url=url,
            category=category,
            document_type=document_type,
            title=title or filename,
            tags=[],
            uploaded_by=uploaded_by,
            created_at=now,
            updated_at=now,
        )

    async def get_file(self, file_id: uuid.UUID) -> MediaFile | None:
        mf = await self._repo.get_by_id(file_id)
        if mf and mf.tenant_id != self._tenant_id:
            return None
        return mf

    async def list_files(
        self, category: str | None = None, document_type: str | None = None,
        search: str | None = None, offset: int = 0, limit: int = 50,
    ) -> tuple[list[MediaFile], int]:
        return await self._repo.list(self._tenant_id, category, document_type, search, offset, limit)

    async def update_file(self, file_id: uuid.UUID, **kwargs) -> MediaFile | None:
        mf = await self.get_file(file_id)
        if not mf:
            return None
        filtered = {k: v for k, v in kwargs.items() if v is not None}
        if filtered:
            return await self._repo.update(file_id, **filtered)
        return mf

    async def delete_file(self, file_id: uuid.UUID) -> bool:
        mf = await self.get_file(file_id)
        if not mf:
            return False
        await self._storage.delete(mf.storage_key)
        return await self._repo.delete(file_id)

    async def validate_ids(self, file_ids: list[uuid.UUID]) -> list[str]:
        """Return list of valid file IDs that exist for this tenant."""
        files = await self._repo.get_many_by_ids(file_ids)
        return [str(f.id) for f in files if f.tenant_id == self._tenant_id]
