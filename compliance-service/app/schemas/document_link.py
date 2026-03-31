"""Schemas for evidence document links."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OrmBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class DocumentLinkCreate(BaseModel):
    media_file_id: uuid.UUID
    document_type: str
    description: str | None = None


class DocumentLinkResponse(OrmBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    record_id: uuid.UUID | None = None
    plot_id: uuid.UUID | None = None
    media_file_id: uuid.UUID
    document_type: str
    file_hash: str | None
    filename: str | None
    description: str | None
    uploaded_at: datetime
    metadata_: dict


class DocumentLinkWithUrl(DocumentLinkResponse):
    """Extended response that includes the media file URL."""
    url: str | None = None
