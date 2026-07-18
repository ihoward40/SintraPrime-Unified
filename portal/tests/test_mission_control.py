"""Mission Control API contract tests."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from portal.auth.rbac import CurrentUser, Permission, get_current_user
from portal.routers import mission_control


def _admin() -> CurrentUser:
    return CurrentUser(
        {
            "sub": "00000000-0000-0000-0000-000000000001",
            "tenant_id": "00000000-0000-0000-0000-000000000002",
            "role": "SUPER_ADMIN",
            "permissions": [Permission.ADMIN_DASHBOARD],
        }
    )


def test_summary_marks_missing_sources_unavailable(monkeypatch):
    app = FastAPI()
    app.include_router(mission_control.router)
    app.dependency_overrides[get_current_user] = _admin

    monkeypatch.setattr(mission_control, "_check_database", lambda: {"status": "healthy", "type": "sqlite"})
    monkeypatch.setattr(mission_control, "_check_recovery_api", lambda: {"status": "healthy", "external_action": "locked"})
    monkeypatch.setattr(mission_control, "_check_evidence_platform", lambda: {"status": "healthy", "cases": [{"evidence_items": 3}]})
    monkeypatch.setattr(mission_control, "_check_scheduler", lambda: {"status": "healthy", "jobs": 4})
    monkeypatch.setattr(mission_control, "_check_agents", lambda: {"status": "healthy", "running": 2})

    response = TestClient(app).get("/api/v1/mission-control/summary")
    assert response.status_code == 200
    body = response.json()
    assert body["active_agents"] == {"value": 2, "status": "verified"}
    assert body["evidence_items"] == {"value": 3, "status": "verified"}
    assert body["active_runs"]["status"] == "unavailable"
    assert body["pending_decisions"]["value"] is None
    assert body["kill_switch"]["value"] == "locked"
