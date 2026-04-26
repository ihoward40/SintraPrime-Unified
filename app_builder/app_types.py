"""
App Types & Data Models for SintraPrime App Builder
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class AppType(str, Enum):
    LEGAL_PORTAL = "legal_portal"
    FINANCIAL_DASHBOARD = "financial_dashboard"
    TRUST_MANAGER = "trust_manager"
    CLIENT_CRM = "client_crm"
    CASE_TRACKER = "case_tracker"
    LANDING_PAGE = "landing_page"
    APPOINTMENT_BOOKING = "appointment_booking"
    DOCUMENT_PORTAL = "document_portal"
    CUSTOM = "custom"


class ComponentType(str, Enum):
    HERO = "hero"
    NAVBAR = "navbar"
    FOOTER = "footer"
    FORM = "form"
    TABLE = "table"
    CARD = "card"
    CHART = "chart"
    MODAL = "modal"
    SIDEBAR = "sidebar"
    BUTTON = "button"
    INPUT = "input"
    SELECT = "select"
    TEXTAREA = "textarea"
    BADGE = "badge"
    ALERT = "alert"
    STAT = "stat"
    TIMELINE = "timeline"
    CALENDAR = "calendar"
    FILE_UPLOAD = "file_upload"
    SIGNATURE_PAD = "signature_pad"


class IntegrationType(str, Enum):
    STRIPE = "stripe"
    CALENDAR = "calendar"
    EMAIL = "email"
    SMS = "sms"
    DOCUSIGN = "docusign"
    PLAID = "plaid"
    OPENAI = "openai"
    TWILIO = "twilio"
    SENDGRID = "sendgrid"
    WEBHOOKS = "webhooks"


# ---------------------------------------------------------------------------
# Component & Page Models
# ---------------------------------------------------------------------------

@dataclass
class Component:
    """UI building block for generated apps."""
    type: ComponentType
    props: Dict[str, Any] = field(default_factory=dict)
    children: List["Component"] = field(default_factory=list)
    styles: Dict[str, str] = field(default_factory=dict)
    events: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value if isinstance(self.type, ComponentType) else self.type,
            "props": self.props,
            "children": [c.to_dict() for c in self.children],
            "styles": self.styles,
            "events": self.events,
        }


@dataclass
class Page:
    """A single page/route in the generated app."""
    name: str
    route: str
    components: List[Component] = field(default_factory=list)
    data_sources: List[str] = field(default_factory=list)
    title: str = ""
    description: str = ""
    requires_auth: bool = False
    meta_tags: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "route": self.route,
            "components": [c.to_dict() for c in self.components],
            "data_sources": self.data_sources,
            "title": self.title or self.name,
            "description": self.description,
            "requires_auth": self.requires_auth,
            "meta_tags": self.meta_tags,
        }


# ---------------------------------------------------------------------------
# Database Models
# ---------------------------------------------------------------------------

@dataclass
class Column:
    """A database column definition."""
    name: str
    type: str  # TEXT, INTEGER, REAL, BLOB, BOOLEAN, DATETIME, JSON
    primary_key: bool = False
    nullable: bool = True
    unique: bool = False
    default: Optional[str] = None
    foreign_key: Optional[str] = None  # "table.column"
    index: bool = False


@dataclass
class Table:
    """A database table definition."""
    name: str
    columns: List[Column] = field(default_factory=list)
    indexes: List[str] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "columns": [
                {
                    "name": c.name,
                    "type": c.type,
                    "primary_key": c.primary_key,
                    "nullable": c.nullable,
                    "unique": c.unique,
                    "default": c.default,
                    "foreign_key": c.foreign_key,
                    "index": c.index,
                }
                for c in self.columns
            ],
            "indexes": self.indexes,
            "description": self.description,
        }


@dataclass
class Relationship:
    """A relationship between two tables."""
    from_table: str
    to_table: str
    relationship_type: str  # one_to_one, one_to_many, many_to_many
    from_column: str
    to_column: str


@dataclass
class DatabaseSchema:
    """Complete database schema definition."""
    name: str
    tables: List[Table] = field(default_factory=list)
    relationships: List[Relationship] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "tables": [t.to_dict() for t in self.tables],
            "relationships": [
                {
                    "from_table": r.from_table,
                    "to_table": r.to_table,
                    "type": r.relationship_type,
                    "from_column": r.from_column,
                    "to_column": r.to_column,
                }
                for r in self.relationships
            ],
            "description": self.description,
        }


# ---------------------------------------------------------------------------
# App Spec
# ---------------------------------------------------------------------------

@dataclass
class AppSpec:
    """Complete specification for generating a web app."""
    name: str
    description: str
    app_type: AppType = AppType.CUSTOM
    pages: List[Page] = field(default_factory=list)
    features: List[str] = field(default_factory=list)
    database_schema: Optional[DatabaseSchema] = None
    styling: Dict[str, str] = field(default_factory=dict)
    integrations: List[IntegrationType] = field(default_factory=list)
    seo: Dict[str, str] = field(default_factory=dict)
    auth_required: bool = False
    theme: str = "sintra"  # sintra, legal, financial, minimal

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "app_type": self.app_type.value,
            "pages": [p.to_dict() for p in self.pages],
            "features": self.features,
            "database_schema": self.database_schema.to_dict() if self.database_schema else None,
            "styling": self.styling,
            "integrations": [i.value for i in self.integrations],
            "seo": self.seo,
            "auth_required": self.auth_required,
            "theme": self.theme,
        }


# ---------------------------------------------------------------------------
# App Template
# ---------------------------------------------------------------------------

@dataclass
class AppTemplate:
    """A reusable app template."""
    name: str
    display_name: str
    description: str
    app_type: AppType
    thumbnail: str = ""
    tags: List[str] = field(default_factory=list)
    spec: Optional[AppSpec] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "app_type": self.app_type.value,
            "thumbnail": self.thumbnail,
            "tags": self.tags,
        }


# ---------------------------------------------------------------------------
# Build Result
# ---------------------------------------------------------------------------

@dataclass
class BuildResult:
    """Result of building an app."""
    success: bool
    app_id: str = ""
    app_url: str = ""
    files_created: List[str] = field(default_factory=list)
    database_name: str = ""
    stripe_product_id: str = ""
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    preview_url: str = ""
    build_time_seconds: float = 0.0
    spec: Optional[AppSpec] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "app_id": self.app_id,
            "app_url": self.app_url,
            "files_created": self.files_created,
            "database_name": self.database_name,
            "stripe_product_id": self.stripe_product_id,
            "errors": self.errors,
            "warnings": self.warnings,
            "preview_url": self.preview_url,
            "build_time_seconds": self.build_time_seconds,
        }


# ---------------------------------------------------------------------------
# Stripe Types
# ---------------------------------------------------------------------------

@dataclass
class StripeConfig:
    """Stripe configuration for a firm/app."""
    firm_name: str
    products: List[Dict[str, Any]] = field(default_factory=list)
    subscription_products: List[Dict[str, Any]] = field(default_factory=list)
    customer_portal_enabled: bool = True
    invoice_prefix: str = "INV"
    currency: str = "usd"
    webhook_events: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "firm_name": self.firm_name,
            "products": self.products,
            "subscription_products": self.subscription_products,
            "customer_portal_enabled": self.customer_portal_enabled,
            "invoice_prefix": self.invoice_prefix,
            "currency": self.currency,
            "webhook_events": self.webhook_events,
        }


# ---------------------------------------------------------------------------
# Digital Twin Types
# ---------------------------------------------------------------------------

@dataclass
class LegalMatter:
    matter_id: str
    title: str
    matter_type: str  # civil, criminal, estate, trust, contract, etc.
    status: str  # active, closed, pending
    jurisdiction: str
    court: str = ""
    attorney: str = ""
    deadlines: List[str] = field(default_factory=list)
    documents: List[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class FinancialProfile:
    total_assets: float = 0.0
    total_debts: float = 0.0
    monthly_income: float = 0.0
    monthly_expenses: float = 0.0
    credit_score: int = 0
    accounts: List[Dict[str, Any]] = field(default_factory=list)
    investments: List[Dict[str, Any]] = field(default_factory=list)
    debts: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def net_worth(self) -> float:
        return self.total_assets - self.total_debts

    @property
    def debt_to_income_ratio(self) -> float:
        if self.monthly_income == 0:
            return 0.0
        return self.total_debts / (self.monthly_income * 12)


@dataclass
class Property:
    property_id: str
    name: str
    property_type: str  # real_estate, vehicle, valuable, crypto
    value: float = 0.0
    address: str = ""
    owned_outright: bool = False
    mortgage_balance: float = 0.0
    title_holder: str = ""


@dataclass
class Relationship:
    relationship_id: str
    name: str
    relationship_type: str  # spouse, child, parent, business_partner, creditor, attorney
    contact_info: Dict[str, str] = field(default_factory=dict)
    legal_role: str = ""  # beneficiary, executor, trustee, guardian
    notes: str = ""


@dataclass
class Directive:
    directive_id: str
    title: str
    directive_type: str  # healthcare_proxy, living_will, durable_poa, financial_poa
    status: str  # draft, signed, notarized, filed
    agent_name: str = ""
    document_path: str = ""
    signed_date: str = ""
    notarized: bool = False


@dataclass
class Business:
    business_id: str
    name: str
    entity_type: str  # llc, corporation, partnership, sole_prop, nonprofit
    ownership_percentage: float = 0.0
    state_of_formation: str = ""
    ein: str = ""
    status: str = "active"
    registered_agent: str = ""
    annual_revenue: float = 0.0


@dataclass
class DigitalAsset:
    asset_id: str
    name: str
    asset_type: str  # bank_account, crypto_wallet, social_media, domain, ip, subscription
    value: float = 0.0
    account_number: str = ""
    institution: str = ""
    beneficiary: str = ""
    access_instructions: str = ""


@dataclass
class LifeEvent:
    event_id: str
    event_type: str  # legal, financial, health, family, business, property
    title: str
    description: str = ""
    date: str = ""
    impact_level: str = "low"  # low, medium, high, critical
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LifeSnapshot:
    user_id: str
    name: str
    snapshot_date: str
    legal_matters: List[LegalMatter] = field(default_factory=list)
    financial_profile: Optional[FinancialProfile] = None
    properties: List[Property] = field(default_factory=list)
    relationships: List[Relationship] = field(default_factory=list)
    health_directives: List[Directive] = field(default_factory=list)
    business_interests: List[Business] = field(default_factory=list)
    digital_assets: List[DigitalAsset] = field(default_factory=list)
    risk_score: float = 0.0
    estate_readiness_score: float = 0.0


@dataclass
class RiskReport:
    user_id: str
    overall_risk_score: float
    risk_level: str  # low, medium, high, critical
    vulnerabilities: List[Dict[str, str]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    critical_gaps: List[str] = field(default_factory=list)
    generated_at: str = ""


@dataclass
class EstateReport:
    user_id: str
    readiness_score: float
    readiness_level: str  # not_started, partial, mostly_ready, fully_protected
    has_will: bool = False
    has_trust: bool = False
    has_poa: bool = False
    has_healthcare_directive: bool = False
    beneficiaries_named: bool = False
    documents_signed: bool = False
    missing_documents: List[str] = field(default_factory=list)
    next_steps: List[str] = field(default_factory=list)
    generated_at: str = ""


@dataclass
class Recommendation:
    priority: int  # 1=highest
    category: str
    title: str
    description: str
    action_items: List[str] = field(default_factory=list)
    estimated_cost: str = ""
    time_to_complete: str = ""


@dataclass
class ScenarioAnalysis:
    scenario: str
    current_state: Dict[str, Any] = field(default_factory=dict)
    projected_state: Dict[str, Any] = field(default_factory=dict)
    risks: List[str] = field(default_factory=list)
    opportunities: List[str] = field(default_factory=list)
    recommended_actions: List[str] = field(default_factory=list)
    confidence_score: float = 0.0


@dataclass
class LifePortfolio:
    user_id: str
    name: str
    generated_at: str
    snapshot: Optional[LifeSnapshot] = None
    risk_report: Optional[RiskReport] = None
    estate_report: Optional[EstateReport] = None
    recommendations: List[Recommendation] = field(default_factory=list)
    documents_manifest: List[str] = field(default_factory=list)
    summary: str = ""


@dataclass
class TemplateSummary:
    name: str
    display_name: str
    description: str
    app_type: str
    tags: List[str] = field(default_factory=list)
