"""
Life Command Center — Master Orchestrator for All Aspects of an Entity's Life
SintraPrime Life & Entity Governance Engine
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .entity_formation import EntityFormationEngine
from .estate_planning_engine import EstatePlanningEngine
from .asset_protection_system import AssetProtectionSystem
from .real_estate_intelligence import RealEstateIntelligence
from .personal_legal_advisor import PersonalLegalAdvisor


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------

@dataclass
class LifeProfile:
    """Comprehensive profile of a living entity."""
    name: str
    entity_type: str  # individual, family, small_business, corporation
    location: str
    age: Optional[int]
    assets: Dict[str, Any]
    liabilities: Dict[str, Any]
    income_sources: List[Dict[str, Any]]
    legal_matters: List[Dict[str, Any]]
    goals: List[str]
    risk_tolerance: str  # conservative, moderate, aggressive
    marital_status: str
    children: List[Dict[str, Any]]
    profession: str
    business_owner: bool
    net_worth: float
    annual_income: float
    existing_documents: List[str]
    insurance_coverage: Dict[str, Any]
    tax_situation: Dict[str, Any]


@dataclass
class LifeActionPlan:
    """Comprehensive life action plan across all domains."""
    profile_name: str
    immediate_actions: List[str]  # Do this week
    short_term: List[str]         # Next 90 days
    medium_term: List[str]        # 6-12 months
    long_term: List[str]          # 1-5 years
    estimated_value_created: float  # Money saved/made by following plan
    risk_reduced: str
    domain_priorities: Dict[str, List[str]]  # by domain: legal, financial, governance
    estimated_cost_to_implement: float
    professional_referrals: List[Dict[str, str]]


@dataclass
class ComprehensiveAuditReport:
    """Full-spectrum audit of a person's life governance status."""
    profile_name: str
    overall_score: int  # 0-100
    domain_scores: Dict[str, int]
    legal_vulnerabilities: List[str]
    financial_gaps: List[str]
    estate_planning_status: Dict[str, bool]
    asset_protection_score: int
    credit_health: str
    insurance_gaps: List[str]
    compliance_status: Dict[str, str]
    top_risks: List[str]
    quick_wins: List[str]
    estimated_total_risk_exposure: float


@dataclass
class UpdatedPlan:
    """Updated life plan after a life event."""
    life_event: str
    previous_plan_summary: str
    triggered_updates: List[str]
    new_immediate_actions: List[str]
    new_documents_needed: List[str]
    updated_beneficiaries: List[str]
    updated_entity_structure: Optional[str]
    tax_planning_triggered: List[str]
    urgency_level: str  # low, medium, high, critical


# ---------------------------------------------------------------------------
# Life Command Center
# ---------------------------------------------------------------------------

class LifeCommandCenter:
    """
    Master orchestrator that manages ALL aspects of a living entity's life.

    Integrates entity formation, estate planning, asset protection,
    real estate intelligence, and personal legal matters into a unified
    life governance system.
    """

    def __init__(self) -> None:
        self.entity_engine = EntityFormationEngine()
        self.estate_engine = EstatePlanningEngine()
        self.asset_protection = AssetProtectionSystem()
        self.real_estate = RealEstateIntelligence()
        self.personal_legal = PersonalLegalAdvisor()

    def onboard_entity(self, profile_data: dict) -> LifeProfile:
        """
        Process comprehensive intake questionnaire results and create a LifeProfile.

        Args:
            profile_data: Comprehensive dict from intake questionnaire

        Returns:
            LifeProfile with full situation analysis
        """
        # Extract and normalize all fields
        name = profile_data.get("name", "[ENTITY NAME]")
        entity_type = profile_data.get("entity_type", "individual")
        location = profile_data.get("location", profile_data.get("state", "CA"))
        age = profile_data.get("age")
        assets = profile_data.get("assets", {})
        liabilities = profile_data.get("liabilities", {})
        income_sources = profile_data.get("income_sources", [])
        legal_matters = profile_data.get("legal_matters", [])
        goals = profile_data.get("goals", [])
        risk_tolerance = profile_data.get("risk_tolerance", "moderate")
        marital_status = profile_data.get("marital_status", "single")
        children = profile_data.get("children", [])
        profession = profile_data.get("profession", "business_owner")
        business_owner = profile_data.get("business_owner", False)

        # Calculate net worth
        total_assets = sum(
            v if isinstance(v, (int, float)) else 0
            for v in assets.values()
        ) if assets else profile_data.get("total_assets", 0)

        total_liabilities = sum(
            v if isinstance(v, (int, float)) else 0
            for v in liabilities.values()
        ) if liabilities else profile_data.get("total_liabilities", 0)

        net_worth = profile_data.get("net_worth", total_assets - total_liabilities)

        # Calculate annual income
        if income_sources:
            annual_income = sum(
                s.get("annual_amount", s.get("monthly", 0) * 12)
                for s in income_sources
            )
        else:
            annual_income = profile_data.get("annual_income", 0)

        existing_docs = profile_data.get("existing_documents", [])
        insurance = profile_data.get("insurance_coverage", {})
        tax_situation = profile_data.get("tax_situation", {})

        return LifeProfile(
            name=name,
            entity_type=entity_type,
            location=location,
            age=age,
            assets=assets,
            liabilities=liabilities,
            income_sources=income_sources,
            legal_matters=legal_matters,
            goals=goals,
            risk_tolerance=risk_tolerance,
            marital_status=marital_status,
            children=children,
            profession=profession,
            business_owner=business_owner,
            net_worth=net_worth,
            annual_income=annual_income,
            existing_documents=existing_docs,
            insurance_coverage=insurance,
            tax_situation=tax_situation,
        )

    def generate_life_action_plan(self, profile: LifeProfile) -> LifeActionPlan:
        """
        Generate a comprehensive cross-domain life action plan.

        Analyzes legal, financial, governance, and personal needs to produce
        a prioritized action plan with estimated value created.

        Args:
            profile: LifeProfile from onboard_entity()

        Returns:
            LifeActionPlan with prioritized immediate and long-term actions
        """
        immediate: List[str] = []
        short_term: List[str] = []
        medium_term: List[str] = []
        long_term: List[str] = []
        domain_priorities: Dict[str, List[str]] = {
            "legal": [],
            "financial": [],
            "governance": [],
            "estate_planning": [],
            "asset_protection": [],
            "insurance": [],
            "real_estate": [],
        }
        value_created = 0.0
        risk_reduced_items = []

        has_will = "will" in " ".join(profile.existing_documents).lower()
        has_poa = "power of attorney" in " ".join(profile.existing_documents).lower()
        has_trust = "trust" in " ".join(profile.existing_documents).lower()
        has_umbrella = bool(profile.insurance_coverage.get("umbrella"))
        has_disability = bool(profile.insurance_coverage.get("disability"))

        # === LEGAL / ESTATE PLANNING ===
        if not has_will:
            immediate.append("⚡ Execute Last Will and Testament — die without one and the state decides who gets your assets")
            domain_priorities["estate_planning"].append("Execute Last Will and Testament (CRITICAL)")
            value_created += profile.net_worth * 0.05  # Avoid expensive probate

        if not has_poa:
            immediate.append("⚡ Execute Durable Financial Power of Attorney and Healthcare Power of Attorney — without these, family needs court order if you're incapacitated")
            domain_priorities["legal"].append("Powers of Attorney — Financial and Healthcare")

        if profile.net_worth > 200_000 and not has_trust:
            short_term.append("📋 Create Revocable Living Trust to avoid costly probate and maintain privacy")
            domain_priorities["estate_planning"].append("Revocable Living Trust — avoid probate")
            value_created += profile.net_worth * 0.03  # Avoid ~3% probate cost

        # === BUSINESS / ENTITY ===
        if profile.business_owner and not any("llc" in d.lower() or "corporation" in d.lower() for d in profile.existing_documents):
            immediate.append("🏢 Form LLC to separate personal assets from business liability — personal home and savings are at risk without it")
            domain_priorities["governance"].append("Form LLC for business operations")
            risk_reduced_items.append("Personal liability exposure from business")
            value_created += 50_000  # Estimated liability protection value

        if profile.business_owner and profile.annual_income > 40_000:
            short_term.append(f"💰 Consult CPA about S-Corp election — estimated annual tax savings: ${min(profile.annual_income * 0.08, 15_000):,.0f}")
            domain_priorities["financial"].append("S-Corp election analysis")
            value_created += min(profile.annual_income * 0.08, 15_000)

        # === INSURANCE ===
        if not has_umbrella:
            immediate.append("☂️ Purchase personal umbrella liability policy ($2M coverage costs ~$200-$400/year — protects your entire net worth)")
            domain_priorities["insurance"].append("Umbrella liability policy")
            risk_reduced_items.append("Uninsured liability claims")

        if not has_disability and profile.annual_income > 50_000:
            short_term.append(f"🏥 Purchase own-occupation disability insurance — your income of ${profile.annual_income:,.0f}/year is your most valuable asset")
            domain_priorities["insurance"].append("Disability insurance")
            risk_reduced_items.append("Income loss from disability")

        # === ASSET PROTECTION ===
        if profile.net_worth > 500_000:
            short_term.append("🛡️ Conduct asset protection analysis — structure assets to minimize creditor exposure")
            domain_priorities["asset_protection"].append("Asset protection structure review")

        if profile.marital_status == "married" and not any("prenup" in d.lower() or "postnup" in d.lower() for d in profile.existing_documents) and profile.net_worth > 200_000:
            medium_term.append("💍 Consider postnuptial agreement to clarify asset ownership and protect pre-marital assets")
            domain_priorities["legal"].append("Postnuptial agreement")

        # === RETIREMENT / FINANCIAL ===
        if profile.annual_income > 0:
            short_term.append(f"📈 Maximize 401(k)/retirement contributions (${23_000:,}/year; up to ${69_000:,} with profit sharing) — unlimited creditor protection + tax deferral")
            domain_priorities["financial"].append("Maximize retirement contributions")
            value_created += profile.annual_income * 0.25 * 0.25  # Rough tax savings estimate

        # === ESTATE TAX ===
        if profile.net_worth > 11_000_000:
            medium_term.append(f"💸 Begin estate tax planning — potential exposure: ${max(0, profile.net_worth - 13_610_000) * 0.40:,.0f}. Start annual gifting program and GRAT strategy.")
            domain_priorities["estate_planning"].append("Estate tax minimization (GRAT, ILIT, annual gifting)")
            value_created += max(0, profile.net_worth - 13_610_000) * 0.40 * 0.30  # Potential savings

        # === BOI COMPLIANCE ===
        if profile.business_owner:
            immediate.append("📋 File Beneficial Ownership Information (BOI) report with FinCEN — penalties: $591/day for non-compliance")
            domain_priorities["governance"].append("BOI Report filing (FinCEN CTA compliance)")

        # === LIFE EVENTS ===
        if profile.children and any(c.get("age", 18) < 18 for c in profile.children):
            immediate.append("👶 Designate guardian for minor children in your Will — most critical if you have young children")
            short_term.append("📑 Create testamentary trust for minor children to control distribution age (recommend age 25)")

        if profile.age and profile.age >= 50 and not any("ltc" in d.lower() or "long term care" in d.lower() for d in profile.existing_documents):
            medium_term.append("🏥 Evaluate long-term care insurance — premiums 3x lower at 55 than 65. Consider hybrid life/LTC policy.")

        # === BENEFICIARY DESIGNATIONS ===
        short_term.append("📌 Review and update ALL beneficiary designations (retirement accounts, life insurance, TOD accounts) — these override your Will")
        domain_priorities["estate_planning"].append("Update beneficiary designations")

        # === CREDIT MONITORING ===
        long_term.append("📊 Annual credit report review (AnnualCreditReport.com) and net worth calculation")
        long_term.append("⚖️ Annual estate plan review — update after marriage, divorce, birth, death, or major asset change")
        long_term.append("🏢 Annual compliance calendar review — ensure all entities current on annual reports, BOI updates, tax filings")

        # Professional referrals
        referrals = []
        if not has_will or not has_trust:
            referrals.append({"type": "Estate Planning Attorney", "when": "Immediately", "estimated_cost": "$2,000-$5,000"})
        if profile.business_owner:
            referrals.append({"type": "Business Attorney (Business Formation)", "when": "This week", "estimated_cost": "$500-$2,000"})
            referrals.append({"type": "CPA (Business Tax Planning)", "when": "This quarter", "estimated_cost": "$1,500-$5,000/year"})
        if profile.net_worth > 1_000_000:
            referrals.append({"type": "Asset Protection Attorney", "when": "This quarter", "estimated_cost": "$3,000-$10,000"})
        if not has_disability:
            referrals.append({"type": "Independent Insurance Broker", "when": "This month", "estimated_cost": "No fee (broker paid by insurer)"})

        risk_reduced_summary = (
            f"Implementing this plan reduces key risks: {'; '.join(risk_reduced_items[:4])}. "
            f"Overall risk profile improves from {'High' if profile.net_worth > 500_000 and not has_will else 'Medium'} to Low."
        )

        return LifeActionPlan(
            profile_name=profile.name,
            immediate_actions=immediate,
            short_term=short_term,
            medium_term=medium_term,
            long_term=long_term,
            estimated_value_created=round(value_created, 2),
            risk_reduced=risk_reduced_summary,
            domain_priorities=domain_priorities,
            estimated_cost_to_implement=sum([
                3500 if not has_will else 0,
                1000 if not has_poa else 0,
                5000 if not has_trust and profile.net_worth > 200_000 else 0,
                500 if profile.business_owner else 0,
                300 if not has_umbrella else 0,
                2000 if not has_disability else 0,
            ]),
            professional_referrals=referrals,
        )

    def comprehensive_audit(self, profile: LifeProfile) -> ComprehensiveAuditReport:
        """
        Perform a full-spectrum audit of a person's life governance status.

        Args:
            profile: LifeProfile to audit

        Returns:
            ComprehensiveAuditReport with scores and recommendations
        """
        domain_scores: Dict[str, int] = {}

        # Estate planning score
        estate_score = 0
        estate_status = {
            "has_will": any("will" in d.lower() for d in profile.existing_documents),
            "has_trust": any("trust" in d.lower() for d in profile.existing_documents),
            "has_financial_poa": any("power of attorney" in d.lower() or "poa" in d.lower() for d in profile.existing_documents),
            "has_healthcare_poa": any("healthcare" in d.lower() and "power" in d.lower() for d in profile.existing_documents),
            "has_advance_directive": any("advance directive" in d.lower() or "living will" in d.lower() for d in profile.existing_documents),
            "beneficiaries_updated": profile.assets.get("beneficiaries_updated", False),
        }
        estate_score = sum(25 if k in ["has_will", "has_trust"] else 15 for k, v in estate_status.items() if v)
        domain_scores["estate_planning"] = min(100, estate_score)

        # Asset protection score
        ap_score = 50  # baseline
        if profile.insurance_coverage.get("umbrella"):
            ap_score += 20
        if any("llc" in d.lower() for d in profile.existing_documents) and profile.business_owner:
            ap_score += 20
        if profile.insurance_coverage.get("professional_liability"):
            ap_score += 10
        domain_scores["asset_protection"] = min(100, ap_score)

        # Insurance score
        ins_score = 0
        if profile.insurance_coverage.get("health"):
            ins_score += 30
        if profile.insurance_coverage.get("life"):
            ins_score += 20
        if profile.insurance_coverage.get("disability"):
            ins_score += 25
        if profile.insurance_coverage.get("umbrella"):
            ins_score += 15
        if profile.insurance_coverage.get("auto"):
            ins_score += 10
        domain_scores["insurance"] = min(100, ins_score)

        # Compliance score
        compliance_score = 70  # assume mostly compliant
        boi_filed = profile.existing_documents and any("boi" in d.lower() for d in profile.existing_documents)
        if profile.business_owner and not boi_filed:
            compliance_score -= 30
        domain_scores["compliance"] = compliance_score

        # Financial / governance score
        fin_score = 60
        if profile.net_worth > 0:
            fin_score += 10
        if profile.annual_income > 0 and profile.assets.get("retirement", 0) > profile.annual_income:
            fin_score += 20
        domain_scores["financial"] = min(100, fin_score)

        overall = int(sum(domain_scores.values()) / len(domain_scores))

        # Vulnerabilities and gaps
        legal_vulnerabilities = []
        if not estate_status["has_will"]:
            legal_vulnerabilities.append("❌ No Will — intestate succession laws will distribute your assets")
        if not estate_status["has_financial_poa"]:
            legal_vulnerabilities.append("❌ No Durable Power of Attorney — family needs court order if you're incapacitated")
        if profile.business_owner and not any("llc" in d.lower() for d in profile.existing_documents):
            legal_vulnerabilities.append("❌ No business entity — personal assets exposed to business liabilities")

        financial_gaps = []
        if not profile.insurance_coverage.get("disability"):
            financial_gaps.append(f"❌ No disability insurance — ${profile.annual_income:,.0f}/year income unprotected")
        if not profile.assets.get("emergency_fund"):
            financial_gaps.append("❌ Emergency fund not verified — recommend 3-6 months expenses liquid")
        if not profile.assets.get("retirement"):
            financial_gaps.append("❌ No retirement savings identified — maximize 401(k)/IRA immediately")

        insurance_gaps = []
        for coverage_type in ["umbrella", "disability", "life", "health"]:
            if not profile.insurance_coverage.get(coverage_type):
                insurance_gaps.append(f"Missing: {coverage_type.replace('_', ' ').title()} Insurance")

        total_risk_exposure = 0.0
        if not estate_status["has_will"]:
            total_risk_exposure += profile.net_worth * 0.05  # probate cost
        if not profile.insurance_coverage.get("umbrella"):
            total_risk_exposure += profile.net_worth * 0.10  # liability exposure
        if profile.business_owner and not any("llc" in d.lower() for d in profile.existing_documents):
            total_risk_exposure += profile.net_worth * 0.30  # business liability

        quick_wins = [
            "File for homestead exemption (free — 5 min online)",
            "Add beneficiary designation to all retirement/life accounts (free)",
            "Register at donotcall.gov to reduce robocalls (free)",
            "Freeze credit at all 3 bureaus (free — identity theft protection)",
            "Enable 2FA on all financial accounts (free)",
            "Create free IRS account at irs.gov and set IP PIN (free)",
        ]

        return ComprehensiveAuditReport(
            profile_name=profile.name,
            overall_score=overall,
            domain_scores=domain_scores,
            legal_vulnerabilities=legal_vulnerabilities,
            financial_gaps=financial_gaps,
            estate_planning_status=estate_status,
            asset_protection_score=domain_scores["asset_protection"],
            credit_health="Pull credit report at AnnualCreditReport.com to assess",
            insurance_gaps=insurance_gaps,
            compliance_status={
                "boi_report": "Filed" if boi_filed else ("Required — file at fincen.gov/boi" if profile.business_owner else "N/A"),
                "business_licenses": "Review local requirements",
                "tax_filings": "Assume current unless flagged",
            },
            top_risks=[v for v in legal_vulnerabilities + financial_gaps + insurance_gaps][:5],
            quick_wins=quick_wins,
            estimated_total_risk_exposure=total_risk_exposure,
        )

    def monitor_life_changes(self, profile: LifeProfile, changes: dict) -> UpdatedPlan:
        """
        Update recommendations when life circumstances change.

        Life event triggers: marriage, divorce, birth, death, business_sale,
        job_loss, inheritance, lawsuit, moving_states, serious_illness

        Args:
            profile: Current LifeProfile
            changes: dict with 'event_type', 'details', and any relevant data

        Returns:
            UpdatedPlan with triggered actions based on the life event
        """
        event_type = changes.get("event_type", "").lower()
        details = changes.get("details", {})

        triggered_updates: List[str] = []
        new_immediate: List[str] = []
        new_documents: List[str] = []
        updated_beneficiaries: List[str] = []
        tax_planning: List[str] = []
        urgency = "medium"

        if event_type == "marriage":
            urgency = "high"
            triggered_updates = [
                "Revoke and replace existing Will (marriage may revoke prior Will in many states)",
                "Execute new Durable POA naming spouse",
                "Execute new Healthcare POA naming spouse",
                "Consider Revocable Living Trust (joint trust)",
                "Update all beneficiary designations to include spouse",
                "Review title to real estate (add spouse or title as Tenancy by the Entirety)",
                "File joint tax return for first time (evaluate married filing jointly vs. separately)",
                "Review and update life insurance beneficiaries",
                "Consider prenuptial/postnuptial agreement if assets or business interests involved",
            ]
            new_documents = ["Updated Last Will and Testament", "Joint Living Trust", "Updated Powers of Attorney", "Marriage Certificate (copy for records)"]
            updated_beneficiaries = ["Spouse designated as primary beneficiary on all accounts"]
            tax_planning = ["Evaluate married filing jointly vs. separately", "Review Social Security strategy", "Review health insurance options (join spouse's plan?)"]
            new_immediate = ["Update beneficiary designations within 30 days", "Execute new Will and POA immediately"]

        elif event_type == "divorce":
            urgency = "critical"
            triggered_updates = [
                "IMMEDIATE: Remove ex-spouse as beneficiary from all accounts",
                "IMMEDIATE: Revoke any POA naming ex-spouse",
                "Execute new Will — divorce may automatically revoke gifts to ex-spouse but don't rely on this",
                "File QDRO (Qualified Domestic Relations Order) if dividing retirement accounts",
                "Update title to real property per divorce decree",
                "Close joint bank and credit accounts",
                "Remove ex-spouse from LLC/business documents",
                "Review and update all insurance policies",
                "Update estate plan to reflect new single status",
            ]
            new_documents = ["New Last Will and Testament", "New Powers of Attorney", "New Healthcare Directive", "QDRO (if applicable)"]
            updated_beneficiaries = ["URGENT: Remove ex-spouse from all beneficiary designations"]
            tax_planning = ["Change to single or head of household filing status", "Review alimony tax treatment (post-2018 divorce — not deductible)", "Evaluate retirement account tax impact of division"]
            new_immediate = ["Remove ex-spouse as beneficiary TODAY", "Revoke POA naming ex-spouse TODAY", "Change passwords on all financial accounts TODAY"]

        elif event_type == "birth" or event_type == "adoption":
            urgency = "high"
            triggered_updates = [
                "Update Will to include new child and name guardian",
                "Establish testamentary trust or living trust for minor child",
                "Update all beneficiary designations",
                "Consider 529 education savings plan (contributions grow tax-free)",
                "Review life insurance — additional dependent increases income replacement need",
                "Review disability insurance",
                "Name a guardian in your Will NOW (most urgent task)",
            ]
            new_documents = ["Updated Will with guardianship designation", "529 Plan account", "Updated beneficiary forms"]
            updated_beneficiaries = ["Add child as contingent beneficiary"]
            tax_planning = ["Child tax credit ($2,000/year)", "Dependent care FSA ($5,000/year pre-tax)", "529 superfunding option", "Earned Income Tax Credit if income qualifies"]
            new_immediate = ["Update Will with guardian designation within 30 days", "Open 529 plan"]

        elif event_type == "death":
            urgency = "critical"
            deceased = details.get("deceased", "family member")
            triggered_updates = [
                f"IMMEDIATE: Do not pay any debts of deceased until estate is assessed — some debts die with the person",
                "Locate original Will and deliver to probate court",
                "File for Letters Testamentary (executor authority) with probate court",
                "File for Letters of Administration if no Will",
                "Notify Social Security Administration within 30 days",
                "File final income tax return for deceased",
                "File estate tax return (Form 706) if estate exceeds exemption",
                "CRITICAL: File portability election on Form 706 even if no estate tax (protects surviving spouse's exemption)",
                "Transfer assets per Will/Trust/beneficiary designations",
                "Update survivor's estate plan (survivor needs new plan)",
            ]
            new_documents = ["Letters Testamentary/Administration", "Form 706 (estate tax return)", "Updated survivor's estate plan"]
            updated_beneficiaries = [f"Update all accounts to reflect death of {deceased}"]
            tax_planning = ["Step-up in basis for inherited assets (eliminates capital gains on appreciation)", "Portability election — preserve deceased spouse's exemption", "File Form 706 within 9 months of death"]
            new_immediate = ["Locate Will and notify probate court", "Notify SSA of death", "Do not pay debts until advised by estate attorney"]

        elif event_type == "business_sale":
            urgency = "high"
            triggered_updates = [
                "MAJOR CAPITAL GAINS EVENT — coordinate with CPA before closing",
                "Evaluate installment sale to spread gain over multiple years",
                "Consider opportunity zone investment for deferral",
                "Evaluate Qualified Small Business Stock (QSBS) exclusion if applicable (up to 100% exclusion)",
                "Charitable planning: Donor Advised Fund to offset income in year of sale",
                "Post-sale estate planning: Net worth increase triggers new estate tax analysis",
                "Update entity structure — operating LLC no longer needed",
                "Wind down or dissolve business entities properly",
            ]
            tax_planning = ["QSBS Section 1202 exclusion (up to 100% of gain excluded if C-Corp, held 5+ years)", "Installment sale to spread gain", "Opportunity Zone investment", "Charitable Remainder Trust", "Review state tax implications"]
            new_immediate = ["Consult CPA BEFORE signing any sale documents", "Evaluate tax structure of sale (asset sale vs. stock sale)"]

        elif event_type == "inheritance":
            urgency = "medium"
            triggered_updates = [
                "Document date-of-death value for step-up in basis calculation",
                "Inherited IRA rules: Must take RMDs within 10 years (if non-spouse beneficiary)",
                "Evaluate whether to accept or disclaim inheritance (if better for estate tax planning)",
                "Update estate plan to reflect increased net worth",
                "Evaluate asset protection strategies for inherited funds",
                "Inherited retirement accounts: Do NOT roll to your own IRA (separate 'Inherited IRA')",
            ]
            tax_planning = ["Step-up in basis eliminates prior appreciation", "Inherited IRA 10-year distribution rule", "Potential estate tax on inherited estate if large enough", "Gifts from inheritance subject to gift tax reporting if >$18K/recipient"]
            new_immediate = ["Open separate inherited IRA (do not commingle with your own)", "Document date-of-death values"]

        elif event_type == "lawsuit":
            urgency = "critical"
            triggered_updates = [
                "IMMEDIATE: Do NOT transfer assets — fraudulent conveyance laws can void transfers made to avoid creditors",
                "IMMEDIATE: Notify all relevant insurance carriers",
                "IMMEDIATE: Retain litigation attorney",
                "Do NOT discuss case on social media",
                "Document and preserve all evidence",
                "Review all insurance coverage limits",
                "Existing asset protection structures are now LOCKED IN — new transfers suspect",
            ]
            new_immediate = ["Contact insurance carrier immediately", "Retain litigation attorney TODAY", "Do NOT move any assets"]

        elif event_type == "moving_states":
            urgency = "medium"
            new_state = details.get("new_state", "")
            triggered_updates = [
                f"Update domicile to {new_state} (change driver's license, voter registration, file Declaration of Domicile)",
                "Review Will and Trust — state-specific provisions may need updating",
                "Update LLC registered agent (register as foreign entity in new state)",
                "Review homestead exemption changes",
                f"Review state income tax implications of moving to {new_state}",
                "Update car title, registration, insurance to new state",
                "Review non-compete enforceability change",
            ]
            tax_planning = [f"State income tax in {new_state}", "Establish new state residency to avoid exit audit from prior state", "File final return in old state; first return in new state"]

        elif event_type == "job_loss":
            urgency = "high"
            triggered_updates = [
                "File for unemployment compensation IMMEDIATELY (file same day as termination)",
                "Evaluate COBRA health insurance vs marketplace (marketplace within 60-day special enrollment)",
                "Do NOT cash out 401(k) — rollover to IRA (preserve retirement savings and avoid taxes/penalties)",
                "Review non-compete restrictions before seeking new employment",
                "Evaluate severance agreement with employment attorney before signing",
                "Update emergency fund strategy",
                "Review and reduce discretionary expenses",
            ]
            new_immediate = ["File for unemployment today", "Compare COBRA vs marketplace health insurance (60-day window)", "Roll 401(k) to IRA — do NOT cash out"]
            tax_planning = ["Unemployment is taxable income", "COBRA premiums not deductible unless itemizing", "Consider Roth conversion in low-income year"]

        elif event_type == "serious_illness":
            urgency = "critical"
            triggered_updates = [
                "IMMEDIATE: Execute or update Healthcare POA",
                "IMMEDIATE: Execute Advance Healthcare Directive / Living Will",
                "IMMEDIATE: Execute Financial POA",
                "Complete and sign POLST form with physician",
                "Review and update beneficiary designations",
                "Confirm Will and Trust are current",
                "Consider Medicaid planning if long-term care anticipated",
                "Review life insurance (accelerated death benefit riders)",
            ]
            new_documents = ["Healthcare POA", "Advance Directive / Living Will", "POLST Form", "Updated Financial POA"]
            new_immediate = ["Execute POA documents TODAY", "Complete POLST with doctor TODAY", "Notify trusted family members of plan locations"]

        else:
            triggered_updates = ["Life event noted — review your estate plan and consult your advisors"]
            new_immediate = ["Schedule review with estate planning attorney"]

        return UpdatedPlan(
            life_event=event_type,
            previous_plan_summary=f"Prior plan for {profile.name} — net worth ${profile.net_worth:,.0f}",
            triggered_updates=triggered_updates,
            new_immediate_actions=new_immediate,
            new_documents_needed=new_documents,
            updated_beneficiaries=updated_beneficiaries,
            updated_entity_structure=None,
            tax_planning_triggered=tax_planning,
            urgency_level=urgency,
        )
