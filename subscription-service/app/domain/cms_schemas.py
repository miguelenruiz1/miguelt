"""Pydantic schemas for CMS page builder."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ─── Section ─────────────────────────────────────────────────────────────────

class CmsSectionCreate(BaseModel):
    block_type: str = Field(..., min_length=1, max_length=50)
    sort_order: int = 0
    is_visible: bool = True
    config: dict[str, Any] = Field(default_factory=dict)
    css_class: str | None = None
    anchor_id: str | None = None


class CmsSectionUpdate(BaseModel):
    block_type: str | None = None
    sort_order: int | None = None
    is_visible: bool | None = None
    config: dict[str, Any] | None = None
    css_class: str | None = None
    anchor_id: str | None = None


class CmsSectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    page_id: str
    block_type: str
    sort_order: int
    is_visible: bool
    config: dict[str, Any]
    css_class: str | None
    anchor_id: str | None
    created_at: datetime
    updated_at: datetime


# ─── Script ──────────────────────────────────────────────────────────────────

class CmsScriptCreate(BaseModel):
    page_id: str | None = None
    name: str = Field(..., min_length=1, max_length=100)
    placement: str = Field(default="head", pattern=r"^(head|body_start|body_end)$")
    script_content: str = Field(..., min_length=1)
    is_active: bool = True
    sort_order: int = 0


class CmsScriptUpdate(BaseModel):
    name: str | None = None
    placement: str | None = None
    script_content: str | None = None
    is_active: bool | None = None
    sort_order: int | None = None


class CmsScriptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    page_id: str | None
    name: str
    placement: str
    script_content: str
    is_active: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime


# ─── Page ────────────────────────────────────────────────────────────────────

class CmsPageCreate(BaseModel):
    slug: str = Field(..., min_length=1, max_length=255)
    title: str = Field(..., min_length=1, max_length=255)
    # SEO
    seo_title: str | None = None
    seo_description: str | None = None
    seo_keywords: str | None = None
    og_title: str | None = None
    og_description: str | None = None
    og_image: str | None = None
    og_type: str | None = None
    twitter_card: str | None = None
    canonical_url: str | None = None
    robots: str | None = None
    json_ld: dict[str, Any] | None = None
    lang: str = "es"
    # Layout
    navbar_config: dict[str, Any] | None = None
    footer_config: dict[str, Any] | None = None
    theme_overrides: dict[str, Any] | None = None


class CmsPageUpdate(BaseModel):
    slug: str | None = None
    title: str | None = None
    status: str | None = None
    # SEO
    seo_title: str | None = None
    seo_description: str | None = None
    seo_keywords: str | None = None
    og_title: str | None = None
    og_description: str | None = None
    og_image: str | None = None
    og_type: str | None = None
    twitter_card: str | None = None
    canonical_url: str | None = None
    robots: str | None = None
    json_ld: dict[str, Any] | None = None
    lang: str | None = None
    # Layout
    navbar_config: dict[str, Any] | None = None
    footer_config: dict[str, Any] | None = None
    theme_overrides: dict[str, Any] | None = None


class CmsPageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    slug: str
    title: str
    status: str
    published_at: datetime | None
    unpublished_at: datetime | None
    # SEO
    seo_title: str | None
    seo_description: str | None
    seo_keywords: str | None
    og_title: str | None
    og_description: str | None
    og_image: str | None
    og_type: str | None
    twitter_card: str | None
    canonical_url: str | None
    robots: str | None
    json_ld: dict[str, Any] | None
    lang: str
    # Layout
    navbar_config: dict[str, Any] | None
    footer_config: dict[str, Any] | None
    theme_overrides: dict[str, Any] | None
    # Audit
    created_by: str | None
    updated_by: str | None
    created_at: datetime
    updated_at: datetime
    # Relations
    sections: list[CmsSectionOut] = []
    scripts: list[CmsScriptOut] = []


# ─── Public page (rendered for visitors) ─────────────────────────────────────

class CmsPublicPageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    title: str
    lang: str
    # SEO
    seo_title: str | None
    seo_description: str | None
    seo_keywords: str | None
    og_title: str | None
    og_description: str | None
    og_image: str | None
    og_type: str | None
    twitter_card: str | None
    canonical_url: str | None
    robots: str | None
    json_ld: dict[str, Any] | None
    # Layout
    navbar_config: dict[str, Any] | None
    footer_config: dict[str, Any] | None
    theme_overrides: dict[str, Any] | None
    # Content
    sections: list[CmsSectionOut]
    # Scripts grouped by placement
    scripts_head: list[CmsScriptOut] = []
    scripts_body_start: list[CmsScriptOut] = []
    scripts_body_end: list[CmsScriptOut] = []


# ─── Reorder request ─────────────────────────────────────────────────────────

class ReorderItem(BaseModel):
    id: str
    sort_order: int


class ReorderRequest(BaseModel):
    items: list[ReorderItem]
