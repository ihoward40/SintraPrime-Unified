"""Phase 16C — Multi-Tenant Law Firm Dashboard: data models."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class TenantStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ONBOARDING = "onboarding"
    CHURNED = "churned"


class UserRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    ATTORNEY = "attorney"
    PARALEGAL = "paralegal"
    STAFF = "staff"
    VIEWER = "viewer"


class IsolationLevel(str, Enum):
    SHARED = "shared"          # shared DB schema, row-level isolation
    SCHEMA = "schema"          # separate DB schema per tenant
    DEDICATED = "dedicated"    # dedicated DB instance


@dataclass
class Tenant:
    """A law firm tenant."""
    tenant_id: str
    firm_name: str
    domain: str
    status: TenantStatus = TenantStatus.ONBOARDING
    isolation_level: IsolationLevel = IsolationLevel.SHARED
    plan_tier: str = "starter"
    settings: Dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_active(self) -> bool:
        return self.status == TenantStatus.ACTIVE


@dataclass
class TenantUser:
    """A user within a tenant."""
    user_id: str
    tenant_id: str
    email: str
    name: str
    role: UserRole = UserRole.STAFF
    permissions: List[str] = field(default_factory=list)
    active: bool = True
    last_login: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TenantResource:
    """A resource (case, document, etc.) owned by a tenant."""
    resource_id: str
    tenant_id: str
    resource_type: str
    name: str
    owner_user_id: str
    data: Dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0
    updated_at: float = 0.0


@dataclass
class TenantMetrics:
    """Aggregated metrics for a tenant."""
    tenant_id: str
    total_users: int = 0
    active_users: int = 0
    total_cases: int = 0
    total_documents: int = 0
    api_calls_this_month: int = 0
    storage_used_mb: float = 0.0
    last_activity: Optional[float] = None


@dataclass
class AccessContext:
    """Security context for a request within a tenant."""
    tenant_id: str
    user_id: str
    role: UserRole
    permissions: List[str] = field(default_factory=list)
    ip_address: str = ""
    session_id: str = ""
