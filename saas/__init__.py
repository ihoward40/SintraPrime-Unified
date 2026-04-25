"""
SintraPrime-Unified SaaS Infrastructure Package

Multi-tenant subscription management system for law firms, financial advisors, and individuals.
"""

from .subscription_engine import (
    SubscriptionEngine,
    SubscriptionPlan,
    Subscription,
    PlanTier,
)
from .tenant_manager import (
    TenantManager,
    Tenant,
    WhiteLabelConfig,
    TenantMetrics,
)
from .billing_portal import (
    BillingPortal,
    BillingDashboard,
    Invoice,
)
from .onboarding import (
    OnboardingEngine,
    OnboardingStep,
    OnboardingState,
)
from .usage_tracker import (
    UsageTracker,
    UsageMetric,
    UsageReport,
    QuotaStatus,
)
from .marketplace import (
    Marketplace,
    AddOn,
    AddOnType,
)

__all__ = [
    # Subscription
    "SubscriptionEngine",
    "SubscriptionPlan",
    "Subscription",
    "PlanTier",
    # Tenant
    "TenantManager",
    "Tenant",
    "WhiteLabelConfig",
    "TenantMetrics",
    # Billing
    "BillingPortal",
    "BillingDashboard",
    "Invoice",
    # Onboarding
    "OnboardingEngine",
    "OnboardingStep",
    "OnboardingState",
    # Usage
    "UsageTracker",
    "UsageMetric",
    "UsageReport",
    "QuotaStatus",
    # Marketplace
    "Marketplace",
    "AddOn",
    "AddOnType",
]

__version__ = "1.0.0"
