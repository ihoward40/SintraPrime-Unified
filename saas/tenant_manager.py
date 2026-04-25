"""
Tenant Manager for SintraPrime-Unified SaaS

Manages multi-tenant architecture with schema-per-tenant isolation,
tenant lifecycle, and white-label configuration.
"""

import logging
import psycopg2
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, List, Any
import json
import uuid

logger = logging.getLogger(__name__)


class TenantStatus(str, Enum):
    """Tenant lifecycle states."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"
    TRIAL = "trial"


class DataResidency(str, Enum):
    """Data residency options."""
    US = "us"
    EU = "eu"
    UK = "uk"


@dataclass
class WhiteLabelConfig:
    """White-label configuration for tenants."""
    firm_name: str
    logo_url: Optional[str] = None
    primary_color: str = "#0066CC"
    secondary_color: str = "#F0F0F0"
    accent_color: str = "#FF6600"
    custom_domain: Optional[str] = None
    ai_persona_name: str = "SintraPrime AI"
    support_email: str = "support@sintraprime.com"
    terms_url: Optional[str] = None
    privacy_url: Optional[str] = None
    custom_footer: Optional[str] = None
    enable_branded_emails: bool = True
    favicon_url: Optional[str] = None


@dataclass
class TenantMetrics:
    """Metrics for a tenant."""
    tenant_id: str
    active_users: int
    total_documents: int
    total_queries: int
    storage_gb: float
    monthly_api_calls: int
    monthly_voice_minutes: int
    last_updated: datetime = field(default_factory=datetime.utcnow)


@dataclass
class OnboardingProgress:
    """Onboarding progress tracking."""
    current_step: int = 0  # 0-6
    completed_steps: List[int] = field(default_factory=list)
    step_data: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    completion_percentage: int = 0
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


@dataclass
class Tenant:
    """Represents a SintraPrime tenant."""
    id: str
    name: str
    plan_id: str
    status: TenantStatus
    admin_email: str
    schema_name: str
    custom_domain: Optional[str]
    white_label_config: WhiteLabelConfig
    data_residency: DataResidency
    onboarding_progress: OnboardingProgress
    api_keys: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    suspended_at: Optional[datetime] = None
    suspension_reason: Optional[str] = None
    deleted_at: Optional[datetime] = None


class TenantManager:
    """
    Manages multi-tenant SaaS infrastructure.
    
    Features:
    - Schema-per-tenant PostgreSQL isolation
    - Tenant lifecycle management
    - White-label configuration
    - Data residency selection
    - Onboarding progress tracking
    - Resource quotas
    """

    # Default resource quotas per plan
    PLAN_QUOTAS = {
        "solo": {
            "max_users": 1,
            "max_api_keys": 2,
            "storage_gb": 10,
            "api_rate_limit": 100,  # per hour
            "workspace_invites": 0,
        },
        "professional": {
            "max_users": 5,
            "max_api_keys": 5,
            "storage_gb": 100,
            "api_rate_limit": 1000,
            "workspace_invites": 4,
        },
        "law_firm": {
            "max_users": 25,
            "max_api_keys": 10,
            "storage_gb": 500,
            "api_rate_limit": 5000,
            "workspace_invites": 24,
        },
        "enterprise": {
            "max_users": None,  # unlimited
            "max_api_keys": None,
            "storage_gb": None,
            "api_rate_limit": None,
            "workspace_invites": None,
        },
    }

    def __init__(self, postgres_url: str):
        """Initialize with PostgreSQL connection string."""
        self.postgres_url = postgres_url
        self._tenants: Dict[str, Tenant] = {}
        self._schemas_created: set = set()

    def _get_connection(self):
        """Get a PostgreSQL connection."""
        try:
            conn = psycopg2.connect(self.postgres_url)
            conn.autocommit = True
            return conn
        except psycopg2.Error as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise

    def create_tenant(
        self,
        name: str,
        plan_id: str,
        admin_email: str,
        custom_domain: Optional[str] = None,
        data_residency: DataResidency = DataResidency.US,
        white_label_config: Optional[WhiteLabelConfig] = None,
    ) -> Tenant:
        """
        Create a new tenant.
        
        Args:
            name: Tenant/firm name
            plan_id: Subscription plan (solo, professional, law_firm, enterprise)
            admin_email: Admin email address
            custom_domain: Optional custom domain
            data_residency: Data residency location
            white_label_config: White-label configuration
            
        Returns:
            Tenant object
        """
        tenant_id = str(uuid.uuid4())
        schema_name = f"tenant_{tenant_id.replace('-', '_')}"

        if white_label_config is None:
            white_label_config = WhiteLabelConfig(firm_name=name)
        else:
            white_label_config.firm_name = name

        tenant = Tenant(
            id=tenant_id,
            name=name,
            plan_id=plan_id,
            status=TenantStatus.TRIAL if plan_id == "trial" else TenantStatus.ACTIVE,
            admin_email=admin_email,
            schema_name=schema_name,
            custom_domain=custom_domain,
            white_label_config=white_label_config,
            data_residency=data_residency,
            onboarding_progress=OnboardingProgress(),
        )

        # Create the schema
        if self.provision_schema(tenant_id):
            self._tenants[tenant_id] = tenant
            logger.info(f"Created tenant {tenant_id} ({name})")
            return tenant
        else:
            raise Exception(f"Failed to provision schema for tenant {tenant_id}")

    def provision_schema(self, tenant_id: str) -> bool:
        """
        Create an isolated PostgreSQL schema for the tenant.
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            True if successful, False otherwise
        """
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            logger.error(f"Tenant not found: {tenant_id}")
            return False

        schema_name = tenant.schema_name

        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Create schema
            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
            logger.info(f"Created schema {schema_name}")

            # Create core tables in the tenant schema
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {schema_name}.users (
                    id UUID PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    name VARCHAR(255),
                    role VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {schema_name}.matters (
                    id UUID PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    client_id UUID,
                    status VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {schema_name}.documents (
                    id UUID PRIMARY KEY,
                    matter_id UUID,
                    filename VARCHAR(255) NOT NULL,
                    document_type VARCHAR(50),
                    size_bytes BIGINT,
                    storage_path VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {schema_name}.usage_logs (
                    id UUID PRIMARY KEY,
                    metric_type VARCHAR(50),
                    quantity INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {schema_name}.api_keys (
                    id UUID PRIMARY KEY,
                    key_hash VARCHAR(255) UNIQUE NOT NULL,
                    name VARCHAR(255),
                    last_used_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP
                )
            """)

            conn.commit()
            cursor.close()
            conn.close()

            self._schemas_created.add(schema_name)
            logger.info(f"Provisioned schema {schema_name} for tenant {tenant_id}")
            return True

        except psycopg2.Error as e:
            logger.error(f"Failed to provision schema: {e}")
            return False

    def configure_white_label(
        self,
        tenant_id: str,
        config: WhiteLabelConfig
    ) -> bool:
        """Update white-label configuration."""
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            logger.error(f"Tenant not found: {tenant_id}")
            return False

        tenant.white_label_config = config
        tenant.updated_at = datetime.utcnow()
        logger.info(f"Updated white-label config for tenant {tenant_id}")
        return True

    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """Get tenant by ID."""
        return self._tenants.get(tenant_id)

    def get_tenant_by_domain(self, domain: str) -> Optional[Tenant]:
        """Get tenant by custom domain."""
        for tenant in self._tenants.values():
            if tenant.custom_domain == domain:
                return tenant
        return None

    def update_custom_domain(self, tenant_id: str, domain: str) -> bool:
        """Update custom domain for a tenant."""
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return False

        # Check if domain is already taken
        if self.get_tenant_by_domain(domain):
            logger.warning(f"Domain already in use: {domain}")
            return False

        tenant.custom_domain = domain
        tenant.updated_at = datetime.utcnow()
        logger.info(f"Updated domain for tenant {tenant_id} to {domain}")
        return True

    def suspend_tenant(self, tenant_id: str, reason: str) -> bool:
        """Suspend a tenant's access."""
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return False

        tenant.status = TenantStatus.SUSPENDED
        tenant.suspended_at = datetime.utcnow()
        tenant.suspension_reason = reason
        tenant.updated_at = datetime.utcnow()

        logger.warning(f"Suspended tenant {tenant_id}: {reason}")
        return True

    def reactivate_tenant(self, tenant_id: str) -> bool:
        """Reactivate a suspended tenant."""
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return False

        if tenant.status != TenantStatus.SUSPENDED:
            logger.warning(f"Cannot reactivate tenant with status: {tenant.status}")
            return False

        tenant.status = TenantStatus.ACTIVE
        tenant.suspended_at = None
        tenant.suspension_reason = None
        tenant.updated_at = datetime.utcnow()

        logger.info(f"Reactivated tenant {tenant_id}")
        return True

    def delete_tenant(self, tenant_id: str, reason: str = "User requested") -> bool:
        """
        Delete a tenant and its schema.
        
        This is irreversible and should include a confirmation step.
        """
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return False

        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Drop the tenant schema and all its data
            cursor.execute(f"DROP SCHEMA IF EXISTS {tenant.schema_name} CASCADE")

            conn.commit()
            cursor.close()
            conn.close()

            tenant.status = TenantStatus.DELETED
            tenant.deleted_at = datetime.utcnow()
            tenant.updated_at = datetime.utcnow()

            logger.info(f"Deleted tenant {tenant_id}: {reason}")
            return True

        except psycopg2.Error as e:
            logger.error(f"Failed to delete tenant schema: {e}")
            return False

    def get_tenant_metrics(self, tenant_id: str) -> Optional[TenantMetrics]:
        """Get usage metrics for a tenant."""
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return None

        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            schema = tenant.schema_name

            # Query user count
            cursor.execute(f"SELECT COUNT(*) FROM {schema}.users")
            active_users = cursor.fetchone()[0]

            # Query document count
            cursor.execute(f"SELECT COUNT(*) FROM {schema}.documents")
            total_documents = cursor.fetchone()[0]

            # Query storage
            cursor.execute(f"""
                SELECT COALESCE(SUM(size_bytes), 0) FROM {schema}.documents
            """)
            storage_bytes = cursor.fetchone()[0]
            storage_gb = storage_bytes / (1024 ** 3)

            # Query API calls
            cursor.execute(f"""
                SELECT COUNT(*) FROM {schema}.usage_logs
                WHERE metric_type = 'api_call'
                AND created_at >= NOW() - INTERVAL '30 days'
            """)
            monthly_api_calls = cursor.fetchone()[0]

            cursor.close()
            conn.close()

            return TenantMetrics(
                tenant_id=tenant_id,
                active_users=active_users,
                total_documents=total_documents,
                total_queries=monthly_api_calls,
                storage_gb=storage_gb,
                monthly_api_calls=monthly_api_calls,
                monthly_voice_minutes=0,  # Would be tracked in production
            )

        except psycopg2.Error as e:
            logger.error(f"Failed to get tenant metrics: {e}")
            return None

    def update_onboarding_progress(
        self,
        tenant_id: str,
        step: int,
        step_data: Dict[str, Any]
    ) -> bool:
        """Update onboarding progress for a tenant."""
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return False

        tenant.onboarding_progress.current_step = step
        if step not in tenant.onboarding_progress.completed_steps:
            tenant.onboarding_progress.completed_steps.append(step)

        tenant.onboarding_progress.step_data[step] = step_data
        tenant.onboarding_progress.completion_percentage = (
            (len(tenant.onboarding_progress.completed_steps) / 6) * 100
        )

        if tenant.onboarding_progress.completion_percentage == 100:
            tenant.onboarding_progress.completed_at = datetime.utcnow()

        logger.info(f"Updated onboarding for tenant {tenant_id}: step {step}")
        return True

    def generate_api_key(self, tenant_id: str, key_name: str) -> Optional[str]:
        """Generate an API key for a tenant."""
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return None

        quota = self.PLAN_QUOTAS.get(tenant.plan_id, {})
        max_keys = quota.get("max_api_keys")

        if max_keys and len(tenant.api_keys) >= max_keys:
            logger.warning(f"API key limit reached for tenant {tenant_id}")
            return None

        # Generate a unique API key
        api_key = f"sk-{tenant_id}-{uuid.uuid4().hex[:32]}"
        tenant.api_keys.append(api_key)

        logger.info(f"Generated API key for tenant {tenant_id}")
        return api_key

    def get_quota(self, tenant_id: str) -> Optional[Dict]:
        """Get resource quota for a tenant."""
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return None

        return self.PLAN_QUOTAS.get(tenant.plan_id)

    def check_quota(
        self,
        tenant_id: str,
        resource: str,
        current_value: int
    ) -> Tuple[bool, Optional[int]]:
        """
        Check if a tenant has exceeded a resource quota.
        
        Returns:
            (is_within_quota, limit_value)
        """
        quota = self.get_quota(tenant_id)
        if not quota:
            return True, None

        limit = quota.get(resource)
        if limit is None:
            return True, None

        if current_value >= limit:
            return False, limit

        return True, limit

    def list_tenants(self, status: Optional[TenantStatus] = None) -> List[Tenant]:
        """List all tenants, optionally filtered by status."""
        tenants = list(self._tenants.values())
        if status:
            tenants = [t for t in tenants if t.status == status]
        return tenants

    def get_plan_features(self, plan_id: str) -> Dict[str, Any]:
        """Get feature matrix for a plan."""
        features_map = {
            "solo": {
                "max_users": 1,
                "queries_per_day": 50,
                "voice_minutes_per_month": 60,
                "documents_per_month": 500,
                "white_label": False,
                "client_portal": False,
                "custom_models": False,
                "sla_uptime": None,
                "dedicated_support": False,
            },
            "professional": {
                "max_users": 5,
                "queries_per_day": 500,
                "voice_minutes_per_month": 300,
                "documents_per_month": 2000,
                "white_label": False,
                "client_portal": False,
                "custom_models": False,
                "sla_uptime": None,
                "dedicated_support": True,
            },
            "law_firm": {
                "max_users": 25,
                "queries_per_day": None,  # unlimited
                "voice_minutes_per_month": None,
                "documents_per_month": None,
                "white_label": True,
                "client_portal": True,
                "custom_models": False,
                "sla_uptime": 0.999,
                "dedicated_support": True,
            },
            "enterprise": {
                "max_users": None,
                "queries_per_day": None,
                "voice_minutes_per_month": None,
                "documents_per_month": None,
                "white_label": True,
                "client_portal": True,
                "custom_models": True,
                "sla_uptime": 0.9995,
                "dedicated_support": True,
            },
        }
        return features_map.get(plan_id, {})
