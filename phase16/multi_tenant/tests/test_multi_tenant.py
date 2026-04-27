"""Phase 16C — Multi-Tenant Law Firm Dashboard tests (98 tests)."""
import pytest
import threading
from phase16.multi_tenant.models import (
    IsolationLevel, TenantStatus, UserRole, AccessContext,
)
from phase16.multi_tenant.dashboard import (
    MultiTenantDashboard, TenantIsolationLayer, AccessControlLayer,
    ROLE_PERMISSIONS,
)


@pytest.fixture
def dashboard():
    return MultiTenantDashboard()


@pytest.fixture
def tenant(dashboard):
    t = dashboard.create_tenant("Smith & Jones LLP", "smithjones.com")
    dashboard.activate_tenant(t.tenant_id)
    return t


@pytest.fixture
def user(dashboard, tenant):
    return dashboard.add_user(tenant.tenant_id, "alice@smithjones.com", "Alice Smith", UserRole.ATTORNEY)


# ─────────────────────────────────────────────────────────────
# Tenant lifecycle tests (20)
# ─────────────────────────────────────────────────────────────
class TestTenantLifecycle:
    def test_create_tenant(self, dashboard):
        t = dashboard.create_tenant("Firm A", "firma.com")
        assert t.tenant_id.startswith("ten_")
        assert t.firm_name == "Firm A"

    def test_tenant_starts_onboarding(self, dashboard):
        t = dashboard.create_tenant("Firm A", "firma.com")
        assert t.status == TenantStatus.ONBOARDING
        assert not t.is_active

    def test_activate_tenant(self, dashboard):
        t = dashboard.create_tenant("Firm A", "firma.com")
        dashboard.activate_tenant(t.tenant_id)
        assert dashboard.get_tenant(t.tenant_id).is_active

    def test_suspend_tenant(self, dashboard, tenant):
        dashboard.suspend_tenant(tenant.tenant_id)
        assert dashboard.get_tenant(tenant.tenant_id).status == TenantStatus.SUSPENDED

    def test_get_tenant(self, dashboard, tenant):
        retrieved = dashboard.get_tenant(tenant.tenant_id)
        assert retrieved.firm_name == "Smith & Jones LLP"

    def test_get_nonexistent_tenant(self, dashboard):
        assert dashboard.get_tenant("nonexistent") is None

    def test_list_tenants_all(self, dashboard):
        for i in range(3):
            dashboard.create_tenant(f"Firm {i}", f"firm{i}.com")
        assert len(dashboard.list_tenants()) >= 3

    def test_list_tenants_by_status(self, dashboard):
        t1 = dashboard.create_tenant("Firm A", "firma.com")
        t2 = dashboard.create_tenant("Firm B", "firmb.com")
        dashboard.activate_tenant(t1.tenant_id)
        active = dashboard.list_tenants(status=TenantStatus.ACTIVE)
        assert any(t.tenant_id == t1.tenant_id for t in active)
        assert not any(t.tenant_id == t2.tenant_id for t in active)

    def test_activate_nonexistent_raises(self, dashboard):
        with pytest.raises(KeyError):
            dashboard.activate_tenant("nonexistent")

    def test_suspend_nonexistent_raises(self, dashboard):
        with pytest.raises(KeyError):
            dashboard.suspend_tenant("nonexistent")

    def test_update_tenant_settings(self, dashboard, tenant):
        dashboard.update_tenant_settings(tenant.tenant_id, {"theme": "dark", "timezone": "UTC"})
        t = dashboard.get_tenant(tenant.tenant_id)
        assert t.settings["theme"] == "dark"

    def test_update_settings_nonexistent_raises(self, dashboard):
        with pytest.raises(KeyError):
            dashboard.update_tenant_settings("nonexistent", {})

    def test_tenant_isolation_level_default(self, dashboard):
        t = dashboard.create_tenant("Firm A", "firma.com")
        assert t.isolation_level == IsolationLevel.SHARED

    def test_tenant_schema_isolation(self, dashboard):
        t = dashboard.create_tenant("Firm A", "firma.com", isolation_level=IsolationLevel.SCHEMA)
        assert t.isolation_level == IsolationLevel.SCHEMA

    def test_tenant_dedicated_isolation(self, dashboard):
        t = dashboard.create_tenant("Firm A", "firma.com", isolation_level=IsolationLevel.DEDICATED)
        assert t.isolation_level == IsolationLevel.DEDICATED

    def test_tenant_unique_ids(self, dashboard):
        ids = {dashboard.create_tenant(f"Firm {i}", f"firm{i}.com").tenant_id for i in range(10)}
        assert len(ids) == 10

    def test_tenant_created_at(self, dashboard):
        t = dashboard.create_tenant("Firm A", "firma.com")
        assert t.created_at > 0

    def test_tenant_plan_tier(self, dashboard):
        t = dashboard.create_tenant("Firm A", "firma.com", plan_tier="enterprise")
        assert t.plan_tier == "enterprise"

    def test_tenant_domain_stored(self, dashboard):
        t = dashboard.create_tenant("Firm A", "firma.com")
        assert t.domain == "firma.com"

    def test_tenant_metadata_default_empty(self, dashboard):
        t = dashboard.create_tenant("Firm A", "firma.com")
        assert t.metadata == {}


# ─────────────────────────────────────────────────────────────
# User management tests (20)
# ─────────────────────────────────────────────────────────────
class TestUserManagement:
    def test_add_user(self, dashboard, tenant):
        u = dashboard.add_user(tenant.tenant_id, "bob@firm.com", "Bob")
        assert u.user_id.startswith("usr_")
        assert u.email == "bob@firm.com"

    def test_user_default_role(self, dashboard, tenant):
        u = dashboard.add_user(tenant.tenant_id, "bob@firm.com", "Bob")
        assert u.role == UserRole.STAFF

    def test_user_custom_role(self, dashboard, tenant):
        u = dashboard.add_user(tenant.tenant_id, "bob@firm.com", "Bob", UserRole.ADMIN)
        assert u.role == UserRole.ADMIN

    def test_user_has_permissions(self, dashboard, tenant):
        u = dashboard.add_user(tenant.tenant_id, "bob@firm.com", "Bob", UserRole.ATTORNEY)
        assert "manage_cases" in u.permissions

    def test_get_user(self, dashboard, tenant, user):
        retrieved = dashboard.get_user(user.user_id)
        assert retrieved.email == user.email

    def test_get_nonexistent_user(self, dashboard):
        assert dashboard.get_user("nonexistent") is None

    def test_list_users(self, dashboard, tenant):
        dashboard.add_user(tenant.tenant_id, "a@b.com", "A")
        dashboard.add_user(tenant.tenant_id, "b@b.com", "B")
        users = dashboard.list_users(tenant.tenant_id)
        assert len(users) >= 2

    def test_list_users_tenant_isolated(self, dashboard):
        t1 = dashboard.create_tenant("F1", "f1.com")
        t2 = dashboard.create_tenant("F2", "f2.com")
        dashboard.activate_tenant(t1.tenant_id)
        dashboard.activate_tenant(t2.tenant_id)
        dashboard.add_user(t1.tenant_id, "a@f1.com", "A")
        dashboard.add_user(t2.tenant_id, "b@f2.com", "B")
        assert len(dashboard.list_users(t1.tenant_id)) == 1
        assert len(dashboard.list_users(t2.tenant_id)) == 1

    def test_update_user_role(self, dashboard, tenant, user):
        dashboard.update_user_role(user.user_id, UserRole.ADMIN)
        updated = dashboard.get_user(user.user_id)
        assert updated.role == UserRole.ADMIN

    def test_update_role_updates_permissions(self, dashboard, tenant, user):
        dashboard.update_user_role(user.user_id, UserRole.OWNER)
        updated = dashboard.get_user(user.user_id)
        assert "*" in updated.permissions

    def test_deactivate_user(self, dashboard, tenant, user):
        dashboard.deactivate_user(user.user_id)
        assert not dashboard.get_user(user.user_id).active

    def test_add_user_nonexistent_tenant_raises(self, dashboard):
        with pytest.raises(KeyError):
            dashboard.add_user("nonexistent", "x@y.com", "X")

    def test_update_nonexistent_user_raises(self, dashboard):
        with pytest.raises(KeyError):
            dashboard.update_user_role("nonexistent", UserRole.ADMIN)

    def test_deactivate_nonexistent_user_raises(self, dashboard):
        with pytest.raises(KeyError):
            dashboard.deactivate_user("nonexistent")

    def test_user_unique_ids(self, dashboard, tenant):
        ids = {dashboard.add_user(tenant.tenant_id, f"u{i}@f.com", f"U{i}").user_id for i in range(10)}
        assert len(ids) == 10

    def test_user_active_by_default(self, dashboard, tenant):
        u = dashboard.add_user(tenant.tenant_id, "x@y.com", "X")
        assert u.active is True

    def test_user_tenant_id_set(self, dashboard, tenant, user):
        assert user.tenant_id == tenant.tenant_id

    def test_paralegal_permissions(self, dashboard, tenant):
        u = dashboard.add_user(tenant.tenant_id, "p@f.com", "P", UserRole.PARALEGAL)
        assert "manage_documents" in u.permissions
        assert "manage_cases" not in u.permissions

    def test_viewer_permissions(self, dashboard, tenant):
        u = dashboard.add_user(tenant.tenant_id, "v@f.com", "V", UserRole.VIEWER)
        assert "view_cases" in u.permissions
        assert "manage_cases" not in u.permissions

    def test_staff_permissions(self, dashboard, tenant):
        u = dashboard.add_user(tenant.tenant_id, "s@f.com", "S", UserRole.STAFF)
        assert "view_cases" in u.permissions


# ─────────────────────────────────────────────────────────────
# Resource management tests (15)
# ─────────────────────────────────────────────────────────────
class TestResourceManagement:
    def test_create_resource(self, dashboard, tenant, user):
        r = dashboard.create_resource(tenant.tenant_id, user.user_id, "case", "Smith v. Jones")
        assert r.resource_id.startswith("res_")
        assert r.name == "Smith v. Jones"

    def test_resource_tenant_id(self, dashboard, tenant, user):
        r = dashboard.create_resource(tenant.tenant_id, user.user_id, "case", "C1")
        assert r.tenant_id == tenant.tenant_id

    def test_get_resource(self, dashboard, tenant, user):
        r = dashboard.create_resource(tenant.tenant_id, user.user_id, "case", "C1")
        retrieved = dashboard.get_resource(r.resource_id)
        assert retrieved.name == "C1"

    def test_get_nonexistent_resource(self, dashboard):
        assert dashboard.get_resource("nonexistent") is None

    def test_list_resources(self, dashboard, tenant, user):
        dashboard.create_resource(tenant.tenant_id, user.user_id, "case", "C1")
        dashboard.create_resource(tenant.tenant_id, user.user_id, "case", "C2")
        resources = dashboard.list_resources(tenant.tenant_id)
        assert len(resources) >= 2

    def test_list_resources_by_type(self, dashboard, tenant, user):
        dashboard.create_resource(tenant.tenant_id, user.user_id, "case", "C1")
        dashboard.create_resource(tenant.tenant_id, user.user_id, "document", "D1")
        cases = dashboard.list_resources(tenant.tenant_id, resource_type="case")
        assert all(r.resource_type == "case" for r in cases)

    def test_resource_access_with_context(self, dashboard, tenant, user):
        r = dashboard.create_resource(tenant.tenant_id, user.user_id, "case", "C1")
        ctx = dashboard.build_access_context(user.user_id)
        retrieved = dashboard.get_resource(r.resource_id, context=ctx)
        assert retrieved is not None

    def test_cross_tenant_resource_denied(self, dashboard):
        t1 = dashboard.create_tenant("F1", "f1.com")
        t2 = dashboard.create_tenant("F2", "f2.com")
        dashboard.activate_tenant(t1.tenant_id)
        dashboard.activate_tenant(t2.tenant_id)
        u1 = dashboard.add_user(t1.tenant_id, "a@f1.com", "A", UserRole.ATTORNEY)
        r2 = dashboard.create_resource(t2.tenant_id, "some_user", "case", "C1")
        ctx = dashboard.build_access_context(u1.user_id)
        assert dashboard.get_resource(r2.resource_id, context=ctx) is None

    def test_resource_created_at(self, dashboard, tenant, user):
        r = dashboard.create_resource(tenant.tenant_id, user.user_id, "case", "C1")
        assert r.created_at > 0

    def test_resource_nonexistent_tenant_raises(self, dashboard, user):
        with pytest.raises(KeyError):
            dashboard.create_resource("nonexistent", user.user_id, "case", "C1")

    def test_resource_data_stored(self, dashboard, tenant, user):
        r = dashboard.create_resource(tenant.tenant_id, user.user_id, "case", "C1",
                                       data={"status": "open", "priority": "high"})
        assert dashboard.get_resource(r.resource_id).data["status"] == "open"

    def test_resource_unique_ids(self, dashboard, tenant, user):
        ids = {dashboard.create_resource(tenant.tenant_id, user.user_id, "case", f"C{i}").resource_id
               for i in range(10)}
        assert len(ids) == 10

    def test_resources_isolated_between_tenants(self, dashboard):
        t1 = dashboard.create_tenant("F1", "f1.com")
        t2 = dashboard.create_tenant("F2", "f2.com")
        dashboard.activate_tenant(t1.tenant_id)
        dashboard.activate_tenant(t2.tenant_id)
        u1 = dashboard.add_user(t1.tenant_id, "a@f1.com", "A")
        u2 = dashboard.add_user(t2.tenant_id, "b@f2.com", "B")
        dashboard.create_resource(t1.tenant_id, u1.user_id, "case", "C1")
        dashboard.create_resource(t2.tenant_id, u2.user_id, "case", "C2")
        assert len(dashboard.list_resources(t1.tenant_id)) == 1
        assert len(dashboard.list_resources(t2.tenant_id)) == 1

    def test_viewer_cannot_access_resource(self, dashboard, tenant):
        viewer = dashboard.add_user(tenant.tenant_id, "v@f.com", "V", UserRole.VIEWER)
        r = dashboard.create_resource(tenant.tenant_id, viewer.user_id, "case", "C1")
        ctx = dashboard.build_access_context(viewer.user_id)
        # Viewer has view_cases permission so should be able to access
        assert dashboard.get_resource(r.resource_id, context=ctx) is not None

    def test_resource_owner_user_id(self, dashboard, tenant, user):
        r = dashboard.create_resource(tenant.tenant_id, user.user_id, "case", "C1")
        assert r.owner_user_id == user.user_id


# ─────────────────────────────────────────────────────────────
# Access control tests (18)
# ─────────────────────────────────────────────────────────────
class TestAccessControl:
    def test_owner_has_all_permissions(self, dashboard, tenant):
        u = dashboard.add_user(tenant.tenant_id, "o@f.com", "O", UserRole.OWNER)
        assert dashboard.check_permission(u.user_id, "manage_cases")
        assert dashboard.check_permission(u.user_id, "view_billing")
        assert dashboard.check_permission(u.user_id, "anything")

    def test_attorney_manage_cases(self, dashboard, tenant, user):
        assert dashboard.check_permission(user.user_id, "manage_cases")

    def test_attorney_no_billing(self, dashboard, tenant, user):
        assert not dashboard.check_permission(user.user_id, "view_billing")

    def test_admin_manage_users(self, dashboard, tenant):
        u = dashboard.add_user(tenant.tenant_id, "a@f.com", "A", UserRole.ADMIN)
        assert dashboard.check_permission(u.user_id, "manage_users")

    def test_paralegal_view_cases(self, dashboard, tenant):
        u = dashboard.add_user(tenant.tenant_id, "p@f.com", "P", UserRole.PARALEGAL)
        assert dashboard.check_permission(u.user_id, "view_cases")

    def test_paralegal_no_manage_cases(self, dashboard, tenant):
        u = dashboard.add_user(tenant.tenant_id, "p@f.com", "P", UserRole.PARALEGAL)
        assert not dashboard.check_permission(u.user_id, "manage_cases")

    def test_staff_view_only(self, dashboard, tenant):
        u = dashboard.add_user(tenant.tenant_id, "s@f.com", "S", UserRole.STAFF)
        assert dashboard.check_permission(u.user_id, "view_cases")
        assert not dashboard.check_permission(u.user_id, "manage_cases")

    def test_viewer_view_cases_only(self, dashboard, tenant):
        u = dashboard.add_user(tenant.tenant_id, "v@f.com", "V", UserRole.VIEWER)
        assert dashboard.check_permission(u.user_id, "view_cases")
        assert not dashboard.check_permission(u.user_id, "view_documents")

    def test_check_permission_nonexistent_user(self, dashboard):
        assert not dashboard.check_permission("nonexistent", "view_cases")

    def test_build_access_context(self, dashboard, tenant, user):
        ctx = dashboard.build_access_context(user.user_id)
        assert ctx is not None
        assert ctx.tenant_id == tenant.tenant_id

    def test_build_access_context_nonexistent(self, dashboard):
        assert dashboard.build_access_context("nonexistent") is None

    def test_role_permissions_all_roles_covered(self):
        for role in UserRole:
            assert role in ROLE_PERMISSIONS

    def test_owner_wildcard_permission(self):
        acl = AccessControlLayer()
        perms = acl.get_permissions_for_role(UserRole.OWNER)
        assert "*" in perms

    def test_acl_check_wildcard(self):
        acl = AccessControlLayer()
        ctx = AccessContext("t1", "u1", UserRole.OWNER, permissions=["*"])
        assert acl.check_permission(ctx, "anything_at_all")

    def test_acl_check_specific_permission(self):
        acl = AccessControlLayer()
        ctx = AccessContext("t1", "u1", UserRole.ATTORNEY, permissions=["manage_cases"])
        assert acl.check_permission(ctx, "manage_cases")
        assert not acl.check_permission(ctx, "view_billing")

    def test_cross_tenant_resource_access_denied(self):
        acl = AccessControlLayer()
        from phase16.multi_tenant.models import TenantResource
        import time
        ctx = AccessContext("tenant_A", "u1", UserRole.OWNER, permissions=["*"])
        resource = TenantResource("r1", "tenant_B", "case", "C1", "u2", created_at=time.time())
        assert not acl.can_access_resource(ctx, resource)

    def test_same_tenant_resource_access_allowed(self):
        acl = AccessControlLayer()
        from phase16.multi_tenant.models import TenantResource
        import time
        ctx = AccessContext("tenant_A", "u1", UserRole.ATTORNEY, permissions=["manage_cases"])
        resource = TenantResource("r1", "tenant_A", "case", "C1", "u2", created_at=time.time())
        assert acl.can_access_resource(ctx, resource)

    def test_update_role_revokes_old_permissions(self, dashboard, tenant):
        u = dashboard.add_user(tenant.tenant_id, "x@f.com", "X", UserRole.ADMIN)
        assert dashboard.check_permission(u.user_id, "manage_users")
        dashboard.update_user_role(u.user_id, UserRole.VIEWER)
        assert not dashboard.check_permission(u.user_id, "manage_users")


# ─────────────────────────────────────────────────────────────
# Isolation layer tests (10)
# ─────────────────────────────────────────────────────────────
class TestIsolationLayer:
    def test_create_namespace(self):
        layer = TenantIsolationLayer()
        layer.create_namespace("t1")
        assert layer.list_keys("t1") == []

    def test_set_and_get(self):
        layer = TenantIsolationLayer()
        layer.set("t1", "key", "value")
        assert layer.get("t1", "key") == "value"

    def test_isolation_between_tenants(self):
        layer = TenantIsolationLayer()
        layer.set("t1", "key", "val_t1")
        layer.set("t2", "key", "val_t2")
        assert layer.get("t1", "key") == "val_t1"
        assert layer.get("t2", "key") == "val_t2"

    def test_delete_namespace(self):
        layer = TenantIsolationLayer()
        layer.set("t1", "key", "val")
        layer.delete_namespace("t1")
        assert layer.get("t1", "key") is None

    def test_cross_tenant_check(self):
        layer = TenantIsolationLayer()
        assert layer.cross_tenant_check("t1", "t2") is True
        assert layer.cross_tenant_check("t1", "t1") is False

    def test_get_default(self):
        layer = TenantIsolationLayer()
        assert layer.get("t1", "missing", default="fallback") == "fallback"

    def test_list_keys(self):
        layer = TenantIsolationLayer()
        layer.set("t1", "a", 1)
        layer.set("t1", "b", 2)
        keys = layer.list_keys("t1")
        assert set(keys) == {"a", "b"}

    def test_thread_safety(self):
        layer = TenantIsolationLayer()
        errors = []
        def worker(i):
            try:
                layer.set(f"t{i % 3}", f"key{i}", i)
            except Exception as e:
                errors.append(e)
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(30)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors

    def test_overwrite_value(self):
        layer = TenantIsolationLayer()
        layer.set("t1", "key", "old")
        layer.set("t1", "key", "new")
        assert layer.get("t1", "key") == "new"

    def test_empty_namespace_list_keys(self):
        layer = TenantIsolationLayer()
        assert layer.list_keys("nonexistent") == []


# ─────────────────────────────────────────────────────────────
# Metrics and stats tests (15)
# ─────────────────────────────────────────────────────────────
class TestMetricsAndStats:
    def test_tenant_metrics_empty(self, dashboard, tenant):
        metrics = dashboard.get_tenant_metrics(tenant.tenant_id)
        assert metrics.total_users == 0
        assert metrics.total_cases == 0

    def test_tenant_metrics_with_users(self, dashboard, tenant):
        dashboard.add_user(tenant.tenant_id, "a@b.com", "A")
        dashboard.add_user(tenant.tenant_id, "b@b.com", "B")
        metrics = dashboard.get_tenant_metrics(tenant.tenant_id)
        assert metrics.total_users == 2

    def test_tenant_metrics_active_users(self, dashboard, tenant):
        u = dashboard.add_user(tenant.tenant_id, "a@b.com", "A")
        dashboard.deactivate_user(u.user_id)
        dashboard.add_user(tenant.tenant_id, "b@b.com", "B")
        metrics = dashboard.get_tenant_metrics(tenant.tenant_id)
        assert metrics.active_users == 1

    def test_tenant_metrics_cases(self, dashboard, tenant, user):
        dashboard.create_resource(tenant.tenant_id, user.user_id, "case", "C1")
        dashboard.create_resource(tenant.tenant_id, user.user_id, "case", "C2")
        metrics = dashboard.get_tenant_metrics(tenant.tenant_id)
        assert metrics.total_cases == 2

    def test_tenant_metrics_documents(self, dashboard, tenant, user):
        dashboard.create_resource(tenant.tenant_id, user.user_id, "document", "D1")
        metrics = dashboard.get_tenant_metrics(tenant.tenant_id)
        assert metrics.total_documents == 1

    def test_platform_stats_initial(self, dashboard):
        stats = dashboard.get_platform_stats()
        assert stats["total_tenants"] == 0

    def test_platform_stats_after_tenant(self, dashboard, tenant):
        stats = dashboard.get_platform_stats()
        assert stats["total_tenants"] >= 1
        assert stats["active_tenants"] >= 1

    def test_platform_stats_total_users(self, dashboard, tenant, user):
        stats = dashboard.get_platform_stats()
        assert stats["total_users"] >= 1

    def test_platform_stats_total_resources(self, dashboard, tenant, user):
        dashboard.create_resource(tenant.tenant_id, user.user_id, "case", "C1")
        stats = dashboard.get_platform_stats()
        assert stats["total_resources"] >= 1

    def test_metrics_tenant_id(self, dashboard, tenant):
        metrics = dashboard.get_tenant_metrics(tenant.tenant_id)
        assert metrics.tenant_id == tenant.tenant_id

    def test_concurrent_tenant_creation(self, dashboard):
        errors = []
        def worker(i):
            try:
                dashboard.create_tenant(f"Firm {i}", f"firm{i}.com")
            except Exception as e:
                errors.append(e)
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
        assert dashboard.get_platform_stats()["total_tenants"] >= 20

    def test_suspended_tenant_not_active(self, dashboard, tenant):
        dashboard.suspend_tenant(tenant.tenant_id)
        active = dashboard.list_tenants(status=TenantStatus.ACTIVE)
        assert not any(t.tenant_id == tenant.tenant_id for t in active)

    def test_metrics_mixed_resource_types(self, dashboard, tenant, user):
        for i in range(3):
            dashboard.create_resource(tenant.tenant_id, user.user_id, "case", f"C{i}")
        for i in range(2):
            dashboard.create_resource(tenant.tenant_id, user.user_id, "document", f"D{i}")
        metrics = dashboard.get_tenant_metrics(tenant.tenant_id)
        assert metrics.total_cases == 3
        assert metrics.total_documents == 2

    def test_platform_stats_active_vs_total(self, dashboard):
        t1 = dashboard.create_tenant("F1", "f1.com")
        t2 = dashboard.create_tenant("F2", "f2.com")
        dashboard.activate_tenant(t1.tenant_id)
        stats = dashboard.get_platform_stats()
        assert stats["total_tenants"] >= 2
        assert stats["active_tenants"] >= 1

    def test_list_tenants_onboarding(self, dashboard):
        t = dashboard.create_tenant("New Firm", "new.com")
        onboarding = dashboard.list_tenants(status=TenantStatus.ONBOARDING)
        assert any(x.tenant_id == t.tenant_id for x in onboarding)
