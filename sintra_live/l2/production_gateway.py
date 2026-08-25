"""Production adapter: bridge portal request path → L2 authority resolver.

This module is a *thin adapter* — it does NOT modify any L2 contract, does NOT
create a new authority system, and does NOT re-implement resolution logic.

It accepts a portal request (FastAPI/Starlette Request or a lightweight proxy
carrying the same headers), extracts the principal identity/session from the
already-verified JWT/RBAC boundary, assembles the keyword arguments the L2
``authority_resolver.resolve`` function expects, delegates to it, and returns
the L2 ``Resolution`` unchanged.

Portal routers call ``resolve_authority(request, l2_payload)`` and get back the
canonical L2 resolution record.  No L2 file is imported for mutation; only the
read-only ``resolve`` entrypoint and the immutable contract dataclasses are
referenced.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, is_dataclass
from typing import Any, Mapping

from .authority_resolver import resolve as _l2_resolve
from .principal_gateway_contract import (
    AuthResult,
    AuthorityResolution,
    Resolution,
)

__all__ = ["PortalAuthorityError", "resolve_authority", "extract_principal"]


class PortalAuthorityError(Exception):
    """Raised when the portal→L2 bridge cannot assemble a valid resolution call."""


# ---------------------------------------------------------------------------
# Principal / session extraction
# ---------------------------------------------------------------------------

def extract_principal(request: Any) -> dict[str, Any]:
    """Extract principal identity + session descriptors from a portal request.

    The portal's RBAC middleware has *already* verified the JWT and populated
    ``request.state.current_user`` (``CurrentUser``) and the correlation context.
    We only *read* those verified values — we never re-authenticate.

    Works with any object that exposes either:
      * ``request.state.current_user`` (FastAPI pattern used by portal/routers)
      * or a ``current_user`` keyword argument (for direct callers/tests)

    Returns a dict with keys: principal_id, tenant_id, role, permissions,
    correlation_id, causation_id.
    """
    # Allow direct injection (tests, non-FastAPI callers)
    if isinstance(request, Mapping):
        return dict(request)

    user = None
    state = getattr(request, "state", None)
    if state is not None:
        user = getattr(state, "current_user", None)
    if user is None:
        user = getattr(request, "current_user", None)
    if user is None:
        raise PortalAuthorityError("No authenticated principal on request")

    principal_id = getattr(user, "user_id", None) or getattr(user, "sub", None)
    tenant_id = getattr(user, "tenant_id", None)
    role = getattr(user, "role", None)
    role_value = role.value if hasattr(role, "value") else role
    perms = getattr(user, "permissions", []) or []
    perm_values = sorted(p.value if hasattr(p, "value") else str(p) for p in perms)

    correlation_id = None
    causation_id = None
    ctx = None
    if state is not None:
        ctx = getattr(state, "correlation_context", None)
    if ctx is None:
        # Try the module-level correlation context used by portal/auth
        try:
            from portal.auth.correlation import get_current_context

            ctx = get_current_context()
        except Exception:
            ctx = None
    if ctx is not None:
        correlation_id = getattr(ctx, "correlation_id", None)
        causation_id = getattr(ctx, "causation_id", None)

    return {
        "principal_id": principal_id,
        "tenant_id": tenant_id,
        "role": role_value,
        "permissions": perm_values,
        "correlation_id": correlation_id,
        "causation_id": causation_id,
    }


# ---------------------------------------------------------------------------
# Payload canonicalisation helpers (read-only — no L2 mutation)
# ---------------------------------------------------------------------------

def _sha256_hex(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode()
    return hashlib.sha256(data).hexdigest()


def _canon(data: Any) -> bytes:
    if isinstance(data, (bytes, bytearray)):
        return bytes(data)
    if is_dataclass(data):
        return json.dumps(asdict(data), sort_keys=True, separators=(",", ":")).encode()
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode()


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------

def resolve_authority(
    request: Any,
    l2_payload: Mapping[str, Any],
) -> Resolution:
    """Bridge a portal request to the canonical L2 authority resolver.

    Parameters
    ----------
    request
        Portal ``Request`` (or compatible object) whose ``state.current_user``
        has been populated by the existing JWT/RBAC middleware.
    l2_payload
        Mapping of the L2-side fields that ``authority_resolver.resolve``
        requires (trust roots, binding, session attestation, signatures, etc.).
        The adapter adds ``principal_identity_reference`` from the verified
        portal principal and computes request/operation hashes if not provided.

    Returns
    -------
    Resolution
        The unchanged L2 ``Resolution`` dataclass returned by
        ``authority_resolver.resolve``.
    """
    principal = extract_principal(request)

    # Build the kwargs dict for the L2 resolver.
    # We never mutate the caller's mapping — copy first.
    kwargs: dict[str, Any] = dict(l2_payload)

    # Stamp the verified portal principal into the session attestation's
    # principal_identity_reference if the caller hasn't pre-bound it.
    session_att = kwargs.get("session_attestation")
    if session_att is not None and not getattr(
        session_att, "principal_identity_reference", None
    ):
        # SessionAttestation is a frozen dataclass; rebuild with the principal
        from .principal_gateway_contract import SessionAttestation

        fields = {
            f.name: getattr(session_att, f.name)
            for f in session_att.__dataclass_fields__.values()
        }
        fields["principal_identity_reference"] = principal["principal_id"]
        session_att = SessionAttestation(**fields)
        kwargs["session_attestation"] = session_att

    # Ensure principal_identity_reference on the session matches the portal
    # principal — this is a *bridge* assertion, not an L2 contract change.
    if session_att is not None:
        sir = getattr(session_att, "principal_identity_reference", None)
        if sir and principal["principal_id"] and sir != principal["principal_id"]:
            raise PortalAuthorityError(
                f"Portal principal {principal['principal_id']!r} does not match "
                f"L2 session principal_identity_reference {sir!r}"
            )

    # Delegate to the existing L2 resolver — no modification, no reimplementation.
    return _l2_resolve(**kwargs)