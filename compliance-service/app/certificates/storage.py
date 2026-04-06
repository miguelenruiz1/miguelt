"""Certificate file storage — local, S3, or GCS."""
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
    """Saves certificate files to the local filesystem (DEV ONLY).

    On Cloud Run / GKE the filesystem is ephemeral and files are lost on
    container restart. Use S3Storage or GCSStorage in production.
    """

    BASE_DIR = Path(os.environ.get("CERTIFICATE_LOCAL_DIR", "/app/uploads/certificates"))

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

        log.info("local_storage_upload", path=str(file_path), size=len(data))
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
        log.info("s3_storage_upload", bucket=self._bucket, key=key, size=len(data))
        return url


class GCSStorage:
    """Uploads certificate files to Google Cloud Storage (Cloud Run friendly)."""

    def __init__(self) -> None:
        settings = get_settings()
        try:
            from google.cloud import storage as gcs  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "GCS storage requires `google-cloud-storage` to be installed"
            ) from exc

        self._client = gcs.Client()
        self._bucket_name = settings.AWS_BUCKET_NAME  # reuse env var
        self._bucket = self._client.bucket(self._bucket_name)

    async def upload(
        self,
        tenant_id: str,
        year: int,
        filename: str,
        data: bytes,
        content_type: str = "application/pdf",
    ) -> str:
        key = f"certificates/{tenant_id}/{year}/{filename}"
        blob = self._bucket.blob(key)
        blob.upload_from_string(data, content_type=content_type)
        url = f"https://storage.googleapis.com/{self._bucket_name}/{key}"
        log.info("gcs_storage_upload", bucket=self._bucket_name, key=key, size=len(data))
        return url


def _is_running_on_cloud_run() -> bool:
    return bool(os.environ.get("K_SERVICE")) or bool(os.environ.get("CLOUD_RUN_JOB"))


def get_storage() -> IStorage:
    """Factory: returns the appropriate storage backend based on settings.

    On Cloud Run, refuses to use LocalStorage (filesystem is ephemeral).
    """
    settings = get_settings()
    backend = (settings.CERTIFICATE_STORAGE or "local").lower()

    if backend == "s3":
        return S3Storage()
    if backend == "gcs":
        return GCSStorage()

    if _is_running_on_cloud_run():
        log.error(
            "local_storage_on_cloud_run_refused",
            hint="Set CERTIFICATE_STORAGE=gcs or s3 — local FS is ephemeral on Cloud Run",
        )
        raise RuntimeError(
            "LocalStorage is not allowed on Cloud Run. "
            "Set CERTIFICATE_STORAGE=gcs (or s3) and configure bucket credentials."
        )
    return LocalStorage()
