"""Service for CMS page builder — pages, sections, scripts."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

import redis.asyncio as aioredis
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import CmsPage, CmsSection, CmsScript

CACHE_PREFIX = "cms:page:"
CACHE_TTL = 60  # seconds


class CmsService:
    def __init__(self, db: AsyncSession, redis: aioredis.Redis | None = None) -> None:
        self.db = db
        self.redis = redis

    # ─── Helpers ──────────────────────────────────────────────────────────────

    def _new_id(self) -> str:
        return str(uuid.uuid4())

    async def _invalidate_cache(self, slug: str) -> None:
        if self.redis:
            await self.redis.delete(f"{CACHE_PREFIX}{slug}")

    # ─── Pages — CRUD ────────────────────────────────────────────────────────

    async def list_pages(self, status: str | None = None) -> list[CmsPage]:
        stmt = (
            select(CmsPage)
            .options(selectinload(CmsPage.sections), selectinload(CmsPage.scripts))
            .order_by(CmsPage.updated_at.desc())
        )
        if status:
            stmt = stmt.where(CmsPage.status == status)
        result = await self.db.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_page(self, page_id: str) -> CmsPage | None:
        stmt = (
            select(CmsPage)
            .where(CmsPage.id == page_id)
            .options(selectinload(CmsPage.sections), selectinload(CmsPage.scripts))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_page(self, data: dict[str, Any], created_by: str | None = None) -> CmsPage:
        page = CmsPage(
            id=self._new_id(),
            created_by=created_by,
            updated_by=created_by,
            **data,
        )
        self.db.add(page)
        await self.db.flush()
        # Reload with relationships
        return await self.get_page(page.id)  # type: ignore[return-value]

    async def update_page(self, page_id: str, data: dict[str, Any], updated_by: str | None = None) -> CmsPage | None:
        page = await self.get_page(page_id)
        if page is None:
            return None
        old_slug = page.slug
        for key, value in data.items():
            setattr(page, key, value)
        page.updated_by = updated_by
        page.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        # Invalidate old and new slug caches
        await self._invalidate_cache(old_slug)
        if page.slug != old_slug:
            await self._invalidate_cache(page.slug)
        return await self.get_page(page.id)  # type: ignore[return-value]

    async def delete_page(self, page_id: str) -> bool:
        page = await self.get_page(page_id)
        if page is None:
            return False
        slug = page.slug
        await self.db.delete(page)
        await self.db.flush()
        await self._invalidate_cache(slug)
        return True

    # ─── Publish / Unpublish ──────────────────────────────────────────────────

    async def publish_page(self, page_id: str, updated_by: str | None = None) -> CmsPage | None:
        page = await self.get_page(page_id)
        if page is None:
            return None
        now = datetime.now(timezone.utc)
        page.status = "published"
        page.published_at = now
        page.unpublished_at = None
        page.updated_by = updated_by
        page.updated_at = now
        await self.db.flush()
        await self._invalidate_cache(page.slug)
        return await self.get_page(page.id)  # type: ignore[return-value]

    async def unpublish_page(self, page_id: str, updated_by: str | None = None) -> CmsPage | None:
        page = await self.get_page(page_id)
        if page is None:
            return None
        now = datetime.now(timezone.utc)
        page.status = "draft"
        page.unpublished_at = now
        page.updated_by = updated_by
        page.updated_at = now
        await self.db.flush()
        await self._invalidate_cache(page.slug)
        return await self.get_page(page.id)  # type: ignore[return-value]

    # ─── Duplicate ────────────────────────────────────────────────────────────

    async def duplicate_page(self, page_id: str, created_by: str | None = None) -> CmsPage | None:
        original = await self.get_page(page_id)
        if original is None:
            return None
        new_id = self._new_id()
        now = datetime.now(timezone.utc)
        clone = CmsPage(
            id=new_id,
            slug=f"{original.slug}-copy-{new_id[:8]}",
            title=f"{original.title} (copia)",
            status="draft",
            published_at=None,
            unpublished_at=None,
            seo_title=original.seo_title,
            seo_description=original.seo_description,
            seo_keywords=original.seo_keywords,
            og_title=original.og_title,
            og_description=original.og_description,
            og_image=original.og_image,
            og_type=original.og_type,
            twitter_card=original.twitter_card,
            canonical_url=None,
            robots=original.robots,
            json_ld=original.json_ld,
            lang=original.lang,
            navbar_config=original.navbar_config,
            footer_config=original.footer_config,
            theme_overrides=original.theme_overrides,
            created_by=created_by,
            updated_by=created_by,
        )
        self.db.add(clone)
        await self.db.flush()

        # Clone sections
        for sec in original.sections:
            self.db.add(CmsSection(
                id=self._new_id(),
                page_id=new_id,
                block_type=sec.block_type,
                sort_order=sec.sort_order,
                is_visible=sec.is_visible,
                config=sec.config,
                css_class=sec.css_class,
                anchor_id=sec.anchor_id,
            ))

        # Clone page-level scripts
        for scr in original.scripts:
            self.db.add(CmsScript(
                id=self._new_id(),
                page_id=new_id,
                name=scr.name,
                placement=scr.placement,
                script_content=scr.script_content,
                is_active=scr.is_active,
                sort_order=scr.sort_order,
            ))

        await self.db.flush()
        return await self.get_page(new_id)

    # ─── Public page (cached) ────────────────────────────────────────────────

    async def get_public_page(self, slug: str) -> dict[str, Any] | None:
        # Try Redis cache first
        if self.redis:
            cached = await self.redis.get(f"{CACHE_PREFIX}{slug}")
            if cached:
                return json.loads(cached)

        stmt = (
            select(CmsPage)
            .where(CmsPage.slug == slug, CmsPage.status == "published")
            .options(selectinload(CmsPage.sections), selectinload(CmsPage.scripts))
        )
        result = await self.db.execute(stmt)
        page = result.scalar_one_or_none()
        if page is None:
            return None

        # Build public response
        visible_sections = sorted(
            [s for s in page.sections if s.is_visible],
            key=lambda s: s.sort_order,
        )
        active_scripts = sorted(
            [s for s in page.scripts if s.is_active],
            key=lambda s: s.sort_order,
        )
        # Also include global scripts (page_id IS NULL)
        global_stmt = (
            select(CmsScript)
            .where(CmsScript.page_id.is_(None), CmsScript.is_active.is_(True))
            .order_by(CmsScript.sort_order)
        )
        global_result = await self.db.execute(global_stmt)
        global_scripts = list(global_result.scalars().all())

        all_scripts = global_scripts + active_scripts

        def _script_to_dict(s: CmsScript) -> dict:
            return {
                "id": s.id,
                "page_id": s.page_id,
                "name": s.name,
                "placement": s.placement,
                "script_content": s.script_content,
                "is_active": s.is_active,
                "sort_order": s.sort_order,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            }

        def _section_to_dict(s: CmsSection) -> dict:
            return {
                "id": s.id,
                "page_id": s.page_id,
                "block_type": s.block_type,
                "sort_order": s.sort_order,
                "is_visible": s.is_visible,
                "config": s.config,
                "css_class": s.css_class,
                "anchor_id": s.anchor_id,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            }

        data: dict[str, Any] = {
            "slug": page.slug,
            "title": page.title,
            "lang": page.lang,
            "seo_title": page.seo_title,
            "seo_description": page.seo_description,
            "seo_keywords": page.seo_keywords,
            "og_title": page.og_title,
            "og_description": page.og_description,
            "og_image": page.og_image,
            "og_type": page.og_type,
            "twitter_card": page.twitter_card,
            "canonical_url": page.canonical_url,
            "robots": page.robots,
            "json_ld": page.json_ld,
            "navbar_config": page.navbar_config,
            "footer_config": page.footer_config,
            "theme_overrides": page.theme_overrides,
            "sections": [_section_to_dict(s) for s in visible_sections],
            "scripts_head": [_script_to_dict(s) for s in all_scripts if s.placement == "head"],
            "scripts_body_start": [_script_to_dict(s) for s in all_scripts if s.placement == "body_start"],
            "scripts_body_end": [_script_to_dict(s) for s in all_scripts if s.placement == "body_end"],
        }

        # Cache in Redis
        if self.redis:
            await self.redis.setex(f"{CACHE_PREFIX}{slug}", CACHE_TTL, json.dumps(data, default=str))

        return data

    # ─── Sections — CRUD ──────────────────────────────────────────────────────

    async def create_section(self, page_id: str, data: dict[str, Any]) -> CmsSection | None:
        page = await self.get_page(page_id)
        if page is None:
            return None
        section = CmsSection(id=self._new_id(), page_id=page_id, **data)
        self.db.add(section)
        await self.db.flush()
        await self.db.refresh(section)
        await self._invalidate_cache(page.slug)
        return section

    async def update_section(self, section_id: str, data: dict[str, Any]) -> CmsSection | None:
        stmt = select(CmsSection).where(CmsSection.id == section_id).options(selectinload(CmsSection.page))
        result = await self.db.execute(stmt)
        section = result.scalar_one_or_none()
        if section is None:
            return None
        for key, value in data.items():
            setattr(section, key, value)
        section.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(section)
        if section.page:
            await self._invalidate_cache(section.page.slug)
        return section

    async def delete_section(self, section_id: str) -> bool:
        stmt = select(CmsSection).where(CmsSection.id == section_id).options(selectinload(CmsSection.page))
        result = await self.db.execute(stmt)
        section = result.scalar_one_or_none()
        if section is None:
            return False
        slug = section.page.slug if section.page else None
        await self.db.delete(section)
        await self.db.flush()
        if slug:
            await self._invalidate_cache(slug)
        return True

    async def reorder_sections(self, page_id: str, items: list[dict[str, Any]]) -> list[CmsSection]:
        page = await self.get_page(page_id)
        if page is None:
            return []
        for item in items:
            await self.db.execute(
                update(CmsSection)
                .where(CmsSection.id == item["id"], CmsSection.page_id == page_id)
                .values(sort_order=item["sort_order"], updated_at=datetime.now(timezone.utc))
            )
        await self.db.flush()
        await self._invalidate_cache(page.slug)
        # Return updated sections
        stmt = (
            select(CmsSection)
            .where(CmsSection.page_id == page_id)
            .order_by(CmsSection.sort_order)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ─── Scripts — CRUD ───────────────────────────────────────────────────────

    async def list_scripts(self, page_id: str | None = None) -> list[CmsScript]:
        stmt = select(CmsScript).order_by(CmsScript.sort_order)
        if page_id is not None:
            stmt = stmt.where(CmsScript.page_id == page_id)
        else:
            stmt = stmt.where(CmsScript.page_id.is_(None))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_script(self, data: dict[str, Any]) -> CmsScript:
        script = CmsScript(id=self._new_id(), **data)
        self.db.add(script)
        await self.db.flush()
        await self.db.refresh(script)
        # Invalidate page cache if page-level script
        if script.page_id:
            page = await self.get_page(script.page_id)
            if page:
                await self._invalidate_cache(page.slug)
        return script

    async def update_script(self, script_id: str, data: dict[str, Any]) -> CmsScript | None:
        stmt = select(CmsScript).where(CmsScript.id == script_id)
        result = await self.db.execute(stmt)
        script = result.scalar_one_or_none()
        if script is None:
            return None
        for key, value in data.items():
            setattr(script, key, value)
        script.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(script)
        if script.page_id:
            page = await self.get_page(script.page_id)
            if page:
                await self._invalidate_cache(page.slug)
        return script

    async def delete_script(self, script_id: str) -> bool:
        stmt = select(CmsScript).where(CmsScript.id == script_id)
        result = await self.db.execute(stmt)
        script = result.scalar_one_or_none()
        if script is None:
            return False
        page_id = script.page_id
        await self.db.delete(script)
        await self.db.flush()
        if page_id:
            page = await self.get_page(page_id)
            if page:
                await self._invalidate_cache(page.slug)
        return True
