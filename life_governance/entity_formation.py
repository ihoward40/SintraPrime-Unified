"""
Entity Formation Engine — Master Business Entity Creation and Structuring
SintraPrime Life & Entity Governance Engine
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------

@dataclass
class EntityStructure:
    """Describes a business entity type with all key attributes."""
    entity_type: str
    jurisdiction: str
    formation_documents: List[str]
    tax_treatment: str
    liability_protection: str
    governance_requirements: List[str]
    annual_compliance: List[str]
    estimated_formation_cost: float
    estimated_annual_maintenance: float
    pros: List[str]
    cons: List[str]
    recommended_for: List[str]


@dataclass
class EntityRecommendation:
    """Result of an entity recommendation analysis."""
    primary_recommendation: EntityStructure
    alternatives: List[EntityStructure]
    reasoning: str
    tax_implications: str
    liability_analysis: str
    next_steps: List[str]
    warnings: List[str]


@dataclass
class LLCFormationPackage:
    """Complete LLC formation package."""
    state: str
    articles_of_organization: str
    operating_agreement: str
    ein_instructions: str
    registered_agent_info: str
    initial_resolutions: str
    membership_certificate_template: str
    banking_resolution_template: str
    filing_fee: float
    filing_instructions: str
    state_comparison: Dict[str, Any]
    checklist: List[str]


@dataclass
class CorporationFormationPackage:
    """Complete corporation formation package."""
    state: str
    articles_of_incorporation: str
    bylaws: str
    initial_board_resolutions: str
    stock_certificate_template: str
    shareholder_agreement: str
    s_election_instructions: str
    organizational_minutes: str
    filing_fee: float
    checklist: List[str]


@dataclass
class HoldingStructureStrategy:
    """Multi-entity asset segregation strategy."""
    structure_description: str
    entity_layers: List[Dict[str, str]]
    intercompany_agreements: List[str]
    management_fee_structure: str
    charging_order_analysis: str
    series_llc_applicability: bool
    implementation_steps: List[str]
    estimated_total_cost: float


@dataclass
class NonprofitFormationPackage:
    """Complete nonprofit 501(c)(3)/(c)(4)/(c)(6) formation package."""
    mission_statement: str
    articles_of_incorporation: str
    bylaws: str
    irs_form_guidance: str
    state_exemption_steps: List[str]
    conflict_of_interest_policy: str
    whistleblower_policy: str
    document_retention_policy: str
    board_governance_guide: str
    checklist: List[str]


@dataclass
class AnnualComplianceCalendar:
    """Annual compliance calendar for a business entity."""
    entity_name: str
    entity_type: str
    state: str
    deadlines: List[Dict[str, str]]
    tax_filings: List[Dict[str, str]]
    boi_requirements: str
    license_renewals: List[str]
    registered_agent_renewal: str
    estimated_annual_cost: float


# ---------------------------------------------------------------------------
# Filing Fees by State (LLC)
# ---------------------------------------------------------------------------

LLC_FILING_FEES: Dict[str, float] = {
    "AL": 200, "AK": 250, "AZ": 85, "AR": 50, "CA": 70,
    "CO": 50, "CT": 120, "DE": 90, "FL": 125, "GA": 100,
    "HI": 50, "ID": 100, "IL": 150, "IN": 95, "IA": 50,
    "KS": 160, "KY": 40, "LA": 100, "ME": 175, "MD": 100,
    "MA": 500, "MI": 50, "MN": 155, "MS": 50, "MO": 50,
    "MT": 70, "NE": 100, "NV": 425, "NH": 100, "NJ": 125,
    "NM": 50, "NY": 200, "NC": 125, "ND": 135, "OH": 99,
    "OK": 100, "OR": 100, "PA": 125, "RI": 150, "SC": 110,
    "SD": 150, "TN": 300, "TX": 300, "UT": 54, "VT": 125,
    "VA": 100, "WA": 200, "WV": 100, "WI": 130, "WY": 100,
}

# Annual report fees by state
ANNUAL_REPORT_FEES: Dict[str, float] = {
    "AL": 100, "AK": 100, "AZ": 0, "AR": 150, "CA": 800,
    "CO": 10, "CT": 80, "DE": 300, "FL": 138, "GA": 50,
    "HI": 15, "ID": 0, "IL": 75, "IN": 30, "IA": 60,
    "KS": 55, "KY": 15, "LA": 30, "ME": 85, "MD": 300,
    "MA": 500, "MI": 25, "MN": 0, "MS": 25, "MO": 0,
    "MT": 15, "NE": 13, "NV": 350, "NH": 100, "NJ": 75,
    "NM": 0, "NY": 9, "NC": 200, "ND": 50, "OH": 0,
    "OK": 25, "OR": 100, "PA": 70, "RI": 50, "SC": 0,
    "SD": 50, "TN": 300, "TX": 0, "UT": 20, "VT": 35,
    "VA": 50, "WA": 60, "WV": 25, "WI": 25, "WY": 60,
}


# ---------------------------------------------------------------------------
# Entity Formation Engine
# ---------------------------------------------------------------------------

class EntityFormationEngine:
    """
    Master business entity creation and structuring engine.

    Covers all major entity types across all 50 US states with
    comprehensive formation documents, compliance calendars, and
    strategic recommendations.
    """

    # -----------------------------------------------------------------------
    # Entity type catalog
    # -----------------------------------------------------------------------

    ENTITY_CATALOG: Dict[str, Dict[str, Any]] = {
        "sole_proprietorship": {
            "tax_treatment": "Pass-through; reported on Schedule C (Form 1040)",
            "liability_protection": "None — personal assets fully exposed",
            "formation_documents": ["DBA filing (if using trade name)", "Business license", "Local permits"],
            "governance_requirements": [],
            "annual_compliance": ["Schedule C with personal return", "Self-employment tax (SE)", "Estimated quarterly taxes"],
            "pros": ["Zero formation cost", "Simplest structure", "Full control", "No separate tax return"],
            "cons": ["Unlimited personal liability", "Hard to raise capital", "No credibility with investors", "Self-employment tax on all net income"],
            "recommended_for": ["Solo freelancers testing an idea", "Very low-risk activities", "Short-term projects"],
            "estimated_formation_cost": 50,
            "estimated_annual_maintenance": 100,
        },
        "single_member_llc": {
            "tax_treatment": "Disregarded entity (Schedule C) by default; can elect S-Corp",
            "liability_protection": "Strong — personal assets separated from business debts",
            "formation_documents": ["Articles of Organization", "Operating Agreement", "EIN application (SS-4)"],
            "governance_requirements": ["Maintain separate bank account", "Annual meeting (some states)", "Operating agreement"],
            "annual_compliance": ["State annual report", "BOI report (FinCEN)", "Franchise/privilege tax (some states)"],
            "pros": ["Personal liability protection", "Pass-through taxation", "Flexible management", "Can elect S-Corp tax treatment", "Minimal formalities"],
            "cons": ["Self-employment tax if not electing S-Corp", "Annual state fees", "Some states have high franchise taxes (CA, NY)", "Single owner may lack credibility"],
            "recommended_for": ["Solo entrepreneurs", "Freelancers with liability concerns", "Real estate investors (one property)", "Side businesses"],
            "estimated_formation_cost": 300,
            "estimated_annual_maintenance": 500,
        },
        "multi_member_llc": {
            "tax_treatment": "Partnership (Form 1065 + K-1s) by default; can elect S-Corp or C-Corp",
            "liability_protection": "Strong — members generally not personally liable",
            "formation_documents": ["Articles of Organization", "Multi-member Operating Agreement", "EIN application", "Partnership agreement elements"],
            "governance_requirements": ["Operating agreement required", "Member meetings", "Proper record-keeping", "Separate financials"],
            "annual_compliance": ["Form 1065 (partnership return)", "K-1s for all members", "State annual report", "BOI report"],
            "pros": ["Liability protection for all members", "Flexible profit allocation", "Pass-through taxation", "Can add members easily"],
            "cons": ["More complex operating agreement needed", "Partnership tax return (Form 1065)", "Potential self-employment tax issues", "Charging order may not be enough in some states"],
            "recommended_for": ["Multiple business partners", "Family businesses", "Joint ventures", "Professional practices"],
            "estimated_formation_cost": 750,
            "estimated_annual_maintenance": 1500,
        },
        "series_llc": {
            "tax_treatment": "Each series treated as separate entity; IRS guidance evolving",
            "liability_protection": "Very strong — liability isolated between series (in states recognizing series)",
            "formation_documents": ["Master LLC Articles with series provisions", "Master Operating Agreement", "Series Operating Agreement for each series"],
            "governance_requirements": ["Strict record-keeping per series", "Separate accounting per series", "Series designations in operating agreement"],
            "annual_compliance": ["Annual report (master)", "Separate records per series", "Tax treatment varies by state"],
            "pros": ["One filing for multiple protected compartments", "Cost-effective for multiple assets", "Liability wall between series", "Ideal for real estate portfolios"],
            "cons": ["Not recognized in all states", "IRS guidance incomplete", "Lenders may be unfamiliar", "Complex accounting required"],
            "recommended_for": ["Real estate investors with multiple properties", "Multiple business lines", "Investment portfolios needing segregation"],
            "estimated_formation_cost": 1000,
            "estimated_annual_maintenance": 2000,
        },
        "s_corporation": {
            "tax_treatment": "Pass-through; shareholders taxed on K-1 income; payroll tax savings vs LLC",
            "liability_protection": "Strong — corporate shield protects shareholders",
            "formation_documents": ["Articles of Incorporation", "Corporate Bylaws", "Form 2553 (S Election)", "Organizational minutes", "Stock certificates"],
            "governance_requirements": ["Board of directors", "Annual shareholder meeting", "Corporate minutes", "Stock ledger", "Officer appointments"],
            "annual_compliance": ["Form 1120-S", "K-1s for shareholders", "Payroll tax returns", "State corporate return", "Annual report"],
            "pros": ["Self-employment tax savings on distributions", "Corporate credibility", "Established legal precedent", "Can have stock classes (limited)"],
            "cons": ["Max 100 shareholders", "Must pay reasonable salary", "S-Corp election restrictions", "More formalities required", "No non-US citizen shareholders"],
            "recommended_for": ["Profitable businesses >$40K net income", "Service businesses", "Businesses where owner works in the company"],
            "estimated_formation_cost": 1500,
            "estimated_annual_maintenance": 3000,
        },
        "c_corporation": {
            "tax_treatment": "Separate taxable entity (21% flat rate); double taxation on dividends",
            "liability_protection": "Strong — corporate liability shield",
            "formation_documents": ["Articles of Incorporation", "Corporate Bylaws", "Organizational minutes", "Stock certificates", "Shareholder agreements"],
            "governance_requirements": ["Board of directors", "Annual meetings", "Corporate minutes", "Formal records", "Officer structure"],
            "annual_compliance": ["Form 1120", "State corporate return", "Payroll taxes", "Annual report", "BOI report"],
            "pros": ["Unlimited shareholders", "Multiple share classes", "VC/investor preferred", "QSBS exclusion (Section 1202)", "No S-Corp restrictions", "Retained earnings at 21%"],
            "cons": ["Double taxation on dividends", "More complex compliance", "Higher accounting costs", "Not ideal for pass-through income"],
            "recommended_for": ["Startups seeking VC funding", "Businesses planning IPO", "Large companies with many investors", "Businesses retaining significant earnings"],
            "estimated_formation_cost": 2000,
            "estimated_annual_maintenance": 5000,
        },
        "b_corporation": {
            "tax_treatment": "Same as underlying entity type (C-Corp or LLC)",
            "liability_protection": "Same as underlying entity type",
            "formation_documents": ["B-Corp certification application", "Articles with benefit purpose", "Bylaws with stakeholder consideration"],
            "governance_requirements": ["Annual benefit report", "Third-party assessment (B Lab)", "Stakeholder consideration in decision-making"],
            "annual_compliance": ["B Impact Assessment (every 3 years)", "Annual benefit report", "Standard corporate filings"],
            "pros": ["Mission-aligned structure", "Attract impact investors", "Legal protection for decisions balancing profit and purpose", "Marketing differentiation"],
            "cons": ["B Lab certification fees", "Additional reporting burdens", "Recertification every 3 years"],
            "recommended_for": ["Social enterprises", "Mission-driven businesses", "Companies seeking impact investors"],
            "estimated_formation_cost": 3000,
            "estimated_annual_maintenance": 4000,
        },
        "nonprofit_501c3": {
            "tax_treatment": "Tax-exempt on income related to mission; donations tax-deductible",
            "liability_protection": "Directors generally not personally liable for organizational debts",
            "formation_documents": ["Articles of Incorporation (nonprofit)", "Bylaws", "Form 1023 or 1023-EZ", "Conflict of interest policy", "Mission statement"],
            "governance_requirements": ["Board of directors (at least 3)", "Annual meetings", "No private inurement", "Public benefit purpose", "Governance policies"],
            "annual_compliance": ["Form 990/990-EZ/990-N", "State charity registration", "State annual report", "Lobbying limitations tracking"],
            "pros": ["Tax-exempt status", "Tax-deductible donations", "Grants eligibility", "Public trust", "Preferred by many foundations"],
            "cons": ["No private benefit", "Complex IRS application", "Annual Form 990 public disclosure", "Board governance requirements", "Cannot distribute profits"],
            "recommended_for": ["Charitable missions", "Education organizations", "Religious organizations", "Scientific research", "Community service"],
            "estimated_formation_cost": 2500,
            "estimated_annual_maintenance": 3500,
        },
        "lllp": {
            "tax_treatment": "Partnership taxation (Form 1065)",
            "liability_protection": "General partners have limited liability (unlike regular LP); limited partners fully protected",
            "formation_documents": ["Certificate of Limited Partnership (LLLP election)", "Partnership Agreement", "EIN application"],
            "governance_requirements": ["General partner(s) manage", "Limited partner protections", "Annual partnership meetings"],
            "annual_compliance": ["Form 1065", "K-1s", "State annual report", "State registration"],
            "pros": ["All partners have liability protection", "Pass-through taxation", "Flexible profit sharing", "Good for family businesses"],
            "cons": ["Not available in all states", "More complex than LLC", "Lenders may be unfamiliar"],
            "recommended_for": ["Family businesses", "Investment funds", "Oil and gas", "Real estate with multiple partners"],
            "estimated_formation_cost": 1500,
            "estimated_annual_maintenance": 2500,
        },
    }

    # -----------------------------------------------------------------------
    # Core Recommendation Engine
    # -----------------------------------------------------------------------

    def recommend_entity_structure(self, facts: dict) -> EntityRecommendation:
        """
        Analyze facts and recommend the optimal entity structure.

        Args:
            facts: Dictionary with keys like 'num_owners', 'industry',
                   'liability_concern', 'investor_plans', 'annual_revenue',
                   'state', 'nonprofit_purpose', 'employees', 'net_income'

        Returns:
            EntityRecommendation with primary and alternative recommendations.
        """
        num_owners: int = facts.get("num_owners", 1)
        liability_concern: bool = facts.get("liability_concern", True)
        investor_plans: bool = facts.get("investor_plans", False)
        net_income: float = facts.get("net_income", 0)
        state: str = facts.get("state", "DE")
        nonprofit_purpose: bool = facts.get("nonprofit_purpose", False)
        industry: str = facts.get("industry", "general")
        real_estate_focus: bool = facts.get("real_estate_focus", False)
        multiple_properties: bool = facts.get("multiple_properties", False)
        mission_driven: bool = facts.get("mission_driven", False)

        warnings: List[str] = []
        alternatives: List[EntityStructure] = []

        # --- Decision tree ---
        if nonprofit_purpose:
            primary_key = "nonprofit_501c3"
            reasoning = (
                "A nonprofit 501(c)(3) is recommended because you have a charitable, "
                "educational, or religious purpose. This provides tax exemption and allows "
                "tax-deductible donations, critical for charitable fundraising."
            )
            tax_implications = "Exempt from federal income tax on mission-related income. Donations are deductible by donors."
            liability_analysis = "Directors and officers generally protected from personal liability for organizational obligations."

        elif investor_plans and num_owners > 1:
            primary_key = "c_corporation"
            reasoning = (
                "A C-Corporation (incorporated in Delaware) is strongly recommended for "
                "businesses seeking venture capital or angel investment. Investors overwhelmingly "
                "prefer Delaware C-Corps due to well-established corporate law, Series A/B "
                "preferred stock flexibility, and QSBS tax exclusion (Section 1202)."
            )
            tax_implications = "21% flat corporate tax; double taxation on dividends; QSBS exclusion can eliminate up to $10M in capital gains."
            liability_analysis = "Strong corporate liability shield; directors protected if duties observed."
            if state != "DE":
                warnings.append(f"Consider incorporating in Delaware even if operating in {state} — lower cost for investor preference.")

        elif multiple_properties and real_estate_focus:
            primary_key = "series_llc"
            reasoning = (
                "A Series LLC is optimal for multiple real estate properties because "
                "each property can be a separate series with isolated liability, "
                "while maintaining a single master entity for administrative simplicity."
            )
            tax_implications = "Pass-through taxation per series. IRS guidance evolving — consult tax advisor."
            liability_analysis = "Each series creates a liability wall around that property, protecting other series assets."
            warnings.append("Series LLCs not recognized in all states. Verify your state recognizes series LLCs.")

        elif net_income > 40000 and not investor_plans and num_owners <= 100:
            primary_key = "s_corporation"
            reasoning = (
                f"With net income exceeding ${net_income:,.0f}, electing S-Corp tax treatment "
                "will save significant self-employment taxes. As an S-Corp, you pay yourself a "
                "reasonable salary (subject to payroll taxes) and take the remainder as distributions "
                "(not subject to SE tax), creating substantial savings."
            )
            tax_implications = (
                f"Estimated SE tax savings: ${min(net_income * 0.15, 9000):,.0f}/year "
                "by splitting salary and distributions."
            )
            liability_analysis = "Corporate shield protects personal assets from business liabilities."
            # Add LLC as alternative
            alternatives.append(self._build_entity_structure("single_member_llc" if num_owners == 1 else "multi_member_llc", state))

        elif num_owners == 1:
            primary_key = "single_member_llc"
            reasoning = (
                "A Single-Member LLC is the optimal structure for a solo business owner. "
                "It provides personal liability protection, simple pass-through taxation "
                "(reported on Schedule C), and minimal formalities compared to a corporation."
            )
            tax_implications = "All profits/losses flow to your personal return (Schedule C). Can elect S-Corp status once income warrants it."
            liability_analysis = "Strong separation between personal and business assets. Maintain separate bank account and do not commingle funds."

        else:
            primary_key = "multi_member_llc"
            reasoning = (
                "A Multi-Member LLC provides the best balance of liability protection, "
                "tax flexibility, and operational simplicity for multiple business partners. "
                "The operating agreement governs profit sharing, management, and exit rights."
            )
            tax_implications = "Taxed as partnership (Form 1065 + K-1s). Can elect S-Corp or C-Corp treatment if advantageous."
            liability_analysis = "Each member's personal assets are protected from LLC business debts and judgments."

        primary = self._build_entity_structure(primary_key, state)

        # Build alternatives if not already populated
        if not alternatives:
            alt_keys = [k for k in ["single_member_llc", "s_corporation", "c_corporation", "multi_member_llc"]
                        if k != primary_key][:2]
            alternatives = [self._build_entity_structure(k, state) for k in alt_keys]

        next_steps = [
            f"1. Register the entity in {state} (or a favorable state like Delaware/Wyoming)",
            "2. Obtain an EIN from the IRS (free, online at irs.gov — takes minutes)",
            "3. Open a dedicated business bank account",
            "4. Draft and execute your governing document (Operating Agreement / Bylaws)",
            "5. Register for state and local business licenses",
            "6. Set up bookkeeping system (QuickBooks, Wave, or Xero)",
            "7. File Beneficial Ownership Information (BOI) report with FinCEN within 90 days",
            "8. Consult a CPA about tax elections and estimated tax payments",
        ]

        return EntityRecommendation(
            primary_recommendation=primary,
            alternatives=alternatives,
            reasoning=reasoning,
            tax_implications=tax_implications,
            liability_analysis=liability_analysis,
            next_steps=next_steps,
            warnings=warnings,
        )

    def _build_entity_structure(self, entity_key: str, state: str = "DE") -> EntityStructure:
        """Build an EntityStructure from the catalog."""
        data = self.ENTITY_CATALOG.get(entity_key, self.ENTITY_CATALOG["single_member_llc"])
        return EntityStructure(
            entity_type=entity_key.replace("_", " ").title(),
            jurisdiction=state,
            formation_documents=data["formation_documents"],
            tax_treatment=data["tax_treatment"],
            liability_protection=data["liability_protection"],
            governance_requirements=data["governance_requirements"],
            annual_compliance=data["annual_compliance"],
            estimated_formation_cost=data["estimated_formation_cost"],
            estimated_annual_maintenance=data["estimated_annual_maintenance"],
            pros=data["pros"],
            cons=data["cons"],
            recommended_for=data["recommended_for"],
        )

    # -----------------------------------------------------------------------
    # LLC Formation
    # -----------------------------------------------------------------------

    def form_llc(self, details: dict) -> LLCFormationPackage:
        """
        Generate a complete LLC formation package.

        Args:
            details: Dictionary with 'state', 'company_name', 'members',
                     'registered_agent', 'principal_office', 'purpose',
                     'management_type' (member-managed or manager-managed)
        """
        state = details.get("state", "WY")
        company_name = details.get("company_name", "[COMPANY NAME], LLC")
        members = details.get("members", [{"name": "[MEMBER NAME]", "ownership": "100%"}])
        management_type = details.get("management_type", "member-managed")
        purpose = details.get("purpose", "any lawful business purpose")
        principal_office = details.get("principal_office", "[PRINCIPAL OFFICE ADDRESS]")
        registered_agent = details.get("registered_agent", "[REGISTERED AGENT NAME AND ADDRESS]")
        formation_date = details.get("formation_date", datetime.date.today().isoformat())

        articles = self._draft_articles_of_organization(
            company_name, state, purpose, registered_agent, principal_office, management_type
        )
        operating_agreement = self._draft_operating_agreement(
            company_name, state, members, management_type, purpose, formation_date
        )
        ein_instructions = self._ein_instructions(company_name)
        reg_agent_info = self._registered_agent_guide(state)
        initial_resolutions = self._draft_initial_resolutions_llc(company_name, members, formation_date)
        membership_cert = self._membership_certificate_template(company_name)
        banking_resolution = self._banking_resolution_template(company_name)

        filing_fee = LLC_FILING_FEES.get(state, 100)

        filing_instructions = (
            f"Filing Instructions for {state} LLC Formation:\n"
            f"1. Complete the Articles of Organization above\n"
            f"2. Submit to the {state} Secretary of State office\n"
            f"3. Pay the ${filing_fee:.2f} filing fee\n"
            f"4. Processing time: 1-3 business days (expedited) to 2-4 weeks (standard)\n"
            f"5. Online filing available at most state SOS websites\n"
        )

        state_comparison = self._wyoming_delaware_nevada_comparison()

        checklist = [
            f"☐ Choose a unique name ({company_name}) — check availability at {state} SOS",
            "☐ Designate a registered agent (must have physical address in state)",
            "☐ File Articles of Organization",
            f"☐ Pay ${filing_fee:.2f} filing fee",
            "☐ Draft and sign Operating Agreement",
            "☐ Obtain EIN from IRS (free at irs.gov/businesses/small-businesses-self-employed/apply-for-an-employer-identification-number-ein-online)",
            "☐ Open dedicated business bank account",
            "☐ File BOI report with FinCEN within 90 days of formation",
            "☐ Apply for required business licenses and permits",
            "☐ Set up separate bookkeeping",
            "☐ Issue membership certificates to members",
        ]

        return LLCFormationPackage(
            state=state,
            articles_of_organization=articles,
            operating_agreement=operating_agreement,
            ein_instructions=ein_instructions,
            registered_agent_info=reg_agent_info,
            initial_resolutions=initial_resolutions,
            membership_certificate_template=membership_cert,
            banking_resolution_template=banking_resolution,
            filing_fee=filing_fee,
            filing_instructions=filing_instructions,
            state_comparison=state_comparison,
            checklist=checklist,
        )

    def _draft_articles_of_organization(
        self,
        company_name: str,
        state: str,
        purpose: str,
        registered_agent: str,
        principal_office: str,
        management_type: str,
    ) -> str:
        return f"""
ARTICLES OF ORGANIZATION
OF
{company_name}

A Limited Liability Company

Filed with the {state} Secretary of State

ARTICLE I — NAME
The name of the limited liability company is: {company_name}

ARTICLE II — PURPOSE
The purpose of the Company is to engage in {purpose} as permitted by
the laws of the State of {state}.

ARTICLE III — REGISTERED AGENT AND OFFICE
The name and address of the registered agent for service of process is:
{registered_agent}

ARTICLE IV — PRINCIPAL OFFICE
The address of the principal office of the Company is:
{principal_office}

ARTICLE V — MANAGEMENT
The Company shall be {management_type}.

ARTICLE VI — ORGANIZER
The name and address of the organizer of the Company is set forth below.
The organizer's authority terminates upon the filing of these Articles.

ARTICLE VII — LIABILITY
The liability of the members shall be limited as provided under the laws
of the State of {state}.

ARTICLE VIII — DURATION
The duration of the Company shall be perpetual unless dissolved in
accordance with the Operating Agreement or applicable law.

IN WITNESS WHEREOF, the undersigned has executed these Articles of
Organization as of the date filed with the Secretary of State.

____________________________
Organizer Signature

____________________________
Printed Name

Date: ____________________
""".strip()

    def _draft_operating_agreement(
        self,
        company_name: str,
        state: str,
        members: List[dict],
        management_type: str,
        purpose: str,
        formation_date: str,
    ) -> str:
        members_str = "\n".join(
            f"  - {m.get('name','[MEMBER]')}: {m.get('ownership','[%]')} membership interest"
            for m in members
        )
        return f"""
OPERATING AGREEMENT
OF {company_name}

A {state} Limited Liability Company

Effective Date: {formation_date}

ARTICLE 1 — ORGANIZATION
1.1 Formation. The Company was organized as a limited liability company under the laws of {state}.
1.2 Name. The Company's name is {company_name}.
1.3 Purpose. The Company is organized to engage in {purpose}.
1.4 Registered Office and Agent. As stated in the Articles of Organization.
1.5 Term. The Company shall exist perpetually unless dissolved.
1.6 Fiscal Year. The fiscal year of the Company shall end on December 31 of each year.

ARTICLE 2 — MEMBERS AND MEMBERSHIP INTERESTS
2.1 Members. The following are the Members of the Company:
{members_str}
2.2 Additional Members. New Members may be admitted only upon unanimous consent of existing Members.
2.3 Membership Certificates. The Company shall issue Membership Certificates evidencing each Member's interest.
2.4 Transfer Restrictions. No Member may transfer, assign, sell, pledge, or encumber their membership
    interest without prior written consent of a majority in interest of the other Members.
2.5 Right of First Refusal. Each Member grants the Company and other Members a right of first refusal
    upon any proposed transfer of membership interests.

ARTICLE 3 — CAPITAL CONTRIBUTIONS
3.1 Initial Contributions. Each Member has made or agrees to make the initial capital contribution set
    forth in Exhibit A attached hereto.
3.2 Additional Contributions. No Member shall be required to make any additional capital contribution.
    Additional contributions may be made upon unanimous consent.
3.3 Capital Accounts. The Company shall maintain a separate capital account for each Member.
3.4 No Interest on Capital. No Member shall be entitled to interest on their capital contribution.
3.5 Return of Capital. No Member has the right to demand or receive the return of their capital
    contribution except upon dissolution.

ARTICLE 4 — ALLOCATIONS AND DISTRIBUTIONS
4.1 Allocation of Profits and Losses. Profits and losses shall be allocated to Members in proportion
    to their respective membership interests, unless otherwise agreed in writing.
4.2 Special Allocations. The Members may agree to special allocations provided they have substantial
    economic effect under Treasury Regulation § 1.704-1(b).
4.3 Distributions. Distributions shall be made to Members at such times and in such amounts as
    determined by the Managing Member(s) or majority vote of Members.
4.4 Withholding. The Company may withhold from any distribution amounts required by law.
4.5 Limitation on Distributions. No distribution shall be made if, after giving effect thereto, the
    Company would not be able to pay its debts as they become due.

ARTICLE 5 — MANAGEMENT
5.1 Management Structure. The Company shall be {management_type}.
5.2 Powers of Members/Managers. The Member(s)/Manager(s) shall have full authority to manage the
    Company's business and affairs, including the power to:
    (a) Enter into contracts on behalf of the Company
    (b) Open and manage bank accounts
    (c) Hire and fire employees and contractors
    (d) Acquire and dispose of Company assets
    (e) Borrow funds and execute promissory notes
    (f) Execute deeds, mortgages, and other instruments
5.3 Voting. Matters requiring Member approval shall be decided by majority vote (by percentage interest)
    unless this Agreement requires a higher threshold.
5.4 Unanimous Consent Required. The following actions require unanimous written consent:
    (a) Amendment of this Operating Agreement
    (b) Merger or consolidation of the Company
    (c) Sale of substantially all assets
    (d) Admission of new Members
    (e) Voluntary dissolution

ARTICLE 6 — OFFICERS
6.1 Officers. The Members/Managers may appoint officers, including a President, Vice President,
    Secretary, and Treasurer, and delegate authority to such officers.
6.2 Removal. Any officer may be removed by the Managing Member(s) at any time.

ARTICLE 7 — BOOKS, RECORDS, AND ACCOUNTING
7.1 Books and Records. The Company shall maintain complete and accurate books and records.
7.2 Inspection Rights. Each Member has the right to inspect and copy Company records upon reasonable notice.
7.3 Tax Returns. The Company shall prepare and file all required tax returns.
7.4 Bank Accounts. The Company shall maintain separate bank accounts in the Company's name.
7.5 Fiscal Year. The fiscal year shall end December 31.

ARTICLE 8 — TAX MATTERS
8.1 Tax Classification. The Company shall be treated as a [disregarded entity / partnership] for
    federal income tax purposes unless a different election is made.
8.2 Tax Matters Representative. [MEMBER NAME] is designated as the Tax Matters Representative.
8.3 Tax Elections. The Tax Matters Representative may make or revoke tax elections on behalf of
    the Company, including a Section 754 election.

ARTICLE 9 — INDEMNIFICATION AND LIABILITY
9.1 Indemnification. The Company shall indemnify each Member and Manager against claims arising
    from their role in the Company, provided they acted in good faith.
9.2 Limitation of Liability. No Member or Manager shall be personally liable for any debt,
    obligation, or liability of the Company solely by reason of being a Member or Manager.
9.3 Insurance. The Company may maintain liability insurance.

ARTICLE 10 — DISSOLUTION AND WINDING UP
10.1 Dissolution Events. The Company shall dissolve upon:
    (a) Unanimous written consent of all Members
    (b) Judicial dissolution ordered by a court
    (c) Administrative dissolution by the Secretary of State
10.2 Winding Up. Upon dissolution, the Company shall wind up its affairs.
10.3 Order of Distribution. Upon winding up: (1) creditors paid, (2) Member loans repaid,
    (3) capital accounts returned, (4) remaining assets distributed per membership interest.

ARTICLE 11 — MISCELLANEOUS
11.1 Entire Agreement. This Agreement constitutes the entire agreement among the Members.
11.2 Amendments. This Agreement may be amended only by unanimous written consent.
11.3 Governing Law. This Agreement shall be governed by the laws of {state}.
11.4 Severability. If any provision is invalid, the remaining provisions shall remain in effect.
11.5 Counterparts. This Agreement may be executed in counterparts.
11.6 No Oral Modifications. No oral modification of this Agreement shall be effective.

SIGNATURES:

{"".join(chr(10) + f"____________________________" + chr(10) + f"{m.get('name','[MEMBER]')}, Member" + chr(10) + "Date: ____________________" + chr(10) for m in members)}

EXHIBIT A — CAPITAL CONTRIBUTIONS
[Set forth each Member's initial capital contribution]
""".strip()

    def _ein_instructions(self, company_name: str) -> str:
        return f"""
EIN APPLICATION INSTRUCTIONS FOR {company_name}

Method 1 — Online (Fastest, Recommended):
1. Go to: https://www.irs.gov/businesses/small-businesses-self-employed/apply-for-an-employer-identification-number-ein-online
2. Select "Limited Liability Company" as entity type
3. Complete the online interview (15-20 minutes)
4. EIN issued IMMEDIATELY upon completion
5. Print/save the confirmation letter (CP 575)

Method 2 — IRS Form SS-4 (Mail/Fax):
1. Download Form SS-4 from irs.gov
2. Complete all fields:
   - Line 1: {company_name}
   - Line 2: Trade name (if different)
   - Line 4a: Mailing address
   - Line 7a/b: Responsible party name and SSN
   - Line 9a: Type of entity (Limited liability company)
   - Line 9b: Number of members
   - Line 10: Reason for applying (Started new business)
   - Line 11: Date business started
3. Fax to: (855) 641-6935 (receives EIN in ~4 business days)
4. Mail to: IRS, Cincinnati, OH 45999 (4-5 weeks)

Important Notes:
- The EIN is free — never pay a third party to obtain one
- You need an EIN before opening a business bank account
- Use the EIN for all business tax filings and documents
- An EIN does not expire
""".strip()

    def _registered_agent_guide(self, state: str) -> str:
        return f"""
REGISTERED AGENT REQUIREMENTS — {state}

What is a Registered Agent?
A registered agent is an individual or company designated to receive official
legal documents (lawsuits, government notices) on behalf of your LLC.

Requirements:
- Must have a physical street address in {state} (no P.O. boxes)
- Must be available during normal business hours (M-F, 9am-5pm)
- Must be 18+ if an individual, or authorized to do business in {state}

Options:
1. Serve as your own registered agent (if you have a {state} address)
2. Use a professional registered agent service (recommended):
   - Northwest Registered Agent: ~$125/year
   - ZenBusiness: ~$99/year
   - Registered Agents Inc.: ~$100/year
   - CT Corporation: ~$329/year (large enterprise)
   - LegalZoom: ~$299/year

Why Use a Professional Service?
- Privacy (your home address stays off public records)
- Reliability (never miss a legal notice)
- You can live/work anywhere
- Notifications forwarded immediately

Important: If you change your registered agent, file a Statement of Change
with the {state} Secretary of State.
""".strip()

    def _draft_initial_resolutions_llc(
        self, company_name: str, members: List[dict], formation_date: str
    ) -> str:
        return f"""
INITIAL RESOLUTIONS OF THE MEMBERS
OF {company_name}

Date: {formation_date}

The undersigned, constituting all the Members of {company_name} (the "Company"),
hereby adopt the following resolutions:

RESOLVED, that the Operating Agreement of the Company is hereby approved and adopted.

RESOLVED, that the following persons are appointed as officers:
  President/CEO: [NAME]
  Treasurer/CFO: [NAME]
  Secretary: [NAME]

RESOLVED, that the Company is authorized to open bank accounts at [BANK NAME],
and that the following persons are authorized signatories: [NAMES].

RESOLVED, that the Company's fiscal year shall end on December 31 of each year.

RESOLVED, that the Tax Matters Representative of the Company shall be [MEMBER NAME].

RESOLVED, that the following initial capital contributions are accepted:
{"".join(chr(10) + f"  {m.get('name','[MEMBER]')}: $[AMOUNT] for {m.get('ownership','[%]')} membership interest" for m in members)}

RESOLVED, that the officers and managers are authorized to take all actions
necessary to carry out the purposes of these resolutions.

IN WITNESS WHEREOF, the undersigned Members have executed these resolutions.

{"".join(chr(10) + f"____________________________" + chr(10) + f"{m.get('name','[MEMBER]')}, Member" + chr(10) for m in members)}
""".strip()

    def _membership_certificate_template(self, company_name: str) -> str:
        return f"""
MEMBERSHIP CERTIFICATE

{company_name}
A Limited Liability Company

Certificate No.: ____
Date of Issuance: ________________

THIS CERTIFIES THAT ________________________________ is the owner of
____________% membership interest in {company_name}, a limited liability
company organized under the laws of the State of ____________.

This certificate is issued subject to and governed by the Operating Agreement
of the Company, as amended from time to time.

Transfer of this interest is restricted as provided in the Operating Agreement.

In Witness Whereof, the Company has caused this certificate to be executed.

{company_name}

By: ___________________________
Name: _________________________
Title: Managing Member / Manager
Date: _________________________
""".strip()

    def _banking_resolution_template(self, company_name: str) -> str:
        return f"""
BANKING RESOLUTION
{company_name}

RESOLVED, that [BANK NAME] is designated as a depository for the funds of
{company_name} (the "Company").

RESOLVED, that the following individuals are authorized to:
(a) Open, maintain, and close accounts
(b) Sign checks and drafts
(c) Make deposits and withdrawals
(d) Access online banking
(e) Authorize wire transfers and ACH transactions

Authorized Signatories:
Name: _________________________ Title: _______________ Signature: _______________
Name: _________________________ Title: _______________ Signature: _______________

RESOLVED, that the bank is authorized to honor any instrument signed by the
above authorized persons without inquiry as to the circumstances.

Certified to be a true and complete resolution of {company_name}.

____________________________
Secretary / Managing Member
Date: ____________________
""".strip()

    def _wyoming_delaware_nevada_comparison(self) -> Dict[str, Any]:
        return {
            "Wyoming": {
                "filing_fee": 100,
                "annual_fee": 60,
                "privacy": "High — no public member/manager disclosure",
                "charging_order": "Strongest in the nation — exclusive remedy",
                "state_income_tax": "None",
                "franchise_tax": "None",
                "best_for": "Privacy-focused LLCs, asset protection, non-residents",
                "series_llc": True,
            },
            "Delaware": {
                "filing_fee": 90,
                "annual_fee": 300,
                "privacy": "Moderate — registered agent info public",
                "charging_order": "Strong",
                "state_income_tax": "None for out-of-state income",
                "franchise_tax": "None for LLCs",
                "best_for": "VC-backed companies, multi-state operations, investors",
                "series_llc": True,
            },
            "Nevada": {
                "filing_fee": 425,
                "annual_fee": 350,
                "privacy": "High — no public disclosure of owners",
                "charging_order": "Strong",
                "state_income_tax": "None",
                "franchise_tax": "None",
                "best_for": "Privacy, no state tax, gaming/entertainment",
                "series_llc": False,
            },
            "Home State": {
                "recommendation": "Often best if you operate locally — avoids foreign registration costs and complexity",
                "note": "If you incorporate in another state but operate in your home state, you must register as a foreign entity in your home state — paying fees in both states",
            },
        }

    # -----------------------------------------------------------------------
    # Corporation Formation
    # -----------------------------------------------------------------------

    def form_corporation(self, details: dict) -> CorporationFormationPackage:
        """
        Generate a complete corporation formation package.

        Args:
            details: dict with 'state', 'company_name', 'directors',
                     'shareholders', 'authorized_shares', 's_election',
                     'purpose', 'registered_agent'
        """
        state = details.get("state", "DE")
        company_name = details.get("company_name", "[COMPANY NAME], Inc.")
        directors = details.get("directors", [{"name": "[DIRECTOR NAME]", "address": "[ADDRESS]"}])
        shareholders = details.get("shareholders", [{"name": "[SHAREHOLDER]", "shares": 1000}])
        authorized_shares = details.get("authorized_shares", 10_000_000)
        s_election = details.get("s_election", False)
        purpose = details.get("purpose", "any lawful business purpose")
        registered_agent = details.get("registered_agent", "[REGISTERED AGENT]")

        articles = f"""
ARTICLES OF INCORPORATION
OF {company_name}

ARTICLE I — NAME
The name of the corporation is: {company_name}

ARTICLE II — PURPOSE
The purpose of the corporation is to engage in {purpose}.

ARTICLE III — AUTHORIZED SHARES
The corporation is authorized to issue {authorized_shares:,} shares of
Common Stock, par value $0.0001 per share.

ARTICLE IV — REGISTERED AGENT
The registered agent in the State of {state} is: {registered_agent}

ARTICLE V — DIRECTORS
The initial board of directors consists of {len(directors)} director(s):
{"".join(chr(10) + f'  {d["name"]}, {d.get("address","[ADDRESS]")}' for d in directors)}

ARTICLE VI — LIABILITY OF DIRECTORS
No director shall be personally liable to the corporation or shareholders
for monetary damages for breach of fiduciary duty as a director, except as
required by applicable law.

ARTICLE VII — INDEMNIFICATION
The corporation shall indemnify its directors and officers to the fullest
extent permitted by applicable law.

ARTICLE VIII — INCORPORATOR
IN WITNESS WHEREOF, I have hereunto set my hand this ____ day of _______, 20__.
Incorporator: ____________________________
""".strip()

        bylaws = f"""
BYLAWS OF {company_name}

ARTICLE I — OFFICES
1.1 Principal Office. The principal office of the Corporation shall be located at
    [ADDRESS].
1.2 Registered Office. As stated in the Articles of Incorporation.

ARTICLE II — SHAREHOLDERS
2.1 Annual Meeting. Annual meetings shall be held on the [DAY] of [MONTH] each year.
2.2 Special Meetings. Special meetings may be called by the Board of Directors or
    by shareholders holding at least 10% of outstanding shares.
2.3 Notice. Written notice of meetings shall be given at least 10 days in advance.
2.4 Quorum. A majority of outstanding shares constitutes a quorum.
2.5 Voting. Each share entitles the holder to one vote on matters submitted to shareholders.
2.6 Action Without Meeting. Shareholders may act by unanimous written consent without meeting.

ARTICLE III — BOARD OF DIRECTORS
3.1 Number. The Board shall consist of [NUMBER] directors, as fixed by shareholders.
3.2 Election. Directors shall be elected annually by shareholders.
3.3 Term. Directors serve one-year terms.
3.4 Removal. Directors may be removed with or without cause by a majority vote of shareholders.
3.5 Vacancies. Vacancies may be filled by the remaining directors.
3.6 Regular Meetings. The Board shall meet [FREQUENCY].
3.7 Quorum. A majority of directors constitutes a quorum.
3.8 Committees. The Board may establish committees, including an Audit Committee.

ARTICLE IV — OFFICERS
4.1 Officers. The Corporation shall have: President/CEO, Secretary, and Treasurer/CFO.
4.2 Election. Officers are elected by the Board of Directors.
4.3 Duties of President. The President shall be the Chief Executive Officer.
4.4 Duties of Secretary. The Secretary shall maintain corporate records and minutes.
4.5 Duties of Treasurer. The Treasurer shall maintain financial records.

ARTICLE V — STOCK
5.1 Certificates. Stock certificates shall be signed by the President and Secretary.
5.2 Transfers. Stock transfers shall be recorded in the stock transfer ledger.
5.3 Lost Certificates. The Board may issue replacement certificates upon satisfactory proof.
5.4 Record Date. The Board may fix a record date for shareholder matters.

ARTICLE VI — DIVIDENDS
6.1 Dividends. The Board may declare dividends from surplus or net profits.

ARTICLE VII — INDEMNIFICATION
7.1 Indemnification. The Corporation shall indemnify directors, officers, employees,
    and agents to the fullest extent permitted by law.

ARTICLE VIII — FISCAL YEAR
8.1 Fiscal Year. The fiscal year ends December 31.

ARTICLE IX — AMENDMENTS
9.1 Amendment. Bylaws may be amended by the Board of Directors or shareholders.
""".strip()

        s_election_instructions = ""
        if s_election:
            s_election_instructions = """
S-CORPORATION ELECTION INSTRUCTIONS (IRS FORM 2553)

To elect S-Corporation tax status:

1. Eligibility Requirements (ALL must be met):
   ✓ Domestic corporation
   ✓ No more than 100 shareholders
   ✓ All shareholders are US citizens/residents or certain trusts/estates
   ✓ Only one class of stock
   ✓ Not an ineligible corporation (banks, insurance companies, etc.)

2. Filing Form 2553:
   - Download from: irs.gov/forms-pubs/about-form-2553
   - File within 75 days of incorporation for election to apply this year
   - OR by March 15 for election to apply to the current year
   - Sign by all shareholders

3. After Election:
   - Corporation files Form 1120-S (not 1120)
   - Each shareholder receives Schedule K-1
   - Pay yourself a "reasonable salary" (W-2)
   - Remaining profits distributed as distributions (no SE tax)
   - Tax savings example: If you earn $150K, salary of $80K + $70K distribution
     saves approximately $10,000 in SE taxes annually

4. Losing S-Corp Status:
   - Violating eligibility requirements terminates S status
   - Cannot re-elect S status for 5 years after termination
""".strip()

        initial_resolutions = f"""
ORGANIZATIONAL MINUTES AND INITIAL BOARD RESOLUTIONS
OF {company_name}

Date: [DATE]
Location: [LOCATION] / [VIDEOCONFERENCE]

Directors Present: {"".join(d['name'] + ', ' for d in directors)}

The initial meeting of the Board of Directors was duly called and held.

RESOLVED, that the Bylaws of the Corporation are hereby adopted.

RESOLVED, that the following individuals are appointed as officers:
  President/CEO: [NAME]
  Secretary: [NAME]
  Treasurer/CFO: [NAME]

RESOLVED, that [BANK NAME] is selected as the depository bank of the Corporation,
and the officers are authorized to open accounts and sign banking documents.

RESOLVED, that the Corporation's fiscal year shall end December 31.

RESOLVED, that the officers are authorized to issue the following shares:
{"".join(chr(10) + f'  {s["name"]}: {s.get("shares", 0):,} shares of Common Stock' for s in shareholders)}

RESOLVED, that the officers are authorized to apply for an EIN, register
in any state where the corporation does business, and take all actions
necessary to commence business operations.

____________________________
Secretary, {company_name}
Date: ____________________
""".strip()

        return CorporationFormationPackage(
            state=state,
            articles_of_incorporation=articles,
            bylaws=bylaws,
            initial_board_resolutions=initial_resolutions,
            stock_certificate_template=self._stock_certificate_template(company_name),
            shareholder_agreement="[Comprehensive Shareholder Agreement — attach separately]",
            s_election_instructions=s_election_instructions,
            organizational_minutes=initial_resolutions,
            filing_fee=LLC_FILING_FEES.get(state, 100),
            checklist=[
                "☐ Choose and check corporation name availability",
                "☐ File Articles of Incorporation",
                "☐ Pay state filing fee",
                "☐ Appoint registered agent",
                "☐ Adopt Bylaws",
                "☐ Hold organizational meeting",
                "☐ Appoint directors and officers",
                "☐ Issue stock to founders",
                "☐ Obtain EIN from IRS",
                "☐ File S-Corp election (Form 2553) if desired",
                "☐ Open corporate bank account",
                "☐ File BOI report with FinCEN",
                "☐ Obtain required business licenses",
            ],
        )

    def _stock_certificate_template(self, company_name: str) -> str:
        return f"""
STOCK CERTIFICATE

{company_name.upper()}

Certificate Number: ______        Shares: _______________

THIS CERTIFIES THAT ________________________________ is the registered holder
of ________________ shares of the Common Stock of {company_name}, a corporation
organized under the laws of the State of ____________.

The shares represented by this Certificate are subject to the provisions of the
Corporation's Articles of Incorporation, Bylaws, and any applicable Shareholder
Agreement. Transfer of shares is restricted as provided therein.

IN WITNESS WHEREOF, the Corporation has caused this Certificate to be executed.

{company_name}

By: ___________________________        By: ___________________________
    President/CEO                           Secretary
    
Date: _________________________
""".strip()

    # -----------------------------------------------------------------------
    # Holding Company Structure
    # -----------------------------------------------------------------------

    def holding_company_structure(self, assets: dict) -> HoldingStructureStrategy:
        """
        Design a multi-entity holding company structure for asset segregation.

        Args:
            assets: dict with 'real_estate', 'ip_assets', 'operating_businesses',
                    'state', 'owner_name'
        """
        state = assets.get("state", "WY")
        owner_name = assets.get("owner_name", "[OWNER]")
        has_real_estate = bool(assets.get("real_estate"))
        has_ip = bool(assets.get("ip_assets"))
        has_operations = bool(assets.get("operating_businesses"))

        entity_layers = [
            {
                "name": f"{owner_name} Holdings LLC",
                "type": "Holding LLC (Wyoming)",
                "purpose": "Master holding company — owns all other entities",
                "owns": "100% of all subsidiary LLCs",
            }
        ]

        if has_operations:
            entity_layers.append({
                "name": f"{owner_name} Operations LLC",
                "type": "Operating LLC",
                "purpose": "Day-to-day business operations, employees, contracts",
                "owns": "Operating assets, contracts, employees",
                "owned_by": "Holding LLC (100%)",
            })

        if has_ip:
            entity_layers.append({
                "name": f"{owner_name} IP Holdings LLC",
                "type": "IP Holding LLC",
                "purpose": "Owns all intellectual property — trademarks, patents, copyrights, domain names",
                "owns": "All IP assets; licenses them to Operating LLC",
                "owned_by": "Holding LLC (100%)",
            })

        if has_real_estate:
            entity_layers.append({
                "name": f"{owner_name} Real Estate LLC (or Series LLC)",
                "type": "Real Estate LLC",
                "purpose": "Holds all real property — insulates real estate from business liability",
                "owns": "All real estate assets",
                "owned_by": "Holding LLC (100%)",
            })

        intercompany_agreements = [
            "Management Services Agreement — Holding LLC provides management to Operating LLC for a fee",
            "IP License Agreement — IP LLC licenses intellectual property to Operating LLC at fair market royalty rate",
            "Lease Agreement — Real Estate LLC leases property to Operating LLC at fair market rent",
            "Intercompany Loan Agreement — if funds transferred between entities (must charge market interest rate)",
            "Cost Sharing Agreement — allocating shared expenses among entities",
        ]

        return HoldingStructureStrategy(
            structure_description=(
                f"Multi-entity holding structure with {owner_name} Holdings LLC as master entity. "
                "Each subsidiary isolates specific asset classes, preventing liability from one "
                "business line from infecting others."
            ),
            entity_layers=entity_layers,
            intercompany_agreements=intercompany_agreements,
            management_fee_structure=(
                "The Operating LLC pays the Holding LLC a monthly management fee (typically 5-15% of revenue) "
                "for administrative services, stripping profits from the operating entity (where lawsuit risk is highest) "
                "up to the holding company (where assets are protected). Must be documented and at arm's length."
            ),
            charging_order_analysis=(
                f"Wyoming LLCs provide the strongest charging order protection in the US. "
                "A charging order is the EXCLUSIVE remedy for a creditor of an LLC member — "
                "the creditor CANNOT foreclose on the membership interest, force a sale, or "
                "access LLC assets. They can only receive distributions IF the LLC makes them. "
                "This creates powerful negotiating leverage."
            ),
            series_llc_applicability=bool(has_real_estate and len(assets.get("real_estate", [])) > 1),
            implementation_steps=[
                f"1. Form {owner_name} Holdings LLC in Wyoming ($100 filing fee)",
                "2. Form Operating LLC in your home state (if different from WY)",
                "3. Form IP Holdings LLC if you have IP worth protecting",
                "4. Form Real Estate LLC (or Series LLC) if you own real estate",
                "5. Draft all intercompany agreements",
                "6. Transfer assets to appropriate entity (deed transfers, IP assignments, etc.)",
                "7. Open separate bank accounts for each entity",
                "8. File BOI reports for all entities with FinCEN",
                "9. Establish separate bookkeeping for each entity",
                "10. Review structure annually with your attorney and CPA",
            ],
            estimated_total_cost=sum([500] + [300 for _ in entity_layers[1:]]),
        )

    # -----------------------------------------------------------------------
    # Nonprofit Formation
    # -----------------------------------------------------------------------

    def nonprofit_formation(self, mission: dict) -> NonprofitFormationPackage:
        """
        Generate a complete nonprofit 501(c)(3) formation package.

        Args:
            mission: dict with 'organization_name', 'mission_statement',
                     'state', 'activities', 'directors', 'tax_exempt_type'
        """
        org_name = mission.get("organization_name", "[ORGANIZATION NAME]")
        mission_stmt = mission.get("mission_statement", "[MISSION STATEMENT]")
        state = mission.get("state", "CA")
        directors = mission.get("directors", [{"name": "[DIRECTOR]", "role": "President"}])
        tax_exempt_type = mission.get("tax_exempt_type", "501(c)(3)")

        articles = f"""
ARTICLES OF INCORPORATION OF {org_name}
A Nonprofit Public Benefit Corporation

ARTICLE I — NAME
The name of this corporation is {org_name}.

ARTICLE II — PURPOSE
This corporation is a nonprofit public benefit corporation organized exclusively for
charitable, educational, and scientific purposes within the meaning of Section 501(c)(3)
of the Internal Revenue Code.

The specific purpose of this corporation is: {mission_stmt}

ARTICLE III — NONPROFIT STATUS
This corporation is not organized for the private gain of any person. No part of the
net earnings of this organization shall inure to the benefit of, or be distributable to
its members, trustees, officers, or other private persons.

ARTICLE IV — DISSOLUTION
Upon dissolution, assets shall be distributed to a charitable organization under
Section 501(c)(3) of the Internal Revenue Code, as determined by the Board.

ARTICLE V — REGISTERED AGENT
[REGISTERED AGENT NAME AND ADDRESS IN {state}]

ARTICLE VI — DIRECTORS
Initial Board of Directors:
{"".join(chr(10) + f'  {d["name"]}, {d.get("role","Director")}' for d in directors)}

ARTICLE VII — INCORPORATOR
[INCORPORATOR NAME AND ADDRESS]

Executed on: ____________________
""".strip()

        return NonprofitFormationPackage(
            mission_statement=mission_stmt,
            articles_of_incorporation=articles,
            bylaws=self._nonprofit_bylaws(org_name, directors),
            irs_form_guidance=self._irs_form_1023_guidance(org_name, tax_exempt_type),
            state_exemption_steps=[
                f"1. File Articles of Incorporation with {state} Secretary of State",
                "2. Hold organizational meeting and adopt bylaws",
                "3. Obtain EIN from IRS",
                "4. File IRS Form 1023 (or 1023-EZ if eligible) for federal tax exemption",
                "5. Wait for IRS determination letter (can take 3-12 months)",
                f"6. Apply for {state} state tax exemption (varies by state)",
                "7. Register with state attorney general for charitable solicitation (required in most states)",
                "8. Open organizational bank account",
                "9. Establish accounting system and chart of accounts",
                "10. Begin record-keeping for Form 990 compliance",
            ],
            conflict_of_interest_policy=self._conflict_of_interest_policy(org_name),
            whistleblower_policy=self._whistleblower_policy(org_name),
            document_retention_policy=self._document_retention_policy(org_name),
            board_governance_guide=self._board_governance_guide(),
            checklist=[
                "☐ Draft mission statement",
                "☐ Recruit initial board of directors (minimum 3, ideally 5-7)",
                "☐ Choose state of incorporation",
                "☐ File Articles of Incorporation",
                "☐ Adopt Bylaws",
                "☐ Obtain EIN",
                "☐ File Form 1023 or 1023-EZ",
                "☐ Adopt conflict of interest policy",
                "☐ Open bank account",
                "☐ Register for charitable solicitation in relevant states",
                "☐ Set up accounting system",
                "☐ Plan first board meeting",
            ],
        )

    def _nonprofit_bylaws(self, org_name: str, directors: List[dict]) -> str:
        return f"""
BYLAWS OF {org_name}
A Nonprofit Corporation

ARTICLE I — NAME AND OFFICES
1.1 Name: {org_name}
1.2 Principal Office: [ADDRESS]

ARTICLE II — PURPOSES
2.1 Mission: As stated in the Articles of Incorporation.
2.2 Limitations: No substantial part of activities shall be lobbying; no political campaign activity.

ARTICLE III — BOARD OF DIRECTORS
3.1 Powers. The Board of Directors shall manage the affairs of the corporation.
3.2 Number. The Board shall consist of not fewer than 3 and not more than 15 directors.
3.3 Election. Directors shall be elected by the Board at each annual meeting.
3.4 Terms. Directors serve [2]-year terms and may be re-elected for [2] additional terms.
3.5 Qualifications. Directors must be committed to the mission and free of conflicts.
3.6 Compensation. Directors shall serve without compensation unless approved by the Board.
3.7 Removal. A director may be removed for cause by a two-thirds vote of the Board.
3.8 Vacancies. Vacancies may be filled by a majority vote of remaining directors.

ARTICLE IV — MEETINGS
4.1 Regular Meetings. The Board shall meet at least [4] times per year.
4.2 Annual Meeting. The annual meeting shall be held in [MONTH].
4.3 Special Meetings. May be called by the Chair or any two directors.
4.4 Notice. At least [7] days notice required.
4.5 Quorum. A majority of directors constitutes a quorum.
4.6 Action. Decisions require majority vote of directors present at a quorum meeting.
4.7 Remote Participation. Directors may participate by telephone or videoconference.

ARTICLE V — OFFICERS
5.1 Officers. Board Chair, Vice Chair, Secretary, Treasurer (CFO), and Executive Director.
5.2 Election. Officers elected by Board annually.
5.3 Executive Director. The Executive Director manages day-to-day operations.

ARTICLE VI — COMMITTEES
6.1 Executive Committee. May act on behalf of Board between meetings.
6.2 Finance Committee. Oversees financial management and audit.
6.3 Nominating Committee. Identifies and recommends new directors.

ARTICLE VII — FISCAL YEAR AND FINANCES
7.1 Fiscal Year. Ends December 31.
7.2 Budget. Board approves annual budget.
7.3 Audit. Annual audit or review required if revenue exceeds [threshold].
7.4 Signing Authority. Checks over $[AMOUNT] require two signatures.

ARTICLE VIII — CONFLICT OF INTEREST
8.1 Policy. Directors and officers must disclose conflicts and recuse from related votes.
8.2 Annual Disclosure. All directors annually complete conflict of interest disclosure.

ARTICLE IX — INDEMNIFICATION
9.1 Indemnification. Corporation shall indemnify directors and officers as permitted by law.

ARTICLE X — AMENDMENTS
10.1 These Bylaws may be amended by a two-thirds vote of the Board of Directors.
""".strip()

    def _irs_form_1023_guidance(self, org_name: str, tax_type: str) -> str:
        return f"""
IRS {tax_type} APPLICATION GUIDANCE FOR {org_name}

FORM 1023 vs FORM 1023-EZ:
- Form 1023-EZ: For organizations with projected annual gross receipts ≤$50,000
  and total assets ≤$250,000. Simpler 3-page form. Fee: $275.
- Form 1023: Full application for larger organizations. Fee: $600.
  Required if 1023-EZ eligibility criteria not met.

KEY SECTIONS OF FORM 1023:
Part I:    Identification of Applicant (EIN, address, contact)
Part II:   Organizational Structure (articles and bylaws)
Part III:  Required Provisions Check (purpose clause, dissolution clause)
Part IV:   Narrative Description of Activities — MOST IMPORTANT SECTION
           Describe specifically what you do, how you do it, who you serve
Part V:    Compensation and Other Financial Arrangements
Part VI:   Members and Other Individuals / Organizations
Part VII:  History of Organization (if not newly formed)
Part VIII: Specific Activities (lobbying, gaming, other)
Part IX:   Financial Data (3 years of budgets or actuals)
Part X:    Public Charity Status (most choose 509(a)(1) or (a)(2))

FILING PROCESS:
1. Complete Form 1023 online at pay.gov
2. Attach: Articles of Incorporation (certified copy), Bylaws, conflict of interest policy
3. Pay filing fee ($275 or $600)
4. IRS processes in 3-6 months (may take longer)
5. IRS may send questions (Form 886-A) — respond promptly
6. Receive Determination Letter (Letter 947) — KEEP FOREVER

PUBLIC CHARITY STATUS:
Most new nonprofits qualify under:
- Section 509(a)(1) with 170(b)(1)(A)(vi): Publicly supported organizations
  (must receive at least 33.33% of support from public/government sources)
- Section 509(a)(2): Service-providing organizations
  (support from admissions, sales, services)

AFTER RECEIVING EXEMPTION:
- File Form 990 annually (990-N if <$50K revenue; 990-EZ if <$200K; 990 if larger)
- State charitable registration renewal
- Maintain public support test (509(a)(1) organizations)
- No private inurement or excessive compensation
- Keep lobbying to a non-substantial level
""".strip()

    def _conflict_of_interest_policy(self, org_name: str) -> str:
        return f"""
CONFLICT OF INTEREST POLICY
{org_name}

I. PURPOSE
This policy is intended to protect {org_name}'s (the "Organization") interest when it is
contemplating entering into a transaction or arrangement that might benefit the private interest
of an officer or director of the Organization.

II. DEFINITIONS
Interested Person: Any director, officer, or member of a committee who has a direct or indirect
financial interest in a transaction with the Organization.

Financial Interest: A person has a financial interest if they have (a) an ownership or investment
interest, (b) a compensation arrangement, or (c) a potential ownership, investment, or compensation
arrangement with any entity with which the Organization has or is contemplating a transaction.

III. PROCEDURES
1. Disclosure. An interested person must disclose the existence of any financial interest.
2. Recusal. The interested person must leave the meeting while the transaction is discussed and voted.
3. Vote. The remaining board members shall vote on whether the transaction is fair to the Organization.
4. Documentation. All disclosures and votes shall be recorded in board minutes.

IV. ANNUAL DISCLOSURE
Each director and officer must annually sign a disclosure statement identifying any financial interests.

V. VIOLATIONS
Violations of this policy may result in removal from the board.
""".strip()

    def _whistleblower_policy(self, org_name: str) -> str:
        return f"""
WHISTLEBLOWER PROTECTION POLICY
{org_name}

{org_name} is committed to lawful and ethical behavior. This policy encourages the reporting
of any illegal, unethical, or improper conduct without fear of retaliation.

REPORTING: Reports may be made to the Board Chair, Executive Director, or an anonymous hotline.
PROTECTION: No retaliation shall be taken against any person reporting in good faith.
CONFIDENTIALITY: Reports shall be kept confidential to the extent possible.
INVESTIGATION: All reports shall be promptly and thoroughly investigated.
""".strip()

    def _document_retention_policy(self, org_name: str) -> str:
        return f"""
DOCUMENT RETENTION AND DESTRUCTION POLICY
{org_name}

PERMANENT RETENTION: Articles of Incorporation, Bylaws, Board minutes, IRS Determination
Letter, audited financial statements, property records, contracts.

7 YEARS: Accounts payable/receivable, bank statements, canceled checks, expense reports,
tax returns and workpapers, Form 990s.

3 YEARS: Bank reconciliations, employment applications, general correspondence.

DESTROY: Documents should be destroyed after retention period by shredding or deletion.
EXCEPTION: Destruction halted if litigation, government investigation, or audit is pending.
""".strip()

    def _board_governance_guide(self) -> str:
        return """
NONPROFIT BOARD GOVERNANCE BEST PRACTICES

FIDUCIARY DUTIES:
1. Duty of Care — Make informed decisions; attend meetings; read materials
2. Duty of Loyalty — Put organization first; no self-dealing
3. Duty of Obedience — Stay true to the mission; comply with laws

BOARD RESPONSIBILITIES:
- Hire and evaluate the Executive Director
- Approve strategic plan and annual budget
- Ensure adequate resources (fundraising)
- Oversee legal and financial compliance
- Maintain financial reserves (3-6 months of expenses)

BEST PRACTICES:
- Conduct annual board self-assessment
- Provide board orientation for new members
- Maintain D&O (Directors & Officers) liability insurance
- Review Form 990 before filing (it's public!)
- Hold executive sessions without staff when needed
- Separate governance (board) from management (staff)
""".strip()

    # -----------------------------------------------------------------------
    # Compliance Calendar
    # -----------------------------------------------------------------------

    def compliance_calendar(self, entity: dict) -> AnnualComplianceCalendar:
        """
        Generate an annual compliance calendar for a business entity.

        Args:
            entity: dict with 'name', 'type', 'state', 'tax_year_end',
                    'has_employees', 'fiscal_year_end'
        """
        name = entity.get("name", "[ENTITY NAME]")
        entity_type = entity.get("type", "LLC")
        state = entity.get("state", "WY")
        has_employees = entity.get("has_employees", False)
        fy_end = entity.get("fiscal_year_end", "December 31")

        deadlines: List[Dict[str, str]] = []

        # Federal tax deadlines
        if "llc" in entity_type.lower() and "single" in entity_type.lower():
            deadlines.append({"deadline": "April 15", "task": "Schedule C due with personal Form 1040 (or Oct 15 with extension)"})
        elif "s_corp" in entity_type.lower() or entity_type == "S-Corporation":
            deadlines.append({"deadline": "March 15", "task": "Form 1120-S due (or Sep 15 with extension)"})
            deadlines.append({"deadline": "March 15", "task": "Schedule K-1s distributed to shareholders"})
        elif entity_type in ["LLC", "Multi-Member LLC", "Partnership"]:
            deadlines.append({"deadline": "March 15", "task": "Form 1065 due (or Sep 15 with extension)"})
            deadlines.append({"deadline": "March 15", "task": "Schedule K-1s distributed to members"})
        elif entity_type in ["C-Corporation"]:
            deadlines.append({"deadline": "April 15", "task": "Form 1120 due (or Oct 15 with extension)"})

        # Estimated taxes
        deadlines += [
            {"deadline": "April 15", "task": "Q1 estimated tax payment due"},
            {"deadline": "June 15", "task": "Q2 estimated tax payment due"},
            {"deadline": "September 15", "task": "Q3 estimated tax payment due"},
            {"deadline": "January 15 (next year)", "task": "Q4 estimated tax payment due"},
        ]

        if has_employees:
            deadlines += [
                {"deadline": "Monthly/Semi-weekly", "task": "Payroll tax deposits (941)"},
                {"deadline": "January 31", "task": "W-2s distributed to employees"},
                {"deadline": "January 31", "task": "Form 941 (Q4) due"},
                {"deadline": "January 31", "task": "Form 940 (FUTA) annual return due"},
                {"deadline": "January 31", "task": "1099-NEC to contractors"},
            ]

        # State annual report
        annual_report_fee = ANNUAL_REPORT_FEES.get(state, 100)
        deadlines.append({
            "deadline": "Varies by state — check SOS website",
            "task": f"State Annual Report/Biennial Report for {state} (fee: ${annual_report_fee:.2f})"
        })

        # BOI report
        boi_requirements = """
BENEFICIAL OWNERSHIP INFORMATION (BOI) REPORT — FinCEN Requirements:
- Required under Corporate Transparency Act (CTA) effective January 1, 2024
- Who must file: Most LLCs, corporations, and similar entities
- Exemptions: Large companies (>20 FT employees, >$5M revenue, US office), regulated entities
- New entities (formed in 2024+): File within 90 days of formation
- Existing entities (formed before 2024): File by January 1, 2025
- Updates: File within 30 days of any change in beneficial owners
- Penalty for non-compliance: $591/day + criminal penalties
- File at: fincen.gov/boi
- Information required: Legal name, DOB, address, ID number for each beneficial owner (>25% ownership or substantial control)
"""

        return AnnualComplianceCalendar(
            entity_name=name,
            entity_type=entity_type,
            state=state,
            deadlines=sorted(deadlines, key=lambda x: x["deadline"]),
            tax_filings=[
                {"form": "Form 1065/1120-S/1120/990", "due": "March 15 or April 15", "purpose": "Annual federal tax return"},
                {"form": "State Return", "due": "Varies by state", "purpose": "State income/franchise tax return"},
                {"form": "Form 941", "due": "Quarterly", "purpose": "Payroll taxes (if employees)"},
                {"form": "BOI Report", "due": "See above", "purpose": "FinCEN beneficial ownership disclosure"},
            ],
            boi_requirements=boi_requirements,
            license_renewals=[
                "Business operating license (annual or biennial — check local municipality)",
                "Professional licenses (varies by profession and state)",
                "Industry-specific permits (food service, construction, health care, financial services)",
                "Sales tax permit renewal (if selling taxable goods/services)",
            ],
            registered_agent_renewal=f"Registered agent fee due annually (typically $100-$350). Check your registered agent service for renewal dates.",
            estimated_annual_cost=annual_report_fee + 500,  # rough estimate
        )
