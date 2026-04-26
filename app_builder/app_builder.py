"""
AppBuilder — Autonomous Web/App Builder for SintraPrime
=======================================================
Manus-style autonomous builder specialized for legal and financial use cases.
One command to production-ready web apps with database, Stripe, and SEO.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from .app_types import (
    AppSpec, AppType, AppTemplate, BuildResult, Component, ComponentType,
    DatabaseSchema, IntegrationType, Page, Table, Column,
)
from .database_builder import DatabaseBuilder
from .site_generator import SiteGenerator
from .stripe_integrator import StripeIntegrator


class AppBuilder:
    """
    Autonomous web/app builder inspired by Manus AI.

    Creates full web apps from natural language descriptions or structured specs.
    Specializes in legal portals, financial dashboards, trust management, CRMs.
    Includes auto-generated database, Stripe billing, SEO meta tags.
    """

    # Natural language keyword → AppType mapping
    _TYPE_KEYWORDS: Dict[str, AppType] = {
        "law firm": AppType.LEGAL_PORTAL,
        "legal portal": AppType.LEGAL_PORTAL,
        "attorney": AppType.LEGAL_PORTAL,
        "lawyer": AppType.LEGAL_PORTAL,
        "practice": AppType.LEGAL_PORTAL,
        "financial dashboard": AppType.FINANCIAL_DASHBOARD,
        "finance": AppType.FINANCIAL_DASHBOARD,
        "budget": AppType.FINANCIAL_DASHBOARD,
        "investment": AppType.FINANCIAL_DASHBOARD,
        "trust": AppType.TRUST_MANAGER,
        "estate": AppType.TRUST_MANAGER,
        "probate": AppType.TRUST_MANAGER,
        "crm": AppType.CLIENT_CRM,
        "client management": AppType.CLIENT_CRM,
        "contacts": AppType.CLIENT_CRM,
        "case tracker": AppType.CASE_TRACKER,
        "matter": AppType.CASE_TRACKER,
        "docket": AppType.CASE_TRACKER,
        "deadline": AppType.CASE_TRACKER,
        "landing page": AppType.LANDING_PAGE,
        "marketing": AppType.LANDING_PAGE,
        "appointment": AppType.APPOINTMENT_BOOKING,
        "booking": AppType.APPOINTMENT_BOOKING,
        "schedule": AppType.APPOINTMENT_BOOKING,
        "document portal": AppType.DOCUMENT_PORTAL,
        "document sharing": AppType.DOCUMENT_PORTAL,
        "file management": AppType.DOCUMENT_PORTAL,
    }

    def __init__(
        self,
        output_dir: str = "/tmp/sintra_apps",
        db_builder: Optional[DatabaseBuilder] = None,
        site_gen: Optional[SiteGenerator] = None,
        stripe: Optional[StripeIntegrator] = None,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.db_builder = db_builder or DatabaseBuilder()
        self.site_gen = site_gen or SiteGenerator()
        self.stripe = stripe or StripeIntegrator()
        self._apps: Dict[str, AppSpec] = {}

    # ------------------------------------------------------------------
    # Natural Language → Spec
    # ------------------------------------------------------------------

    def build_from_description(self, description: str) -> AppSpec:
        """
        Parse a natural language description and return an AppSpec.

        Example:
            spec = builder.build_from_description(
                "Build a law firm website for Smith & Associates, "
                "specializing in estate planning in California."
            )
        """
        description_lower = description.lower()

        # Detect app type
        app_type = AppType.CUSTOM
        for keyword, a_type in self._TYPE_KEYWORDS.items():
            if keyword in description_lower:
                app_type = a_type
                break

        # Extract app name from description (take first N words)
        words = description.split()
        name_words = [w for w in words[:6] if len(w) > 2]
        app_name = " ".join(name_words[:4]).title().rstrip(".,")

        # Determine features from keywords
        features = []
        if any(k in description_lower for k in ["contact", "intake", "form"]):
            features.append("contact_form")
        if any(k in description_lower for k in ["appointment", "booking", "schedule"]):
            features.append("appointment_booking")
        if any(k in description_lower for k in ["payment", "billing", "stripe", "invoice"]):
            features.append("stripe_billing")
        if any(k in description_lower for k in ["document", "upload", "file"]):
            features.append("document_management")
        if any(k in description_lower for k in ["dashboard", "analytics", "report"]):
            features.append("analytics_dashboard")
        if any(k in description_lower for k in ["auth", "login", "secure", "portal"]):
            features.append("authentication")
        if any(k in description_lower for k in ["seo", "search", "google"]):
            features.append("seo_optimization")

        # Default features by app type
        default_features = {
            AppType.LEGAL_PORTAL: ["contact_form", "practice_areas", "attorney_profiles", "seo_optimization"],
            AppType.FINANCIAL_DASHBOARD: ["analytics_dashboard", "authentication", "data_export"],
            AppType.TRUST_MANAGER: ["document_management", "authentication", "beneficiary_portal"],
            AppType.CLIENT_CRM: ["contact_form", "authentication", "analytics_dashboard"],
            AppType.CASE_TRACKER: ["authentication", "deadline_tracking", "document_management"],
            AppType.LANDING_PAGE: ["contact_form", "seo_optimization"],
            AppType.APPOINTMENT_BOOKING: ["appointment_booking", "email_notifications"],
            AppType.DOCUMENT_PORTAL: ["document_management", "authentication"],
            AppType.CUSTOM: [],
        }
        features = list(set(features + default_features.get(app_type, [])))

        # Generate pages based on app type
        pages = self._default_pages_for_type(app_type, app_name)

        # Generate database schema
        db_schema = self.db_builder.from_description(description)

        # Determine integrations
        integrations = []
        if "stripe_billing" in features:
            integrations.append(IntegrationType.STRIPE)
        if "appointment_booking" in features:
            integrations.append(IntegrationType.CALENDAR)
        if "email_notifications" in features:
            integrations.append(IntegrationType.EMAIL)

        spec = AppSpec(
            name=app_name,
            description=description,
            app_type=app_type,
            pages=pages,
            features=features,
            database_schema=db_schema,
            styling={"primary_color": "#1e40af", "font": "Inter"},
            integrations=integrations,
            seo={
                "title": app_name,
                "description": description[:160],
                "keywords": self._extract_seo_keywords(description),
            },
            auth_required="authentication" in features,
            theme="legal" if app_type in (AppType.LEGAL_PORTAL, AppType.TRUST_MANAGER) else "sintra",
        )

        app_id = str(uuid.uuid4())[:8]
        self._apps[app_id] = spec
        return spec

    def _extract_seo_keywords(self, text: str) -> str:
        legal_kw = ["attorney", "lawyer", "law firm", "legal services", "estate planning",
                    "trust", "probate", "litigation", "contract"]
        financial_kw = ["financial planning", "investment", "budget", "wealth management"]
        found = [kw for kw in legal_kw + financial_kw if kw in text.lower()]
        return ", ".join(found[:8])

    def _default_pages_for_type(self, app_type: AppType, name: str) -> List[Page]:
        """Return default pages for a given app type."""
        common_home = Page(
            name="Home",
            route="/",
            components=[
                Component(ComponentType.NAVBAR, props={"title": name}),
                Component(ComponentType.HERO, props={"title": name, "subtitle": "Professional Services"}),
                Component(ComponentType.FOOTER, props={"firm_name": name}),
            ],
            title=f"{name} - Home",
        )

        pages_by_type: Dict[AppType, List[Page]] = {
            AppType.LEGAL_PORTAL: [
                common_home,
                Page(name="Practice Areas", route="/practice-areas",
                     components=[Component(ComponentType.CARD, props={"variant": "practice_area"})],
                     title=f"{name} - Practice Areas"),
                Page(name="Attorneys", route="/attorneys",
                     components=[Component(ComponentType.CARD, props={"variant": "attorney_bio"})],
                     title=f"{name} - Our Team"),
                Page(name="Contact", route="/contact",
                     components=[Component(ComponentType.FORM, props={"form_type": "legal_intake"})],
                     title=f"{name} - Contact Us"),
                Page(name="Client Portal", route="/portal", requires_auth=True,
                     components=[Component(ComponentType.SIDEBAR, props={}),
                                 Component(ComponentType.TABLE, props={"data_type": "matters"})],
                     title="Client Portal"),
            ],
            AppType.FINANCIAL_DASHBOARD: [
                common_home,
                Page(name="Dashboard", route="/dashboard", requires_auth=True,
                     components=[Component(ComponentType.STAT, props={"metrics": ["net_worth", "monthly_cashflow"]}),
                                 Component(ComponentType.CHART, props={"chart_type": "line", "data": "transactions"})],
                     title="Financial Dashboard"),
                Page(name="Accounts", route="/accounts", requires_auth=True,
                     components=[Component(ComponentType.TABLE, props={"data_type": "accounts"})]),
                Page(name="Budget", route="/budget", requires_auth=True,
                     components=[Component(ComponentType.CHART, props={"chart_type": "bar", "data": "budget"})]),
            ],
            AppType.TRUST_MANAGER: [
                common_home,
                Page(name="Trust Overview", route="/trust", requires_auth=True,
                     components=[Component(ComponentType.STAT, props={"metrics": ["trust_value", "distributions"]}),
                                 Component(ComponentType.TABLE, props={"data_type": "beneficiaries"})]),
                Page(name="Documents", route="/documents", requires_auth=True,
                     components=[Component(ComponentType.FILE_UPLOAD, props={}),
                                 Component(ComponentType.TABLE, props={"data_type": "documents"})]),
                Page(name="Distributions", route="/distributions", requires_auth=True,
                     components=[Component(ComponentType.TABLE, props={"data_type": "distributions"})]),
            ],
            AppType.CLIENT_CRM: [
                common_home,
                Page(name="Clients", route="/clients", requires_auth=True,
                     components=[Component(ComponentType.TABLE, props={"data_type": "clients"}),
                                 Component(ComponentType.BUTTON, props={"label": "Add Client"})]),
                Page(name="Matters", route="/matters", requires_auth=True,
                     components=[Component(ComponentType.TABLE, props={"data_type": "matters"})]),
                Page(name="Calendar", route="/calendar", requires_auth=True,
                     components=[Component(ComponentType.CALENDAR, props={})]),
                Page(name="Reports", route="/reports", requires_auth=True,
                     components=[Component(ComponentType.CHART, props={"chart_type": "pie", "data": "clients_by_type"})]),
            ],
            AppType.LANDING_PAGE: [
                common_home,
                Page(name="Contact", route="/contact",
                     components=[Component(ComponentType.FORM, props={"form_type": "contact"})]),
            ],
        }

        return pages_by_type.get(app_type, [common_home])

    # ------------------------------------------------------------------
    # Build Methods
    # ------------------------------------------------------------------

    def build(self, spec: AppSpec) -> BuildResult:
        """Generate a complete app from a spec."""
        start = time.time()
        app_id = str(uuid.uuid4())[:8]
        app_dir = self.output_dir / f"{app_id}_{spec.name.replace(' ', '_').lower()}"
        app_dir.mkdir(parents=True, exist_ok=True)

        files_created = []
        errors = []
        warnings = []
        stripe_product_id = ""
        db_name = ""

        try:
            # Generate HTML site
            html_files = self.site_gen.generate_html_site(spec)
            for filename, content in html_files.items():
                fpath = app_dir / filename
                fpath.parent.mkdir(parents=True, exist_ok=True)
                fpath.write_text(content)
                files_created.append(str(fpath))

            # Generate database
            if spec.database_schema:
                db_name = f"{app_id}_{spec.name.replace(' ', '_').lower()}.db"
                db_path = str(app_dir / db_name)
                self.db_builder.generate_sqlite(spec.database_schema, db_path)
                files_created.append(db_path)

                # Write migration file
                migration_sql = self.db_builder.generate_migration(spec.database_schema)
                migration_path = app_dir / "migration.sql"
                migration_path.write_text(migration_sql)
                files_created.append(str(migration_path))

                # Generate FastAPI endpoints
                api_code = self.db_builder.generate_api_endpoints(spec.database_schema)
                api_path = app_dir / "api.py"
                api_path.write_text(api_code)
                files_created.append(str(api_path))

            # Stripe integration
            if IntegrationType.STRIPE in spec.integrations:
                stripe_config = self.stripe.setup_legal_billing(
                    spec.name, spec.features
                )
                product_id = self.stripe.create_subscription_product(
                    spec.name, 99.00, spec.features
                )
                stripe_product_id = product_id

                payment_form = self.stripe.generate_payment_form(product_id)
                payment_path = app_dir / "payment.html"
                payment_path.write_text(payment_form)
                files_created.append(str(payment_path))

            # Write spec as JSON
            spec_path = app_dir / "app_spec.json"
            spec_path.write_text(json.dumps(spec.to_dict(), indent=2))
            files_created.append(str(spec_path))

            self._apps[app_id] = spec

            return BuildResult(
                success=True,
                app_id=app_id,
                app_url=f"http://localhost:8080/{app_id}",
                files_created=files_created,
                database_name=db_name,
                stripe_product_id=stripe_product_id,
                errors=errors,
                warnings=warnings,
                preview_url=f"/builder/preview/{app_id}",
                build_time_seconds=round(time.time() - start, 2),
                spec=spec,
            )

        except Exception as e:
            errors.append(str(e))
            return BuildResult(
                success=False,
                app_id=app_id,
                errors=errors,
                build_time_seconds=round(time.time() - start, 2),
            )

    def build_legal_portal(
        self,
        client_name: str,
        practice_areas: List[str],
        jurisdiction: str = "United States",
    ) -> BuildResult:
        """
        One-command legal portal builder.

        Example:
            result = builder.build_legal_portal(
                "Smith & Associates",
                ["Estate Planning", "Trust Law", "Probate"],
                "California"
            )
        """
        description = (
            f"Law firm website for {client_name}, practicing {', '.join(practice_areas)} "
            f"in {jurisdiction}. Include client portal, intake forms, and document management."
        )
        spec = self.build_from_description(description)
        spec.name = client_name
        spec.features += ["attorney_profiles", "practice_area_pages", "stripe_billing"]
        spec.integrations.append(IntegrationType.STRIPE)
        spec.seo["keywords"] = f"{', '.join(practice_areas)}, attorney, {jurisdiction}"
        return self.build(spec)

    def build_financial_dashboard(self, user_profile: Dict[str, Any]) -> BuildResult:
        """
        Build a personal finance dashboard from user profile data.
        """
        name = user_profile.get("name", "My Finance Dashboard")
        description = (
            f"Personal financial dashboard for {name}. "
            "Track accounts, budgets, investments, credit, and net worth. "
            "Includes analytics charts and financial health scoring."
        )
        spec = self.build_from_description(description)
        spec.name = f"{name} Finance Dashboard"
        spec.app_type = AppType.FINANCIAL_DASHBOARD
        spec.auth_required = True
        spec.theme = "financial"
        return self.build(spec)

    def build_trust_manager(self, trust_details: Dict[str, Any]) -> BuildResult:
        """
        Build a trust management portal.
        """
        trust_name = trust_details.get("trust_name", "Family Trust")
        trustee = trust_details.get("trustee", "")
        description = (
            f"Trust management portal for {trust_name}. "
            f"Trustee: {trustee}. Manage beneficiaries, distributions, documents, "
            "assets, and compliance reporting."
        )
        spec = self.build_from_description(description)
        spec.name = f"{trust_name} Portal"
        spec.app_type = AppType.TRUST_MANAGER
        spec.auth_required = True
        spec.theme = "legal"
        return self.build(spec)

    def build_client_crm(self, firm_details: Dict[str, Any]) -> BuildResult:
        """
        Build a law firm CRM.
        """
        firm_name = firm_details.get("firm_name", "Law Firm")
        description = (
            f"Client CRM for {firm_name}. Manage clients, matters, deadlines, "
            "billing, documents, and communications. Includes analytics dashboard."
        )
        spec = self.build_from_description(description)
        spec.name = f"{firm_name} CRM"
        spec.app_type = AppType.CLIENT_CRM
        spec.auth_required = True
        spec.integrations.append(IntegrationType.STRIPE)
        spec.integrations.append(IntegrationType.EMAIL)
        return self.build(spec)

    # ------------------------------------------------------------------
    # Preview & Deploy
    # ------------------------------------------------------------------

    def preview(self, spec: AppSpec) -> str:
        """Generate a standalone preview HTML page for the app spec."""
        return self.site_gen.generate_landing_page(
            title=spec.name,
            subtitle=spec.description,
            features=spec.features,
            cta="Get Started",
        )

    def deploy(self, spec: AppSpec, target: str = "local") -> str:
        """
        Deploy the built app.

        targets: local, docker, vercel, railway
        Returns the deployment URL.
        """
        result = self.build(spec)
        if not result.success:
            raise RuntimeError(f"Build failed: {result.errors}")

        if target == "local":
            return f"http://localhost:8080/{result.app_id}"
        elif target == "docker":
            dockerfile = self._generate_dockerfile(spec, result)
            docker_path = Path(result.files_created[0]).parent / "Dockerfile"
            docker_path.write_text(dockerfile)
            return f"docker run -p 8080:8080 sintra/{result.app_id}"
        elif target == "vercel":
            return f"https://{result.app_id}.vercel.app"
        elif target == "railway":
            return f"https://{result.app_id}.railway.app"
        else:
            return f"http://localhost:8080/{result.app_id}"

    def _generate_dockerfile(self, spec: AppSpec, result: BuildResult) -> str:
        return f"""FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install fastapi uvicorn sqlite3
EXPOSE 8080
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8080"]
"""

    def iterate(self, app_id: str, feedback: str) -> BuildResult:
        """
        Improve an existing app based on feedback.

        Example:
            result = builder.iterate(app_id, "Add a dark mode toggle and improve the intake form")
        """
        if app_id not in self._apps:
            return BuildResult(
                success=False,
                app_id=app_id,
                errors=[f"App {app_id} not found"],
            )

        spec = self._apps[app_id]
        feedback_lower = feedback.lower()

        # Apply feedback modifications
        if "dark mode" in feedback_lower:
            spec.styling["dark_mode"] = "true"
        if "intake form" in feedback_lower or "contact form" in feedback_lower:
            if "contact_form" not in spec.features:
                spec.features.append("contact_form")
        if "stripe" in feedback_lower or "payment" in feedback_lower:
            if IntegrationType.STRIPE not in spec.integrations:
                spec.integrations.append(IntegrationType.STRIPE)
        if "calendar" in feedback_lower or "booking" in feedback_lower:
            if IntegrationType.CALENDAR not in spec.integrations:
                spec.integrations.append(IntegrationType.CALENDAR)

        spec.description += f" [Updated: {feedback}]"
        return self.build(spec)

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def list_apps(self) -> List[Dict[str, Any]]:
        return [
            {"app_id": app_id, "name": spec.name, "app_type": spec.app_type.value}
            for app_id, spec in self._apps.items()
        ]

    def get_app(self, app_id: str) -> Optional[AppSpec]:
        return self._apps.get(app_id)
