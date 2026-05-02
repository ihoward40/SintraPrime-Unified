"""
Role-Based Access Control (RBAC) for the SintraPrime Portal.

Role hierarchy:
  SUPER_ADMIN > FIRM_ADMIN > ATTORNEY > PARALEGAL > ACCOUNTANT > CLIENT > VIEWER

Permissions are checked via FastAPI dependencies.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum
from functools import lru_cache

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..auth.jwt_handler import TokenError, decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


# ── Roles ─────────────────────────────────────────────────────────────────────

class Role(StrEnum):
    SUPER_ADMIN = "SUPER_ADMIN"
    FIRM_ADMIN  = "FIRM_ADMIN"
    ATTORNEY    = "ATTORNEY"
    PARALEGAL   = "PARALEGAL"
    ACCOUNTANT  = "ACCOUNTANT"
    CLIENT      = "CLIENT"
    VIEWER      = "VIEWER"


# Role hierarchy for inheritance checks
ROLE_HIERARCHY: dict[Role, int] = {
    Role.SUPER_ADMIN: 100,
    Role.FIRM_ADMIN:  80,
    Role.ATTORNEY:    60,
    Role.PARALEGAL:   40,
    Role.ACCOUNTANT:  35,
    Role.CLIENT:      20,
    Role.VIEWER:      10,
}


# ── Permissions ───────────────────────────────────────────────────────────────

class Permission(StrEnum):
    # User management
    USER_CREATE          = "user:create"
    USER_READ            = "user:read"
    USER_UPDATE          = "user:update"
    USER_DELETE          = "user:delete"
    USER_INVITE          = "user:invite"
    USER_MANAGE_ROLES    = "user:manage_roles"

    # Client management
    CLIENT_CREATE        = "client:create"
    CLIENT_READ          = "client:read"
    CLIENT_UPDATE        = "client:update"
    CLIENT_DELETE        = "client:delete"

    # Case management
    CASE_CREATE          = "case:create"
    CASE_READ            = "case:read"
    CASE_UPDATE          = "case:update"
    CASE_DELETE          = "case:delete"
    CASE_ASSIGN          = "case:assign"
    CASE_CLOSE           = "case:close"
    CASE_READ_PRIVATE_NOTES = "case:read_private_notes"
    CASE_CONFLICT_CHECK  = "case:conflict_check"

    # Document management
    DOC_UPLOAD           = "document:upload"
    DOC_READ             = "document:read"
    DOC_UPDATE           = "document:update"
    DOC_DELETE           = "document:delete"
    DOC_SHARE            = "document:share"
    DOC_SHARE_EXTERNAL   = "document:share_external"
    DOC_DOWNLOAD         = "document:download"
    DOC_VERSION          = "document:version"
    DOC_BULK             = "document:bulk"
    DOC_SIGN             = "document:sign"

    # Messaging
    MSG_SEND             = "message:send"
    MSG_READ             = "message:read"
    MSG_DELETE           = "message:delete"
    MSG_CREATE_THREAD    = "message:create_thread"

    # Billing
    BILLING_READ         = "billing:read"
    BILLING_CREATE       = "billing:create"
    BILLING_UPDATE       = "billing:update"
    BILLING_DELETE       = "billing:delete"
    BILLING_TIME_TRACK   = "billing:time_track"
    BILLING_TRUST        = "billing:trust_accounting"
    BILLING_REPORT       = "billing:report"
    PAYMENT_PROCESS      = "payment:process"

    # Notifications
    NOTIF_READ           = "notification:read"
    NOTIF_MANAGE         = "notification:manage"

    # Admin
    ADMIN_DASHBOARD      = "admin:dashboard"
    ADMIN_SETTINGS       = "admin:settings"
    ADMIN_API_KEYS       = "admin:api_keys"
    ADMIN_AUDIT_LOG      = "admin:audit_log"
    ADMIN_BRANDING       = "admin:branding"
    ADMIN_QUOTA          = "admin:quota"
    ADMIN_SYSTEM         = "admin:system"  # SUPER_ADMIN only

    # Audit
    AUDIT_READ           = "audit:read"
    AUDIT_EXPORT         = "audit:export"


# ── Role → Permission mapping ─────────────────────────────────────────────────

ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.SUPER_ADMIN: frozenset(Permission),  # all permissions

    Role.FIRM_ADMIN: frozenset([
        # Users
        Permission.USER_CREATE, Permission.USER_READ, Permission.USER_UPDATE,
        Permission.USER_DELETE, Permission.USER_INVITE, Permission.USER_MANAGE_ROLES,
        # Clients
        Permission.CLIENT_CREATE, Permission.CLIENT_READ, Permission.CLIENT_UPDATE, Permission.CLIENT_DELETE,
        # Cases
        Permission.CASE_CREATE, Permission.CASE_READ, Permission.CASE_UPDATE,
        Permission.CASE_DELETE, Permission.CASE_ASSIGN, Permission.CASE_CLOSE,
        Permission.CASE_READ_PRIVATE_NOTES, Permission.CASE_CONFLICT_CHECK,
        # Documents
        Permission.DOC_UPLOAD, Permission.DOC_READ, Permission.DOC_UPDATE, Permission.DOC_DELETE,
        Permission.DOC_SHARE, Permission.DOC_SHARE_EXTERNAL, Permission.DOC_DOWNLOAD,
        Permission.DOC_VERSION, Permission.DOC_BULK, Permission.DOC_SIGN,
        # Messaging
        Permission.MSG_SEND, Permission.MSG_READ, Permission.MSG_DELETE, Permission.MSG_CREATE_THREAD,
        # Billing
        Permission.BILLING_READ, Permission.BILLING_CREATE, Permission.BILLING_UPDATE,
        Permission.BILLING_DELETE, Permission.BILLING_TIME_TRACK, Permission.BILLING_TRUST,
        Permission.BILLING_REPORT, Permission.PAYMENT_PROCESS,
        # Notifications
        Permission.NOTIF_READ, Permission.NOTIF_MANAGE,
        # Admin
        Permission.ADMIN_DASHBOARD, Permission.ADMIN_SETTINGS, Permission.ADMIN_API_KEYS,
        Permission.ADMIN_AUDIT_LOG, Permission.ADMIN_BRANDING, Permission.ADMIN_QUOTA,
        # Audit
        Permission.AUDIT_READ, Permission.AUDIT_EXPORT,
    ]),

    Role.ATTORNEY: frozenset([
        Permission.CLIENT_CREATE, Permission.CLIENT_READ, Permission.CLIENT_UPDATE,
        Permission.CASE_CREATE, Permission.CASE_READ, Permission.CASE_UPDATE,
        Permission.CASE_ASSIGN, Permission.CASE_CLOSE,
        Permission.CASE_READ_PRIVATE_NOTES, Permission.CASE_CONFLICT_CHECK,
        Permission.DOC_UPLOAD, Permission.DOC_READ, Permission.DOC_UPDATE,
        Permission.DOC_SHARE, Permission.DOC_SHARE_EXTERNAL, Permission.DOC_DOWNLOAD,
        Permission.DOC_VERSION, Permission.DOC_BULK, Permission.DOC_SIGN,
        Permission.MSG_SEND, Permission.MSG_READ, Permission.MSG_CREATE_THREAD,
        Permission.BILLING_READ, Permission.BILLING_CREATE, Permission.BILLING_UPDATE,
        Permission.BILLING_TIME_TRACK, Permission.BILLING_REPORT,
        Permission.NOTIF_READ,
        Permission.AUDIT_READ,
    ]),

    Role.PARALEGAL: frozenset([
        Permission.CLIENT_READ,
        Permission.CASE_READ, Permission.CASE_UPDATE,
        Permission.DOC_UPLOAD, Permission.DOC_READ, Permission.DOC_DOWNLOAD,
        Permission.DOC_VERSION, Permission.DOC_BULK,
        Permission.MSG_SEND, Permission.MSG_READ, Permission.MSG_CREATE_THREAD,
        Permission.BILLING_READ, Permission.BILLING_TIME_TRACK,
        Permission.NOTIF_READ,
    ]),

    Role.ACCOUNTANT: frozenset([
        Permission.CLIENT_READ,
        Permission.DOC_UPLOAD, Permission.DOC_READ, Permission.DOC_DOWNLOAD,
        Permission.BILLING_READ, Permission.BILLING_CREATE, Permission.BILLING_UPDATE,
        Permission.BILLING_TRUST, Permission.BILLING_REPORT, Permission.PAYMENT_PROCESS,
        Permission.NOTIF_READ,
        Permission.AUDIT_READ,
    ]),

    Role.CLIENT: frozenset([
        # Clients can only access their own data (enforced by RLS + service layer)
        Permission.CLIENT_READ,
        Permission.CASE_READ,
        Permission.DOC_READ, Permission.DOC_DOWNLOAD, Permission.DOC_SIGN,
        Permission.MSG_SEND, Permission.MSG_READ, Permission.MSG_CREATE_THREAD,
        Permission.BILLING_READ, Permission.PAYMENT_PROCESS,
        Permission.NOTIF_READ,
    ]),

    Role.VIEWER: frozenset([
        Permission.CLIENT_READ,
        Permission.CASE_READ,
        Permission.DOC_READ,
        Permission.MSG_READ,
        Permission.BILLING_READ,
        Permission.NOTIF_READ,
    ]),
}


# ── Current user model ────────────────────────────────────────────────────────

class CurrentUser:
    """Represents the authenticated user extracted from the JWT."""

    def __init__(self, payload: dict):
        self.user_id: str    = payload["sub"]
        self.tenant_id: str  = payload["tenant_id"]
        self.role: Role      = Role(payload["role"])
        self.permissions: frozenset[Permission] = frozenset(
            Permission(p) for p in payload.get("permissions", []) if p in Permission._value2member_map_
        )

    def has_permission(self, *perms: Permission) -> bool:
        return all(p in self.permissions for p in perms)

    def has_role(self, min_role: Role) -> bool:
        return ROLE_HIERARCHY.get(self.role, 0) >= ROLE_HIERARCHY.get(min_role, 0)

    def is_super_admin(self) -> bool:
        return self.role == Role.SUPER_ADMIN

    def is_firm_admin(self) -> bool:
        return self.role in (Role.SUPER_ADMIN, Role.FIRM_ADMIN)

    def is_staff(self) -> bool:
        """Attorney, Paralegal, Accountant, or above."""
        return self.has_role(Role.ACCOUNTANT)

    def is_client(self) -> bool:
        return self.role == Role.CLIENT


# ── FastAPI dependencies ──────────────────────────────────────────────────────

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser:
    """Extract and validate JWT, return CurrentUser. Raises 401 if invalid."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_access_token(credentials.credentials)
        return CurrentUser(payload)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_permissions(*perms: Permission) -> Callable:
    """FastAPI dependency factory. Checks that user has ALL listed permissions."""
    async def dependency(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        missing = [p for p in perms if not current_user.has_permission(p)]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permissions: {', '.join(missing)}",
            )
        return current_user
    return dependency


def require_role(min_role: Role) -> Callable:
    """Require user to have at least the given role level."""
    async def dependency(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not current_user.has_role(min_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role: {min_role.value} or higher",
            )
        return current_user
    return dependency


def require_same_tenant(current_user: CurrentUser, tenant_id: str) -> None:
    """Check that the current user belongs to the requested tenant."""
    if not current_user.is_super_admin() and current_user.tenant_id != str(tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: cross-tenant operation not allowed",
        )


@lru_cache
def get_role_permissions(role: Role) -> frozenset[Permission]:
    """Return the full permission set for a role (cached)."""
    return ROLE_PERMISSIONS.get(role, frozenset())
