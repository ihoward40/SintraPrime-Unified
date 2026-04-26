"""
Phase 15E — Competitor Intel Engine
Scrapes, analyzes, and tracks top legal AI competitors weekly.
Produces structured intelligence reports with feature gaps, pricing,
and strategic positioning recommendations.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class CompetitorCategory(str, Enum):
    LEGAL_AI = "legal_ai"
    LEGAL_TECH = "legal_tech"
    CRM = "crm"
    DOCUMENT_AUTOMATION = "document_automation"
    INTAKE = "intake"
    BILLING = "billing"


class PricingModel(str, Enum):
    SUBSCRIPTION = "subscription"
    PER_SEAT = "per_seat"
    USAGE_BASED = "usage_based"
    FREEMIUM = "freemium"
    ENTERPRISE = "enterprise"
    UNKNOWN = "unknown"


class ThreatLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ChangeType(str, Enum):
    NEW_FEATURE = "new_feature"
    PRICE_CHANGE = "price_change"
    NEW_INTEGRATION = "new_integration"
    REBRANDING = "rebranding"
    FUNDING = "funding"
    PARTNERSHIP = "partnership"
    NEGATIVE_REVIEW = "negative_review"
    OUTAGE = "outage"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class PricingTier:
    name: str
    price_monthly: Optional[float] = None
    price_annual: Optional[float] = None
    features: List[str] = field(default_factory=list)
    user_limit: Optional[int] = None
    is_free: bool = False


@dataclass
class Competitor:
    competitor_id: str
    name: str
    website: str
    category: CompetitorCategory
    description: str = ""
    pricing_model: PricingModel = PricingModel.UNKNOWN
    pricing_tiers: List[PricingTier] = field(default_factory=list)
    features: List[str] = field(default_factory=list)
    integrations: List[str] = field(default_factory=list)
    target_market: str = "law firms"
    founded_year: Optional[int] = None
    funding_total: Optional[float] = None
    employee_count: Optional[int] = None
    g2_rating: Optional[float] = None
    capterra_rating: Optional[float] = None
    monthly_traffic: Optional[int] = None
    threat_level: ThreatLevel = ThreatLevel.MEDIUM
    notes: str = ""
    last_scraped_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_min_price(self) -> Optional[float]:
        prices = [t.price_monthly for t in self.pricing_tiers if t.price_monthly is not None]
        return min(prices) if prices else None

    def has_feature(self, feature: str) -> bool:
        return any(feature.lower() in f.lower() for f in self.features)

    def domain(self) -> str:
        return urlparse(self.website).netloc


@dataclass
class CompetitorChange:
    change_id: str
    competitor_id: str
    change_type: ChangeType
    description: str
    detected_at: datetime = field(default_factory=datetime.utcnow)
    significance: int = 3  # 1-5
    source_url: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FeatureGap:
    feature: str
    sintra_has: bool
    competitors_with_feature: List[str]
    priority: int  # 1=low, 5=critical
    recommendation: str = ""


@dataclass
class IntelReport:
    report_id: str
    generated_at: datetime
    competitors_analyzed: int
    changes_detected: List[CompetitorChange]
    feature_gaps: List[FeatureGap]
    pricing_comparison: Dict[str, Any]
    threat_summary: Dict[str, int]
    strategic_recommendations: List[str]
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_markdown(self) -> str:
        lines = [
            f"# SintraPrime Competitor Intelligence Report",
            f"**Generated:** {self.generated_at.strftime('%Y-%m-%d %H:%M UTC')}",
            f"**Competitors Analyzed:** {self.competitors_analyzed}",
            "",
            "## Threat Summary",
        ]
        for level, count in self.threat_summary.items():
            lines.append(f"- **{level.upper()}**: {count} competitor(s)")

        if self.changes_detected:
            lines += ["", "## Recent Changes Detected"]
            for change in self.changes_detected[:10]:
                lines.append(
                    f"- [{change.change_type.value}] **{change.competitor_id}**: "
                    f"{change.description} _(significance: {change.significance}/5)_"
                )

        if self.feature_gaps:
            lines += ["", "## Feature Gap Analysis"]
            lines.append("| Feature | SintraPrime | Competitors With It | Priority |")
            lines.append("|---------|-------------|---------------------|----------|")
            for gap in sorted(self.feature_gaps, key=lambda g: g.priority, reverse=True):
                sintra = "✅" if gap.sintra_has else "❌"
                comps = ", ".join(gap.competitors_with_feature[:3])
                lines.append(f"| {gap.feature} | {sintra} | {comps} | {gap.priority}/5 |")

        if self.pricing_comparison:
            lines += ["", "## Pricing Comparison"]
            lines.append("| Competitor | Min Price/mo | Model |")
            lines.append("|------------|--------------|-------|")
            for name, data in self.pricing_comparison.items():
                price = f"${data.get('min_price', 'N/A')}" if data.get('min_price') else "N/A"
                model = data.get('model', 'Unknown')
                lines.append(f"| {name} | {price} | {model} |")

        if self.strategic_recommendations:
            lines += ["", "## Strategic Recommendations"]
            for i, rec in enumerate(self.strategic_recommendations, 1):
                lines.append(f"{i}. {rec}")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Scraper (HTTP adapter)
# ---------------------------------------------------------------------------

class WebScraper:
    """
    Thin HTTP scraper wrapper.
    In production, uses requests + BeautifulSoup.
    In tests, the http_client is mocked.
    """

    def __init__(self, http_client=None, rate_limit_seconds: float = 1.0):
        self._http = http_client
        self._rate_limit = rate_limit_seconds
        self._last_request_at: float = 0.0

    def fetch(self, url: str) -> Optional[str]:
        """Fetches a URL and returns the HTML content."""
        elapsed = time.time() - self._last_request_at
        if elapsed < self._rate_limit:
            time.sleep(self._rate_limit - elapsed)

        if self._http is None:
            logger.warning("WebScraper: no HTTP client — returning empty content")
            return None

        try:
            resp = self._http.get(url, timeout=10, headers={
                "User-Agent": "Mozilla/5.0 (compatible; SintraPrimeBot/1.0)"
            })
            self._last_request_at = time.time()
            if resp.status_code == 200:
                return resp.text
            return None
        except Exception as e:
            logger.error("Scrape error for %s: %s", url, e)
            return None

    def extract_text(self, html: str) -> str:
        """Strips HTML tags and returns plain text."""
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def extract_price(self, text: str) -> Optional[float]:
        """Extracts the first dollar amount from text."""
        match = re.search(r"\$\s*(\d+(?:\.\d{2})?)", text)
        if match:
            return float(match.group(1))
        return None

    def extract_rating(self, text: str) -> Optional[float]:
        """Extracts a rating like '4.5/5' or '4.5 out of 5'."""
        match = re.search(r"(\d+\.\d+)\s*(?:/\s*5|out of 5)", text)
        if match:
            return float(match.group(1))
        return None


# ---------------------------------------------------------------------------
# Change detector
# ---------------------------------------------------------------------------

class ChangeDetector:
    """Detects changes between two snapshots of competitor data."""

    def detect_changes(
        self,
        old: Competitor,
        new: Competitor,
    ) -> List[CompetitorChange]:
        changes: List[CompetitorChange] = []

        # Feature changes
        old_features = set(old.features)
        new_features = set(new.features)
        added = new_features - old_features
        for f in added:
            changes.append(CompetitorChange(
                change_id=self._make_id(new.competitor_id, f),
                competitor_id=new.competitor_id,
                change_type=ChangeType.NEW_FEATURE,
                description=f"New feature detected: {f}",
                significance=3,
            ))

        # Pricing changes
        old_price = old.get_min_price()
        new_price = new.get_min_price()
        if old_price is not None and new_price is not None and old_price != new_price:
            direction = "decreased" if new_price < old_price else "increased"
            changes.append(CompetitorChange(
                change_id=self._make_id(new.competitor_id, "price"),
                competitor_id=new.competitor_id,
                change_type=ChangeType.PRICE_CHANGE,
                description=f"Pricing {direction}: ${old_price:.0f} → ${new_price:.0f}/mo",
                significance=4,
            ))

        # Integration changes
        old_integrations = set(old.integrations)
        new_integrations = set(new.integrations)
        added_integrations = new_integrations - old_integrations
        for integration in added_integrations:
            changes.append(CompetitorChange(
                change_id=self._make_id(new.competitor_id, integration),
                competitor_id=new.competitor_id,
                change_type=ChangeType.NEW_INTEGRATION,
                description=f"New integration: {integration}",
                significance=2,
            ))

        # Funding changes
        if (old.funding_total or 0) < (new.funding_total or 0):
            changes.append(CompetitorChange(
                change_id=self._make_id(new.competitor_id, "funding"),
                competitor_id=new.competitor_id,
                change_type=ChangeType.FUNDING,
                description=f"Funding increased to ${new.funding_total:,.0f}",
                significance=5,
            ))

        return changes

    @staticmethod
    def _make_id(competitor_id: str, key: str) -> str:
        return hashlib.md5(f"{competitor_id}:{key}:{datetime.utcnow().date()}".encode()).hexdigest()[:12]


# ---------------------------------------------------------------------------
# Feature gap analyzer
# ---------------------------------------------------------------------------

SINTRA_FEATURES = {
    "AI legal Q&A",
    "Document drafting",
    "Case management",
    "Client intake",
    "E-signature",
    "Payment processing",
    "Lead nurturing",
    "CPA referrals",
    "Discord integration",
    "Slack alerts",
    "Analytics dashboard",
    "Email sequences",
    "Proposal generator",
    "Contract management",
    "Knowledge base",
    "Voice calls",
    "SMS outreach",
    "Multi-agent swarm",
    "GOD_MODE automation",
}


class FeatureGapAnalyzer:
    """Compares SintraPrime features against competitors."""

    def __init__(self, sintra_features: Optional[set] = None):
        self._sintra_features = sintra_features or SINTRA_FEATURES

    def analyze(self, competitors: List[Competitor]) -> List[FeatureGap]:
        # Collect all features across competitors
        all_features: Dict[str, List[str]] = {}
        for comp in competitors:
            for feature in comp.features:
                if feature not in all_features:
                    all_features[feature] = []
                all_features[feature].append(comp.name)

        gaps: List[FeatureGap] = []
        for feature, comp_names in all_features.items():
            sintra_has = any(
                feature.lower() in sf.lower() or sf.lower() in feature.lower()
                for sf in self._sintra_features
            )
            # Priority based on how many competitors have it
            priority = min(5, len(comp_names) + 1)
            if not sintra_has:
                priority = min(5, priority + 1)  # Higher priority for gaps

            gaps.append(FeatureGap(
                feature=feature,
                sintra_has=sintra_has,
                competitors_with_feature=comp_names,
                priority=priority,
                recommendation=(
                    f"Consider adding '{feature}' — {len(comp_names)} competitor(s) have it."
                    if not sintra_has else ""
                ),
            ))

        return sorted(gaps, key=lambda g: (not g.sintra_has, g.priority), reverse=True)


# ---------------------------------------------------------------------------
# Strategic recommendation engine
# ---------------------------------------------------------------------------

class StrategyEngine:
    """Generates strategic recommendations from intel data."""

    def generate_recommendations(
        self,
        competitors: List[Competitor],
        gaps: List[FeatureGap],
        changes: List[CompetitorChange],
    ) -> List[str]:
        recs: List[str] = []

        # Price positioning
        prices = [c.get_min_price() for c in competitors if c.get_min_price()]
        if prices:
            avg_price = sum(prices) / len(prices)
            recs.append(
                f"Market average entry price is ${avg_price:.0f}/mo. "
                f"Price SintraPrime at ${avg_price * 0.85:.0f}/mo to undercut while maintaining margin."
            )

        # Critical feature gaps
        critical_gaps = [g for g in gaps if not g.sintra_has and g.priority >= 4]
        for gap in critical_gaps[:3]:
            recs.append(
                f"HIGH PRIORITY: Add '{gap.feature}' — "
                f"{len(gap.competitors_with_feature)} competitor(s) already offer this."
            )

        # Funding threats
        funding_changes = [c for c in changes if c.change_type == ChangeType.FUNDING]
        for change in funding_changes:
            recs.append(
                f"THREAT: {change.competitor_id} received new funding. "
                f"Accelerate feature development to maintain competitive lead."
            )

        # Low-threat opportunities
        low_threat = [c for c in competitors if c.threat_level == ThreatLevel.LOW]
        if low_threat:
            names = ", ".join(c.name for c in low_threat[:2])
            recs.append(
                f"Acquisition opportunity: {names} are low-threat and may be acquirable "
                f"to absorb their customer base."
            )

        # Default recommendation
        if not recs:
            recs.append(
                "Continue monitoring competitors weekly. No immediate threats detected."
            )

        return recs


# ---------------------------------------------------------------------------
# Main Intel Engine
# ---------------------------------------------------------------------------

class CompetitorIntelEngine:
    """
    Orchestrates weekly competitor intelligence gathering.
    Manages a registry of competitors, detects changes, analyzes gaps,
    and generates actionable reports.
    """

    def __init__(
        self,
        scraper: Optional[WebScraper] = None,
        change_detector: Optional[ChangeDetector] = None,
        gap_analyzer: Optional[FeatureGapAnalyzer] = None,
        strategy_engine: Optional[StrategyEngine] = None,
        on_change_detected: Optional[Callable[[CompetitorChange], None]] = None,
        on_report_generated: Optional[Callable[[IntelReport], None]] = None,
    ):
        self._scraper = scraper or WebScraper()
        self._change_detector = change_detector or ChangeDetector()
        self._gap_analyzer = gap_analyzer or FeatureGapAnalyzer()
        self._strategy_engine = strategy_engine or StrategyEngine()
        self._on_change_detected = on_change_detected
        self._on_report_generated = on_report_generated
        self._competitors: Dict[str, Competitor] = {}
        self._snapshots: Dict[str, Competitor] = {}  # Previous snapshots
        self._changes: List[CompetitorChange] = []
        self._reports: List[IntelReport] = []
        self._load_default_competitors()

    # ------------------------------------------------------------------
    # Competitor registry
    # ------------------------------------------------------------------

    def add_competitor(self, competitor: Competitor) -> None:
        self._competitors[competitor.competitor_id] = competitor

    def get_competitor(self, competitor_id: str) -> Optional[Competitor]:
        return self._competitors.get(competitor_id)

    def list_competitors(
        self, category: Optional[CompetitorCategory] = None,
        threat_level: Optional[ThreatLevel] = None,
    ) -> List[Competitor]:
        comps = list(self._competitors.values())
        if category:
            comps = [c for c in comps if c.category == category]
        if threat_level:
            comps = [c for c in comps if c.threat_level == threat_level]
        return comps

    def update_competitor(self, competitor: Competitor) -> List[CompetitorChange]:
        """Updates a competitor and detects changes from the previous snapshot."""
        old = self._snapshots.get(competitor.competitor_id)
        changes: List[CompetitorChange] = []

        if old:
            changes = self._change_detector.detect_changes(old, competitor)
            for change in changes:
                self._changes.append(change)
                if self._on_change_detected:
                    self._on_change_detected(change)

        # Save snapshot
        self._snapshots[competitor.competitor_id] = self._competitors.get(
            competitor.competitor_id
        ) or competitor
        self._competitors[competitor.competitor_id] = competitor
        competitor.last_scraped_at = datetime.utcnow()
        return changes

    # ------------------------------------------------------------------
    # Report generation
    # ------------------------------------------------------------------

    def generate_report(self) -> IntelReport:
        competitors = list(self._competitors.values())
        gaps = self._gap_analyzer.analyze(competitors)
        recent_changes = [
            c for c in self._changes
            if (datetime.utcnow() - c.detected_at).days <= 7
        ]
        recommendations = self._strategy_engine.generate_recommendations(
            competitors, gaps, recent_changes
        )

        # Pricing comparison
        pricing = {}
        for comp in competitors:
            pricing[comp.name] = {
                "min_price": comp.get_min_price(),
                "model": comp.pricing_model.value,
            }

        # Threat summary
        threat_summary: Dict[str, int] = {}
        for comp in competitors:
            level = comp.threat_level.value
            threat_summary[level] = threat_summary.get(level, 0) + 1

        report = IntelReport(
            report_id=f"RPT-{datetime.utcnow().strftime('%Y%m%d-%H%M')}",
            generated_at=datetime.utcnow(),
            competitors_analyzed=len(competitors),
            changes_detected=recent_changes,
            feature_gaps=gaps,
            pricing_comparison=pricing,
            threat_summary=threat_summary,
            strategic_recommendations=recommendations,
        )
        self._reports.append(report)

        if self._on_report_generated:
            self._on_report_generated(report)

        return report

    def get_latest_report(self) -> Optional[IntelReport]:
        return self._reports[-1] if self._reports else None

    def get_all_changes(self) -> List[CompetitorChange]:
        return list(self._changes)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_competitors": len(self._competitors),
            "total_changes": len(self._changes),
            "total_reports": len(self._reports),
            "high_threat_count": len(self.list_competitors(threat_level=ThreatLevel.HIGH)),
            "critical_threat_count": len(self.list_competitors(threat_level=ThreatLevel.CRITICAL)),
        }

    # ------------------------------------------------------------------
    # Default competitor data
    # ------------------------------------------------------------------

    def _load_default_competitors(self) -> None:
        defaults = [
            Competitor(
                competitor_id="clio",
                name="Clio",
                website="https://www.clio.com",
                category=CompetitorCategory.LEGAL_TECH,
                description="Practice management software for law firms",
                pricing_model=PricingModel.SUBSCRIPTION,
                pricing_tiers=[
                    PricingTier("Starter", price_monthly=49.0, features=["Case management", "Billing"]),
                    PricingTier("Boutique", price_monthly=79.0, features=["Case management", "Billing", "Client portal"]),
                    PricingTier("Elite", price_monthly=109.0, features=["All features"]),
                ],
                features=["Case management", "Billing", "Document management", "Client portal", "Time tracking"],
                integrations=["QuickBooks", "Outlook", "Google Workspace", "Dropbox"],
                threat_level=ThreatLevel.HIGH,
                g2_rating=4.6,
                monthly_traffic=500000,
            ),
            Competitor(
                competitor_id="harvey",
                name="Harvey AI",
                website="https://www.harvey.ai",
                category=CompetitorCategory.LEGAL_AI,
                description="AI for legal research and document drafting",
                pricing_model=PricingModel.ENTERPRISE,
                features=["AI legal Q&A", "Document drafting", "Legal research", "Contract analysis"],
                integrations=["Microsoft 365", "Salesforce"],
                threat_level=ThreatLevel.CRITICAL,
                funding_total=100_000_000,
            ),
            Competitor(
                competitor_id="lexisnexis",
                name="LexisNexis",
                website="https://www.lexisnexis.com",
                category=CompetitorCategory.LEGAL_TECH,
                description="Legal research and analytics platform",
                pricing_model=PricingModel.SUBSCRIPTION,
                pricing_tiers=[
                    PricingTier("Basic", price_monthly=150.0, features=["Legal research"]),
                    PricingTier("Professional", price_monthly=350.0, features=["All features"]),
                ],
                features=["Legal research", "Case law search", "Regulatory compliance", "Analytics"],
                threat_level=ThreatLevel.MEDIUM,
                g2_rating=4.1,
            ),
            Competitor(
                competitor_id="smokeball",
                name="Smokeball",
                website="https://www.smokeball.com",
                category=CompetitorCategory.LEGAL_TECH,
                description="Law practice management with AI features",
                pricing_model=PricingModel.SUBSCRIPTION,
                pricing_tiers=[
                    PricingTier("Bill", price_monthly=99.0, features=["Billing", "Time tracking"]),
                    PricingTier("Boost", price_monthly=149.0, features=["All features", "AI drafting"]),
                ],
                features=["Document automation", "Case management", "AI drafting", "Email management"],
                threat_level=ThreatLevel.MEDIUM,
                g2_rating=4.4,
            ),
        ]
        for comp in defaults:
            self._competitors[comp.competitor_id] = comp
