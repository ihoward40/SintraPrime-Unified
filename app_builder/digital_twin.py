"""
DigitalTwin — AI Life Model for SintraPrime
============================================
The most unique feature in all of AI: a persistent, comprehensive model
of the user's legal, financial, and life situation.

Tracks every domain of a person's life:
- Legal matters (cases, trusts, contracts)
- Financial profile (assets, debts, credit)
- Properties (real estate, vehicles, valuables)
- Relationships (family, business, legal contacts)
- Health directives (proxy, living will, POA)
- Business interests (LLCs, partnerships, equity)
- Digital assets (accounts, crypto, IP)

Provides:
- Life risk assessment
- Estate readiness scoring
- Governance recommendations
- What-if scenario analysis
- Complete life portfolio export
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .app_types import (
    Business, Directive, DigitalAsset, EstateReport, FinancialProfile,
    LifeEvent, LifePortfolio, LifeSnapshot, LegalMatter, Property,
    Recommendation, Relationship, RiskReport, ScenarioAnalysis,
)


class DigitalTwin:
    """
    Digital Twin — AI model of a user's entire life situation.

    Unlike any other AI feature, the Digital Twin maintains a living,
    breathing model of who you are: your assets, your legal standing,
    your relationships, your vulnerabilities, and your readiness for
    the future.

    This is life governance at scale.
    """

    def __init__(self, storage_dir: str = "/tmp/sintra_twins"):
        self._storage_dir = Path(storage_dir)
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._twins: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Core CRUD
    # ------------------------------------------------------------------

    def create(self, user_id: str, name: str) -> "DigitalTwin":
        """Create a new Digital Twin for a user."""
        twin_data = {
            "user_id": user_id,
            "name": name,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "legal_matters": [],
            "financial_profile": {
                "total_assets": 0.0,
                "total_debts": 0.0,
                "monthly_income": 0.0,
                "monthly_expenses": 0.0,
                "credit_score": 0,
                "accounts": [],
                "investments": [],
                "debts": [],
            },
            "properties": [],
            "relationships": [],
            "health_directives": [],
            "business_interests": [],
            "digital_assets": [],
            "life_events": [],
            "risk_score": 0.0,
            "estate_readiness_score": 0.0,
        }
        self._twins[user_id] = twin_data
        self._persist(user_id)
        return self

    def load(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Load a twin from memory or disk."""
        if user_id in self._twins:
            return self._twins[user_id]
        path = self._storage_dir / f"{user_id}.json"
        if path.exists():
            data = json.loads(path.read_text())
            self._twins[user_id] = data
            return data
        return None

    def _get_or_create(self, user_id: str, name: str = "User") -> Dict[str, Any]:
        twin = self.load(user_id)
        if not twin:
            self.create(user_id, name)
            twin = self._twins[user_id]
        return twin

    def _persist(self, user_id: str) -> None:
        if user_id in self._twins:
            path = self._storage_dir / f"{user_id}.json"
            path.write_text(json.dumps(self._twins[user_id], indent=2))

    # ------------------------------------------------------------------
    # Life Event Updates
    # ------------------------------------------------------------------

    def update(self, user_id: str, event: LifeEvent) -> None:
        """Add a life event and update the twin's state accordingly."""
        twin = self._get_or_create(user_id)

        # Store event in history
        twin["life_events"].append({
            "event_id": event.event_id,
            "event_type": event.event_type,
            "title": event.title,
            "description": event.description,
            "date": event.date or datetime.now().isoformat(),
            "impact_level": event.impact_level,
            "data": event.data,
        })

        # Apply event data to twin
        self._apply_event(twin, event)
        twin["updated_at"] = datetime.now().isoformat()

        # Recalculate scores
        twin["risk_score"] = self._calculate_risk_score(twin)
        twin["estate_readiness_score"] = self._calculate_estate_readiness(twin)

        self._persist(user_id)

    def _apply_event(self, twin: Dict[str, Any], event: LifeEvent) -> None:
        """Apply a life event's data to the twin's state."""
        data = event.data

        if event.event_type == "legal":
            if matter_data := data.get("legal_matter"):
                twin["legal_matters"].append(matter_data)

        elif event.event_type == "financial":
            fp = twin["financial_profile"]
            if "total_assets" in data:
                fp["total_assets"] = data["total_assets"]
            if "total_debts" in data:
                fp["total_debts"] = data["total_debts"]
            if "monthly_income" in data:
                fp["monthly_income"] = data["monthly_income"]
            if "credit_score" in data:
                fp["credit_score"] = data["credit_score"]
            if account := data.get("account"):
                fp["accounts"].append(account)
            if debt := data.get("debt"):
                fp["debts"].append(debt)

        elif event.event_type == "property":
            if prop_data := data.get("property"):
                twin["properties"].append(prop_data)

        elif event.event_type == "family":
            if rel_data := data.get("relationship"):
                twin["relationships"].append(rel_data)

        elif event.event_type == "health":
            if directive_data := data.get("directive"):
                twin["health_directives"].append(directive_data)

        elif event.event_type == "business":
            if biz_data := data.get("business"):
                twin["business_interests"].append(biz_data)

        elif event.event_type == "digital":
            if asset_data := data.get("digital_asset"):
                twin["digital_assets"].append(asset_data)

    # ------------------------------------------------------------------
    # Life Snapshot
    # ------------------------------------------------------------------

    def life_snapshot(self, user_id: str) -> LifeSnapshot:
        """Generate a complete snapshot of the user's life state."""
        twin = self.load(user_id)
        if not twin:
            raise ValueError(f"No Digital Twin found for user {user_id}")

        fp_data = twin.get("financial_profile", {})
        financial_profile = FinancialProfile(
            total_assets=fp_data.get("total_assets", 0.0),
            total_debts=fp_data.get("total_debts", 0.0),
            monthly_income=fp_data.get("monthly_income", 0.0),
            monthly_expenses=fp_data.get("monthly_expenses", 0.0),
            credit_score=fp_data.get("credit_score", 0),
            accounts=fp_data.get("accounts", []),
            investments=fp_data.get("investments", []),
            debts=fp_data.get("debts", []),
        )

        legal_matters = [
            LegalMatter(**m) if isinstance(m, dict) else m
            for m in twin.get("legal_matters", [])
            if isinstance(m, dict)
        ]

        properties = [
            Property(**p) if isinstance(p, dict) else p
            for p in twin.get("properties", [])
            if isinstance(p, dict)
        ]

        relationships = [
            Relationship(**r) if isinstance(r, dict) else r
            for r in twin.get("relationships", [])
            if isinstance(r, dict)
        ]

        directives = [
            Directive(**d) if isinstance(d, dict) else d
            for d in twin.get("health_directives", [])
            if isinstance(d, dict)
        ]

        businesses = [
            Business(**b) if isinstance(b, dict) else b
            for b in twin.get("business_interests", [])
            if isinstance(b, dict)
        ]

        digital_assets = [
            DigitalAsset(**a) if isinstance(a, dict) else a
            for a in twin.get("digital_assets", [])
            if isinstance(a, dict)
        ]

        return LifeSnapshot(
            user_id=user_id,
            name=twin.get("name", ""),
            snapshot_date=datetime.now().isoformat(),
            legal_matters=legal_matters,
            financial_profile=financial_profile,
            properties=properties,
            relationships=relationships,
            health_directives=directives,
            business_interests=businesses,
            digital_assets=digital_assets,
            risk_score=twin.get("risk_score", 0.0),
            estate_readiness_score=twin.get("estate_readiness_score", 0.0),
        )

    # ------------------------------------------------------------------
    # Risk Assessment
    # ------------------------------------------------------------------

    def life_risk_assessment(self, user_id: str) -> RiskReport:
        """
        Assess all life risks: legal, financial, estate, digital, relationship.
        Returns a comprehensive risk report with actionable recommendations.
        """
        twin = self.load(user_id)
        if not twin:
            raise ValueError(f"No Digital Twin found for user {user_id}")

        vulnerabilities = []
        recommendations = []
        critical_gaps = []

        fp = twin.get("financial_profile", {})
        directives = twin.get("health_directives", [])
        relationships = twin.get("relationships", [])
        digital_assets = twin.get("digital_assets", [])
        businesses = twin.get("business_interests", [])
        legal_matters = twin.get("legal_matters", [])
        properties = twin.get("properties", [])

        # Financial risks
        assets = fp.get("total_assets", 0)
        debts = fp.get("total_debts", 0)
        income = fp.get("monthly_income", 0)
        credit = fp.get("credit_score", 0)

        if assets == 0 and debts == 0:
            vulnerabilities.append({"category": "financial", "issue": "No financial data tracked", "severity": "medium"})
            recommendations.append("Add your financial accounts to get a complete financial picture.")

        if debts > 0 and income > 0:
            dti = debts / (income * 12)
            if dti > 0.43:
                vulnerabilities.append({
                    "category": "financial",
                    "issue": f"High debt-to-income ratio: {dti:.1%}",
                    "severity": "high",
                })
                critical_gaps.append("Debt load exceeds 43% DTI — refinancing or settlement needed.")
                recommendations.append("Consult a debt specialist to negotiate settlement or restructuring.")

        if credit > 0 and credit < 600:
            vulnerabilities.append({"category": "financial", "issue": f"Low credit score: {credit}", "severity": "high"})
            recommendations.append("Dispute inaccuracies and implement credit repair strategy.")

        # Estate/directive gaps
        if not directives:
            critical_gaps.append("No health directives (healthcare proxy, living will) on file.")
            vulnerabilities.append({"category": "estate", "issue": "No healthcare directives", "severity": "critical"})
        else:
            has_proxy = any(d.get("directive_type") == "healthcare_proxy" if isinstance(d, dict) else d.directive_type == "healthcare_proxy" for d in directives)
            has_will = any(d.get("directive_type") == "living_will" if isinstance(d, dict) else d.directive_type == "living_will" for d in directives)
            if not has_proxy:
                critical_gaps.append("No healthcare proxy designated.")
                vulnerabilities.append({"category": "estate", "issue": "Missing healthcare proxy", "severity": "critical"})
            if not has_will:
                vulnerabilities.append({"category": "estate", "issue": "Missing living will", "severity": "high"})

        # No executor/trustee named
        legal_roles = {
            r.get("legal_role", "") if isinstance(r, dict) else r.legal_role
            for r in relationships
        }
        if "executor" not in legal_roles:
            vulnerabilities.append({"category": "estate", "issue": "No executor named", "severity": "high"})
            recommendations.append("Designate an executor for your estate in your will.")
        if "trustee" not in legal_roles and twin.get("legal_matters"):
            vulnerabilities.append({"category": "trust", "issue": "Trust has no named trustee", "severity": "medium"})

        # Business risks
        for biz in businesses:
            biz_name = biz.get("name", "") if isinstance(biz, dict) else biz.name
            biz_type = biz.get("entity_type", "") if isinstance(biz, dict) else biz.entity_type
            if not biz_type:
                vulnerabilities.append({"category": "business", "issue": f"Business '{biz_name}' entity type unclear", "severity": "medium"})

        # Digital asset risks
        if digital_assets:
            no_beneficiary = [
                a.get("name") if isinstance(a, dict) else a.name
                for a in digital_assets
                if not (a.get("beneficiary") if isinstance(a, dict) else a.beneficiary)
            ]
            if no_beneficiary:
                vulnerabilities.append({
                    "category": "digital",
                    "issue": f"Digital assets without beneficiary: {', '.join(no_beneficiary[:3])}",
                    "severity": "medium",
                })
                recommendations.append("Designate beneficiaries for all digital assets in your estate plan.")

        # Active legal matters
        active_matters = len([m for m in legal_matters if (m.get("status") if isinstance(m, dict) else m.status) == "active"])
        if active_matters > 3:
            vulnerabilities.append({"category": "legal", "issue": f"{active_matters} concurrent active legal matters", "severity": "high"})

        risk_score = self._calculate_risk_score(twin)

        if risk_score >= 80:
            risk_level = "critical"
        elif risk_score >= 60:
            risk_level = "high"
        elif risk_score >= 40:
            risk_level = "medium"
        else:
            risk_level = "low"

        if not vulnerabilities:
            recommendations.append("Your life governance appears well-protected. Schedule an annual review.")

        return RiskReport(
            user_id=user_id,
            overall_risk_score=risk_score,
            risk_level=risk_level,
            vulnerabilities=vulnerabilities,
            recommendations=recommendations,
            critical_gaps=critical_gaps,
            generated_at=datetime.now().isoformat(),
        )

    def _calculate_risk_score(self, twin: Dict[str, Any]) -> float:
        """Calculate a 0-100 risk score (higher = more vulnerable)."""
        score = 0.0
        fp = twin.get("financial_profile", {})
        directives = twin.get("health_directives", [])

        # Financial stress
        assets = fp.get("total_assets", 0)
        debts = fp.get("total_debts", 0)
        income = fp.get("monthly_income", 0)
        credit = fp.get("credit_score", 0)

        if income > 0 and debts > 0:
            dti = debts / (income * 12)
            score += min(dti * 40, 30)  # max 30 points

        if credit > 0:
            credit_risk = max(0, (750 - credit) / 750 * 20)
            score += credit_risk  # max 20 points

        # Missing directives
        if not directives:
            score += 30
        else:
            has_proxy = any(
                (d.get("directive_type") if isinstance(d, dict) else d.directive_type) == "healthcare_proxy"
                for d in directives
            )
            if not has_proxy:
                score += 20

        # No relationships (executor, trustee)
        if not twin.get("relationships"):
            score += 10

        # Active legal matters pressure
        active_matters = len([
            m for m in twin.get("legal_matters", [])
            if (m.get("status") if isinstance(m, dict) else m.status) == "active"
        ])
        score += min(active_matters * 5, 20)

        return round(min(score, 100.0), 1)

    # ------------------------------------------------------------------
    # Estate Readiness
    # ------------------------------------------------------------------

    def estate_readiness(self, user_id: str) -> EstateReport:
        """
        Assess how estate-ready the user is.
        Checks: will, trust, POA, healthcare directive, beneficiaries.
        """
        twin = self.load(user_id)
        if not twin:
            raise ValueError(f"No Digital Twin found for user {user_id}")

        directives = twin.get("health_directives", [])
        relationships = twin.get("relationships", [])
        legal_matters = twin.get("legal_matters", [])

        directive_types = {
            (d.get("directive_type") if isinstance(d, dict) else d.directive_type)
            for d in directives
        }
        legal_types = {
            (m.get("matter_type") if isinstance(m, dict) else m.matter_type)
            for m in legal_matters
        }
        legal_roles = {
            (r.get("legal_role", "") if isinstance(r, dict) else r.legal_role)
            for r in relationships
        }

        has_will = "will" in legal_types or "testamentary" in directive_types
        has_trust = any(t in legal_types for t in ("trust", "trust_administration", "revocable", "irrevocable"))
        has_poa = "durable_poa" in directive_types or "financial_poa" in directive_types
        has_healthcare = "healthcare_proxy" in directive_types or "living_will" in directive_types
        beneficiaries_named = "beneficiary" in legal_roles
        documents_signed = any(
            (d.get("status") if isinstance(d, dict) else d.status) in ("signed", "notarized", "filed")
            for d in directives
        )

        missing_documents = []
        next_steps = []

        if not has_will:
            missing_documents.append("Last Will and Testament")
            next_steps.append("Draft and execute a Last Will and Testament with a licensed attorney.")
        if not has_trust:
            missing_documents.append("Revocable Living Trust")
            next_steps.append("Consider a Revocable Living Trust to avoid probate and protect privacy.")
        if not has_poa:
            missing_documents.append("Durable Power of Attorney (Financial)")
            next_steps.append("Execute a Durable Power of Attorney to designate a financial agent.")
        if not has_healthcare:
            missing_documents.append("Healthcare Proxy / Living Will")
            next_steps.append("Complete a Healthcare Proxy and Living Will immediately.")
        if not beneficiaries_named:
            next_steps.append("Designate beneficiaries on all accounts, life insurance, and retirement plans.")

        # Scoring (100-point scale)
        score = 0
        if has_will: score += 25
        if has_trust: score += 20
        if has_poa: score += 20
        if has_healthcare: score += 20
        if beneficiaries_named: score += 10
        if documents_signed: score += 5

        if score >= 90:
            readiness_level = "fully_protected"
        elif score >= 65:
            readiness_level = "mostly_ready"
        elif score >= 35:
            readiness_level = "partial"
        else:
            readiness_level = "not_started"

        if not next_steps:
            next_steps.append("✅ Estate plan is complete. Schedule an annual review with your attorney.")

        return EstateReport(
            user_id=user_id,
            readiness_score=float(score),
            readiness_level=readiness_level,
            has_will=has_will,
            has_trust=has_trust,
            has_poa=has_poa,
            has_healthcare_directive=has_healthcare,
            beneficiaries_named=beneficiaries_named,
            documents_signed=documents_signed,
            missing_documents=missing_documents,
            next_steps=next_steps,
            generated_at=datetime.now().isoformat(),
        )

    def _calculate_estate_readiness(self, twin: Dict[str, Any]) -> float:
        directives = twin.get("health_directives", [])
        legal_matters = twin.get("legal_matters", [])
        relationships = twin.get("relationships", [])

        score = 0.0
        directive_types = {
            (d.get("directive_type") if isinstance(d, dict) else d.directive_type)
            for d in directives
        }
        legal_types = {
            (m.get("matter_type") if isinstance(m, dict) else m.matter_type)
            for m in legal_matters
        }
        legal_roles = {
            (r.get("legal_role", "") if isinstance(r, dict) else r.legal_role)
            for r in relationships
        }

        if any(t in legal_types for t in ("will", "testamentary")): score += 25
        if any(t in legal_types for t in ("trust", "trust_administration")): score += 20
        if any(t in directive_types for t in ("durable_poa", "financial_poa")): score += 20
        if any(t in directive_types for t in ("healthcare_proxy", "living_will")): score += 20
        if "beneficiary" in legal_roles: score += 15

        return round(score, 1)

    # ------------------------------------------------------------------
    # Governance Recommendations
    # ------------------------------------------------------------------

    def governance_recommendations(self, user_id: str) -> List[Recommendation]:
        """
        Generate actionable life governance recommendations.
        Prioritized by urgency and impact.
        """
        twin = self.load(user_id)
        if not twin:
            raise ValueError(f"No Digital Twin found for user {user_id}")

        risk_report = self.life_risk_assessment(user_id)
        estate_report = self.estate_readiness(user_id)
        recommendations = []
        priority = 1

        # Critical estate gaps
        for doc in estate_report.missing_documents:
            recommendations.append(Recommendation(
                priority=priority,
                category="estate_planning",
                title=f"Execute: {doc}",
                description=f"Your estate plan is missing a {doc}. This document is critical for asset protection and life governance.",
                action_items=[
                    f"Contact an estate planning attorney",
                    f"Draft and review the {doc}",
                    "Get document notarized",
                    "Store securely (attorney safe, digital vault)",
                ],
                estimated_cost="$500 - $3,000",
                time_to_complete="2-4 weeks",
            ))
            priority += 1

        # Financial risks
        fp = twin.get("financial_profile", {})
        if fp.get("credit_score", 0) > 0 and fp["credit_score"] < 620:
            recommendations.append(Recommendation(
                priority=priority,
                category="financial_health",
                title="Credit Repair Program",
                description=f"Your credit score of {fp['credit_score']} is limiting financial options.",
                action_items=[
                    "Pull all 3 credit reports (AnnualCreditReport.com)",
                    "Dispute inaccurate items in writing",
                    "Negotiate pay-for-delete with creditors",
                    "Open a secured credit card to rebuild",
                ],
                estimated_cost="$0 - $500",
                time_to_complete="6-12 months",
            ))
            priority += 1

        # Active matters needing attention
        active_matters = [
            m for m in twin.get("legal_matters", [])
            if (m.get("status") if isinstance(m, dict) else m.status) == "active"
        ]
        if len(active_matters) > 2:
            recommendations.append(Recommendation(
                priority=priority,
                category="legal_management",
                title="Legal Matter Consolidation",
                description=f"You have {len(active_matters)} active legal matters. Consider consolidation and prioritization.",
                action_items=[
                    "Review each matter with your attorney",
                    "Identify matters that can be resolved",
                    "Set firm deadlines on each case",
                    "Consider alternative dispute resolution",
                ],
                estimated_cost="$1,000 - $5,000",
                time_to_complete="3-6 months",
            ))
            priority += 1

        # Digital assets
        digital_assets = twin.get("digital_assets", [])
        if digital_assets and not any(
            (a.get("beneficiary") if isinstance(a, dict) else a.beneficiary)
            for a in digital_assets
        ):
            recommendations.append(Recommendation(
                priority=priority,
                category="digital_estate",
                title="Digital Asset Beneficiary Designation",
                description="Your digital assets (accounts, crypto, IP) have no designated beneficiaries.",
                action_items=[
                    "Create a digital asset inventory",
                    "Store credentials in a secure password manager",
                    "Designate beneficiaries in your trust/will",
                    "Create access instructions for executor",
                ],
                estimated_cost="$0 - $200",
                time_to_complete="1-2 weeks",
            ))
            priority += 1

        if not recommendations:
            recommendations.append(Recommendation(
                priority=1,
                category="maintenance",
                title="Annual Life Portfolio Review",
                description="Your life governance is strong. Schedule a yearly review to stay current.",
                action_items=[
                    "Meet with estate planning attorney annually",
                    "Update beneficiary designations after life events",
                    "Review financial profile quarterly",
                    "Back up all legal documents digitally",
                ],
                estimated_cost="$500 - $1,500/year",
                time_to_complete="Ongoing",
            ))

        return recommendations

    # ------------------------------------------------------------------
    # What-If Scenarios
    # ------------------------------------------------------------------

    def what_if(self, user_id: str, scenario: str) -> ScenarioAnalysis:
        """
        Run a what-if scenario analysis on the user's life situation.

        Examples:
        - "What if I start a business?"
        - "What if I get divorced?"
        - "What if I inherit $500,000?"
        - "What if I become disabled?"
        - "What if I move to Florida?"
        """
        twin = self.load(user_id)
        if not twin:
            raise ValueError(f"No Digital Twin found for user {user_id}")

        scenario_lower = scenario.lower()
        fp = twin.get("financial_profile", {})

        current_state = {
            "net_worth": fp.get("total_assets", 0) - fp.get("total_debts", 0),
            "monthly_income": fp.get("monthly_income", 0),
            "credit_score": fp.get("credit_score", 0),
            "active_legal_matters": len([m for m in twin.get("legal_matters", [])
                                        if (m.get("status") if isinstance(m, dict) else m.status) == "active"]),
            "estate_readiness": twin.get("estate_readiness_score", 0),
        }

        projected_state = dict(current_state)
        risks = []
        opportunities = []
        recommended_actions = []

        if "business" in scenario_lower or "start" in scenario_lower:
            projected_state["net_worth"] = current_state["net_worth"] * 0.85  # Initial capital outlay
            risks = [
                "Personal liability exposure without proper entity formation",
                "Impact on personal credit if business debt accrues",
                "Tax complexity increases significantly",
                "Time away from family and estate planning",
            ]
            opportunities = [
                "Build equity and generational wealth",
                "Tax deductions and retirement plan options (SEP-IRA, Solo 401k)",
                "Asset protection through LLC structure",
                "Potential high-value digital asset creation",
            ]
            recommended_actions = [
                "Form an LLC or S-Corp before operating",
                "Open dedicated business banking accounts",
                "Get business liability insurance",
                "Update your trust/will to include business interests",
                "Consult a CPA for business tax structure",
            ]

        elif "divorce" in scenario_lower or "separation" in scenario_lower:
            projected_state["net_worth"] = current_state["net_worth"] * 0.5
            projected_state["monthly_income"] = current_state["monthly_income"] * 0.7
            risks = [
                "50%+ division of marital assets",
                "Spousal support obligations",
                "Child support and custody legal costs",
                "Possible loss of family home",
                "Beneficiary designations may be void",
            ]
            opportunities = [
                "Financial fresh start and independence",
                "Opportunity to reorganize estate plan",
                "Renegotiate retirement and investment accounts",
            ]
            recommended_actions = [
                "Retain a family law attorney immediately",
                "Secure copies of all financial documents",
                "Update all beneficiary designations",
                "Create new estate plan post-separation",
                "Protect business interests with valuation",
            ]

        elif "inherit" in scenario_lower or "inheritance" in scenario_lower:
            # Try to extract amount
            import re
            amounts = re.findall(r"\$?([\d,]+(?:\.\d+)?)\s*(?:k|thousand|million)?", scenario_lower)
            new_assets = 500000
            if amounts:
                try:
                    new_assets = float(amounts[0].replace(",", ""))
                    if "million" in scenario_lower:
                        new_assets *= 1_000_000
                    elif "k" in scenario_lower or "thousand" in scenario_lower:
                        new_assets *= 1_000
                except ValueError:
                    pass
            projected_state["net_worth"] = current_state["net_worth"] + new_assets
            risks = [
                f"Federal estate tax on amounts over $13.61M (2024)",
                "State inheritance tax in some jurisdictions",
                "Family conflict over distribution",
                "Poor investment decisions under emotional stress",
            ]
            opportunities = [
                "Significant net worth increase",
                "Pay off high-interest debts",
                "Fund children's education (529 plans)",
                "Establish charitable giving vehicle",
                "Max out retirement contributions",
            ]
            recommended_actions = [
                "Consult a tax attorney before accepting inheritance",
                "Consider disclaimed inheritance if estate-tax-efficient",
                "Invest through a diversified portfolio",
                "Update estate plan to reflect new wealth",
                "Establish a revocable trust if not already done",
            ]

        elif "disabled" in scenario_lower or "disability" in scenario_lower:
            projected_state["monthly_income"] = current_state["monthly_income"] * 0.6
            risks = [
                "Loss of 40%+ of income without disability insurance",
                "No one to manage finances without Durable POA",
                "Healthcare costs may deplete assets",
                "Business interests unmanaged without succession plan",
            ]
            opportunities = [
                "SSDI benefits if qualifying disability",
                "Long-term disability insurance payout",
                "Medicaid planning to protect assets",
            ]
            recommended_actions = [
                "Execute a Durable Power of Attorney immediately",
                "Execute a Healthcare Proxy",
                "Review disability insurance coverage",
                "Create a special needs trust if applicable",
                "Set up business succession plan",
            ]

        elif "florida" in scenario_lower or "move" in scenario_lower or "relocate" in scenario_lower:
            state = "Florida"
            if "texas" in scenario_lower:
                state = "Texas"
            elif "nevada" in scenario_lower:
                state = "Nevada"
            risks = [
                f"Need to re-register business entities in {state}",
                "Estate planning documents may need updating for new jurisdiction",
                "Property tax implications of new state",
            ]
            opportunities = [
                f"No state income tax in {state}" if state in ("Florida", "Texas", "Nevada") else "State tax planning opportunities",
                "Florida homestead exemption (up to $500k protection from creditors)",
                "Cost of living adjustments",
            ]
            recommended_actions = [
                f"Establish legal domicile in {state} within 6 months",
                f"Update estate plan for {state} law",
                "Re-register vehicles and update licenses",
                "Review asset protection strategies in new state",
                "Consult a CPA about state tax implications",
            ]

        else:
            risks = ["Unknown scenario — consult an attorney for specific analysis"]
            recommended_actions = ["Schedule a consultation to analyze this specific scenario"]

        confidence = 0.75 if any(
            k in scenario_lower for k in ["business", "divorce", "inherit", "disabled", "florida", "texas"]
        ) else 0.5

        return ScenarioAnalysis(
            scenario=scenario,
            current_state=current_state,
            projected_state=projected_state,
            risks=risks,
            opportunities=opportunities,
            recommended_actions=recommended_actions,
            confidence_score=confidence,
        )

    # ------------------------------------------------------------------
    # Life Portfolio Export
    # ------------------------------------------------------------------

    def export_life_portfolio(self, user_id: str) -> LifePortfolio:
        """
        Export a complete life portfolio — the full SintraPrime life document package.
        Includes snapshot, risk report, estate report, and recommendations.
        """
        twin = self.load(user_id)
        if not twin:
            raise ValueError(f"No Digital Twin found for user {user_id}")

        snapshot = self.life_snapshot(user_id)
        risk_report = self.life_risk_assessment(user_id)
        estate_report = self.estate_readiness(user_id)
        recommendations = self.governance_recommendations(user_id)

        # Document manifest
        docs_manifest = []
        for d in twin.get("health_directives", []):
            name = d.get("title") if isinstance(d, dict) else d.title
            status = d.get("status") if isinstance(d, dict) else d.status
            docs_manifest.append(f"{name} [{status.upper()}]")

        for m in twin.get("legal_matters", []):
            title = m.get("title") if isinstance(m, dict) else m.title
            status = m.get("status") if isinstance(m, dict) else m.status
            docs_manifest.append(f"Legal Matter: {title} [{status.upper()}]")

        # Executive summary
        summary = (
            f"Life Portfolio for {twin.get('name', 'Unknown')} — "
            f"Risk Level: {risk_report.risk_level.upper()} ({risk_report.overall_risk_score}/100) | "
            f"Estate Readiness: {estate_report.readiness_level.replace('_', ' ').title()} ({estate_report.readiness_score}/100) | "
            f"Active Legal Matters: {len([m for m in twin.get('legal_matters', []) if (m.get('status') if isinstance(m, dict) else m.status) == 'active'])} | "
            f"Net Worth: ${snapshot.financial_profile.net_worth:,.2f}"
        )

        portfolio = LifePortfolio(
            user_id=user_id,
            name=twin.get("name", ""),
            generated_at=datetime.now().isoformat(),
            snapshot=snapshot,
            risk_report=risk_report,
            estate_report=estate_report,
            recommendations=recommendations,
            documents_manifest=docs_manifest,
            summary=summary,
        )

        # Save portfolio to disk
        portfolio_path = self._storage_dir / f"{user_id}_portfolio.json"
        portfolio_path.write_text(json.dumps({
            "user_id": user_id,
            "name": portfolio.name,
            "generated_at": portfolio.generated_at,
            "summary": summary,
            "risk_score": risk_report.overall_risk_score,
            "risk_level": risk_report.risk_level,
            "estate_readiness_score": estate_report.readiness_score,
            "estate_readiness_level": estate_report.readiness_level,
            "recommendations_count": len(recommendations),
            "documents_manifest": docs_manifest,
        }, indent=2))

        return portfolio

    # ------------------------------------------------------------------
    # Twin Management
    # ------------------------------------------------------------------

    def list_twins(self) -> List[Dict[str, str]]:
        """List all known digital twins."""
        twins = []
        for uid, data in self._twins.items():
            twins.append({
                "user_id": uid,
                "name": data.get("name", ""),
                "risk_score": str(data.get("risk_score", 0.0)),
                "estate_readiness": str(data.get("estate_readiness_score", 0.0)),
                "updated_at": data.get("updated_at", ""),
            })
        return twins

    def delete_twin(self, user_id: str) -> bool:
        """Delete a digital twin and its storage."""
        if user_id in self._twins:
            del self._twins[user_id]
        path = self._storage_dir / f"{user_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False
