from fastapi.testclient import TestClient

from portal.main import create_app
from portal.services.orchestration import orchestrator


def client():
    orchestrator.RUNS.clear()
    return TestClient(create_app())


def test_plan_endpoint_returns_graph_and_events():
    response = client().post(
        "/api/orchestration/plan",
        json={"objective": "Implement secure code with independent review"},
    )

    assert response.status_code == 200
    body = response.json()
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


def test_run_retrieval_and_events_endpoints():
    test_client = client()
    created = test_client.post("/api/orchestration/plan", json={"objective": "Draft operations runbook"}).json()

    run_response = test_client.get(f"/api/orchestration/runs/{created['run_id']}")
    events_response = test_client.get(f"/api/orchestration/runs/{created['run_id']}/events")

    assert run_response.status_code == 200
    assert events_response.status_code == 200
    assert events_response.json()[0]["event_hash"]


def test_cancel_endpoint_marks_run_cancelled():
    test_client = client()
    created = test_client.post("/api/orchestration/plan", json={"objective": "Research public facts"}).json()

    response = test_client.post(
        f"/api/orchestration/runs/{created['run_id']}/cancel",
        json={"reason": "Principal stopped mock run"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"


def test_approve_endpoint_records_principal_decision():
    test_client = client()
    created = test_client.post("/api/orchestration/execute", json={"objective": "Implement code"}).json()

    response = test_client.post(
        f"/api/orchestration/runs/{created['run_id']}/approve",
        json={"principal_id": "principal-1", "approved": True, "reason": "Reviewed mock evidence"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["approvals"][0]["status"] == "APPROVED"
    assert body["status"] == "COMPLETED"


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
