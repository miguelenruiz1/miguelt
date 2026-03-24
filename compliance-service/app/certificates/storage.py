"""Certificate file storage — local or S3."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol, runtime_checkable

from app.core.logging import get_logger
from app.core.settings import get_settings

log = get_logger(__name__)


@runtime_checkable
class IStorage(Protocol):
    """Abstract storage interface for certificate files."""

    async def upload(
        self,
        tenant_id: str,
        year: int,
        filename: str,
        data: bytes,
        content_type: str = "application/pdf",
    ) -> str:
        """Upload a file and return its public URL."""
        ...


class LocalStorage:
    """Saves certificate files to the local filesystem."""

    BASE_DIR = Path("/app/uploads/certificates")

    async def upload(
        self,
        tenant_id: str,
        year: int,
        filename: str,
        data: bytes,
        content_type: str = "application/pdf",
    ) -> str:
        directory = self.BASE_DIR / tenant_id / str(year)
        directory.mkdir(parents=True, exist_ok=True)

        file_path = directory / filename
        file_path.write_bytes(data)

        log.info(
            "local_storage_upload",
            path=str(file_path),
            size=len(data),
        )
        return f"file://{file_path}"


class S3Storage:
    """Uploads certificate files to AWS S3."""

    def __init__(self) -> None:
        settings = get_settings()
        import boto3

        self._client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )
        self._bucket = settings.AWS_BUCKET_NAME
        self._region = settings.AWS_REGION

    async def upload(
        self,
        tenant_id: str,
        year: int,
        filename: str,
        data: bytes,
        content_type: str = "application/pdf",
    ) -> str:
        key = f"certificates/{tenant_id}/{year}/{filename}"

        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )

        url = f"https://{self._bucket}.s3.{self._region}.amazonaws.com/{key}"
        log.info(
            "s3_storage_upload",
            bucket=self._bucket,
            key=key,
            size=len(data),
        )
        return url


def get_storage() -> IStorage:
    """Factory: returns the appropriate storage backend based on settings."""
    settings = get_settings()
    backend = settings.CERTIFICATE_STORAGE.lower()

    if backend == "s3":
        return S3Storage()
    return LocalStorage()
