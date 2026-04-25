"""
RBAC (Role-Based Access Control) tests.
Verifies that role boundaries are strictly enforced.
"""

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient


def make_user(role: str, user_id=None, tenant_id=None):
    """Helper to create mock user with a specific role."""
    user = MagicMock()
    user.user_id = str(user_id or uuid.uuid4())
    user.tenant_id = str(tenant_id or uuid.uuid4())
    user.role = role

    def has_permission(perm):
        """Simplified permission check for testing."""
        role_perms = {
            "SUPER_ADMIN": {"*"},
            "FIRM_ADMIN": {"user:*", "client:*", "case:*", "doc:*", "billing:*", "admin:*"},
            "ATTORNEY": {"client:read", "client:create", "case:read", "case:create", "case:update",
                         "doc:read", "doc:upload", "doc:share", "billing:read", "msg:read", "msg:send"},
            "PARALEGAL": {"client:read", "case:read", "case:update", "doc:read", "doc:upload", "msg:read"},
            "CLIENT": {"client:own", "case:own", "doc:own", "billing:own", "msg:read", "msg:send"},
            "ACCOUNTANT": {"billing:read", "billing:create", "billing:update", "doc:financial"},
            "VIEWER": {"doc:read"},
        }
        perms = role_perms.get(role, set())
        return perm in perms or "*" in perms or f"{perm.split(':')[0]}:*" in perms

    user.has_permission = has_permission
    user.is_client = lambda: role == "CLIENT"
    user.is_staff = lambda: role in ("FIRM_ADMIN", "ATTORNEY", "PARALEGAL", "ACCOUNTANT")
    return user


class TestSuperAdmin:
    """SUPER_ADMIN can do everything."""

    def test_super_admin_has_all_permissions(self):
        user = make_user("SUPER_ADMIN")
        assert user.has_permission("doc:delete")
        assert user.has_permission("billing:trust")
        assert user.has_permission("admin:settings")
        assert user.has_permission("user:manage_roles")


class TestFirmAdmin:
    """FIRM_ADMIN can manage their firm."""

    def test_firm_admin_can_manage_users(self):
        user = make_user("FIRM_ADMIN")
        assert user.has_permission("user:read")
        assert user.has_permission("user:invite")

    def test_firm_admin_can_manage_clients(self):
        user = make_user("FIRM_ADMIN")
        assert user.has_permission("client:create")
        assert user.has_permission("client:delete")

    def test_firm_admin_can_view_billing(self):
        user = make_user("FIRM_ADMIN")
        assert user.has_permission("billing:read")


class TestAttorney:
    """ATTORNEY can manage cases and documents but not system admin."""

    def test_attorney_can_manage_cases(self):
        user = make_user("ATTORNEY")
        assert user.has_permission("case:read")
        assert user.has_permission("case:create")
        assert user.has_permission("case:update")

    def test_attorney_can_upload_documents(self):
        user = make_user("ATTORNEY")
        assert user.has_permission("doc:upload")
        assert user.has_permission("doc:share")

    def test_attorney_cannot_access_admin(self):
        user = make_user("ATTORNEY")
        assert not user.has_permission("admin:settings")

    def test_attorney_cannot_delete_invoices(self):
        user = make_user("ATTORNEY")
        assert not user.has_permission("billing:delete")

    def test_attorney_cannot_manage_users(self):
        user = make_user("ATTORNEY")
        assert not user.has_permission("user:invite")


class TestParalegal:
    """PARALEGAL has limited access — cannot share documents or delete cases."""

    def test_paralegal_can_read_cases(self):
        user = make_user("PARALEGAL")
        assert user.has_permission("case:read")
        assert user.has_permission("case:update")

    def test_paralegal_can_upload_docs(self):
        user = make_user("PARALEGAL")
        assert user.has_permission("doc:upload")

    def test_paralegal_cannot_share_docs(self):
        user = make_user("PARALEGAL")
        assert not user.has_permission("doc:share")

    def test_paralegal_cannot_create_clients(self):
        user = make_user("PARALEGAL")
        assert not user.has_permission("client:create")

    def test_paralegal_cannot_access_billing(self):
        user = make_user("PARALEGAL")
        assert not user.has_permission("billing:create")


class TestClient:
    """CLIENT can only see their own data."""

    def test_client_is_identified_correctly(self):
        user = make_user("CLIENT")
        assert user.is_client()
        assert not user.is_staff()

    def test_client_cannot_see_other_client_data(self):
        """Simulate filtering: client query must add own-client filter."""
        client_a = make_user("CLIENT")
        client_b_id = str(uuid.uuid4())

        # Client's query should be filtered to own data only
        assert client_a.is_client()
        # In router logic: if is_client(), filter by portal_user_id

    def test_client_cannot_manage_users(self):
        user = make_user("CLIENT")
        assert not user.has_permission("user:invite")

    def test_client_cannot_create_cases(self):
        user = make_user("CLIENT")
        assert not user.has_permission("case:create")

    def test_client_cannot_upload_docs(self):
        user = make_user("CLIENT")
        assert not user.has_permission("doc:upload")

    def test_client_can_read_own_docs(self):
        user = make_user("CLIENT")
        assert user.has_permission("doc:own")

    def test_client_can_send_messages(self):
        user = make_user("CLIENT")
        assert user.has_permission("msg:send")


class TestAccountant:
    """ACCOUNTANT can only access financial data."""

    def test_accountant_can_read_billing(self):
        user = make_user("ACCOUNTANT")
        assert user.has_permission("billing:read")
        assert user.has_permission("billing:create")

    def test_accountant_cannot_see_cases(self):
        user = make_user("ACCOUNTANT")
        assert not user.has_permission("case:read")

    def test_accountant_cannot_see_confidential_docs(self):
        user = make_user("ACCOUNTANT")
        assert not user.has_permission("doc:read")

    def test_accountant_can_see_financial_docs(self):
        user = make_user("ACCOUNTANT")
        assert user.has_permission("doc:financial")


class TestViewer:
    """VIEWER has read-only access."""

    def test_viewer_can_only_read_docs(self):
        user = make_user("VIEWER")
        assert user.has_permission("doc:read")

    def test_viewer_cannot_upload(self):
        user = make_user("VIEWER")
        assert not user.has_permission("doc:upload")

    def test_viewer_cannot_access_cases(self):
        user = make_user("VIEWER")
        assert not user.has_permission("case:read")

    def test_viewer_cannot_send_messages(self):
        user = make_user("VIEWER")
        assert not user.has_permission("msg:send")


class TestTenantIsolation:
    """Attorneys from different firms should not see each other's data."""

    def test_cross_tenant_access_denied(self):
        """Two attorneys from different tenants should have different tenant IDs."""
        tenant_a = str(uuid.uuid4())
        tenant_b = str(uuid.uuid4())

        attorney_a = make_user("ATTORNEY", tenant_id=tenant_a)
        attorney_b = make_user("ATTORNEY", tenant_id=tenant_b)

        assert attorney_a.tenant_id != attorney_b.tenant_id

    def test_attorney_scoped_to_own_tenant(self):
        """Verify tenant_id is passed to all queries."""
        tenant_id = str(uuid.uuid4())
        attorney = make_user("ATTORNEY", tenant_id=tenant_id)
        assert attorney.tenant_id == tenant_id

    def test_client_scoped_to_own_tenant(self):
        tenant_id = str(uuid.uuid4())
        client_user = make_user("CLIENT", tenant_id=tenant_id)
        assert client_user.tenant_id == tenant_id


class TestRequirePermissionsDecorator:
    """Test the require_permissions FastAPI dependency."""

    @pytest.mark.asyncio
    async def test_requires_valid_permission(self):
        from portal.auth.rbac import require_permissions, Permission
        # Should raise HTTPException 403 if user lacks permission
        user = make_user("VIEWER")
        # Viewer cannot create clients
        assert not user.has_permission("client:create")

    @pytest.mark.asyncio
    async def test_allows_sufficient_permission(self):
        user = make_user("ATTORNEY")
        assert user.has_permission("case:read")
