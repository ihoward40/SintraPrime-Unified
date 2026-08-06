from fastapi.testclient import TestClient

from portal.auth.rbac import CurrentUser, Permission, Role, get_current_user
from portal.main import create_app
from portal.services.orchestration import orchestrator

TENANT_A = "00000000-0000-0000-0000-0000000000a1"
TENANT_B = "00000000-0000-0000-0000-0000000000b2"
USER_A = "00000000-0000-0000-0000-000000000101"
USER_B = "00000000-0000-0000-0000-000000000202"
ALL_ORCHESTRATION_PERMS = (
    Permission.ORCHESTRATION_CREATE,
    Permission.ORCHESTRATION_READ,
    Permission.ORCHESTRATION_CANCEL,
    Permission.ORCHESTRATION_APPROVE,
)


def _user(*permissions: Permission, tenant_id: str = TENANT_A, user_id: str = USER_A) -> CurrentUser:
    return CurrentUser(
        {
            "sub": user_id,
            "tenant_id": tenant_id,
            "role": Role.ATTORNEY.value,
            "permissions": [permission.value for permission in permissions],
        }
    )


def client(*permissions: Permission, tenant_id: str = TENANT_A, user_id: str = USER_A):
    orchestrator.RUNS.clear()
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: _user(
        *(permissions or ALL_ORCHESTRATION_PERMS),
        tenant_id=tenant_id,
        user_id=user_id,
    )
    return TestClient(app)


def test_orchestration_endpoints_require_authentication():
    orchestrator.RUNS.clear()
    response = TestClient(create_app()).post(
        "/api/orchestration/plan",
        json={"objective": "Implement secure code with independent review"},
    )

    assert response.status_code == 401


def test_plan_endpoint_returns_graph_and_events_with_tenant_scope():
    response = client().post(
        "/api/orchestration/plan",
        json={"objective": "Implement secure code with independent review"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["tenant_id"] == TENANT_A
    assert body["created_by"] == USER_A
    assert body["status"] == "PLANNED"
    assert body["nodes"]
    assert body["events"][0]["event_type"] == "RUN_PLANNED"


def test_execute_endpoint_records_routing_verification_and_approval():
    response = client().post(
        "/api/orchestration/execute",
        json={"objective": "Implement code and preserve Principal approval for external actions"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "APPROVAL_REQUIRED"
    assert body["routing_decisions"]
    assert body["verification"]
    assert body["reconciliation"]["disputed_claims"]
    assert body["approvals"][0]["status"] == "REQUESTED"


def test_run_retrieval_and_events_endpoints_are_tenant_bound():
    test_client = client()
    created = test_client.post("/api/orchestration/plan", json={"objective": "Draft operations runbook"}).json()

    run_response = test_client.get(f"/api/orchestration/runs/{created['run_id']}")
    events_response = test_client.get(f"/api/orchestration/runs/{created['run_id']}/events")

    assert run_response.status_code == 200
    assert events_response.status_code == 200
    assert events_response.json()[0]["event_hash"]

    other_tenant_app = create_app()
    other_tenant_app.dependency_overrides[get_current_user] = lambda: _user(
        *ALL_ORCHESTRATION_PERMS,
        tenant_id=TENANT_B,
        user_id=USER_B,
    )
    other_tenant_client = TestClient(other_tenant_app)

    assert other_tenant_client.get(f"/api/orchestration/runs/{created['run_id']}").status_code == 404
    assert other_tenant_client.get(f"/api/orchestration/runs/{created['run_id']}/events").status_code == 404


def test_cancel_endpoint_marks_run_cancelled_for_authorized_user():
    test_client = client()
    created = test_client.post("/api/orchestration/plan", json={"objective": "Research public facts"}).json()

    response = test_client.post(
        f"/api/orchestration/runs/{created['run_id']}/cancel",
        json={"reason": "Principal stopped mock run"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"
    assert response.json()["cancelled_by"] == USER_A


def test_cancel_endpoint_rejects_missing_permission():
    test_client = client(Permission.ORCHESTRATION_CREATE, Permission.ORCHESTRATION_READ)
    created = test_client.post("/api/orchestration/plan", json={"objective": "Research public facts"}).json()

    response = test_client.post(
        f"/api/orchestration/runs/{created['run_id']}/cancel",
        json={"reason": "No authority"},
    )

    assert response.status_code == 403


def test_approve_endpoint_records_authenticated_principal_decision():
    test_client = client()
    created = test_client.post("/api/orchestration/execute", json={"objective": "Implement code"}).json()

    response = test_client.post(
        f"/api/orchestration/runs/{created['run_id']}/approve",
        json={"approved": True, "reason": "Reviewed mock evidence"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["approvals"][0]["status"] == "APPROVED"
    assert body["approvals"][0]["principal_id"] == USER_A
    assert body["status"] == "COMPLETED"


def test_approve_endpoint_rejects_missing_permission_and_non_pending_runs():
    test_client = client(Permission.ORCHESTRATION_CREATE, Permission.ORCHESTRATION_READ)
    approval_run = test_client.post("/api/orchestration/execute", json={"objective": "Implement code"}).json()

    denied_response = test_client.post(
        f"/api/orchestration/runs/{approval_run['run_id']}/approve",
        json={"approved": True},
    )
    assert denied_response.status_code == 403

    authorized_client = client()
    planned = authorized_client.post("/api/orchestration/plan", json={"objective": "Draft operations runbook"}).json()
    non_pending_response = authorized_client.post(
        f"/api/orchestration/runs/{planned['run_id']}/approve",
        json={"approved": True},
    )
    assert non_pending_response.status_code == 409


def test_approval_cannot_be_replayed_after_completion():
    test_client = client()
    created = test_client.post("/api/orchestration/execute", json={"objective": "Implement code"}).json()

    first = test_client.post(f"/api/orchestration/runs/{created['run_id']}/approve", json={"approved": True})
    second = test_client.post(f"/api/orchestration/runs/{created['run_id']}/approve", json={"approved": True})

    assert first.status_code == 200
    assert second.status_code == 409


def test_execute_returns_blocked_when_budget_exhausted():
    response = client().post(
        "/api/orchestration/execute",
        json={
            "objective": "Implement code",
            "budget_limits": {"maximum_nodes": 0},
        },
    )

    assert response.status_code == 422


def test_execute_returns_partial_when_node_budget_is_reached_after_work():
    response = client().post(
        "/api/orchestration/execute",
        json={
            "objective": "Implement code",
            "budget_limits": {"maximum_nodes": 1},
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] in {"PARTIAL", "BLOCKED"}