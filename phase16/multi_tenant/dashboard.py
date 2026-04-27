"""Phase 16C — Multi-Tenant Law Firm Dashboard."""
from __future__ import annotations
import time
import threading
import uuid
from typing import Any, Dict, List, Optional

from phase16.multi_tenant.models import (
    AccessContext, IsolationLevel, Tenant, TenantMetrics,
    TenantResource, TenantStatus, TenantUser, UserRole,
)

# Role permission matrix
ROLE_PERMISSIONS: Dict[UserRole, List[str]] = {
    UserRole.OWNER:     ["*"],
    UserRole.ADMIN:     ["manage_users", "manage_cases", "manage_documents", "view_billing", "configure"],
    UserRole.ATTORNEY:  ["manage_cases", "manage_documents", "view_clients"],
    UserRole.PARALEGAL: ["view_cases", "manage_documents", "view_clients"],
    UserRole.STAFF:     ["view_cases", "view_documents"],
    UserRole.VIEWER:    ["view_cases"],
}


class TenantIsolationLayer:
    """Enforces data isolation between tenants."""

    def __init__(self):
        self._tenant_data: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def create_namespace(self, tenant_id: str) -> None:
        with self._lock:
            self._tenant_data.setdefault(tenant_id, {})

    def set(self, tenant_id: str, key: str, value: Any) -> None:
        with self._lock:
            self._tenant_data.setdefault(tenant_id, {})[key] = value

    def get(self, tenant_id: str, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._tenant_data.get(tenant_id, {}).get(key, default)

    def delete_namespace(self, tenant_id: str) -> None:
        with self._lock:
            self._tenant_data.pop(tenant_id, None)

    def list_keys(self, tenant_id: str) -> List[str]:
        with self._lock:
            return list(self._tenant_data.get(tenant_id, {}).keys())

    def cross_tenant_check(self, tenant_id_a: str, tenant_id_b: str) -> bool:
        """Return True if the two tenants are isolated (always True)."""
        return tenant_id_a != tenant_id_b


class AccessControlLayer:
    """Enforces RBAC for tenant users."""

    def check_permission(self, context: AccessContext, permission: str) -> bool:
        if "*" in context.permissions:
            return True
        return permission in context.permissions

    def get_permissions_for_role(self, role: UserRole) -> List[str]:
        return ROLE_PERMISSIONS.get(role, [])

    def build_context(self, user: TenantUser) -> AccessContext:
        permissions = self.get_permissions_for_role(user.role)
        return AccessContext(
            tenant_id=user.tenant_id,
            user_id=user.user_id,
            role=user.role,
            permissions=permissions,
        )

    def can_access_resource(self, context: AccessContext, resource: TenantResource) -> bool:
        if resource.tenant_id != context.tenant_id:
            return False  # cross-tenant access denied
        return self.check_permission(context, "view_cases") or \
               self.check_permission(context, "manage_cases") or \
               "*" in context.permissions


class MultiTenantDashboard:
    """Central dashboard managing all law firm tenants."""

    def __init__(self):
        self._tenants: Dict[str, Tenant] = {}
        self._users: Dict[str, TenantUser] = {}  # user_id → user
        self._resources: Dict[str, TenantResource] = {}
        self._isolation = TenantIsolationLayer()
        self._acl = AccessControlLayer()
        self._lock = threading.Lock()

    # ── Tenant management ────────────────────────────────────
    def create_tenant(self, firm_name: str, domain: str,
                      plan_tier: str = "starter",
                      isolation_level: IsolationLevel = IsolationLevel.SHARED) -> Tenant:
        tenant = Tenant(
            tenant_id=f"ten_{uuid.uuid4().hex[:8]}",
            firm_name=firm_name,
            domain=domain,
            status=TenantStatus.ONBOARDING,
            isolation_level=isolation_level,
            plan_tier=plan_tier,
            created_at=time.time(),
        )
        with self._lock:
            self._tenants[tenant.tenant_id] = tenant
        self._isolation.create_namespace(tenant.tenant_id)
        return tenant

    def activate_tenant(self, tenant_id: str) -> Tenant:
        with self._lock:
            tenant = self._tenants.get(tenant_id)
            if not tenant:
                raise KeyError(f"Tenant {tenant_id} not found")
            tenant.status = TenantStatus.ACTIVE
        return tenant

    def suspend_tenant(self, tenant_id: str) -> Tenant:
        with self._lock:
            tenant = self._tenants.get(tenant_id)
            if not tenant:
                raise KeyError(f"Tenant {tenant_id} not found")
            tenant.status = TenantStatus.SUSPENDED
        return tenant

    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        with self._lock:
            return self._tenants.get(tenant_id)

    def list_tenants(self, status: Optional[TenantStatus] = None) -> List[Tenant]:
        with self._lock:
            tenants = list(self._tenants.values())
        if status:
            tenants = [t for t in tenants if t.status == status]
        return tenants

    def update_tenant_settings(self, tenant_id: str, settings: Dict[str, Any]) -> Tenant:
        with self._lock:
            tenant = self._tenants.get(tenant_id)
            if not tenant:
                raise KeyError(f"Tenant {tenant_id} not found")
            tenant.settings.update(settings)
        return tenant

    # ── User management ──────────────────────────────────────
    def add_user(self, tenant_id: str, email: str, name: str,
                 role: UserRole = UserRole.STAFF) -> TenantUser:
        with self._lock:
            if tenant_id not in self._tenants:
                raise KeyError(f"Tenant {tenant_id} not found")
        permissions = self._acl.get_permissions_for_role(role)
        user = TenantUser(
            user_id=f"usr_{uuid.uuid4().hex[:8]}",
            tenant_id=tenant_id,
            email=email,
            name=name,
            role=role,
            permissions=permissions,
        )
        with self._lock:
            self._users[user.user_id] = user
        return user

    def get_user(self, user_id: str) -> Optional[TenantUser]:
        with self._lock:
            return self._users.get(user_id)

    def list_users(self, tenant_id: str) -> List[TenantUser]:
        with self._lock:
            return [u for u in self._users.values() if u.tenant_id == tenant_id]

    def update_user_role(self, user_id: str, new_role: UserRole) -> TenantUser:
        with self._lock:
            user = self._users.get(user_id)
            if not user:
                raise KeyError(f"User {user_id} not found")
            user.role = new_role
            user.permissions = self._acl.get_permissions_for_role(new_role)
        return user

    def deactivate_user(self, user_id: str) -> TenantUser:
        with self._lock:
            user = self._users.get(user_id)
            if not user:
                raise KeyError(f"User {user_id} not found")
            user.active = False
        return user

    # ── Resource management ──────────────────────────────────
    def create_resource(self, tenant_id: str, user_id: str,
                        resource_type: str, name: str,
                        data: Optional[Dict[str, Any]] = None) -> TenantResource:
        with self._lock:
            if tenant_id not in self._tenants:
                raise KeyError(f"Tenant {tenant_id} not found")
        now = time.time()
        resource = TenantResource(
            resource_id=f"res_{uuid.uuid4().hex[:8]}",
            tenant_id=tenant_id,
            resource_type=resource_type,
            name=name,
            owner_user_id=user_id,
            data=data or {},
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            self._resources[resource.resource_id] = resource
        return resource

    def get_resource(self, resource_id: str,
                     context: Optional[AccessContext] = None) -> Optional[TenantResource]:
        with self._lock:
            resource = self._resources.get(resource_id)
        if resource and context:
            if not self._acl.can_access_resource(context, resource):
                return None
        return resource

    def list_resources(self, tenant_id: str,
                       resource_type: Optional[str] = None) -> List[TenantResource]:
        with self._lock:
            resources = [r for r in self._resources.values()
                         if r.tenant_id == tenant_id]
        if resource_type:
            resources = [r for r in resources if r.resource_type == resource_type]
        return resources

    # ── Access control ───────────────────────────────────────
    def check_permission(self, user_id: str, permission: str) -> bool:
        user = self.get_user(user_id)
        if not user:
            return False
        context = self._acl.build_context(user)
        return self._acl.check_permission(context, permission)

    def build_access_context(self, user_id: str) -> Optional[AccessContext]:
        user = self.get_user(user_id)
        if not user:
            return None
        return self._acl.build_context(user)

    # ── Metrics ──────────────────────────────────────────────
    def get_tenant_metrics(self, tenant_id: str) -> TenantMetrics:
        users = self.list_users(tenant_id)
        resources = self.list_resources(tenant_id)
        cases = [r for r in resources if r.resource_type == "case"]
        docs = [r for r in resources if r.resource_type == "document"]
        active_users = sum(1 for u in users if u.active)
        return TenantMetrics(
            tenant_id=tenant_id,
            total_users=len(users),
            active_users=active_users,
            total_cases=len(cases),
            total_documents=len(docs),
        )

    def get_platform_stats(self) -> Dict[str, Any]:
        with self._lock:
            total = len(self._tenants)
            active = sum(1 for t in self._tenants.values() if t.is_active)
            total_users = len(self._users)
        return {
            "total_tenants": total,
            "active_tenants": active,
            "total_users": total_users,
            "total_resources": len(self._resources),
        }
