"""Basic test for the portal → L2 production gateway adapter.

Verifies:
1. ``extract_principal`` correctly reads a portal-style request object.
2. ``resolve_authority`` delegates to the L2 resolver and returns its
   ``Resolution`` unchanged.
3. The adapter raises ``PortalAuthorityError`` on principal mismatch.

No L2 contract is modified — the test only exercises the bridge.
"""
from __future__ import annotations

import types
from unittest.mock import patch

import pytest

from sintra_live.l2.production_gateway import (
    PortalAuthorityError,
    extract_principal,
    resolve_authority,
)


# ---------------------------------------------------------------------------
# Fake portal request
# ---------------------------------------------------------------------------

class _FakeRole:
    value = "firm_admin"


class _FakePerm:
    def __init__(self, v: str):
        self.value = v


class _FakeUser:
    user_id = "principal-123"
    tenant_id = "tenant-abc"
    role = _FakeRole()
    permissions = [_FakePerm("mission:command"), _FakePerm("read:all")]


class _FakeContext:
    correlation_id = "corr-001"
    causation_id = "cause-001"


class _FakeRequest:
    """Minimal stand-in for a FastAPI Request with state populated by RBAC."""

    def __init__(self):
        self.state = types.SimpleNamespace(
            current_user=_FakeUser(),
            correlation_context=_FakeContext(),
        )


# ---------------------------------------------------------------------------
# extract_principal
# ---------------------------------------------------------------------------

def test_extract_principal_reads_state():
    req = _FakeRequest()
    principal = extract_principal(req)
    assert principal["principal_id"] == "principal-123"
    assert principal["tenant_id"] == "tenant-abc"
    assert principal["role"] == "firm_admin"
    assert "mission:command" in principal["permissions"]
    assert principal["correlation_id"] == "corr-001"


def test_extract_principal_accepts_mapping():
    principal = extract_principal({"principal_id": "x", "tenant_id": "t"})
    assert principal["principal_id"] == "x"


def test_extract_principal_raises_without_user():
    with pytest.raises(PortalAuthorityError):
        extract_principal(types.SimpleNamespace(state=types.SimpleNamespace()))


# ---------------------------------------------------------------------------
# resolve_authority delegation
# ---------------------------------------------------------------------------

def test_resolve_authority_delegates_to_l2():
    """Adapter must call authority_resolver.resolve with the payload and
    return the Resolution object unchanged."""
    from sintra_live.l2.principal_gateway_contract import (
        AuthorityResolution,
        AuthResult,
        Resolution,
    )

    sentinel = Resolution(
        result=AuthResult.DENY,
        record=object.__new__(AuthorityResolution),
    )

    req = _FakeRequest()
    payload = {"mission_id": "m1", "program_id": "p1", "gate_id": "g1"}

    with patch(
        "sintra_live.l2.production_gateway._l2_resolve",
        return_value=sentinel,
    ) as mock:
        result = resolve_authority(req, payload)

    assert result is sentinel
    mock.assert_called_once()
    # The adapter must forward the payload keys
    call_kwargs = mock.call_args.kwargs
    assert call_kwargs["mission_id"] == "m1"
    assert call_kwargs["program_id"] == "p1"
    assert call_kwargs["gate_id"] == "g1"


def test_resolve_authority_rejects_principal_mismatch():
    """If the L2 session attestation names a different principal than the
    verified portal user, the adapter must refuse to bridge."""
    from sintra_live.l2.principal_gateway_contract import SessionAttestation

    # Build a minimal SessionAttestation with a mismatched principal
    # We can't fully construct it (sealing requires valid hashes), so we
    # use a simple object with the attribute set.
    class _FakeSession:
        principal_identity_reference = "someone-else"

    req = _FakeRequest()
    payload = {"session_attestation": _FakeSession()}

    with pytest.raises(PortalAuthorityError, match="does not match"):
        resolve_authority(req, payload)