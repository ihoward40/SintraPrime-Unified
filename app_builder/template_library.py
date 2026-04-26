"""
TemplateLibrary — Pre-built App Templates for SintraPrime
==========================================================
Ready-to-use app templates for legal and financial use cases.
Each template is a fully configured AppSpec ready to build.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .app_types import (
    AppSpec, AppTemplate, AppType, Component, ComponentType,
    IntegrationType, Page, TemplateSummary,
)


class TemplateLibrary:
    """
    Pre-built app templates for one-command deployment.

    Available templates:
    - legal_firm_website: Full law firm marketing site
    - client_document_portal: Secure document sharing
    - trust_management_portal: Trust administration
    - estate_planning_intake: Estate planning questionnaire
    - debt_settlement_tracker: Debt negotiation tracker
    - business_formation_wizard: Step-by-step business setup
    - court_deadline_tracker: Matter deadline management
    - financial_health_dashboard: Personal finance overview
    """

    TEMPLATES: Dict[str, Dict[str, Any]] = {
        "legal_firm_website": {
            "display_name": "Law Firm Website",
            "description": "Full law firm marketing site with practice areas, attorney bios, intake forms, and SEO optimization.",
            "app_type": AppType.LEGAL_PORTAL,
            "tags": ["legal", "marketing", "seo", "intake"],
        },
        "client_document_portal": {
            "display_name": "Client Document Portal",
            "description": "Secure, authenticated portal for sharing legal documents between attorneys and clients.",
            "app_type": AppType.DOCUMENT_PORTAL,
            "tags": ["legal", "documents", "secure", "portal"],
        },
        "trust_management_portal": {
            "display_name": "Trust Management Portal",
            "description": "Full trust administration portal with beneficiary management, distribution tracking, and compliance reporting.",
            "app_type": AppType.TRUST_MANAGER,
            "tags": ["trust", "estate", "beneficiaries", "compliance"],
        },
        "estate_planning_intake": {
            "display_name": "Estate Planning Intake",
            "description": "Multi-step estate planning questionnaire that collects client data for will, trust, and POA preparation.",
            "app_type": AppType.LEGAL_PORTAL,
            "tags": ["estate", "intake", "wizard", "forms"],
        },
        "debt_settlement_tracker": {
            "display_name": "Debt Settlement Tracker",
            "description": "Track debt negotiation progress, settlement offers, creditor communications, and payment plans.",
            "app_type": AppType.CASE_TRACKER,
            "tags": ["debt", "settlement", "financial", "tracker"],
        },
        "business_formation_wizard": {
            "display_name": "Business Formation Wizard",
            "description": "Step-by-step guide and document generator for forming an LLC, S-Corp, or C-Corp.",
            "app_type": AppType.LEGAL_PORTAL,
            "tags": ["business", "llc", "formation", "wizard"],
        },
        "court_deadline_tracker": {
            "display_name": "Court Deadline Tracker",
            "description": "Docket management system for tracking court deadlines, filing dates, and matter milestones.",
            "app_type": AppType.CASE_TRACKER,
            "tags": ["legal", "docket", "deadlines", "court"],
        },
        "financial_health_dashboard": {
            "display_name": "Financial Health Dashboard",
            "description": "Personal finance overview: net worth, accounts, budgets, debts, credit score, and investment tracking.",
            "app_type": AppType.FINANCIAL_DASHBOARD,
            "tags": ["finance", "budget", "investing", "credit"],
        },
    }

    def __init__(self):
        self._custom_templates: Dict[str, AppSpec] = {}

    # ------------------------------------------------------------------
    # Template Retrieval
    # ------------------------------------------------------------------

    def get_template(self, name: str) -> AppSpec:
        """
        Get a fully configured AppSpec for a named template.
        Raises KeyError if template not found.
        """
        if name not in self.TEMPLATES:
            raise KeyError(f"Template '{name}' not found. Available: {', '.join(self.TEMPLATES.keys())}")

        builder = getattr(self, f"_build_{name}", None)
        if builder:
            return builder()
        return self._build_generic(name)

    def customize_template(self, name: str, overrides: Dict[str, Any]) -> AppSpec:
        """
        Get a template and apply overrides.

        Example:
            spec = library.customize_template("legal_firm_website", {
                "name": "Smith & Associates",
                "styling": {"primary_color": "#1a4f2a"},
                "features": ["stripe_billing", "appointment_booking"],
            })
        """
        spec = self.get_template(name)

        if "name" in overrides:
            spec.name = overrides["name"]
        if "description" in overrides:
            spec.description = overrides["description"]
        if "styling" in overrides:
            spec.styling.update(overrides["styling"])
        if "features" in overrides:
            spec.features = list(set(spec.features + overrides["features"]))
        if "integrations" in overrides:
            for integration in overrides["integrations"]:
                if isinstance(integration, str):
                    integration = IntegrationType(integration)
                if integration not in spec.integrations:
                    spec.integrations.append(integration)
        if "theme" in overrides:
            spec.theme = overrides["theme"]
        if "seo" in overrides:
            spec.seo.update(overrides["seo"])
        if "pages" in overrides:
            spec.pages = overrides["pages"]

        return spec

    def list_templates(self) -> List[TemplateSummary]:
        """List all available templates with summaries."""
        summaries = [
            TemplateSummary(
                name=name,
                display_name=meta["display_name"],
                description=meta["description"],
                app_type=meta["app_type"].value,
                tags=meta["tags"],
            )
            for name, meta in self.TEMPLATES.items()
        ]
        return summaries

    # ------------------------------------------------------------------
    # Template Builders
    # ------------------------------------------------------------------

    def _build_generic(self, name: str) -> AppSpec:
        meta = self.TEMPLATES[name]
        return AppSpec(
            name=meta["display_name"],
            description=meta["description"],
            app_type=meta["app_type"],
            features=meta["tags"],
            styling={"primary_color": "#1e40af"},
            theme="legal" if "legal" in meta["tags"] or "trust" in meta["tags"] else "sintra",
        )

    def _build_legal_firm_website(self) -> AppSpec:
        return AppSpec(
            name="Law Firm Website",
            description="Professional law firm marketing website with intake forms and SEO",
            app_type=AppType.LEGAL_PORTAL,
            pages=[
                Page(
                    name="Home", route="/",
                    title="Law Firm — Protecting Your Rights & Legacy",
                    components=[
                        Component(ComponentType.NAVBAR, props={"title": "Law Firm"}),
                        Component(ComponentType.HERO, props={
                            "title": "Your Trusted Legal Partner",
                            "subtitle": "Experienced attorneys protecting your rights, assets, and legacy.",
                            "cta": "Free Consultation",
                        }),
                        Component(ComponentType.CARD, props={"variant": "practice_area"}),
                        Component(ComponentType.CARD, props={"variant": "feature"}),
                        Component(ComponentType.FOOTER, props={"firm_name": "Law Firm"}),
                    ],
                    description="Full-service law firm homepage",
                    meta_tags={"og:type": "website"},
                ),
                Page(
                    name="Practice Areas", route="/practice-areas",
                    title="Practice Areas — Estate Planning, Trust Law, Probate",
                    components=[
                        Component(ComponentType.NAVBAR, props={"title": "Law Firm"}),
                        Component(ComponentType.CARD, props={"variant": "practice_area"}),
                        Component(ComponentType.FOOTER, props={"firm_name": "Law Firm"}),
                    ],
                ),
                Page(
                    name="Attorneys", route="/attorneys",
                    title="Meet Our Attorneys",
                    components=[
                        Component(ComponentType.NAVBAR, props={"title": "Law Firm"}),
                        Component(ComponentType.CARD, props={"variant": "attorney_bio"}),
                        Component(ComponentType.FOOTER, props={"firm_name": "Law Firm"}),
                    ],
                ),
                Page(
                    name="Contact", route="/contact",
                    title="Contact Us — Free Consultation",
                    components=[
                        Component(ComponentType.NAVBAR, props={"title": "Law Firm"}),
                        Component(ComponentType.FORM, props={"form_type": "legal_intake", "practice_area": "General"}),
                        Component(ComponentType.FOOTER, props={"firm_name": "Law Firm"}),
                    ],
                ),
            ],
            features=["contact_form", "practice_areas", "attorney_profiles", "seo_optimization", "appointment_booking"],
            integrations=[IntegrationType.EMAIL, IntegrationType.CALENDAR],
            styling={"primary_color": "#1e3a5f", "font": "Inter"},
            seo={
                "title": "Law Firm — Estate Planning, Trust Law, Probate",
                "description": "Experienced legal team protecting your rights, assets, and legacy. Free consultation.",
                "keywords": "estate planning, trust law, probate attorney, law firm",
            },
            auth_required=False,
            theme="legal",
        )

    def _build_client_document_portal(self) -> AppSpec:
        return AppSpec(
            name="Client Document Portal",
            description="Secure document sharing portal for attorneys and clients",
            app_type=AppType.DOCUMENT_PORTAL,
            pages=[
                Page(
                    name="Login", route="/login",
                    title="Client Portal — Secure Login",
                    components=[
                        Component(ComponentType.FORM, props={"form_type": "login"}),
                    ],
                ),
                Page(
                    name="Dashboard", route="/dashboard", requires_auth=True,
                    title="Document Dashboard",
                    components=[
                        Component(ComponentType.SIDEBAR, props={}),
                        Component(ComponentType.STAT, props={"metrics": ["total_documents", "pending_review", "signed"]}),
                        Component(ComponentType.TABLE, props={"data_type": "documents"}),
                    ],
                ),
                Page(
                    name="Upload", route="/upload", requires_auth=True,
                    title="Upload Document",
                    components=[
                        Component(ComponentType.FILE_UPLOAD, props={"accept": ".pdf,.doc,.docx"}),
                    ],
                ),
                Page(
                    name="Signed Documents", route="/signed", requires_auth=True,
                    title="Signed Documents",
                    components=[
                        Component(ComponentType.TABLE, props={"data_type": "signed_documents"}),
                    ],
                ),
            ],
            features=["document_management", "authentication", "esignature", "encryption"],
            integrations=[IntegrationType.DOCUSIGN, IntegrationType.EMAIL],
            styling={"primary_color": "#1e40af"},
            auth_required=True,
            theme="legal",
        )

    def _build_trust_management_portal(self) -> AppSpec:
        return AppSpec(
            name="Trust Management Portal",
            description="Complete trust administration portal for trustees and beneficiaries",
            app_type=AppType.TRUST_MANAGER,
            pages=[
                Page(
                    name="Trust Overview", route="/trust", requires_auth=True,
                    title="Trust Overview",
                    components=[
                        Component(ComponentType.SIDEBAR, props={}),
                        Component(ComponentType.STAT, props={"metrics": ["trust_value", "total_distributions", "beneficiaries"]}),
                        Component(ComponentType.TIMELINE, props={}),
                    ],
                ),
                Page(
                    name="Beneficiaries", route="/beneficiaries", requires_auth=True,
                    title="Beneficiaries",
                    components=[
                        Component(ComponentType.TABLE, props={"data_type": "beneficiaries"}),
                        Component(ComponentType.CHART, props={"chart_type": "pie", "data": "beneficiary_shares"}),
                    ],
                ),
                Page(
                    name="Distributions", route="/distributions", requires_auth=True,
                    title="Distributions",
                    components=[
                        Component(ComponentType.TABLE, props={"data_type": "distributions"}),
                        Component(ComponentType.BUTTON, props={"label": "Record Distribution", "variant": "primary"}),
                    ],
                ),
                Page(
                    name="Documents", route="/documents", requires_auth=True,
                    title="Trust Documents",
                    components=[
                        Component(ComponentType.FILE_UPLOAD, props={}),
                        Component(ComponentType.TABLE, props={"data_type": "trust_documents"}),
                    ],
                ),
                Page(
                    name="Compliance", route="/compliance", requires_auth=True,
                    title="Compliance & Reporting",
                    components=[
                        Component(ComponentType.CHART, props={"chart_type": "bar", "data": "annual_distributions"}),
                        Component(ComponentType.TABLE, props={"data_type": "tax_filings"}),
                    ],
                ),
            ],
            features=["trust_management", "document_management", "authentication", "beneficiary_portal", "compliance_reporting"],
            integrations=[IntegrationType.EMAIL, IntegrationType.STRIPE],
            auth_required=True,
            theme="legal",
        )

    def _build_estate_planning_intake(self) -> AppSpec:
        return AppSpec(
            name="Estate Planning Intake",
            description="Multi-step estate planning questionnaire for will and trust preparation",
            app_type=AppType.LEGAL_PORTAL,
            pages=[
                Page(
                    name="Start", route="/",
                    title="Estate Planning — Start Your Free Consultation",
                    components=[
                        Component(ComponentType.NAVBAR, props={"title": "Estate Planning"}),
                        Component(ComponentType.HERO, props={
                            "title": "Protect Your Legacy",
                            "subtitle": "Our estate planning questionnaire takes 10 minutes and sets you up for life.",
                            "cta": "Begin Questionnaire",
                        }),
                        Component(ComponentType.FOOTER, props={"firm_name": "Estate Planning Firm"}),
                    ],
                ),
                Page(
                    name="Personal Info", route="/intake/step-1",
                    title="Step 1 — Personal Information",
                    components=[
                        Component(ComponentType.FORM, props={
                            "form_type": "estate_intake_step1",
                            "fields": ["name", "dob", "address", "marital_status", "children"],
                            "step": 1,
                            "total_steps": 5,
                        }),
                    ],
                ),
                Page(
                    name="Assets", route="/intake/step-2",
                    title="Step 2 — Assets & Property",
                    components=[
                        Component(ComponentType.FORM, props={
                            "form_type": "estate_intake_step2",
                            "fields": ["real_estate", "bank_accounts", "investments", "life_insurance", "business_interests"],
                            "step": 2,
                            "total_steps": 5,
                        }),
                    ],
                ),
                Page(
                    name="Beneficiaries", route="/intake/step-3",
                    title="Step 3 — Beneficiaries & Heirs",
                    components=[
                        Component(ComponentType.FORM, props={
                            "form_type": "estate_intake_step3",
                            "fields": ["primary_beneficiary", "contingent_beneficiary", "specific_bequests"],
                            "step": 3,
                            "total_steps": 5,
                        }),
                    ],
                ),
                Page(
                    name="Directives", route="/intake/step-4",
                    title="Step 4 — Healthcare & Financial Directives",
                    components=[
                        Component(ComponentType.FORM, props={
                            "form_type": "estate_intake_step4",
                            "fields": ["healthcare_proxy", "financial_poa", "living_will_wishes"],
                            "step": 4,
                            "total_steps": 5,
                        }),
                    ],
                ),
                Page(
                    name="Review", route="/intake/step-5",
                    title="Step 5 — Review & Submit",
                    components=[
                        Component(ComponentType.STAT, props={"metrics": ["documents_needed", "estimated_cost", "timeline"]}),
                        Component(ComponentType.BUTTON, props={"label": "Schedule Consultation", "href": "/schedule"}),
                    ],
                ),
            ],
            features=["multi_step_form", "contact_form", "appointment_booking", "seo_optimization"],
            integrations=[IntegrationType.EMAIL, IntegrationType.CALENDAR],
            theme="legal",
        )

    def _build_debt_settlement_tracker(self) -> AppSpec:
        return AppSpec(
            name="Debt Settlement Tracker",
            description="Track debt negotiation, settlement offers, and payment plans",
            app_type=AppType.CASE_TRACKER,
            pages=[
                Page(
                    name="Dashboard", route="/dashboard", requires_auth=True,
                    title="Debt Settlement Dashboard",
                    components=[
                        Component(ComponentType.SIDEBAR, props={}),
                        Component(ComponentType.STAT, props={"metrics": ["total_debt", "settled_amount", "savings_percent", "active_accounts"]}),
                        Component(ComponentType.CHART, props={"chart_type": "bar", "data": "debt_by_creditor"}),
                    ],
                ),
                Page(
                    name="Debts", route="/debts", requires_auth=True,
                    title="Active Debts",
                    components=[
                        Component(ComponentType.TABLE, props={"data_type": "debts"}),
                        Component(ComponentType.BUTTON, props={"label": "Add Debt", "variant": "primary"}),
                    ],
                ),
                Page(
                    name="Negotiations", route="/negotiations", requires_auth=True,
                    title="Active Negotiations",
                    components=[
                        Component(ComponentType.TABLE, props={"data_type": "negotiations"}),
                        Component(ComponentType.TIMELINE, props={}),
                    ],
                ),
                Page(
                    name="Settlements", route="/settlements", requires_auth=True,
                    title="Completed Settlements",
                    components=[
                        Component(ComponentType.TABLE, props={"data_type": "settlements"}),
                        Component(ComponentType.STAT, props={"metrics": ["total_savings", "accounts_resolved"]}),
                    ],
                ),
                Page(
                    name="Documents", route="/documents", requires_auth=True,
                    title="Settlement Documents",
                    components=[
                        Component(ComponentType.FILE_UPLOAD, props={}),
                        Component(ComponentType.TABLE, props={"data_type": "settlement_letters"}),
                    ],
                ),
            ],
            features=["authentication", "debt_tracking", "document_management", "analytics_dashboard"],
            integrations=[IntegrationType.EMAIL],
            auth_required=True,
            theme="financial",
        )

    def _build_business_formation_wizard(self) -> AppSpec:
        return AppSpec(
            name="Business Formation Wizard",
            description="Step-by-step business entity formation guide and document generator",
            app_type=AppType.LEGAL_PORTAL,
            pages=[
                Page(
                    name="Home", route="/",
                    title="Business Formation Wizard — Start Your Business Today",
                    components=[
                        Component(ComponentType.NAVBAR, props={"title": "Business Formation"}),
                        Component(ComponentType.HERO, props={
                            "title": "Start Your Business the Right Way",
                            "subtitle": "Form your LLC, S-Corp, or C-Corp with legal guidance every step.",
                            "cta": "Start Formation",
                        }),
                        Component(ComponentType.FOOTER, props={"firm_name": "Business Formation Wizard"}),
                    ],
                ),
                Page(
                    name="Entity Type", route="/wizard/entity-type",
                    title="Choose Your Business Entity",
                    components=[
                        Component(ComponentType.CARD, props={"variant": "entity_type"}),
                        Component(ComponentType.BUTTON, props={"label": "Next: Business Details", "href": "/wizard/details"}),
                    ],
                ),
                Page(
                    name="Business Details", route="/wizard/details",
                    title="Business Details",
                    components=[
                        Component(ComponentType.FORM, props={
                            "form_type": "business_details",
                            "fields": ["business_name", "state", "business_address", "owners", "purpose"],
                        }),
                    ],
                ),
                Page(
                    name="Generate Documents", route="/wizard/documents",
                    title="Generate Formation Documents",
                    components=[
                        Component(ComponentType.STAT, props={"metrics": ["documents_ready", "estimated_cost", "filing_fee"]}),
                        Component(ComponentType.BUTTON, props={"label": "Generate & Download", "variant": "primary"}),
                    ],
                ),
                Page(
                    name="Filing Status", route="/wizard/status", requires_auth=True,
                    title="Filing Status",
                    components=[
                        Component(ComponentType.TIMELINE, props={}),
                        Component(ComponentType.TABLE, props={"data_type": "formation_tasks"}),
                    ],
                ),
            ],
            features=["multi_step_wizard", "document_generation", "contact_form", "stripe_billing"],
            integrations=[IntegrationType.STRIPE, IntegrationType.EMAIL],
            theme="legal",
        )

    def _build_court_deadline_tracker(self) -> AppSpec:
        return AppSpec(
            name="Court Deadline Tracker",
            description="Docket management for court deadlines and matter milestones",
            app_type=AppType.CASE_TRACKER,
            pages=[
                Page(
                    name="Dashboard", route="/dashboard", requires_auth=True,
                    title="Docket Dashboard",
                    components=[
                        Component(ComponentType.SIDEBAR, props={}),
                        Component(ComponentType.STAT, props={"metrics": ["overdue", "due_this_week", "due_this_month", "completed"]}),
                        Component(ComponentType.ALERT, props={"type": "warning", "message": "You have deadlines due this week."}),
                        Component(ComponentType.TABLE, props={"data_type": "deadlines"}),
                    ],
                ),
                Page(
                    name="Matters", route="/matters", requires_auth=True,
                    title="Active Matters",
                    components=[
                        Component(ComponentType.TABLE, props={"data_type": "matters"}),
                        Component(ComponentType.BUTTON, props={"label": "Add Matter", "variant": "primary"}),
                    ],
                ),
                Page(
                    name="Calendar", route="/calendar", requires_auth=True,
                    title="Deadline Calendar",
                    components=[
                        Component(ComponentType.CALENDAR, props={}),
                    ],
                ),
                Page(
                    name="Reports", route="/reports", requires_auth=True,
                    title="Deadline Reports",
                    components=[
                        Component(ComponentType.CHART, props={"chart_type": "bar", "data": "deadlines_by_month"}),
                        Component(ComponentType.TABLE, props={"data_type": "completed_deadlines"}),
                    ],
                ),
            ],
            features=["authentication", "deadline_tracking", "calendar", "email_notifications"],
            integrations=[IntegrationType.EMAIL, IntegrationType.CALENDAR],
            auth_required=True,
            theme="legal",
        )

    def _build_financial_health_dashboard(self) -> AppSpec:
        return AppSpec(
            name="Financial Health Dashboard",
            description="Personal finance overview: net worth, accounts, budgets, debts, credit, investments",
            app_type=AppType.FINANCIAL_DASHBOARD,
            pages=[
                Page(
                    name="Dashboard", route="/dashboard", requires_auth=True,
                    title="Financial Dashboard",
                    components=[
                        Component(ComponentType.SIDEBAR, props={}),
                        Component(ComponentType.STAT, props={"metrics": ["net_worth", "monthly_cashflow", "credit_score", "savings_rate"]}),
                        Component(ComponentType.CHART, props={"chart_type": "line", "data": "net_worth_trend"}),
                        Component(ComponentType.CHART, props={"chart_type": "doughnut", "data": "spending_by_category"}),
                    ],
                ),
                Page(
                    name="Accounts", route="/accounts", requires_auth=True,
                    title="Accounts",
                    components=[
                        Component(ComponentType.TABLE, props={"data_type": "accounts"}),
                        Component(ComponentType.STAT, props={"metrics": ["total_assets", "total_liabilities"]}),
                    ],
                ),
                Page(
                    name="Budget", route="/budget", requires_auth=True,
                    title="Budget",
                    components=[
                        Component(ComponentType.CHART, props={"chart_type": "bar", "data": "budget_vs_actual"}),
                        Component(ComponentType.TABLE, props={"data_type": "budget_categories"}),
                    ],
                ),
                Page(
                    name="Debts", route="/debts", requires_auth=True,
                    title="Debt Tracker",
                    components=[
                        Component(ComponentType.TABLE, props={"data_type": "debts"}),
                        Component(ComponentType.CHART, props={"chart_type": "bar", "data": "debt_payoff_timeline"}),
                    ],
                ),
                Page(
                    name="Investments", route="/investments", requires_auth=True,
                    title="Investment Portfolio",
                    components=[
                        Component(ComponentType.STAT, props={"metrics": ["portfolio_value", "ytd_return", "allocation"]}),
                        Component(ComponentType.CHART, props={"chart_type": "pie", "data": "asset_allocation"}),
                        Component(ComponentType.TABLE, props={"data_type": "holdings"}),
                    ],
                ),
                Page(
                    name="Credit", route="/credit", requires_auth=True,
                    title="Credit Score",
                    components=[
                        Component(ComponentType.STAT, props={"metrics": ["credit_score", "on_time_payments", "utilization"]}),
                        Component(ComponentType.CHART, props={"chart_type": "line", "data": "credit_score_history"}),
                    ],
                ),
            ],
            features=["authentication", "analytics_dashboard", "data_export", "plaid_integration"],
            integrations=[IntegrationType.PLAID, IntegrationType.EMAIL],
            auth_required=True,
            theme="financial",
        )

    # ------------------------------------------------------------------
    # Custom Template Management
    # ------------------------------------------------------------------

    def save_custom_template(self, name: str, spec: AppSpec) -> None:
        """Save a custom template for reuse."""
        self._custom_templates[name] = spec

    def get_custom_template(self, name: str) -> Optional[AppSpec]:
        """Get a custom template by name."""
        return self._custom_templates.get(name)

    def list_custom_templates(self) -> List[str]:
        """List all custom template names."""
        return list(self._custom_templates.keys())
