"""Repository: media_files table."""
from __future__ import annotations

import uuid

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import MediaFile


class MediaFileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def create(self, **kwargs) -> MediaFile:
        mf = MediaFile(**kwargs)
        self._db.add(mf)
        await self._db.flush()
        return mf

    async def get_by_id(self, file_id: uuid.UUID) -> MediaFile | None:
        result = await self._db.execute(select(MediaFile).where(MediaFile.id == file_id))
        return result.scalar_one_or_none()

    async def get_many_by_ids(self, file_ids: list[uuid.UUID]) -> list[MediaFile]:
        if not file_ids:
            return []
        result = await self._db.execute(select(MediaFile).where(MediaFile.id.in_(file_ids)))
        return list(result.scalars().all())

    async def list(
        self,
        tenant_id: uuid.UUID,
        category: str | None = None,
        document_type: str | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[MediaFile], int]:
        q = select(MediaFile).where(MediaFile.tenant_id == tenant_id)
        count_q = select(func.count(MediaFile.id)).where(MediaFile.tenant_id == tenant_id)

        if category:
            q = q.where(MediaFile.category == category)
            count_q = count_q.where(MediaFile.category == category)
        if document_type:
            q = q.where(MediaFile.document_type == document_type)
            count_q = count_q.where(MediaFile.document_type == document_type)
        if search:
            like = f"%{search}%"
            cond = (
                MediaFile.title.ilike(like)
                | MediaFile.original_filename.ilike(like)
                | MediaFile.description.ilike(like)
            )
            q = q.where(cond)
            count_q = count_q.where(cond)

        total = (await self._db.execute(count_q)).scalar_one()
        rows = (await self._db.execute(q.order_by(MediaFile.created_at.desc()).offset(offset).limit(limit))).scalars().all()
        return list(rows), total

    async def update(self, file_id: uuid.UUID, **kwargs) -> MediaFile | None:
        filtered = {k: v for k, v in kwargs.items() if v is not None}
        if filtered:
            await self._db.execute(update(MediaFile).where(MediaFile.id == file_id).values(**filtered))
            await self._db.flush()
        return await self.get_by_id(file_id)

    async def delete(self, file_id: uuid.UUID) -> bool:
        result = await self._db.execute(delete(MediaFile).where(MediaFile.id == file_id))
        await self._db.flush()
        return result.rowcount > 0
