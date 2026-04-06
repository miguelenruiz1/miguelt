"""Authentication endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile, status
from jwt import PyJWTError as JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    CurrentUser,
    get_redis,
    get_tenant_id,
    login_rate_limit,
    password_reset_rate_limit,
    register_rate_limit,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.settings import get_settings
from app.db.session import get_db_session
from app.domain.schemas import (
    AcceptInvitationRequest,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    ResetPasswordRequest,
    TokenRefreshRequest,
    UpdateProfileRequest,
    UserResponse,
    RoleSlim,
)
from app.repositories.user_repo import UserRepository
from app.services.auth_service import AuthService
from app.services.user_service import UserService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _ip(request: Request) -> str | None:
    ff = request.headers.get("X-Forwarded-For")
    if ff:
        return ff.split(",")[0].strip()
    return request.client.host if request.client else None


async def _build_user_response(user, db: AsyncSession) -> UserResponse:
    auth_svc = AuthService(db)
    roles = await auth_svc.get_roles(user)
    permissions = await auth_svc.get_permissions(user)
    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        tenant_id=user.tenant_id,
        avatar_url=user.avatar_url,
        phone=user.phone,
        job_title=user.job_title,
        company=user.company,
        bio=user.bio,
        timezone=user.timezone,
        language=user.language,
        invitation_sent_at=user.invitation_sent_at,
        invitation_accepted_at=user.invitation_accepted_at,
        must_change_password=user.must_change_password,
        onboarding_completed=user.onboarding_completed,
        onboarding_step=user.onboarding_step,
        created_at=user.created_at,
        updated_at=user.updated_at,
        roles=[RoleSlim(id=r.id, name=r.name, slug=r.slug) for r in roles],
        permissions=sorted(permissions),
    )


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    body: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    _rl: Annotated[None, Depends(register_rate_limit)] = None,
) -> UserResponse:
    # Auto-generate tenant slug from company or username when not provided
    tenant_id = body.tenant_id
    if not tenant_id:
        import re, secrets
        base = body.company or body.username
        slug = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")[:40]
        suffix = secrets.token_hex(3)
        tenant_id = f"{slug}-{suffix}"

    svc = AuthService(db)
    user = await svc.register(
        email=body.email,
        username=body.username,
        full_name=body.full_name,
        password=body.password,
        tenant_id=tenant_id,
        phone=body.phone,
        job_title=body.job_title,
        company=body.company,
    )
    return await _build_user_response(user, db)


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    tenant_id: Annotated[str, Depends(get_tenant_id)],
    _rl: Annotated[None, Depends(login_rate_limit)] = None,
) -> LoginResponse:
    svc = AuthService(db)
    user = await svc.authenticate(body.email, body.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # Sync permissions/roles for this tenant (picks up newly added permissions)
    await svc._ensure_seeded(user.tenant_id)
    await db.flush()

    access_token = create_access_token(user.id, user.tenant_id)
    refresh_token, jti = create_refresh_token(user.id, user.tenant_id)

    settings = get_settings()
    ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
    await redis.setex(f"refresh:{user.id}:{jti}", ttl, "1")

    await svc.audit(
        action="user.login",
        tenant_id=user.tenant_id,
        user=user,
        resource_type="user",
        resource_id=user.id,
        ip_address=_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )

    user_resp = await _build_user_response(user, db)
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user_resp,
        permissions=user_resp.permissions,
    )


@router.post("/refresh", response_model=LoginResponse)
async def refresh_tokens(
    body: TokenRefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
) -> LoginResponse:
    creds_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
    )
    try:
        payload = decode_token(body.refresh_token)
    except JWTError:
        raise creds_exc

    if payload.get("type") != "refresh":
        raise creds_exc

    user_id = payload.get("sub")
    jti = payload.get("jti")
    if not user_id or not jti:
        raise creds_exc

    key = f"refresh:{user_id}:{jti}"
    if not await redis.exists(key):
        raise creds_exc

    # Delete old refresh token
    await redis.delete(key)

    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user or not user.is_active:
        raise creds_exc

    # Issue new pair
    access_token = create_access_token(user.id, user.tenant_id)
    new_refresh, new_jti = create_refresh_token(user.id, user.tenant_id)

    settings = get_settings()
    ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
    await redis.setex(f"refresh:{user.id}:{new_jti}", ttl, "1")

    user_resp = await _build_user_response(user, db)
    return LoginResponse(
        access_token=access_token,
        refresh_token=new_refresh,
        user=user_resp,
        permissions=user_resp.permissions,
    )


@router.post("/logout", status_code=204, response_class=Response)
async def logout(
    request: Request,
    current_user: CurrentUser,
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    # Blacklist the access token
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    if token:
        try:
            payload = decode_token(token)
            exp = payload.get("exp", 0)
            remaining = max(int(exp - datetime.now(timezone.utc).timestamp()), 1)
            await redis.setex(f"blacklist:access:{token}", remaining, "1")
        except JWTError:
            pass

    # Delete all refresh tokens for this user
    pattern = f"refresh:{current_user.id}:*"
    keys = await redis.keys(pattern)
    if keys:
        await redis.delete(*keys)

    svc = AuthService(db)
    await svc.audit(
        action="user.logout",
        tenant_id=current_user.tenant_id,
        user=current_user,
    )
    return Response(status_code=204)


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserResponse:
    return await _build_user_response(current_user, db)


@router.patch("/me", response_model=UserResponse)
async def update_me(
    body: UpdateProfileRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserResponse:
    repo = UserRepository(db)
    updates = body.model_dump(exclude_none=True)

    # Email uniqueness check
    if "email" in updates and updates["email"] != current_user.email:
        existing = await repo.get_by_email(updates["email"])
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already in use",
            )

    # Username uniqueness check
    if "username" in updates and updates["username"] != current_user.username:
        existing = await repo.get_by_username(updates["username"])
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already taken",
            )

    if updates:
        svc = UserService(db)
        await svc.update(current_user.id, **updates)

    updated_user = await repo.get_by_id(current_user.id)
    return await _build_user_response(updated_user, db)


@router.post("/me/avatar", response_model=UserResponse)
async def upload_avatar(
    file: UploadFile,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserResponse:
    """Upload avatar via media-service and store reference."""
    from app.clients.media_client import upload_file as media_upload, delete_file as media_delete

    settings = get_settings()

    if file.content_type not in ("image/jpeg", "image/png", "image/webp", "image/gif"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato no soportado. Usa JPG, PNG, WebP o GIF.",
        )

    content = await file.read()
    if len(content) > settings.MAX_AVATAR_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"La imagen excede el límite de {settings.MAX_AVATAR_SIZE // (1024*1024)} MB.",
        )

    media_file = await media_upload(
        tenant_id=current_user.tenant_id,
        file_bytes=content,
        filename=file.filename or f"avatar-{current_user.id}.{file.content_type.split('/')[-1]}",
        content_type=file.content_type,
        category="general",
        document_type="avatar",
        title=f"Avatar — {current_user.full_name}",
        uploaded_by=current_user.id,
    )
    if not media_file:
        raise HTTPException(status_code=502, detail="Error al subir avatar a media-service")

    # Delete old avatar from media-service if it was a media reference
    old_url = current_user.avatar_url or ""
    if old_url and hasattr(current_user, 'avatar_media_file_id') and current_user.avatar_media_file_id:
        await media_delete(current_user.tenant_id, current_user.avatar_media_file_id)

    avatar_url = media_file["url"]
    repo = UserRepository(db)
    svc = UserService(db)
    await svc.update(current_user.id, avatar_url=avatar_url)

    updated_user = await repo.get_by_id(current_user.id)
    return await _build_user_response(updated_user, db)


@router.delete("/me/avatar", response_model=UserResponse)
async def delete_avatar(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserResponse:
    repo = UserRepository(db)
    svc = UserService(db)
    await svc.update(current_user.id, avatar_url=None)

    updated_user = await repo.get_by_id(current_user.id)
    return await _build_user_response(updated_user, db)


@router.patch("/me/password", status_code=204, response_class=Response)
async def change_password(
    body: ChangePasswordRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    svc = UserService(db)
    await svc.change_password(current_user, body.current_password, body.new_password)
    return Response(status_code=204)


@router.post("/accept-invitation", response_model=UserResponse)
async def accept_invitation(
    body: AcceptInvitationRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserResponse:
    svc = AuthService(db)
    user = await svc.accept_invitation(body.token, body.password)
    return await _build_user_response(user, db)


@router.post("/forgot-password", status_code=200)
async def forgot_password(
    body: ForgotPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    _rl: Annotated[None, Depends(password_reset_rate_limit)] = None,
) -> dict:
    svc = AuthService(db)
    await svc.request_password_reset(body.email, redis)
    # Always return 200 — don't reveal if email exists
    return {"detail": "Si el correo existe, recibirás un enlace para restablecer tu contraseña."}


@router.post("/reset-password", response_model=UserResponse)
async def reset_password(
    body: ResetPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
) -> UserResponse:
    svc = AuthService(db)
    user = await svc.reset_password(body.token, body.new_password, redis)
    return await _build_user_response(user, db)
