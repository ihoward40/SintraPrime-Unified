"""
Asset Protection System — Comprehensive Protection from Creditors, Lawsuits, and Government
SintraPrime Life & Entity Governance Engine
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------

@dataclass
class VulnerabilityReport:
    """Assessment of a person's asset vulnerability to creditors and lawsuits."""
    overall_risk_level: str  # Low, Medium, High, Extreme
    profession_risk_score: int  # 1-10
    unprotected_assets: List[Dict[str, Any]]
    protected_assets: List[Dict[str, Any]]
    total_exposed_value: float
    priority_protection_needs: List[str]
    immediate_actions: List[str]
    risk_factors: List[str]


@dataclass
class AssetProtectionPlan:
    """Comprehensive asset protection strategy."""
    total_assets: float
    currently_protected: float
    protection_gap: float
    strategies: List[Dict[str, Any]]
    exemption_strategy: str
    entity_strategy: str
    insurance_layer: str
    estimated_implementation_cost: float
    estimated_protection_value: float
    implementation_steps: List[str]


@dataclass
class HomesteadAnalysis:
    """Homestead exemption analysis."""
    state: str
    home_value: float
    homestead_exemption: float
    protected_amount: float
    unprotected_amount: float
    unlimited_exemption: bool
    requirements: str
    how_to_claim: str
    strategies_to_maximize: List[str]


@dataclass
class RetirementProtectionGuide:
    """Guide to retirement account asset protection."""
    erisa_qualified_plans: str
    ira_protection_by_state: Dict[str, str]
    roth_vs_traditional_analysis: str
    self_directed_strategies: str
    recommended_actions: List[str]


@dataclass
class OffshoreStrategy:
    """Legal offshore asset protection strategy."""
    recommended_structures: List[Dict[str, str]]
    fbar_requirements: str
    form_8938_requirements: str
    pfic_rules: str
    compliance_checklist: List[str]
    cost_estimate: float
    risk_assessment: str


@dataclass
class InsuranceStrategy:
    """Comprehensive insurance optimization strategy."""
    coverage_gaps: List[Dict[str, Any]]
    umbrella_recommendation: Dict[str, Any]
    professional_liability: Dict[str, Any]
    life_insurance_analysis: Dict[str, Any]
    disability_insurance: Dict[str, Any]
    long_term_care: Dict[str, Any]
    business_insurance: Dict[str, Any]
    total_annual_premium_estimate: float
    priority_additions: List[str]


# ---------------------------------------------------------------------------
# Homestead Exemptions by State
# ---------------------------------------------------------------------------

HOMESTEAD_EXEMPTIONS: Dict[str, Any] = {
    "AL": {"amount": 15000, "unlimited": False, "notes": ""},
    "AK": {"amount": 72900, "unlimited": False, "notes": ""},
    "AZ": {"amount": 250000, "unlimited": False, "notes": ""},
    "AR": {"amount": 2500, "unlimited": False, "notes": "Rural 80 acres or 1/4 acre urban unlimited from forced sale"},
    "CA": {"amount": 300000, "unlimited": False, "notes": "$300K-$600K depending on median home value in county"},
    "CO": {"amount": 250000, "unlimited": False, "notes": "$350K if 60+ or disabled"},
    "CT": {"amount": 75000, "unlimited": False, "notes": ""},
    "DE": {"amount": 0, "unlimited": False, "notes": "No homestead exemption"},
    "FL": {"amount": None, "unlimited": True, "notes": "Unlimited — must be Florida resident; 160 acres rural, 1/2 acre urban"},
    "GA": {"amount": 21500, "unlimited": False, "notes": ""},
    "HI": {"amount": 30000, "unlimited": False, "notes": "$60K if 65+"},
    "ID": {"amount": 100000, "unlimited": False, "notes": ""},
    "IL": {"amount": 15000, "unlimited": False, "notes": "$30K if jointly owned"},
    "IN": {"amount": 19300, "unlimited": False, "notes": ""},
    "IA": {"amount": None, "unlimited": True, "notes": "Unlimited — 1/2 acre urban, 40 acres rural"},
    "KS": {"amount": None, "unlimited": True, "notes": "Unlimited — 1 acre urban, 160 acres rural"},
    "KY": {"amount": 5000, "unlimited": False, "notes": ""},
    "LA": {"amount": 35000, "unlimited": False, "notes": ""},
    "ME": {"amount": 80000, "unlimited": False, "notes": "$160K if minor dependents"},
    "MD": {"amount": 0, "unlimited": False, "notes": "No homestead exemption for creditor protection"},
    "MA": {"amount": 500000, "unlimited": False, "notes": "Automatic $125K; file declaration for $500K"},
    "MI": {"amount": None, "unlimited": True, "notes": "Unlimited — cannot be forced to sell primary residence to satisfy most debts"},
    "MN": {"amount": 450000, "unlimited": False, "notes": ""},
    "MS": {"amount": 75000, "unlimited": False, "notes": ""},
    "MO": {"amount": 15000, "unlimited": False, "notes": ""},
    "MT": {"amount": 350000, "unlimited": False, "notes": ""},
    "NE": {"amount": 60000, "unlimited": False, "notes": ""},
    "NV": {"amount": 605000, "unlimited": False, "notes": ""},
    "NH": {"amount": 120000, "unlimited": False, "notes": ""},
    "NJ": {"amount": 0, "unlimited": False, "notes": "No homestead exemption"},
    "NM": {"amount": 60000, "unlimited": False, "notes": ""},
    "NY": {"amount": 89975, "unlimited": False, "notes": "Varies by county; up to $170K in some metro areas"},
    "NC": {"amount": 35000, "unlimited": False, "notes": "$60K if 65+"},
    "ND": {"amount": 100000, "unlimited": False, "notes": ""},
    "OH": {"amount": 161375, "unlimited": False, "notes": ""},
    "OK": {"amount": None, "unlimited": True, "notes": "Unlimited — 1 acre urban, 160 acres rural"},
    "OR": {"amount": 40000, "unlimited": False, "notes": "$50K if jointly owned"},
    "PA": {"amount": 0, "unlimited": False, "notes": "No homestead exemption"},
    "RI": {"amount": 500000, "unlimited": False, "notes": ""},
    "SC": {"amount": 63075, "unlimited": False, "notes": ""},
    "SD": {"amount": None, "unlimited": True, "notes": "Unlimited"},
    "TN": {"amount": 25000, "unlimited": False, "notes": "$50K if 62+ or disabled"},
    "TX": {"amount": None, "unlimited": True, "notes": "Unlimited — 10 acres urban, 100 acres rural (200 for family)"},
    "UT": {"amount": 30000, "unlimited": False, "notes": ""},
    "VT": {"amount": 125000, "unlimited": False, "notes": ""},
    "VA": {"amount": 25000, "unlimited": False, "notes": ""},
    "WA": {"amount": 125000, "unlimited": False, "notes": ""},
    "WV": {"amount": 25000, "unlimited": False, "notes": ""},
    "WI": {"amount": 75000, "unlimited": False, "notes": ""},
    "WY": {"amount": 20000, "unlimited": False, "notes": ""},
}

# IRA protection by state (approximate)
IRA_PROTECTION_BY_STATE: Dict[str, str] = {
    "AK": "Unlimited",
    "AZ": "Unlimited (up to $150K Roth, unlimited traditional)",
    "CA": "Limited — only amounts necessary for support",
    "CO": "Unlimited",
    "CT": "Unlimited",
    "FL": "Unlimited",
    "GA": "Unlimited",
    "IL": "Unlimited",
    "IN": "Unlimited",
    "KS": "Unlimited",
    "KY": "Unlimited",
    "MA": "Unlimited",
    "MN": "Unlimited (reasonable amounts)",
    "MO": "Unlimited",
    "MT": "Unlimited",
    "NV": "Unlimited",
    "NJ": "Unlimited (IRAs not in ERISA plan — state law protects)",
    "NY": "Unlimited (traditional IRA); $1,000,000 Roth",
    "NC": "Unlimited",
    "OH": "Unlimited",
    "OK": "Unlimited",
    "OR": "Unlimited",
    "PA": "Unlimited",
    "TN": "Unlimited",
    "TX": "Unlimited",
    "VA": "Unlimited (with exceptions)",
    "WA": "Unlimited",
    "WY": "Unlimited",
    "DEFAULT": "Limited — typically $1,362,800 federal bankruptcy exemption; state law varies",
}


# ---------------------------------------------------------------------------
# Asset Protection System
# ---------------------------------------------------------------------------

class AssetProtectionSystem:
    """
    Comprehensive asset protection engine.

    Analyzes vulnerability to creditors and lawsuits, and develops
    multi-layer protection strategies using exemptions, entities,
    trusts, and insurance.
    """

    # Lawsuit risk by profession (1-10 scale)
    PROFESSION_RISK: Dict[str, int] = {
        "surgeon": 10,
        "obstetrician": 10,
        "anesthesiologist": 9,
        "physician": 8,
        "attorney": 7,
        "financial_advisor": 7,
        "accountant": 6,
        "architect": 7,
        "engineer": 6,
        "real_estate_agent": 5,
        "contractor": 6,
        "business_owner": 5,
        "executive": 6,
        "pharmacist": 5,
        "dentist": 6,
        "therapist": 5,
        "teacher": 2,
        "software_engineer": 3,
        "accountant_cpa": 6,
        "nurse": 5,
        "truck_driver": 6,
        "pilot": 7,
        "default": 4,
    }

    def vulnerability_assessment(self, profile: dict) -> VulnerabilityReport:
        """
        Assess a person's vulnerability to creditor claims and lawsuits.

        Args:
            profile: dict with 'profession', 'state', 'assets' (list of dicts),
                     'net_worth', 'marital_status', 'business_owner'
        """
        profession = profile.get("profession", "default").lower()
        state = profile.get("state", "CA")
        assets = profile.get("assets", [])
        net_worth = profile.get("net_worth", 500_000)
        marital_status = profile.get("marital_status", "single")
        business_owner = profile.get("business_owner", False)

        risk_score = self.PROFESSION_RISK.get(profession, self.PROFESSION_RISK["default"])

        if business_owner:
            risk_score = min(10, risk_score + 1)

        # Assess assets
        unprotected = []
        protected = []
        total_exposed = 0.0

        homestead_data = HOMESTEAD_EXEMPTIONS.get(state, {})
        homestead_amount = homestead_data.get("amount", 25000) if not homestead_data.get("unlimited") else float("inf")

        for asset in assets:
            asset_type = asset.get("type", "").lower()
            value = asset.get("value", 0)

            if asset_type in ["401k", "pension", "erisa_plan"]:
                protected.append({**asset, "protection": "ERISA — unlimited federal protection"})
            elif asset_type == "ira":
                ira_prot = IRA_PROTECTION_BY_STATE.get(state, IRA_PROTECTION_BY_STATE["DEFAULT"])
                protected.append({**asset, "protection": f"IRA: {ira_prot}"})
            elif asset_type in ["life_insurance_cash_value"]:
                protected.append({**asset, "protection": "Life insurance CSV — protected in most states"})
            elif asset_type in ["primary_home", "home", "residence"]:
                if homestead_data.get("unlimited"):
                    protected.append({**asset, "protection": f"{state} unlimited homestead exemption"})
                elif value <= homestead_amount:
                    protected.append({**asset, "protection": f"Homestead exemption — ${homestead_amount:,.0f}"})
                else:
                    exposed = value - homestead_amount
                    unprotected.append({**asset, "exposed_amount": exposed, "reason": f"Home equity above ${homestead_amount:,.0f} exemption"})
                    total_exposed += exposed
            elif asset_type in ["business_llc", "llc_interest"]:
                protected.append({**asset, "protection": "LLC liability shield (inside assets)"})
            else:
                unprotected.append({**asset, "exposed_amount": value, "reason": "No current protection"})
                total_exposed += value

        risk_level_map = {
            (1, 3): "Low",
            (4, 5): "Medium",
            (6, 7): "High",
            (8, 10): "Extreme",
        }
        risk_level = next((v for (lo, hi), v in risk_level_map.items() if lo <= risk_score <= hi), "Medium")

        risk_factors = []
        if risk_score >= 7:
            risk_factors.append(f"High-risk profession ({profession}) — above-average lawsuit exposure")
        if business_owner:
            risk_factors.append("Business owner — contract disputes, employee claims, customer liability")
        if marital_status == "divorced":
            risk_factors.append("Prior divorce — potential alimony or child support enforcement actions")
        if total_exposed > 500_000:
            risk_factors.append(f"Significant unprotected wealth — ${total_exposed:,.0f} exposed to creditors")

        priority_needs = []
        if total_exposed > 0:
            priority_needs.append(f"Protect ${total_exposed:,.0f} in exposed assets immediately")
        if risk_score >= 7:
            priority_needs.append("Professional liability insurance (malpractice/E&O)")
            priority_needs.append("Umbrella liability policy ($2M+ coverage)")
        if not any(a.get("type") in ["llc_interest", "business_llc"] for a in assets) and business_owner:
            priority_needs.append("Form LLC to separate business from personal assets")

        return VulnerabilityReport(
            overall_risk_level=risk_level,
            profession_risk_score=risk_score,
            unprotected_assets=unprotected,
            protected_assets=protected,
            total_exposed_value=total_exposed,
            priority_protection_needs=priority_needs,
            immediate_actions=[
                "1. Maximize contributions to ERISA-qualified retirement plans (100% protected)",
                "2. Claim homestead exemption (file declaration if required by state)",
                "3. Review and update umbrella liability insurance",
                "4. Ensure all business activities are conducted through an LLC or corporation",
                "5. Separate business and personal finances completely",
            ],
            risk_factors=risk_factors,
        )

    def protection_strategy(self, profile: dict) -> AssetProtectionPlan:
        """
        Develop a comprehensive asset protection plan.

        Args:
            profile: dict with 'net_worth', 'state', 'profession', 'married',
                     'assets', 'has_business', 'risk_tolerance'
        """
        net_worth = profile.get("net_worth", 1_000_000)
        state = profile.get("state", "CA")
        profession = profile.get("profession", "business_owner")
        married = profile.get("married", False)
        has_business = profile.get("has_business", True)
        risk_score = self.PROFESSION_RISK.get(profession.lower(), 4)

        strategies: List[Dict[str, Any]] = []

        # Layer 1: Exemption planning
        homestead_data = HOMESTEAD_EXEMPTIONS.get(state, {})
        strategies.append({
            "layer": "Layer 1 — Exemption Planning",
            "name": "Maximize State Exemptions",
            "actions": [
                f"File homestead declaration (protects up to ${homestead_data.get('amount', 'unlimited'):,})",
                "Max out 401(k)/pension contributions ($23,000/year employee + up to $69,000 total)",
                "Fund life insurance with cash value component (protected in most states)",
                "Understand your state's IRA protection: " + IRA_PROTECTION_BY_STATE.get(state, IRA_PROTECTION_BY_STATE["DEFAULT"]),
            ],
            "cost": 0,
            "protection_value": 500_000,
        })

        # Layer 2: Entity-based protection
        if has_business:
            strategies.append({
                "layer": "Layer 2 — Entity-Based Protection",
                "name": "LLC / Corporation Structure",
                "actions": [
                    "Form Wyoming LLC as holding company",
                    "Ensure all business activities in separate operating LLC",
                    "Separate real estate into standalone LLCs",
                    "Never personally guarantee business debts if avoidable",
                    "Maintain separate bank accounts and bookkeeping",
                    "Conduct all business in entity name",
                ],
                "cost": 1500,
                "protection_value": min(net_worth * 0.5, 2_000_000),
            })

        # Layer 3: Tenancy by entirety (married couples)
        if married:
            tbe_states = ["AK", "AR", "DE", "FL", "HI", "IL", "IN", "KY", "MD", "MA",
                          "MI", "MS", "MO", "NJ", "NY", "NC", "OH", "OK", "OR", "PA",
                          "RI", "TN", "TX", "VT", "VA", "WY"]
            if state in tbe_states:
                strategies.append({
                    "layer": "Layer 3 — Tenancy by the Entirety",
                    "name": "Married Couple Asset Protection",
                    "actions": [
                        f"Title real estate as Tenants by the Entirety in {state}",
                        "Creditor of one spouse CANNOT reach TBE property",
                        "Only joint creditors of BOTH spouses can reach TBE property",
                        "May extend to bank accounts and personal property in some states",
                    ],
                    "cost": 500,
                    "protection_value": min(net_worth * 0.4, 3_000_000),
                })

        # Layer 4: Prenuptial/postnuptial
        if married:
            strategies.append({
                "layer": "Layer 4 — Marital Agreement",
                "name": "Postnuptial Agreement",
                "actions": [
                    "Postnuptial agreement to separate assets if not already done",
                    "Clarify separate vs. community property",
                    "Protect inheritance and pre-marital assets",
                    "Address asset division in case of divorce",
                ],
                "cost": 3000,
                "protection_value": min(net_worth * 0.3, 1_000_000),
            })

        # Layer 5: Insurance
        strategies.append({
            "layer": "Layer 5 — Insurance",
            "name": "Comprehensive Insurance Coverage",
            "actions": [
                "Personal umbrella liability: $2-5M (cost: $200-$500/year)",
                f"Professional liability (malpractice/E&O): ${1_000_000:,} (cost varies by profession)",
                "Directors & Officers (D&O) if business owner",
                "Business owner's policy (BOP) for business property and liability",
            ],
            "cost": 2000,
            "protection_value": 5_000_000,
        })

        protected_estimate = sum(s.get("protection_value", 0) for s in strategies)

        return AssetProtectionPlan(
            total_assets=net_worth,
            currently_protected=min(net_worth * 0.3, protected_estimate),
            protection_gap=max(0, net_worth - min(net_worth * 0.3, protected_estimate)),
            strategies=strategies,
            exemption_strategy=(
                f"Maximize {state} state exemptions: homestead (${homestead_data.get('amount', 'unlimited'):,}), "
                "retirement accounts (ERISA unlimited; IRA per state law), life insurance cash value."
            ),
            entity_strategy=(
                "Holding company structure: Wyoming LLC → Operating LLC + RE LLC + IP LLC. "
                "Charging order protection isolates personal assets from business creditors."
            ),
            insurance_layer=(
                "Personal umbrella policy + professional liability = first line of defense. "
                "Insurance is cheaper than litigation. Maintain adequate coverage at all times."
            ),
            estimated_implementation_cost=sum(s.get("cost", 0) for s in strategies),
            estimated_protection_value=protected_estimate,
            implementation_steps=[
                "1. File homestead declaration immediately (cost: $0-$50, protection: significant)",
                "2. Open umbrella insurance policy this week",
                "3. Form holding company LLC in Wyoming",
                "4. Transfer assets to appropriate entities",
                "5. Update insurance policies",
                "6. Review annually with asset protection attorney",
            ],
        )

    def homestead_analysis(self, state: str, home_value: float) -> HomesteadAnalysis:
        """
        Analyze homestead exemption for a specific state and home value.

        Args:
            state: Two-letter state code
            home_value: Current market value of the home
        """
        data = HOMESTEAD_EXEMPTIONS.get(state.upper(), {"amount": 25000, "unlimited": False, "notes": ""})
        unlimited = data.get("unlimited", False)
        exemption_amount = data.get("amount") if not unlimited else home_value
        notes = data.get("notes", "")

        protected = home_value if unlimited else min(home_value, exemption_amount or 0)
        unprotected = max(0, home_value - protected)

        strategies = []
        if state.upper() in ["FL", "TX"]:
            strategies = [
                "Consider moving to Florida or Texas for unlimited homestead protection (if not already there)",
                "Establish Florida/Texas domicile properly (driver's license, voter registration, declaration)",
                "Pay off mortgage — more equity = more protection under unlimited exemption",
            ]
        elif unprotected > 0:
            strategies = [
                "Consider paying down mortgage — reduces unprotected equity exposed to creditors",
                "Transfer home to LLC (note: may affect mortgage terms and title insurance)",
                "Tenancy by the Entirety title (if married and available in your state)",
                "Consider QPRT (Qualified Personal Residence Trust) for estate tax purposes",
                f"Explore neighboring states with higher exemptions (current {state} exemption: ${exemption_amount:,})",
            ]

        return HomesteadAnalysis(
            state=state.upper(),
            home_value=home_value,
            homestead_exemption=exemption_amount if not unlimited else home_value,
            protected_amount=protected,
            unprotected_amount=unprotected,
            unlimited_exemption=unlimited,
            requirements=(
                f"{'No dollar limit — must be primary residence' if unlimited else f'${exemption_amount:,} exemption'} "
                f"in {state.upper()}. {notes}"
            ),
            how_to_claim=(
                f"In most states, file a 'Declaration of Homestead' with the County Recorder. "
                f"Some states (FL, TX) provide automatic protection. "
                f"Check {state.upper()} state law for exact filing requirements."
            ),
            strategies_to_maximize=strategies,
        )

    def retirement_account_protection(self) -> RetirementProtectionGuide:
        """
        Comprehensive guide to retirement account asset protection.
        """
        return RetirementProtectionGuide(
            erisa_qualified_plans="""
ERISA-QUALIFIED PLANS — UNLIMITED FEDERAL PROTECTION:
Plans covered: 401(k), 403(b), 457(b) governmental, pension plans, profit-sharing plans

Protection: Unlimited under federal ERISA law. Creditors CANNOT reach these accounts —
even in bankruptcy. The U.S. Supreme Court confirmed this in Patterson v. Shumate (1992).

Includes: Your contributions + employer contributions + earnings

Strategy: Maximize contributions to ERISA plans before other investments.
2024 limits: $23,000 employee contribution; $69,000 total (with employer match and profit sharing).
50+ catch-up: Additional $7,500.

Self-employed: Solo 401(k) allows up to $69,000/year in combined contributions.
This is ERISA-protected and provides maximum asset protection for business owners.
""",
            ira_protection_by_state={
                "Federal (Bankruptcy)": f"$1,512,350 for traditional/Roth IRAs (2024-2025, adjusted for inflation)",
                "TX": "Unlimited",
                "FL": "Unlimited",
                "CA": "Only amounts 'necessary for support' (subjective — risky)",
                "NY": "Unlimited for traditional IRA; Roth IRA also protected",
                "WA": "Unlimited",
                "NV": "Unlimited",
                "Default": IRA_PROTECTION_BY_STATE["DEFAULT"],
            },
            roth_vs_traditional_analysis="""
ROTH vs TRADITIONAL IRA — ASSET PROTECTION PERSPECTIVE:
Both receive the same bankruptcy protection at federal level ($1.5M combined limit).
State protection varies — most states protect both equally.

From pure asset protection: Traditional vs Roth doesn't matter much.
From tax perspective: Roth grows tax-free; no RMDs; better for estate planning.
From access perspective: Roth contributions (not earnings) can be withdrawn penalty-free.

RECOMMENDATION: Maximize 401(k)/ERISA plan first (unlimited protection), then Roth IRA.
""",
            self_directed_strategies="""
SELF-DIRECTED IRA STRATEGIES:
A Self-Directed IRA (SDIRA) allows investing in: real estate, private equity, notes,
precious metals, and other non-traditional assets — while maintaining IRA tax benefits.

Asset Protection Note: SDIRA receives same protection as regular IRA.
The underlying assets (e.g., real property held in IRA LLC) are titled in the IRA's name,
providing an additional layer of separation.

PROHIBITED TRANSACTIONS (avoid disqualification):
- Cannot do business with "disqualified persons" (self, spouse, parents, children)
- Cannot use IRA property personally (no self-dealing)
- Cannot provide services to IRA investments

Custodians: Equity Trust, uDirect IRA, Entrust Group, STRATA Trust Company
""",
            recommended_actions=[
                "Max out 401(k)/ERISA plan contributions ($23,000+/year) — unlimited protection",
                "Fund Solo 401(k) if self-employed for maximum contribution flexibility",
                "Contribute to Roth IRA ($7,000/year; $8,000 if 50+)",
                "Keep IRA balance below federal bankruptcy limit ($1.5M) if state protection is limited",
                "Roll old 401(k)s into current employer plan (maintains ERISA protection vs. IRA rollover)",
                "Do NOT roll 401(k) to IRA if your state has limited IRA protection (CA, NJ, etc.)",
            ],
        )

    def offshore_asset_protection(self, profile: dict) -> OffshoreStrategy:
        """
        Legal offshore asset protection structures and compliance requirements.

        Args:
            profile: dict with 'net_worth', 'risk_level', 'state',
                     'existing_offshore', 'citizenship'
        """
        net_worth = profile.get("net_worth", 5_000_000)
        risk_level = profile.get("risk_level", "High")

        structures = [
            {
                "jurisdiction": "Cook Islands (New Zealand)",
                "structure": "Cook Islands Self-Settled Spendthrift Trust",
                "protection_level": "Strongest available — US courts cannot enforce against Cook Islands assets",
                "how_it_works": "Assets transferred to Cook Islands trust with US trustee; if sued, appoint Cook Islands trustee",
                "minimum_recommended": "$1,000,000+",
                "setup_cost": "$20,000-$50,000",
                "annual_maintenance": "$5,000-$15,000",
                "compliance": "FBAR + Form 8938 + Form 3520 (foreign trust) required",
            },
            {
                "jurisdiction": "Nevis (Caribbean)",
                "structure": "Nevis LLC",
                "protection_level": "Very strong — plaintiff must post significant bond to sue in Nevis court",
                "how_it_works": "Form LLC in Nevis; transfer assets to Nevis LLC; Nevis requires bond before litigation",
                "minimum_recommended": "$500,000+",
                "setup_cost": "$5,000-$15,000",
                "annual_maintenance": "$2,000-$5,000",
                "compliance": "FBAR + Form 8938 + Form 5471 (if corp) or Form 8865 (if partnership)",
            },
            {
                "jurisdiction": "Cayman Islands",
                "structure": "Cayman Exempted Limited Partnership",
                "protection_level": "Strong — well-established for investment funds",
                "how_it_works": "Investment assets held in Cayman structure; sophisticated creditor protection",
                "minimum_recommended": "$5,000,000+",
                "setup_cost": "$15,000-$40,000",
                "annual_maintenance": "$5,000-$20,000",
                "compliance": "FBAR + Form 8938 + Form 8865 or 5471",
            },
        ]

        fbar_requirements = """
FBAR (FinCEN Form 114) — REPORT OF FOREIGN BANK AND FINANCIAL ACCOUNTS:
Who must file: US persons with financial interest in, or signature authority over,
foreign accounts with aggregate value exceeding $10,000 at any point during the year.

Deadline: April 15 (automatic extension to October 15)
File at: BSA E-Filing System (bsaefiling.fincen.treas.gov) — NO paper filing
Penalty: $156/day for non-willful violations; up to 50% of account value per year for willful violations

What to report: Foreign bank accounts, brokerage accounts, mutual funds,
offshore LLCs/partnerships where you have >50% interest or signature authority
"""

        form_8938_requirements = """
FORM 8938 (FATCA — FOREIGN ACCOUNT TAX COMPLIANCE ACT):
Who must file: US persons with specified foreign financial assets exceeding:
- Single/MFS living in US: $50,000 year-end OR $75,000 at any point during year
- MFJ living in US: $100,000 year-end OR $150,000 at any point
- Living abroad: Higher thresholds apply

File with: Form 1040 (attached)
Penalty: $10,000 for failure to disclose; up to $50,000 for continued failure

Note: FBAR and Form 8938 are separate — you may need to file BOTH.
"""

        pfic_rules = """
PASSIVE FOREIGN INVESTMENT COMPANY (PFIC) RULES — IRC § 1291-1298:
A PFIC is a foreign corporation that is primarily a passive investment vehicle.
Most offshore mutual funds and ETFs are PFICs.

Consequences of owning PFICs without proper election:
- Punitive tax treatment on gains and distributions
- Interest charges added to tax owed

Elections available:
1. QEF Election (Qualified Electing Fund) — taxed annually as earned
2. Mark-to-Market Election — mark to market annually
3. Default PFIC rules — most punitive; avoid if possible

RECOMMENDATION: If offshore structure includes investment funds, coordinate with
tax attorney experienced in international tax to make proper PFIC elections.
"""

        compliance_checklist = [
            "☐ File FBAR (FinCEN Form 114) annually by April 15",
            "☐ File Form 8938 with Form 1040 if thresholds met",
            "☐ File Form 3520 for offshore trust (within 90 days of trust creation)",
            "☐ File Form 3520-A annually for foreign grantor trust",
            "☐ File Form 5471 if interest in foreign corporation",
            "☐ File Form 8865 if interest in foreign partnership",
            "☐ Report all foreign account income on US tax returns",
            "☐ Maintain documentation of all offshore transactions",
            "☐ Hire international tax attorney familiar with FATCA/FBAR compliance",
            "☐ Consider IRS Voluntary Disclosure if non-compliant in prior years",
        ]

        return OffshoreStrategy(
            recommended_structures=structures,
            fbar_requirements=fbar_requirements,
            form_8938_requirements=form_8938_requirements,
            pfic_rules=pfic_rules,
            compliance_checklist=compliance_checklist,
            cost_estimate=25_000 + 7_500,  # rough setup + annual
            risk_assessment=(
                f"For a {risk_level}-risk individual with ${net_worth:,.0f} in assets: "
                "Offshore structures are a LAST resort — domestic planning (LLC, trusts, exemptions, insurance) "
                "should be exhausted first. Offshore structures are LEGAL but require PERFECT compliance. "
                "Non-compliance carries criminal penalties. Work ONLY with qualified international tax attorneys."
            ),
        )

    def insurance_optimization(self, profile: dict) -> InsuranceStrategy:
        """
        Develop a comprehensive insurance optimization strategy.

        Args:
            profile: dict with 'net_worth', 'annual_income', 'profession',
                     'has_business', 'age', 'has_employees', 'home_value',
                     'existing_insurance'
        """
        net_worth = profile.get("net_worth", 1_000_000)
        annual_income = profile.get("annual_income", 200_000)
        profession = profile.get("profession", "business_owner")
        has_business = profile.get("has_business", False)
        age = profile.get("age", 45)
        has_employees = profile.get("has_employees", False)
        existing_insurance = profile.get("existing_insurance", {})

        # Umbrella recommendation
        recommended_umbrella = max(2_000_000, net_worth * 2)
        umbrella = {
            "recommended_coverage": f"${min(recommended_umbrella, 10_000_000):,.0f}",
            "cost_estimate": f"${200 + (recommended_umbrella / 1_000_000) * 75:.0f}/year",
            "coverage_gap": f"${max(0, recommended_umbrella - existing_insurance.get('umbrella', 0)):,.0f}",
            "how_it_works": "Umbrella policy activates after underlying auto/home policy limits exhausted. Covers: bodily injury, property damage, personal liability, libel/slander",
            "action": "Increase umbrella coverage to match net worth. Requires auto ($300K/$100K min) and home ($300K min) policies underneath.",
        }

        # Professional liability
        professional_liability = {
            "type": self._get_professional_liability_type(profession),
            "recommended_coverage": "$1,000,000 per occurrence / $3,000,000 aggregate",
            "cost_estimate": self._get_pl_cost_estimate(profession),
            "key_provisions": [
                "Claims-made vs occurrence policy — understand the difference",
                "Tail coverage (extended reporting) — CRITICAL when you leave practice/job",
                "Prior acts coverage",
                "Defense costs inside or outside limits",
            ],
        }

        # Life insurance analysis
        recommended_life = annual_income * 10
        life_insurance = {
            "recommended_death_benefit": f"${recommended_life:,.0f} (10x income)",
            "term_vs_permanent": (
                "TERM (recommended for most): Pure death benefit at lowest cost. "
                "20-30 year term covers income replacement need. "
                f"Estimated cost: ${self._term_life_cost(age, recommended_life)}/month. "
                "PERMANENT (for estate planning): Whole or universal life — higher premium, "
                "builds cash value (protected in most states), can be used for ILIT strategy."
            ),
            "ilit_note": (
                f"If estate exceeds ${11_000_000:,}: Consider Irrevocable Life Insurance Trust (ILIT). "
                "ILIT owns policy; death benefit paid to ILIT (not taxable estate); "
                "trust distributes to beneficiaries tax-free."
            ),
        }

        # Disability insurance
        disability = {
            "recommended_coverage": f"${min(annual_income * 0.6, 20_000):,.0f}/month",
            "definition": "OWN-OCCUPATION definition is critical — pays if you can't do YOUR specific job",
            "elimination_period": "90-day elimination period (balance cost vs. emergency fund)",
            "benefit_period": "To age 65 (not 2 or 5 years)",
            "cost_estimate": f"${annual_income * 0.02:.0f}-${annual_income * 0.04:.0f}/year (2-4% of income)",
            "note": "Employer LTD typically covers only 60% and is taxable. Individual policy is tax-free.",
        }

        # Long-term care
        ltc = {
            "recommended_age_to_buy": "50-60 (premiums much lower; still insurable)",
            "coverage_amount": "$4,000-$6,000/month benefit ($150-$200/day)",
            "inflation_protection": "3-5% compound inflation protection is essential",
            "alternatives": "Hybrid life/LTC policy (death benefit if unused); self-insuring if net worth >$5M",
            "cost_estimate": f"${3000 if age < 55 else 5500:,.0f}-${5000 if age < 55 else 9000:,.0f}/year (couple)",
        }

        business_insurance = {
            "general_liability": "$1M/$2M — required by most contracts and landlords",
            "commercial_property": "Replacement cost value of business property",
            "bop": "Business Owner Policy combines GL + property (cost-effective)",
            "workers_comp": "Required by law in most states if you have employees" if has_employees else "N/A (no employees)",
            "employment_practices": "EPLI — wrongful termination, harassment claims" if has_employees else "Consider even without employees",
            "cyber_liability": "CRITICAL — covers data breach, ransomware, customer notification costs",
            "business_interruption": "Covers lost income if business forced to close",
            "key_man": "Protects business if key person dies or becomes disabled",
        } if has_business else {}

        coverage_gaps = []
        if existing_insurance.get("umbrella", 0) < recommended_umbrella:
            coverage_gaps.append({"type": "Umbrella", "gap": f"${recommended_umbrella - existing_insurance.get('umbrella', 0):,.0f}", "priority": "High"})
        if not existing_insurance.get("disability"):
            coverage_gaps.append({"type": "Disability Insurance", "gap": f"${min(annual_income * 0.6, 20_000):,.0f}/month", "priority": "High"})

        total_premium = (
            recommended_umbrella / 1_000_000 * 75 + 200 +
            annual_income * 0.03 +
            3000
        )

        return InsuranceStrategy(
            coverage_gaps=coverage_gaps,
            umbrella_recommendation=umbrella,
            professional_liability=professional_liability,
            life_insurance_analysis=life_insurance,
            disability_insurance=disability,
            long_term_care=ltc,
            business_insurance=business_insurance,
            total_annual_premium_estimate=total_premium,
            priority_additions=[
                "1. Umbrella policy — cheap, covers everything",
                "2. Disability insurance — your income IS your largest asset",
                "3. Professional liability if applicable",
                "4. Long-term care if 50+",
                "5. Review and update life insurance beneficiaries",
            ],
        )

    def _get_professional_liability_type(self, profession: str) -> str:
        mapping = {
            "physician": "Medical Malpractice",
            "surgeon": "Medical Malpractice",
            "attorney": "Legal Malpractice (E&O)",
            "accountant": "Accountant E&O",
            "architect": "Architects & Engineers E&O",
            "engineer": "Engineers E&O",
            "financial_advisor": "Investment Adviser E&O / FINRA Bonds",
            "real_estate_agent": "Real Estate E&O",
            "therapist": "Mental Health Professional Liability",
            "nurse": "Nursing Malpractice",
        }
        return mapping.get(profession.lower(), "Professional Liability / E&O")

    def _get_pl_cost_estimate(self, profession: str) -> str:
        costs = {
            "surgeon": "$30,000-$200,000/year",
            "physician": "$10,000-$50,000/year",
            "attorney": "$1,500-$10,000/year",
            "accountant": "$1,000-$5,000/year",
            "financial_advisor": "$2,000-$10,000/year",
            "architect": "$2,000-$8,000/year",
        }
        return costs.get(profession.lower(), "$1,000-$5,000/year")

    def _term_life_cost(self, age: int, coverage: float) -> str:
        per_million = {
            30: 25, 35: 35, 40: 55, 45: 90, 50: 150, 55: 240, 60: 400
        }
        closest_age = min(per_million.keys(), key=lambda x: abs(x - age))
        monthly = (coverage / 1_000_000) * per_million[closest_age]
        return f"${monthly:.0f}"
