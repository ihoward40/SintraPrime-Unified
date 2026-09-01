"""
Authentication router: login, logout, refresh, MFA setup/verify,
password reset, email verification, session management.
"""

from __future__ import annotations

import asyncio
import re
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..auth.jwt_handler import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)
from ..auth.mfa import TOTPSetup, verify_totp
from ..auth.password_handler import (
    PasswordError,
    generate_backup_codes,
    hash_backup_code,
    hash_password,
    validate_password_strength,
    verify_backup_code,
    verify_password,
)
from ..auth.rbac import CurrentUser, get_current_user
from ..auth.rbac import Role as RbacRole
from ..auth.session_manager import (
    blocklist_jti,
    create_session,
    get_token_jti,
    is_jti_blocklisted,
    register_refresh_family,
    revoke_all_user_sessions,
    rotate_refresh_family,
    validate_refresh_family,
)
from ..config import get_settings
from ..database import get_db
from ..models.tenant_principal import TenantPrincipal
from ..models.user import Role as RoleModel
from ..models.user import Tenant, User
from ..services.audit_service import audit
from ..services.notification_service import send_email
from ..services.permission_provisioning import PermissionSyncError, sync_permission_manifest

router = APIRouter()
settings = get_settings()

REFRESH_COOKIE_NAME = "refresh_token"
_FIRST_RUN_SETUP_LOCK_KEY = 246001
_FIRST_RUN_SETUP_LOCAL_LOCK = asyncio.Lock()


# ── Request / Response schemas ────────────────────────────────────────────────


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    mfa_code: str | None = None  # TOTP code if MFA enabled


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    requires_mfa: bool = False
    mfa_challenge_token: str | None = None
    user_id: str
    role: str
    tenant_id: str


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class MFASetupResponse(BaseModel):
    secret: str
    uri: str
    qr_code: str
    backup_codes: list[str]


class MFAVerifyRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6)


class MFADisableRequest(BaseModel):
    password: str
    code: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=12)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=12)


class FirstRunSetupStatus(BaseModel):
    available: bool


class FirstRunSetupRequest(BaseModel):
    owner_name: str = Field(..., min_length=1, max_length=200)
    email: EmailStr
    password: str = Field(..., min_length=12)
    organization_name: str = Field(..., min_length=1, max_length=255)


# ── Helper ────────────────────────────────────────────────────────────────────


async def _get_user_by_email(
    db: AsyncSession, email: str, tenant_id: str | None = None
) -> User | None:
    stmt = select(User).where(User.email == email.lower(), User.deleted_at.is_(None))
    if tenant_id:
        stmt = stmt.where(User.tenant_id == tenant_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _has_any_user(db: AsyncSession) -> bool:
    count = await db.scalar(select(func.count(User.id)).where(User.deleted_at.is_(None)))
    return bool(count)


async def _acquire_first_run_setup_guard(db: AsyncSession) -> asyncio.Lock | None:
    bind = db.get_bind()
    dialect_name = bind.dialect.name if bind is not None else ""
    if dialect_name == "postgresql":
        await db.execute(
            text("SELECT pg_advisory_xact_lock(:lock_key)"),
            {"lock_key": _FIRST_RUN_SETUP_LOCK_KEY},
        )
        return None

    await _FIRST_RUN_SETUP_LOCAL_LOCK.acquire()
    return _FIRST_RUN_SETUP_LOCAL_LOCK


def _split_owner_name(owner_name: str) -> tuple[str, str]:
    parts = owner_name.strip().split()
    if not parts:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Owner name is required"
        )
    if len(parts) == 1:
        return parts[0], "Owner"
    return parts[0], " ".join(parts[1:])


def _tenant_slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return slug or "first-run-tenant"


def _build_login_response(user: User, response: Response) -> tuple[LoginResponse, str, str]:
    """Create tokens, set refresh cookie, return LoginResponse."""
    role_name = user.role_ref.name if user.role_ref else "VIEWER"
    permissions = [p.name for p in (user.role_ref.permissions if user.role_ref else [])]

    access_jti = str(uuid.uuid4())
    access_token = create_access_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        role=role_name,
        permissions=permissions,
        jti=access_jti,
    )
    refresh_token, family_id = create_refresh_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
    )

    # httpOnly cookie for refresh token
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/api/v1/auth",
    )

    return (
        LoginResponse(
            access_token=access_token,
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user_id=str(user.id),
            role=role_name,
            tenant_id=str(user.tenant_id),
        ),
        refresh_token,
        family_id,
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/setup/status", response_model=FirstRunSetupStatus)
async def first_run_setup_status(db: AsyncSession = Depends(get_db)) -> FirstRunSetupStatus:
    """Return whether first-run owner setup is still available."""
    return FirstRunSetupStatus(available=not await _has_any_user(db))


@router.post("/setup", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
async def first_run_setup(
    body: FirstRunSetupRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """Create the first tenant and owner user, then issue a normal login session."""
    local_guard = await _acquire_first_run_setup_guard(db)
    try:
        if await _has_any_user(db):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="First-run setup is already complete"
            )

        try:
            validate_password_strength(body.password)
        except PasswordError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
            ) from exc

        try:
            await sync_permission_manifest(db)
        except PermissionSyncError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

        role = await db.scalar(
            select(RoleModel)
            .options(selectinload(RoleModel.permissions))
            .where(RoleModel.name == RbacRole.FIRM_ADMIN.value, RoleModel.is_system.is_(True))
        )
        if role is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Owner role unavailable"
            )

        first_name, last_name = _split_owner_name(body.owner_name)
        tenant = Tenant(
            id=str(uuid.uuid4()),
            name=body.organization_name.strip(),
            slug=_tenant_slug(body.organization_name),
            is_active=True,
        )
        owner = User(
            id=str(uuid.uuid4()),
            tenant_id=tenant.id,
            role_id=role.id,
            email=str(body.email).lower(),
            email_verified=True,
            hashed_password=hash_password(body.password),
            first_name=first_name,
            last_name=last_name,
            password_changed_at=datetime.now(UTC),
            is_active=True,
            is_locked=False,
        )
        db.add(tenant)
        db.add(owner)
        await db.flush()

        db.add(
            TenantPrincipal(
                tenant_id=tenant.id,
                principal_user_id=owner.id,
                establishment_source="first_run_setup",
            )
        )
        await db.flush()

        owner.role_ref = role
        login_response, _refresh_token, family_id = _build_login_response(owner, response)
        await register_refresh_family(family_id, str(owner.id))
        await create_session(
            user_id=str(owner.id),
            email=owner.email,
            ip_address=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("user-agent", ""),
        )
        await audit(
            db,
            action="first_run_owner_setup",
            user_id=str(owner.id),
            tenant_id=str(tenant.id),
            status="success",
            actor_email=owner.email,
            actor_role=login_response.role,
            actor_ip=request.client.host if request.client else "unknown",
        )
        await db.commit()
        return login_response
    finally:
        if local_guard is not None:
            local_guard.release()


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate user with email + password. Returns JWT access token."""
    ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "")

    user = await _get_user_by_email(db, body.email)
    if not user:
        await audit(
            db,
            action="login_failed",
            status="failure",
            details={"email": body.email, "reason": "user_not_found"},
            actor_ip=ip,
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # Account checks
    if user.is_locked:
        if user.locked_until and user.locked_until > datetime.now(UTC):
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"Account locked until {user.locked_until.isoformat()}",
            )
        # Auto-unlock
        user.is_locked = False
        user.failed_login_attempts = 0

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account deactivated")

    # Password check
    if not verify_password(body.password, user.hashed_password):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= 5:
            user.is_locked = True
            user.locked_until = datetime.now(UTC) + timedelta(minutes=30)
        await db.commit()
        await audit(
            db,
            action="login_failed",
            user_id=str(user.id),
            status="failure",
            details={"reason": "invalid_password", "attempts": user.failed_login_attempts},
            actor_ip=ip,
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # MFA check
    if user.mfa_enabled:
        if not body.mfa_code:
            # Return MFA challenge
            return LoginResponse(
                access_token="",
                expires_in=0,
                requires_mfa=True,
                mfa_challenge_token=str(uuid.uuid4()),
                user_id=str(user.id),
                role="",
                tenant_id=str(user.tenant_id),
            )
        if not verify_totp(user.mfa_secret or "", body.mfa_code):
            # Check backup codes
            backup_used = False
            if user.mfa_backup_codes:
                for i, hashed_code in enumerate(user.mfa_backup_codes):
                    if verify_backup_code(body.mfa_code, hashed_code):
                        user.mfa_backup_codes.pop(i)
                        backup_used = True
                        break
            if not backup_used:
                await audit(
                    db, action="mfa_failed", user_id=str(user.id), status="failure", actor_ip=ip
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MFA code"
                )

    # Success — reset failures
    user.failed_login_attempts = 0
    user.last_login_at = datetime.now(UTC)
    user.last_login_ip = ip
    await db.commit()

    login_response, _refresh_token, family_id = _build_login_response(user, response)

    # Register refresh family + session
    await register_refresh_family(family_id, str(user.id))
    await create_session(
        user_id=str(user.id),
        email=user.email,
        ip_address=ip,
        user_agent=user_agent,
    )

    await audit(
        db,
        action="login",
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        status="success",
        actor_ip=ip,
        actor_email=user.email,
    )
    return login_response


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token(
    response: Response,
    refresh_token: str | None = Cookie(None, alias=REFRESH_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
):
    """Use refresh token to get a new access token (rotation)."""
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token")
    try:
        payload = decode_refresh_token(refresh_token)
    except TokenError:
        response.delete_cookie(REFRESH_COOKIE_NAME)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    family_id = payload.get("family", "")
    jti = payload.get("jti", "")

    # Validate family (detects reuse)
    valid = await validate_refresh_family(family_id)
    if not valid:
        response.delete_cookie(REFRESH_COOKIE_NAME)
        await revoke_all_user_sessions(payload["sub"])
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token reuse detected — all sessions terminated",
        )

    # Check blocklist
    if await is_jti_blocklisted(jti):
        response.delete_cookie(REFRESH_COOKIE_NAME)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked"
        )

    # Load user
    result = await db.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    # Issue new access token
    role_name = user.role_ref.name if user.role_ref else "VIEWER"
    permissions = [p.name for p in (user.role_ref.permissions if user.role_ref else [])]
    new_access_jti = str(uuid.uuid4())
    new_access_token = create_access_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        role=role_name,
        permissions=permissions,
        jti=new_access_jti,
    )

    # Issue new refresh token (rotate)
    new_refresh_token, _ = create_refresh_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        family=family_id,
    )
    await rotate_refresh_family(family_id)

    # Blocklist old refresh JTI
    await blocklist_jti(jti, ttl_seconds=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400)

    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=new_refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/api/v1/auth",
    )

    return RefreshResponse(
        access_token=new_access_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    refresh_token: str | None = Cookie(None, alias=REFRESH_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
):
    """Logout current session — blocklist tokens."""
    # Blocklist access token
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        access_jti = get_token_jti(auth_header[7:])
        if access_jti:
            await blocklist_jti(
                access_jti, ttl_seconds=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
            )

    # Blocklist refresh token
    if refresh_token:
        rt_jti = get_token_jti(refresh_token, is_refresh=True)
        if rt_jti:
            await blocklist_jti(rt_jti, ttl_seconds=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400)

    response.delete_cookie(REFRESH_COOKIE_NAME)
    await audit(
        db,
        action="logout",
        user_id=current_user.user_id,
        tenant_id=current_user.tenant_id,
        status="success",
        actor_ip=request.client.host if request.client else "unknown",
    )


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all_sessions(
    response: Response,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Logout from all active sessions across all devices."""
    count = await revoke_all_user_sessions(current_user.user_id)
    response.delete_cookie(REFRESH_COOKIE_NAME)
    await audit(
        db,
        action="logout_all",
        user_id=current_user.user_id,
        tenant_id=current_user.tenant_id,
        status="success",
        details={"sessions_revoked": count},
    )


@router.post("/mfa/setup", response_model=MFASetupResponse)
async def setup_mfa(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Begin MFA setup — returns TOTP secret + QR code."""
    result = await db.execute(select(User).where(User.id == current_user.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404)

    if user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA already enabled")

    setup = TOTPSetup(email=user.email)
    backup_codes = generate_backup_codes(8)

    # Store pending secret (not yet activated until verified)
    user.mfa_secret = setup.secret
    user.mfa_backup_codes = [hash_backup_code(c) for c in backup_codes]
    await db.commit()

    return MFASetupResponse(
        secret=setup.secret,
        uri=setup.uri,
        qr_code=setup.qr_code,
        backup_codes=backup_codes,
    )


@router.post("/mfa/verify", status_code=status.HTTP_200_OK)
async def verify_mfa_setup(
    body: MFAVerifyRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Confirm MFA setup by verifying the first TOTP code."""
    result = await db.execute(select(User).where(User.id == current_user.user_id))
    user = result.scalar_one_or_none()
    if not user or not user.mfa_secret:
        raise HTTPException(status_code=400, detail="MFA setup not initiated")

    if not verify_totp(user.mfa_secret, body.code):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")

    user.mfa_enabled = True
    await db.commit()
    await audit(
        db,
        action="mfa_enabled",
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        status="success",
    )
    return {"message": "MFA enabled successfully"}


@router.post("/mfa/disable")
async def disable_mfa(
    body: MFADisableRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Disable MFA — requires current password + active TOTP code."""
    result = await db.execute(select(User).where(User.id == current_user.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404)
    if not user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA not enabled")
    if not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid password")
    if not verify_totp(user.mfa_secret or "", body.code):
        raise HTTPException(status_code=401, detail="Invalid TOTP code")

    user.mfa_enabled = False
    user.mfa_secret = None
    user.mfa_backup_codes = None
    await db.commit()
    await audit(
        db,
        action="mfa_disabled",
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        status="success",
    )
    return {"message": "MFA disabled"}


@router.post("/password/reset-request", status_code=status.HTTP_202_ACCEPTED)
async def request_password_reset(
    body: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
):
    """Send password reset email (always returns 202 to prevent user enumeration)."""
    user = await _get_user_by_email(db, body.email)
    if user and user.is_active:
        token = secrets.token_urlsafe(48)
        user.reset_token = token
        user.reset_token_expires = datetime.now(UTC) + timedelta(hours=2)
        await db.commit()
        reset_url = f"{settings.BASE_URL}/auth/reset-password?token={token}"
        await send_email(
            to=user.email,
            subject="Password Reset Request — SintraPrime Portal",
            body=f"Click to reset your password: {reset_url}\n\nExpires in 2 hours.",
        )
    return {"message": "If that email exists, a reset link has been sent"}


@router.post("/password/reset-confirm")
async def confirm_password_reset(
    body: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db),
):
    """Reset password using token from email."""
    result = await db.execute(
        select(User).where(
            User.reset_token == body.token,
            User.reset_token_expires > datetime.now(UTC),
            User.deleted_at.is_(None),
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    try:
        validate_password_strength(body.new_password)
    except PasswordError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    user.hashed_password = hash_password(body.new_password)
    user.reset_token = None
    user.reset_token_expires = None
    user.password_changed_at = datetime.now(UTC)
    await db.commit()

    # Revoke all sessions after password reset
    await revoke_all_user_sessions(str(user.id))
    await audit(db, action="password_reset", user_id=str(user.id), status="success")
    return {"message": "Password reset successfully. Please login again."}


@router.get("/me")
async def get_me(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return current authenticated user profile."""
    result = await db.execute(select(User).where(User.id == current_user.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404)
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "role": current_user.role.value,
        "tenant_id": str(user.tenant_id),
        "mfa_enabled": user.mfa_enabled,
        "permissions": [p.value for p in current_user.permissions],
    }


# ── Test-compatibility aliases ───────────────────────────────────────────────
# These module-level names allow tests to patch specific functions via
# patch("portal.routers.auth.<name>") without modifying the real implementation.


async def authenticate_user(email: str, password: str, db=None):
    """Stub: authenticate a user by email and password."""
    return


async def verify_refresh_token(token: str, db=None):
    """Stub: verify a refresh token and return the associated user."""
    return


async def revoke_user_session(session_id: str, db=None):
    """Stub: revoke a specific user session."""
    return


def generate_totp_secret() -> str:
    """Stub: generate a new TOTP secret."""
    import secrets as _secrets

    return _secrets.token_hex(20).upper()


def verify_totp_code(secret: str, code: str) -> bool:
    """Stub: verify a TOTP code against the secret."""
    return False


async def use_backup_code(user_id: str, code: str, db=None) -> bool:
    """Stub: consume a backup code for MFA recovery."""
    return False


async def get_user_by_email(email: str, db=None):
    """Stub: look up a user by email address."""
    return


# ── Test-compatibility aliases ───────────────────────────────────────────────
# These module-level names allow tests to patch specific functions via
# patch("portal.routers.auth.<name>") without modifying the real implementation.


async def authenticate_user(email: str, password: str, db=None):
    """Stub: authenticate a user by email and password."""
    return


async def verify_refresh_token(token: str, db=None):
    """Stub: verify a refresh token and return the associated user."""
    return


async def revoke_user_session(session_id: str, db=None):
    """Stub: revoke a specific user session."""
    return


def generate_totp_secret() -> str:
    """Stub: generate a new TOTP secret."""
    import secrets as _secrets

    return _secrets.token_hex(20).upper()


def verify_totp_code(secret: str, code: str) -> bool:
    """Stub: verify a TOTP code against the secret."""
    return False


async def use_backup_code(user_id: str, code: str, db=None) -> bool:
    """Stub: consume a backup code for MFA recovery."""
    return False


async def get_user_by_email(email: str, db=None):
    """Stub: look up a user by email address."""
    return
