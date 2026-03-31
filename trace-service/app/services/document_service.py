"""Service: media file management and event document linking."""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import get_settings
from app.db.models import EventDocumentLink, MediaFile, WorkflowEventType
from app.repositories.media_repo import EventDocumentLinkRepository, MediaFileRepository
from app.storage.backend import get_storage


class MediaService:
    """Centralized media file management."""

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
            created_at=datetime.now(tz=timezone.utc),
            updated_at=datetime.now(tz=timezone.utc),
        )

    async def get_file(self, file_id: uuid.UUID) -> MediaFile | None:
        mf = await self._repo.get_by_id(file_id)
        if mf and mf.tenant_id != self._tenant_id:
            return None
        return mf

    async def list_files(
        self,
        category: str | None = None,
        document_type: str | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[MediaFile], int]:
        return await self._repo.list(
            self._tenant_id, category, document_type, search, offset, limit
        )

    async def update_file(
        self,
        file_id: uuid.UUID,
        title: str | None = None,
        description: str | None = None,
        category: str | None = None,
        document_type: str | None = None,
        tags: list[str] | None = None,
    ) -> MediaFile | None:
        mf = await self.get_file(file_id)
        if not mf:
            return None
        kwargs: dict[str, Any] = {}
        if title is not None:
            kwargs["title"] = title
        if description is not None:
            kwargs["description"] = description
        if category is not None:
            kwargs["category"] = category
        if document_type is not None:
            kwargs["document_type"] = document_type
        if tags is not None:
            kwargs["tags"] = tags
        if kwargs:
            return await self._repo.update(file_id, **kwargs)
        return mf

    async def delete_file(self, file_id: uuid.UUID) -> bool:
        mf = await self.get_file(file_id)
        if not mf:
            return False
        await self._storage.delete(mf.storage_key)
        return await self._repo.delete(file_id)


class DocumentLinkService:
    """Link/unlink media files to custody events and check requirements."""

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._db = session
        self._tenant_id = tenant_id
        self._link_repo = EventDocumentLinkRepository(session)

    async def link_file_to_event(
        self,
        event_id: uuid.UUID,
        asset_id: uuid.UUID,
        media_file_id: uuid.UUID,
        document_type: str,
        is_required: bool = False,
        compliance_source: str | None = None,
        linked_by: str | None = None,
    ) -> EventDocumentLink:
        return await self._link_repo.create(
            id=uuid.uuid4(),
            tenant_id=self._tenant_id,
            event_id=event_id,
            asset_id=asset_id,
            media_file_id=media_file_id,
            document_type=document_type,
            is_required=is_required,
            compliance_source=compliance_source,
            linked_by=linked_by,
            created_at=datetime.now(tz=timezone.utc),
        )

    async def list_event_documents(self, event_id: uuid.UUID) -> list[EventDocumentLink]:
        return await self._link_repo.list_by_event(event_id)

    async def list_asset_documents(self, asset_id: uuid.UUID) -> list[EventDocumentLink]:
        return await self._link_repo.list_by_asset(asset_id)

    async def unlink(self, link_id: uuid.UUID) -> bool:
        return await self._link_repo.delete(link_id)

    # ── Requirements ─────────────────────────────────────────────────────────

    async def get_merged_requirements(
        self,
        event_type_slug: str,
        compliance_active: bool = False,
    ) -> dict[str, Any]:
        from sqlalchemy import select

        result = await self._db.execute(
            select(WorkflowEventType).where(
                WorkflowEventType.tenant_id == self._tenant_id,
                WorkflowEventType.slug == event_type_slug,
            )
        )
        wf_event = result.scalar_one_or_none()
        if not wf_event:
            return {"documents": [], "block_transition": False}

        base = wf_event.required_documents or {}
        base_docs = base.get("documents", [])
        block = base.get("block_transition", False)

        compliance_docs: list[dict] = []
        if compliance_active and wf_event.compliance_required_documents:
            comp = wf_event.compliance_required_documents
            compliance_docs = comp.get("documents", [])
            if comp.get("block_transition"):
                block = True

        merged = base_docs + compliance_docs

        return {
            "event_type_slug": event_type_slug,
            "base_requirements": base_docs,
            "compliance_requirements": compliance_docs,
            "compliance_active": compliance_active,
            "merged_requirements": merged,
            "block_transition": block,
        }

    async def check_completeness(
        self,
        event_id: uuid.UUID,
        event_type_slug: str,
        compliance_active: bool = False,
    ) -> dict[str, Any]:
        reqs = await self.get_merged_requirements(event_type_slug, compliance_active)
        links = await self._link_repo.list_by_event(event_id)

        uploaded_types: dict[str, int] = {}
        for link in links:
            uploaded_types[link.document_type] = uploaded_types.get(link.document_type, 0) + 1

        missing = []
        satisfied = []
        for req in reqs.get("merged_requirements", []):
            doc_type = req["type"]
            count = uploaded_types.get(doc_type, 0)
            if count > 0:
                satisfied.append({"type": doc_type, "label": req.get("label", doc_type), "count": count})
            elif req.get("required", False):
                source = "compliance" if req in reqs.get("compliance_requirements", []) else "base"
                missing.append({"type": doc_type, "label": req.get("label", doc_type), "source": source})

        return {
            "complete": len(missing) == 0,
            "total_uploaded": len(links),
            "total_required": sum(1 for r in reqs.get("merged_requirements", []) if r.get("required")),
            "missing": missing,
            "satisfied": satisfied,
            "block_transition": reqs.get("block_transition", False),
        }
