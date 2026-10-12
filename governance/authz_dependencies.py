"""G4 — Governance API authentication & authorization dependencies.

SP-PARLIAMENT-A2A-REVOCATION-DESIGN-CERT-002 §4: every governance API route requires a
verified Principal JWT. Audit/ledger identity is derived ONLY from verified token
claims; caller-supplied strings (e.g. ``authorized_by``) are metadata at most and can
never establish authority.

Reuses the approved portal JWT verification facility (portal.auth.jwt_handler) and
configuration (portal.config) — no second token-validation system is introduced.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:  # pragma: no cover - exercised implicitly when FastAPI is absent
    from fastapi import Depends, HTTPException, Request

    _FASTAPI_AVAILABLE = True
except ImportError:  # pragma: no cover
    _FASTAPI_AVAILABLE = False

from portal.auth.jwt_handler import TokenError, decode_access_token
from portal.auth.rbac import ROLE_HIERARCHY, Role
from portal.auth.session_manager import is_jti_blocklisted

# Emergency/revocation authority is platform-level: only SUPER_ADMIN (hierarchy 100)
# holds it by role. Tokens may alternatively carry the scope explicitly in their
# ``permissions`` claim (e.g. machine principals minted by the platform).
EMERGENCY_AUTHORITY_MIN_LEVEL = ROLE_HIERARCHY[Role.SUPER_ADMIN]

SCOPE_GOVERNANCE_ACCESS = "governance_access"
SCOPE_EMERGENCY_STOP = "emergency_stop"
SCOPE_REVOCATION = "revocation"
SCOPE_EMERGENCY_STOP_CLEAR = "emergency_stop_clear"

# G4 STOP/CLEAR separation (SP-PARLIAMENT-A2A-G4-STOP-CLEAR-AUTHZ-FIX-002):
# authority to stop is NOT authority to restart. Intervention scopes are NEVER
# granted through broad roles — they exist only as explicit ``permissions``
# claims on the verified token, so token issuance cannot unintentionally grant
# both permissions via implicit privilege expansion.
_ROLE_GRANTED_SCOPES: dict[str, frozenset[str]] = {
    Role.SUPER_ADMIN: frozenset({SCOPE_GOVERNANCE_ACCESS}),
}


@dataclass(frozen=True)
class PrincipalContext:
    """Verified principal derived exclusively from JWT claims."""

    subject: str
    tenant_id: str
    role: str
    jti: str
    scopes: frozenset[str]

    @property
    def role_level(self) -> int:
        try:
            return ROLE_HIERARCHY[Role(self.role)]
        except (ValueError, KeyError):
            return -1


def _build_principal(payload: dict[str, Any]) -> PrincipalContext:
    role = str(payload.get("role", ""))
    granted = set(_ROLE_GRANTED_SCOPES.get(role, frozenset()))
    declared = payload.get("permissions") or []
    if isinstance(declared, (list, tuple, set)):
        granted.update(str(s) for s in declared)
    return PrincipalContext(
        subject=str(payload.get("sub", "")),
        tenant_id=str(payload.get("tenant_id", "")),
        role=role,
        jti=str(payload.get("jti", "")),
        scopes=frozenset(granted),
    )


def _unauthorized(detail: str = "Not authenticated") -> "HTTPException":
    return HTTPException(status_code=401, detail=detail)


def _forbidden(detail: str = "Not authorized") -> "HTTPException":
    return HTTPException(status_code=403, detail=detail)


async def verify_principal_token(request: "Request") -> PrincipalContext:
    """FastAPI dependency: require and verify a Bearer access JWT.

    Anonymous or invalid tokens -> HTTP 401. Revoked tokens (JTI blocklist) are
    rejected with 401. The returned PrincipalContext is the ONLY recognized
    identity for audit/ledger attribution.
    """
    if not _FASTAPI_AVAILABLE:  # pragma: no cover - FastAPI guarded upstream
        raise RuntimeError("FastAPI is not installed")
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise _unauthorized()
    token = header[len("Bearer ") :].strip()
    if not token:
        raise _unauthorized()
    try:
        payload = decode_access_token(token)
    except TokenError as exc:
        raise _unauthorized(f"Invalid token: {exc}") from exc
    jti = payload.get("jti")
    if jti and await is_jti_blocklisted(jti):
        raise _unauthorized("Token has been revoked")
    principal = _build_principal(payload)
    if not principal.subject:
        raise _unauthorized("Token missing subject")
    return principal


# Module-level singleton so downstream default arguments reference a name instead
# of performing a call in a default (ruff B008). The ternary is lazy, so
# Depends(...) is never evaluated without FastAPI.
PrincipalDependency = (
    Depends(verify_principal_token) if _FASTAPI_AVAILABLE else None  # type: ignore[assignment]
)


def require_scope(scope: str):
    """Dependency factory: require ``scope`` for the verified principal.

    Satisfied when the scope is in the token's ``permissions`` claim or is granted
    to the principal's role by the platform role map. Otherwise HTTP 403.
    """

    def _dependency(
        principal: PrincipalContext = PrincipalDependency,
    ) -> PrincipalContext:
        if scope not in principal.scopes:
            raise _forbidden(f"Missing required scope: {scope}")
        return principal

    return _dependency


def bind_tenant(expected_tenant_id: str):
    """Dependency factory: bind the verified principal to a tenant scope.

    SUPER_ADMIN (platform level) is exempt; every other principal whose token
    tenant differs from ``expected_tenant_id`` receives HTTP 403.
    """

    def _dependency(
        principal: PrincipalContext = PrincipalDependency,
    ) -> PrincipalContext:
        if principal.role_level >= EMERGENCY_AUTHORITY_MIN_LEVEL:
            return principal
        if principal.tenant_id != expected_tenant_id:
            raise _forbidden("Cross-tenant access denied")
        return principal

    return _dependency


def emergency_authority_dependency():
    """Convenience: governance emergency-stop chain (verify + emergency_stop scope)."""

    return Depends(require_scope(SCOPE_EMERGENCY_STOP))


__all__ = [
    "EMERGENCY_AUTHORITY_MIN_LEVEL",
    "PrincipalContext",
    "PrincipalDependency",
    "SCOPE_EMERGENCY_STOP",
    "SCOPE_EMERGENCY_STOP_CLEAR",
    "SCOPE_GOVERNANCE_ACCESS",
    "SCOPE_REVOCATION",
    "bind_tenant",
    "emergency_authority_dependency",
    "require_scope",
    "verify_principal_token",
]
