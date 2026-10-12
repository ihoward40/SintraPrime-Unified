"""G4 — Governance API authentication & authorization tests.

SP-PARLIAMENT-A2A-REVOCATION-DESIGN-CERT-002 §6 (N1/N2/N3/N4/N5/N12/N21/N22).

Covers:
- router-structural authentication (401 for anonymous/invalid on EVERY route)
- scope enforcement on emergency-stop and clear (403 without the scope)
- token-derived audit attribution (caller-supplied labels are metadata only)
- fresh-mount inheritance of the dependency chain
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from governance.authz_dependencies import (
    _ROLE_GRANTED_SCOPES,
    SCOPE_EMERGENCY_STOP,
    SCOPE_EMERGENCY_STOP_CLEAR,
    SCOPE_REVOCATION,
    PrincipalContext,
    bind_tenant,
)
from governance.governance_api import create_governance_router
from governance.governance_engine import GovernanceEngine
from portal.auth.jwt_handler import create_access_token


@pytest.fixture
def engine(tmp_path: Path) -> GovernanceEngine:
    return GovernanceEngine(db_path=tmp_path / "audit.db")


@pytest.fixture
def router(engine: GovernanceEngine):
    return create_governance_router(engine)


@pytest.fixture
def client(engine: GovernanceEngine) -> TestClient:
    app = FastAPI()
    app.include_router(create_governance_router(engine))
    return TestClient(app)


def _token(
    role: str = "SUPER_ADMIN",
    tenant: str = "tenant-1",
    permissions: list[str] | None = None,
    user: str = "principal-1",
) -> str:
    return create_access_token(
        user_id=user,
        tenant_id=tenant,
        role=role,
        permissions=permissions if permissions is not None else [],
    )


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# N1 — structural authentication: anonymous/invalid -> 401 everywhere
# ---------------------------------------------------------------------------


def test_n1_anonymous_emergency_stop_denied(client: TestClient) -> None:
    response = client.post("/governance/emergency-stop", params={"authorized_by": "anon"})
    assert response.status_code == 401


def test_n1_anonymous_read_route_denied(client: TestClient) -> None:
    assert client.get("/governance/dashboard").status_code == 401


def test_n1_anonymous_clear_denied(client: TestClient) -> None:
    response = client.post("/governance/emergency-stop/clear")
    assert response.status_code == 401


def test_n1_invalid_token_denied(client: TestClient) -> None:
    response = client.get(
        "/governance/dashboard", headers={"Authorization": "Bearer not-a-jwt"}
    )
    assert response.status_code == 401


def test_n1_garbage_scheme_denied(client: TestClient) -> None:
    response = client.get(
        "/governance/dashboard", headers={"Authorization": "Basic abc"}
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# N2/N3 — authenticated but unauthorized -> 403
# ---------------------------------------------------------------------------


def test_n2_non_privileged_role_denied_stop(client: TestClient) -> None:
    response = client.post(
        "/governance/emergency-stop", headers=_auth(_token(role="PARALEGAL"))
    )
    assert response.status_code == 403


def test_n3_cross_tenant_unprivileged_denied(client: TestClient) -> None:
    response = client.post(
        "/governance/emergency-stop",
        headers=_auth(_token(role="VIEWER", tenant="tenant-9")),
    )
    assert response.status_code == 403


def test_n2_firm_admin_without_scope_denied_stop(client: TestClient) -> None:
    response = client.post(
        "/governance/emergency-stop", headers=_auth(_token(role="FIRM_ADMIN"))
    )
    assert response.status_code == 403


def test_n2_scope_grant_allows_non_role_holder(client: TestClient) -> None:
    response = client.post(
        "/governance/emergency-stop",
        headers=_auth(_token(role="PARALEGAL", permissions=[SCOPE_EMERGENCY_STOP])),
    )
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# N4/N5 — authorized stop/clear with token-derived attribution
# ---------------------------------------------------------------------------


def test_n4_authorized_stop_attributes_verified_principal(
    client: TestClient, engine: GovernanceEngine
) -> None:
    response = client.post(
        "/governance/emergency-stop",
        headers=_auth(_token(user="principal-admin", permissions=[SCOPE_EMERGENCY_STOP])),
        params={"authorized_by": "SPOOFED-LABEL"},
    )
    assert response.status_code == 200
    body = response.json()
    # Audit identity comes from the verified token, never the caller label.
    assert body["authorized_by"] == "principal-admin"
    entries = engine.audit_trail.query(action="emergency_stop")
    assert entries, "expected an audit entry for the stop"
    assert entries[-1].actor == "principal-admin"
    assert entries[-1].metadata.get("caller_supplied_label") == "SPOOFED-LABEL"


def test_n5_authorized_clear_attributes_verified_principal(client: TestClient) -> None:
    # Dual control: STOP and CLEAR are performed by DIFFERENT principals, each
    # holding only its own explicit scope.
    stop = client.post(
        "/governance/emergency-stop",
        headers=_auth(_token(user="stopper", permissions=[SCOPE_EMERGENCY_STOP])),
    )
    assert stop.status_code == 200
    clear = client.post(
        "/governance/emergency-stop/clear",
        headers=_auth(_token(user="releaser", permissions=[SCOPE_EMERGENCY_STOP_CLEAR])),
    )
    assert clear.status_code == 200
    assert clear.json()["cleared_by"] == "releaser"


def test_stop_then_read_shows_state(client: TestClient, engine: GovernanceEngine) -> None:
    client.post(
        "/governance/emergency-stop",
        headers=_auth(_token(permissions=[SCOPE_EMERGENCY_STOP])),
    )
    assert engine.intervention_controller.is_emergency_stopped is True
    client.post(
        "/governance/emergency-stop/clear",
        headers=_auth(_token(permissions=[SCOPE_EMERGENCY_STOP_CLEAR])),
    )
    assert engine.intervention_controller.is_emergency_stopped is False


# ---------------------------------------------------------------------------
# N21 — fresh mount inherits the structural dependency chain
# ---------------------------------------------------------------------------


def test_n21_fresh_mount_still_requires_auth(engine: GovernanceEngine) -> None:
    second_app = FastAPI()
    second_app.include_router(create_governance_router(engine))
    fresh_client = TestClient(second_app)
    assert fresh_client.get("/governance/dashboard").status_code == 401
    assert fresh_client.post("/governance/emergency-stop").status_code == 401


# ---------------------------------------------------------------------------
# N22 — behavioral route inventory: EVERY governance route rejects anonymous
# requests with 401 (this FastAPI version wraps mounted routers, so the
# inventory is asserted by behavior rather than by app.routes introspection).
# ---------------------------------------------------------------------------


def test_n22_route_inventory_all_require_auth(client: TestClient, router) -> None:
    api_routes = [r for r in router.routes if getattr(r, "methods", None)]
    assert len(api_routes) >= 15, f"unexpected route count: {len(api_routes)}"
    checked = 0
    for route in api_routes:
        for method in sorted(route.methods - {"HEAD", "OPTIONS"}):
            response = client.request(method, route.path)
            assert response.status_code == 401, (
                f"unprotected route: {method} {route.path} -> {response.status_code}"
            )
            checked += 1
    assert checked >= 15, f"too few routes exercised: {checked}"


def test_n22_emergency_routes_require_scope(client: TestClient) -> None:
    # Authenticated but scope-less principals are denied on BOTH emergency
    # routes (route-level scope dependency beyond the router-level authn).
    for path in ("/governance/emergency-stop", "/governance/emergency-stop/clear"):
        response = client.post(
            path, headers=_auth(_token(role="PARALEGAL", tenant="tenant-1"))
        )
        assert response.status_code == 403, f"scope not enforced: {path}"



def test_stop_scope_without_clear_scope_denied_on_clear(client: TestClient) -> None:
    # A principal holding ``emergency_stop`` but NOT ``emergency_stop_clear`` may
    # stop but must NOT clear (distinct clearance authority).
    stop = client.post(
        "/governance/emergency-stop",
        headers=_auth(_token(permissions=[SCOPE_EMERGENCY_STOP])),
    )
    assert stop.status_code == 200
    clear = client.post(
        "/governance/emergency-stop/clear",
        headers=_auth(_token(permissions=[SCOPE_EMERGENCY_STOP])),
    )
    assert clear.status_code == 403


def test_revoked_jti_denied(client: TestClient) -> None:
    import asyncio

    from portal.auth.jwt_handler import decode_access_token
    from portal.auth.session_manager import blocklist_jti

    token = _token()
    jti = decode_access_token(token).get("jti")
    if jti:
        asyncio.run(blocklist_jti(jti))
    response = client.get("/governance/dashboard", headers=_auth(token))
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# bind_tenant unit behavior (platform exemption vs cross-tenant denial)
# ---------------------------------------------------------------------------


def _principal(role: str, tenant: str) -> PrincipalContext:
    return PrincipalContext(
        subject="p1", tenant_id=tenant, role=role, jti="jti-1", scopes=frozenset()
    )


def test_bind_tenant_platform_level_exempt() -> None:
    dep = bind_tenant("tenant-1")
    assert dep(_principal("SUPER_ADMIN", "tenant-9")).subject == "p1"


def test_bind_tenant_cross_tenant_denied() -> None:
    from fastapi import HTTPException

    dep = bind_tenant("tenant-1")
    with pytest.raises(HTTPException) as excinfo:
        dep(_principal("ATTORNEY", "tenant-2"))
    assert excinfo.value.status_code == 403


def test_bind_tenant_same_tenant_allowed() -> None:
    dep = bind_tenant("tenant-1")
    assert dep(_principal("ATTORNEY", "tenant-1")).subject == "p1"


def test_revocation_scope_constant_reserved() -> None:
    assert SCOPE_REVOCATION == "revocation"



# ---------------------------------------------------------------------------
# STOP/CLEAR separation (SP-PARLIAMENT-A2A-G4-STOP-CLEAR-AUTHZ-FIX-002):
# authority to stop is NOT authority to restart.
# ---------------------------------------------------------------------------


def test_sep_stop_only_cannot_clear(client: TestClient) -> None:
    stop_token = _token(user="stopper", permissions=[SCOPE_EMERGENCY_STOP])
    stop = client.post("/governance/emergency-stop", headers=_auth(stop_token))
    assert stop.status_code == 200
    # The SAME token that successfully stopped the system CANNOT clear it.
    clear = client.post("/governance/emergency-stop/clear", headers=_auth(stop_token))
    assert clear.status_code == 403
    assert client.post(
        "/governance/emergency-stop/clear", headers=_auth(stop_token)
    ).status_code == 403


def test_sep_clear_only_cannot_stop(client: TestClient) -> None:
    # Establish an active stop with a properly authorized stopper.
    stop = client.post(
        "/governance/emergency-stop",
        headers=_auth(_token(user="stopper", permissions=[SCOPE_EMERGENCY_STOP])),
    )
    assert stop.status_code == 200
    clear_token = _token(user="releaser", permissions=[SCOPE_EMERGENCY_STOP_CLEAR])
    clear = client.post("/governance/emergency-stop/clear", headers=_auth(clear_token))
    assert clear.status_code == 200
    # The CLEAR-only principal CANNOT initiate a new stop.
    assert (
        client.post("/governance/emergency-stop", headers=_auth(clear_token)).status_code
        == 403
    )


def test_sep_broad_role_grants_no_intervention(client: TestClient) -> None:
    # Implicit privilege expansion is blocked: a broad platform role WITHOUT an
    # explicit intervention permission claim cannot stop OR clear.
    broad = _token(user="broad-admin", role="SUPER_ADMIN", permissions=[])
    assert client.post("/governance/emergency-stop", headers=_auth(broad)).status_code == 403
    assert (
        client.post("/governance/emergency-stop/clear", headers=_auth(broad)).status_code
        == 403
    )


def test_sep_role_map_grants_no_intervention_scopes() -> None:
    # Regression guard: no role may implicitly carry the intervention scopes.
    intervention = {SCOPE_EMERGENCY_STOP, SCOPE_EMERGENCY_STOP_CLEAR, SCOPE_REVOCATION}
    for role, scopes in _ROLE_GRANTED_SCOPES.items():
        assert not (scopes & intervention), f"role {role} implicitly grants {scopes & intervention}"


def test_sep_dual_control_end_to_end(client: TestClient, engine: GovernanceEngine) -> None:
    # Distinct principals: stopper stops, releaser clears, both audited under
    # their verified identities.
    stop = client.post(
        "/governance/emergency-stop",
        headers=_auth(_token(user="stopper", permissions=[SCOPE_EMERGENCY_STOP])),
    )
    assert stop.status_code == 200
    assert engine.intervention_controller.is_emergency_stopped is True
    clear = client.post(
        "/governance/emergency-stop/clear",
        headers=_auth(_token(user="releaser", permissions=[SCOPE_EMERGENCY_STOP_CLEAR])),
    )
    assert clear.status_code == 200
    assert engine.intervention_controller.is_emergency_stopped is False
    stop_entries = engine.audit_trail.query(action="emergency_stop")
    assert stop_entries[-1].actor == "stopper"
