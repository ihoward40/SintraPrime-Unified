"""
Marketplace for SintraPrime-Unified SaaS

Add-on marketplace management, revenue sharing, and tenant-specific configuration.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, List, Any
from decimal import Decimal
import uuid

logger = logging.getLogger(__name__)


class AddOnType(str, Enum):
    """Types of add-ons available."""
    COURT_FILING = "court_filing_automation"
    DEPOSITION_PREP = "ai_deposition_prep"
    EXPERT_WITNESS = "expert_witness_finder"
    PACER_ALERTS = "realtime_pacer_alerts"
    FORENSIC_ACCOUNTING = "forensic_accounting_suite"
    MULTI_LANGUAGE = "multi_language_support"
    ML_PREDICTIONS = "advanced_ml_predictions"


class AddOnStatus(str, Enum):
    """Status of an add-on."""
    AVAILABLE = "available"
    ENABLED = "enabled"
    DISABLED = "disabled"
    TRIAL = "trial"
    DEPRECATED = "deprecated"


@dataclass
class AddOnMetadata:
    """Additional metadata for an add-on."""
    features: List[str] = field(default_factory=list)
    documentation_url: Optional[str] = None
    support_tier: str = "standard"  # "standard", "premium", "enterprise"
    setup_time_minutes: int = 15
    training_required: bool = False
    integrations: List[str] = field(default_factory=list)


@dataclass
class AddOn:
    """Represents a marketplace add-on."""
    id: str
    type: AddOnType
    name: str
    description: str
    price: Decimal  # Monthly price
    trial_available: bool
    trial_days: int = 30
    max_trial_per_tenant: bool = True  # Only one trial allowed
    vendor: str = "SintraPrime"
    status: AddOnStatus = AddOnStatus.AVAILABLE
    revenue_share: Decimal = Decimal("20")  # For third-party vendors
    metadata: AddOnMetadata = field(default_factory=AddOnMetadata)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TenantAddOnSubscription:
    """Tenant's subscription to an add-on."""
    id: str
    tenant_id: str
    addon_id: str
    status: str  # "trial", "active", "canceled", "expired"
    enabled_at: datetime = field(default_factory=datetime.utcnow)
    trial_end: Optional[datetime] = None
    canceled_at: Optional[datetime] = None
    config: Dict[str, Any] = field(default_factory=dict)
    usage_metrics: Dict[str, int] = field(default_factory=dict)


@dataclass
class MarketplaceMetrics:
    """Metrics for the marketplace."""
    total_addons: int = 0
    total_subscribers: int = 0
    revenue_generated: Decimal = field(default_factory=lambda: Decimal("0"))
    revenue_shared: Decimal = field(default_factory=lambda: Decimal("0"))
    most_popular_addons: List[Dict[str, Any]] = field(default_factory=list)
    adoption_rate: float = 0.0  # percentage


class Marketplace:
    """
    SaaS add-on marketplace.
    
    Features:
    - Curated add-ons for different practice areas
    - Trial management
    - Tenant-specific configuration
    - Revenue sharing for third-party vendors
    - Usage tracking per add-on
    - Add-on recommendations
    """

    # Built-in add-ons with standard pricing
    STANDARD_ADDONS = {
        AddOnType.COURT_FILING: AddOn(
            id=str(uuid.uuid4()),
            type=AddOnType.COURT_FILING,
            name="Court Filing Automation",
            description="Automated document preparation and e-filing for courts",
            price=Decimal("99"),
            trial_available=True,
            vendor="SintraPrime",
            metadata=AddOnMetadata(
                features=[
                    "Automated form filling",
                    "Multi-jurisdiction support",
                    "E-filing integration",
                    "Court rule compliance checking",
                    "Filing status tracking",
                ],
                documentation_url="https://docs.sintraprime.com/court-filing",
                support_tier="premium",
                setup_time_minutes=30,
                training_required=True,
                integrations=["PACER", "CourtTrax", "LexisNexis"],
            ),
        ),
        AddOnType.DEPOSITION_PREP: AddOn(
            id=str(uuid.uuid4()),
            type=AddOnType.DEPOSITION_PREP,
            name="AI Deposition Prep",
            description="AI-powered deposition preparation with transcript analysis",
            price=Decimal("79"),
            trial_available=True,
            vendor="SintraPrime",
            metadata=AddOnMetadata(
                features=[
                    "Auto transcript analysis",
                    "Question recommendations",
                    "Contradiction detection",
                    "Deposition timeline",
                    "Video conferencing",
                ],
                documentation_url="https://docs.sintraprime.com/deposition-prep",
                setup_time_minutes=20,
                integrations=["Zoom", "Teams", "WebEx"],
            ),
        ),
        AddOnType.EXPERT_WITNESS: AddOn(
            id=str(uuid.uuid4()),
            type=AddOnType.EXPERT_WITNESS,
            name="Expert Witness Finder",
            description="Database of vetted expert witnesses with ratings and rates",
            price=Decimal("49"),
            trial_available=True,
            vendor="SintraPrime",
            metadata=AddOnMetadata(
                features=[
                    "Searchable expert database",
                    "Credentials verification",
                    "Rate negotiations",
                    "Testimonial history",
                    "Contact management",
                ],
                documentation_url="https://docs.sintraprime.com/expert-finder",
                setup_time_minutes=10,
            ),
        ),
        AddOnType.PACER_ALERTS: AddOn(
            id=str(uuid.uuid4()),
            type=AddOnType.PACER_ALERTS,
            name="Real-Time PACER Alerts",
            description="Instant notifications on PACER docket updates",
            price=Decimal("39"),
            trial_available=True,
            vendor="SintraPrime",
            metadata=AddOnMetadata(
                features=[
                    "Real-time docket monitoring",
                    "Custom alert rules",
                    "Mobile notifications",
                    "Docket analysis",
                    "Multi-case tracking",
                ],
                documentation_url="https://docs.sintraprime.com/pacer-alerts",
                setup_time_minutes=15,
            ),
        ),
        AddOnType.FORENSIC_ACCOUNTING: AddOn(
            id=str(uuid.uuid4()),
            type=AddOnType.FORENSIC_ACCOUNTING,
            name="Forensic Accounting Suite",
            description="Complete forensic accounting tools for financial litigation",
            price=Decimal("149"),
            trial_available=True,
            vendor="SintraPrime",
            metadata=AddOnMetadata(
                features=[
                    "Financial statement analysis",
                    "Fraud detection algorithms",
                    "Cash flow analysis",
                    "Valuation models",
                    "Report generation",
                    "Expert integrations",
                ],
                documentation_url="https://docs.sintraprime.com/forensic-accounting",
                support_tier="premium",
                setup_time_minutes=45,
                training_required=True,
            ),
        ),
        AddOnType.MULTI_LANGUAGE: AddOn(
            id=str(uuid.uuid4()),
            type=AddOnType.MULTI_LANGUAGE,
            name="Multi-Language Support",
            description="Support for 25+ languages in documents and client portal",
            price=Decimal("59"),
            trial_available=True,
            vendor="SintraPrime",
            metadata=AddOnMetadata(
                features=[
                    "25+ language support",
                    "Document translation",
                    "Client portal localization",
                    "RTL language support",
                    "Cultural formatting",
                ],
                documentation_url="https://docs.sintraprime.com/multi-language",
                setup_time_minutes=20,
            ),
        ),
        AddOnType.ML_PREDICTIONS: AddOn(
            id=str(uuid.uuid4()),
            type=AddOnType.ML_PREDICTIONS,
            name="Advanced ML Predictions",
            description="Machine learning models for case outcome predictions",
            price=Decimal("99"),
            trial_available=True,
            vendor="SintraPrime",
            metadata=AddOnMetadata(
                features=[
                    "Case outcome prediction",
                    "Settlement probability",
                    "Risk assessment",
                    "Historical case analysis",
                    "Custom model training",
                ],
                documentation_url="https://docs.sintraprime.com/ml-predictions",
                support_tier="premium",
                setup_time_minutes=60,
                training_required=True,
            ),
        ),
    }

    def __init__(self):
        """Initialize marketplace."""
        self._addons: Dict[str, AddOn] = {}
        self._tenant_subscriptions: Dict[str, List[TenantAddOnSubscription]] = {}
        self._addon_trials: Dict[str, List[str]] = {}  # Track used trials
        self._revenue: Dict[str, Dict] = {}  # Revenue tracking

        # Load standard add-ons
        for addon in self.STANDARD_ADDONS.values():
            self._addons[addon.id] = addon

    def list_addons(
        self,
        tenant_id: Optional[str] = None,
        category: Optional[AddOnType] = None,
        include_disabled: bool = False
    ) -> List[AddOn]:
        """
        List available add-ons.
        
        Args:
            tenant_id: Filter by tenant's enabled/subscribed add-ons
            category: Filter by add-on type
            include_disabled: Include disabled add-ons
            
        Returns:
            List of add-ons
        """
        addons = list(self._addons.values())

        # Filter by status
        if not include_disabled:
            addons = [a for a in addons if a.status != AddOnStatus.DEPRECATED]

        # Filter by category
        if category:
            addons = [a for a in addons if a.type == category]

        # Filter by tenant subscription status if tenant_id provided
        if tenant_id:
            tenant_subs = self._tenant_subscriptions.get(tenant_id, [])
            sub_ids = {sub.addon_id for sub in tenant_subs}

            for addon in addons:
                addon.status = (
                    AddOnStatus.ENABLED if addon.id in sub_ids
                    else addon.status
                )

        return addons

    def get_addon(self, addon_id: str) -> Optional[AddOn]:
        """Get add-on details."""
        return self._addons.get(addon_id)

    def enable_addon(
        self,
        tenant_id: str,
        addon_id: str,
        use_trial: bool = False,
        config: Optional[Dict[str, Any]] = None
    ) -> Optional[TenantAddOnSubscription]:
        """
        Enable an add-on for a tenant.
        
        Args:
            tenant_id: Tenant ID
            addon_id: Add-on ID
            use_trial: Use trial period if available
            config: Optional configuration for the add-on
            
        Returns:
            TenantAddOnSubscription or None if failed
        """
        addon = self._addons.get(addon_id)
        if not addon:
            logger.error(f"Add-on not found: {addon_id}")
            return None

        if addon.status == AddOnStatus.DEPRECATED:
            logger.warning(f"Cannot enable deprecated add-on: {addon_id}")
            return None

        # Check if already subscribed
        tenant_subs = self._tenant_subscriptions.get(tenant_id, [])
        if any(sub.addon_id == addon_id for sub in tenant_subs):
            logger.warning(
                f"Tenant {tenant_id} already has add-on {addon_id} enabled"
            )
            return None

        # Check trial eligibility
        trial_end = None
        status = "active"

        if use_trial and addon.trial_available:
            if addon.max_trial_per_tenant:
                # Check if already used trial
                if tenant_id not in self._addon_trials:
                    self._addon_trials[tenant_id] = []

                if addon_id in self._addon_trials[tenant_id]:
                    logger.warning(
                        f"Tenant {tenant_id} already used trial for {addon_id}"
                    )
                    use_trial = False
                else:
                    self._addon_trials[tenant_id].append(addon_id)
                    trial_end = datetime.utcnow() + timedelta(days=addon.trial_days)
                    status = "trial"

        subscription = TenantAddOnSubscription(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            addon_id=addon_id,
            status=status,
            trial_end=trial_end,
            config=config or {},
        )

        if tenant_id not in self._tenant_subscriptions:
            self._tenant_subscriptions[tenant_id] = []

        self._tenant_subscriptions[tenant_id].append(subscription)

        # Track revenue
        self._record_revenue(addon, tenant_id, is_trial=use_trial)

        logger.info(
            f"Enabled add-on {addon.name} for tenant {tenant_id} "
            f"({status})"
        )
        return subscription

    def disable_addon(
        self,
        tenant_id: str,
        addon_id: str,
        reason: Optional[str] = None
    ) -> bool:
        """Disable an add-on for a tenant."""
        tenant_subs = self._tenant_subscriptions.get(tenant_id, [])
        subscription = next(
            (sub for sub in tenant_subs if sub.addon_id == addon_id),
            None
        )

        if not subscription:
            logger.warning(f"Subscription not found for {tenant_id}/{addon_id}")
            return False

        subscription.status = "canceled"
        subscription.canceled_at = datetime.utcnow()

        logger.info(f"Disabled add-on {addon_id} for tenant {tenant_id}")
        return True

    def get_tenant_addons(self, tenant_id: str) -> List[TenantAddOnSubscription]:
        """Get all add-ons enabled for a tenant."""
        return self._tenant_subscriptions.get(tenant_id, [])

    def configure_addon(
        self,
        tenant_id: str,
        addon_id: str,
        config: Dict[str, Any]
    ) -> bool:
        """Update configuration for an enabled add-on."""
        tenant_subs = self._tenant_subscriptions.get(tenant_id, [])
        subscription = next(
            (sub for sub in tenant_subs if sub.addon_id == addon_id),
            None
        )

        if not subscription:
            return False

        subscription.config.update(config)
        logger.info(f"Updated config for {addon_id} on tenant {tenant_id}")
        return True

    def get_addon_config(
        self,
        tenant_id: str,
        addon_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get configuration for an enabled add-on."""
        tenant_subs = self._tenant_subscriptions.get(tenant_id, [])
        subscription = next(
            (sub for sub in tenant_subs if sub.addon_id == addon_id),
            None
        )

        if not subscription:
            return None

        return subscription.config

    def track_addon_usage(
        self,
        tenant_id: str,
        addon_id: str,
        metric: str,
        quantity: int
    ) -> bool:
        """Track usage metric for an add-on."""
        tenant_subs = self._tenant_subscriptions.get(tenant_id, [])
        subscription = next(
            (sub for sub in tenant_subs if sub.addon_id == addon_id),
            None
        )

        if not subscription:
            return False

        subscription.usage_metrics[metric] = subscription.usage_metrics.get(metric, 0) + quantity
        logger.debug(
            f"Tracked {quantity} {metric} for {addon_id} on {tenant_id}"
        )
        return True

    def get_marketplace_metrics(self) -> MarketplaceMetrics:
        """Get overall marketplace metrics."""
        total_addons = len(self._addons)
        total_subscribers = sum(
            len(subs) for subs in self._tenant_subscriptions.values()
        )

        revenue_generated = Decimal("0")
        revenue_shared = Decimal("0")

        for addon_revenue in self._revenue.values():
            revenue_generated += addon_revenue.get("total", Decimal("0"))
            revenue_shared += addon_revenue.get("shared", Decimal("0"))

        adoption_rate = (
            (total_subscribers / (total_addons * 100)) * 100
            if total_addons > 0 else 0
        )

        return MarketplaceMetrics(
            total_addons=total_addons,
            total_subscribers=total_subscribers,
            revenue_generated=revenue_generated,
            revenue_shared=revenue_shared,
            adoption_rate=adoption_rate,
        )

    def recommend_addons(
        self,
        tenant_id: str,
        practice_areas: List[str]
    ) -> List[AddOn]:
        """
        Get add-on recommendations based on practice areas.
        
        Args:
            tenant_id: Tenant ID
            practice_areas: List of practice areas (e.g., "family", "corporate")
            
        Returns:
            Recommended add-ons
        """
        recommendations = []

        # Simple rules-based recommendations
        if any(area in practice_areas for area in ["family", "divorce"]):
            recommendations.append(
                self._addons[next(
                    addon.id for addon in self.STANDARD_ADDONS.values()
                    if addon.type == AddOnType.DEPOSITION_PREP
                )]
            )

        if any(area in practice_areas for area in ["litigation", "court"]):
            recommendations.append(
                self._addons[next(
                    addon.id for addon in self.STANDARD_ADDONS.values()
                    if addon.type == AddOnType.COURT_FILING
                )]
            )

        if any(area in practice_areas for area in ["financial", "tax"]):
            recommendations.append(
                self._addons[next(
                    addon.id for addon in self.STANDARD_ADDONS.values()
                    if addon.type == AddOnType.FORENSIC_ACCOUNTING
                )]
            )

        # Remove already-enabled add-ons
        enabled_ids = {
            sub.addon_id for sub in self.get_tenant_addons(tenant_id)
        }
        recommendations = [a for a in recommendations if a.id not in enabled_ids]

        return recommendations[:3]  # Return top 3

    def _record_revenue(
        self,
        addon: AddOn,
        tenant_id: str,
        is_trial: bool = False
    ):
        """Record revenue from add-on subscription."""
        if addon.id not in self._revenue:
            self._revenue[addon.id] = {"total": Decimal("0"), "shared": Decimal("0")}

        if not is_trial:
            self._revenue[addon.id]["total"] += addon.price
            if addon.vendor != "SintraPrime":
                shared = addon.price * (addon.revenue_share / 100)
                self._revenue[addon.id]["shared"] += shared
