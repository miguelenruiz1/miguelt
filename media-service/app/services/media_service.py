"""Service: media file management."""
from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import get_settings
from app.repositories.media_repo import MediaFileRepository
from app.storage.backend import get_storage
from app.db.models import MediaFile


# Allowed segment regex: lowercase alphanumeric, hyphen, underscore, max 40 chars.
_CATEGORY_RE = re.compile(r"^[a-z0-9_-]{1,40}$")
_FILENAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,200}$")


def _sanitize_category(category: str | None) -> str:
    settings = get_settings()
    cat = (category or "general").strip().lower()
    if not _CATEGORY_RE.match(cat):
        raise ValueError(
            f"Invalid category '{cat}'. Must match [a-z0-9_-]{{1,40}}"
        )
    if cat not in settings.ALLOWED_CATEGORIES:
        raise ValueError(
            f"Category '{cat}' not allowed. Choose one of: {', '.join(settings.ALLOWED_CATEGORIES)}"
        )
    return cat


def _sanitize_filename(filename: str | None) -> str:
    """Strip directory components and reject path traversal."""
    name = (filename or "file").strip()
    # Strip any directory components
    name = name.replace("\\", "/").split("/")[-1]
    if not name or name in (".", ".."):
        return "file"
    if not _FILENAME_RE.match(name):
        # Replace invalid chars with underscore
        name = re.sub(r"[^A-Za-z0-9._-]", "_", name)[:200] or "file"
    return name


def _strip_pii_from_filename(filename: str) -> str:
    """Scrub obvious PII from user-supplied filenames before persisting them.

    People routinely upload files called `factura_JuanPerez_NIT900123456.pdf`.
    Storing that verbatim puts PII in every media listing and log line. We
    mask emails, NITs and long digit runs; harmless tokens (product names,
    descriptions) are kept so the filename remains recognisable.
    """
    import re as _re
    name = filename
    # Email first (greedy) so the NIT regex below doesn't chew up the local-
    # part domain digits.
    name = _re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[email]", name)
    # Colombian NIT `NNNNNNNNN-D`. Lookarounds so identifiers where digits
    # are glued to letters (`NIT900123456-8`) still get masked — `\b`
    # wouldn't fire because `_` / letters are word chars.
    name = _re.sub(r"(?<!\d)\d{6,10}\s*-\s*\d(?!\d)", "[nit]", name)
    # Long digit runs (>= 8) that aren't obviously a year/date.
    name = _re.sub(r"(?<!\d)\d{8,}(?!\d)", "[id]", name)
    return name


def _validate_content_type(content_type: str) -> str:
    """Reject MIME types not in the allowlist."""
    settings = get_settings()
    ct = (content_type or "application/octet-stream").split(";")[0].strip().lower()
    if ct not in settings.ALLOWED_MIME_TYPES:
        raise ValueError(
            f"Content type '{ct}' not allowed. Allowed: {', '.join(settings.ALLOWED_MIME_TYPES)}"
        )
    return ct


# Magic-byte signatures mapped to the MIME types that must match on upload.
# The allowlist is intentionally narrow: only the file types the platform
# actually serves. Types NOT in here (e.g. application/json, text/csv) are
# accepted on content-type alone because they have no stable binary signature.
_MAGIC_SIGNATURES: tuple[tuple[str, tuple[bytes, ...]], ...] = (
    ("image/jpeg", (b"\xff\xd8\xff",)),
    ("image/png", (b"\x89PNG\r\n\x1a\n",)),
    ("image/gif", (b"GIF87a", b"GIF89a")),
    ("image/webp", (b"RIFF",)),  # RIFF....WEBP — first 4 bytes suffice for screen
    ("application/pdf", (b"%PDF-",)),
    ("application/zip", (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")),
    # Office docs are zip containers too
    ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", (b"PK\x03\x04",)),
    ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", (b"PK\x03\x04",)),
)


def _verify_magic_bytes(content: bytes, declared_mime: str) -> None:
    """Confirm the file's leading bytes match its declared MIME type.

    Without this, a client can upload an `.exe` with Content-Type:
    image/jpeg and the allowlist check passes. Only checked for the binary
    types we know the signature of; unknown types pass through unchanged.
    """
    for mime, signatures in _MAGIC_SIGNATURES:
        if mime == declared_mime:
            if not any(content.startswith(sig) for sig in signatures):
                raise ValueError(
                    f"File content does not match declared type '{declared_mime}' "
                    "(magic byte mismatch)"
                )
            return


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
        # Sanitize first so a malicious request fails before reading bytes
        category = _sanitize_category(category)
        original_filename = _strip_pii_from_filename(_sanitize_filename(file.filename))
        content_type = _validate_content_type(file.content_type or "application/octet-stream")

        content = await file.read()

        max_bytes = settings.DOCUMENT_MAX_SIZE_MB * 1024 * 1024
        if len(content) > max_bytes:
            raise ValueError(f"File exceeds {settings.DOCUMENT_MAX_SIZE_MB}MB limit")

        _verify_magic_bytes(content, content_type)

        file_hash = hashlib.sha256(content).hexdigest()

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
        category = _sanitize_category(category)
        filename = _strip_pii_from_filename(_sanitize_filename(filename))
        content_type = _validate_content_type(content_type)
        max_bytes = settings.DOCUMENT_MAX_SIZE_MB * 1024 * 1024
        if len(data) > max_bytes:
            raise ValueError(f"File exceeds {settings.DOCUMENT_MAX_SIZE_MB}MB limit")
        _verify_magic_bytes(data, content_type)

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
