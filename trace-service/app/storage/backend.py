"""Storage backends for the media module.

Supports local filesystem (dev) and S3-compatible (production).
All backends implement the same interface: upload, delete, get_url.
"""
from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Protocol

from app.core.settings import get_settings


def _sanitize_filename(name: str) -> str:
    """Remove or replace chars that are problematic in URLs and filesystems."""
    # Keep alphanumeric, dots, hyphens, underscores
    name = re.sub(r'[^\w.\-]', '_', name)
    # Collapse multiple underscores
    name = re.sub(r'_+', '_', name)
    return name.strip('_') or 'file'


class IStorage(Protocol):
    """Storage backend interface."""

    @property
    def backend_name(self) -> str: ...

    async def upload(
        self,
        tenant_id: str,
        filename: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        category: str = "general",
    ) -> tuple[str, str]:
        """Upload a file. Returns (storage_key, public_url)."""
        ...

    async def delete(self, storage_key: str) -> bool:
        """Delete a file by storage key. Returns True if deleted."""
        ...

    async def get_url(self, storage_key: str) -> str:
        """Get the public/accessible URL for a storage key."""
        ...


class LocalStorage:
    """Local filesystem storage — for development."""

    def __init__(self) -> None:
        settings = get_settings()
        self._base = Path(settings.UPLOADS_BASE_PATH)

    @property
    def backend_name(self) -> str:
        return "local"

    async def upload(
        self,
        tenant_id: str,
        filename: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        category: str = "general",
    ) -> tuple[str, str]:
        # storage_key = media/{tenant_id}/{category}/{unique_filename}
        unique_prefix = uuid.uuid4().hex[:8]
        safe_filename = f"{unique_prefix}_{_sanitize_filename(filename)}"
        storage_key = f"media/{tenant_id}/{category}/{safe_filename}"

        file_path = self._base / storage_key
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(data)

        url = f"/uploads/{storage_key}"
        return storage_key, url

    async def delete(self, storage_key: str) -> bool:
        file_path = self._base / storage_key
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    async def get_url(self, storage_key: str) -> str:
        return f"/uploads/{storage_key}"


class S3Storage:
    """AWS S3 (or compatible) storage — for production."""

    def __init__(self) -> None:
        settings = get_settings()
        self._bucket = settings.AWS_S3_BUCKET
        self._region = settings.AWS_S3_REGION
        self._endpoint = settings.AWS_S3_ENDPOINT

    @property
    def backend_name(self) -> str:
        return "s3"

    def _get_client(self):
        import boto3
        settings = get_settings()
        kwargs = {
            "aws_access_key_id": settings.AWS_ACCESS_KEY_ID,
            "aws_secret_access_key": settings.AWS_SECRET_ACCESS_KEY,
            "region_name": self._region,
        }
        if self._endpoint:
            kwargs["endpoint_url"] = self._endpoint
        return boto3.client("s3", **kwargs)

    async def upload(
        self,
        tenant_id: str,
        filename: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        category: str = "general",
    ) -> tuple[str, str]:
        unique_prefix = uuid.uuid4().hex[:8]
        safe_filename = f"{unique_prefix}_{_sanitize_filename(filename)}"
        storage_key = f"media/{tenant_id}/{category}/{safe_filename}"

        client = self._get_client()
        client.put_object(
            Bucket=self._bucket,
            Key=storage_key,
            Body=data,
            ContentType=content_type,
        )

        url = await self.get_url(storage_key)
        return storage_key, url

    async def delete(self, storage_key: str) -> bool:
        client = self._get_client()
        client.delete_object(Bucket=self._bucket, Key=storage_key)
        return True

    async def get_url(self, storage_key: str) -> str:
        if self._endpoint:
            return f"{self._endpoint}/{self._bucket}/{storage_key}"
        return f"https://{self._bucket}.s3.{self._region}.amazonaws.com/{storage_key}"


_storage_instance: IStorage | None = None


def get_storage() -> IStorage:
    """Factory: returns configured storage backend (cached singleton)."""
    global _storage_instance
    if _storage_instance is not None:
        return _storage_instance

    settings = get_settings()
    backend = settings.STORAGE_BACKEND

    if backend == "s3":
        _storage_instance = S3Storage()
    else:
        _storage_instance = LocalStorage()

    return _storage_instance
