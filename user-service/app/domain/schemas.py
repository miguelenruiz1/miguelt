"""Pydantic schemas for user-service."""
from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

T = TypeVar("T")


# ─── Auth ─────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=100)
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8)
    phone: str | None = Field(None, max_length=30)
    job_title: str | None = Field(None, max_length=255)
    company: str | None = Field(None, max_length=255)
    tenant_id: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class UpdateProfileRequest(BaseModel):
    full_name: str | None = Field(None, max_length=255)
    username: str | None = Field(None, min_length=3, max_length=100)
    email: EmailStr | None = None
    avatar_url: str | None = None
    phone: str | None = Field(None, max_length=30)
    job_title: str | None = Field(None, max_length=255)
    company: str | None = Field(None, max_length=255)
    bio: str | None = None
    timezone: str | None = Field(None, max_length=100)
    language: str | None = Field(None, max_length=10)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class InviteUserRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    role_ids: list[str] = []


class AdminUpdateUser(BaseModel):
    full_name: str | None = Field(None, min_length=1, max_length=255)
    is_active: bool | None = None
    username: str | None = Field(None, min_length=1, max_length=150)
    phone: str | None = None
    job_title: str | None = None
    company: str | None = None
    bio: str | None = None
    timezone: str | None = None
    language: str | None = None


class AcceptInvitationRequest(BaseModel):
    token: str
    password: str = Field(min_length=8)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


# ─── Roles & Permissions ─────────────────────────────────────────────────────

class RoleSlim(BaseModel):
    id: str
    name: str
    slug: str

    model_config = {"from_attributes": True}


class PermissionResponse(BaseModel):
    id: str
    name: str
    slug: str
    module: str
    description: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class RoleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    slug: str = Field(min_length=1, max_length=100)
    description: str | None = None


class RoleUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)
    description: str | None = None


class RoleResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: str | None = None
    is_system: bool
    tenant_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BulkSetPermissionsRequest(BaseModel):
    permission_ids: list[str]


class RoleTemplateResponse(BaseModel):
    id: str
    tenant_id: str
    slug: str
    name: str
    description: str | None = None
    icon: str
    permissions: list[str]
    is_default: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RoleTemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    slug: str = Field(min_length=1, max_length=100)
    description: str | None = None
    icon: str = Field(default="shield", max_length=50)
    permissions: list[str] = []


class RoleTemplateUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)
    description: str | None = None
    icon: str | None = Field(None, max_length=50)
    permissions: list[str] | None = None


class CreateFromTemplateRequest(BaseModel):
    template_id: str


# ─── Users ───────────────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    full_name: str
    is_active: bool
    is_superuser: bool
    tenant_id: str
    avatar_url: str | None = None
    phone: str | None = None
    job_title: str | None = None
    company: str | None = None
    bio: str | None = None
    timezone: str | None = None
    language: str | None = None
    invitation_sent_at: datetime | None = None
    invitation_accepted_at: datetime | None = None
    must_change_password: bool = False
    onboarding_completed: bool = False
    onboarding_step: str = "welcome"
    created_at: datetime
    updated_at: datetime
    roles: list[RoleSlim] = []
    permissions: list[str] = []

    model_config = {"from_attributes": True}


# ─── Login ───────────────────────────────────────────────────────────────────

class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse
    permissions: list[str]


# ─── Audit ───────────────────────────────────────────────────────────────────

class AuditLogResponse(BaseModel):
    id: str
    user_id: str | None = None
    user_email: str | None = None
    action: str
    resource_type: str | None = None
    resource_id: str | None = None
    metadata: dict | None = Field(None, alias="event_data")
    ip_address: str | None = None
    user_agent: str | None = None
    tenant_id: str
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


# ─── Email Templates ─────────────────────────────────────────────────────

class EmailTemplateOut(BaseModel):
    id: str
    tenant_id: str
    slug: str
    subject: str
    html_body: str
    description: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EmailTemplateUpdate(BaseModel):
    subject: str | None = Field(None, max_length=500)
    html_body: str | None = None
    description: str | None = None
    is_active: bool | None = None


class TestEmailRequest(BaseModel):
    to: EmailStr | None = None


# ─── Email Config ────────────────────────────────────────────────────────────

class EmailConfigOut(BaseModel):
    id: str
    tenant_id: str
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    smtp_use_tls: bool = True
    admin_email: str | None = None
    test_email: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EmailConfigUpdate(BaseModel):
    smtp_host: str | None = Field(None, max_length=255)
    smtp_port: int | None = None
    smtp_user: str | None = Field(None, max_length=255)
    smtp_password: str | None = Field(None, max_length=500)
    smtp_from: str | None = Field(None, max_length=255)
    smtp_use_tls: bool | None = None
    admin_email: str | None = Field(None, max_length=255)
    test_email: str | None = Field(None, max_length=255)


# ─── Pagination ──────────────────────────────────────────────────────────────

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    offset: int
    limit: int
