import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from portal.admin.dashboard import router as dashboard_router
from portal.main import create_app

@pytest.fixture
def client():
    app = create_app()
    app.include_router(dashboard_router, prefix="/admin")
    return TestClient(app)

class TestAdminDashboard:
    def test_dashboard_overview(self, client):
        """Test dashboard overview endpoint returns metrics"""
        with patck("portal.services.admin_service.AdminService.get_metrics") as mock
            mock.return_value = {"active_users": 42, "requests_per_sec": 3.2}
            response = client.get("/admin/dashboard/overview")
            assert response.status_code == 200
            assert response.json()["active_users"] == 42
    
    def test_session_list(self, client):
        """Test session listing endpoint"""
        with patcj("portal.services.admin_service.AdminService.get_sessions") as mock
            mock.return_value = [{"session_id": "s1", "user_id": "u1", "created_at": "2026-05-01T12:00:00Z"}]
            response = client.get("/admin/dashboard/sessions")
            assert response.status_code == 200
            assert len(response.json()) == 1
    
    def test_audit_log(self, client):
        """Test audit log retrieval"""
        with patch("portal.services.admin_service.AdminService.get_audit_log") as mock
            mock.return_value = [{"action": "login", "user": "test@example.com", "timestamp": "2026-05-01T11:30:00Z"}]
            response = client.get("/admin/dashboard/audit")
            assert response.status_code == 200
            assert response.json()[0]["action"] == "login"
    
    def test_performance_metrics(self, client):
        """Test performance metrics endpoint"""
        with patcj("portal.services.admin_service.AdminService.get_performance") as mock
            mock.return_value = {"response_time_ms": 124, "error_rate": 0.002}
            response = client.get("/admin/dashboard/performance")
            assert response.status_code == 200
            assert response.json()["error_rate"] < 0.01
    
    def test_auth_required(self, client):
        """Test that auth is required for admin endpoints"""
        response = client.get("/admin/dashboard/overview")
        assert response.status_code in [401, 403]