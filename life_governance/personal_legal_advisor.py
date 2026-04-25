"""
Personal Legal Advisor — Navigating Personal Legal Situations
SintraPrime Life & Entity Governance Engine
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------

@dataclass
class FamilyLawStrategy:
    """Strategy for family law matters."""
    situation: str
    overview: str
    key_issues: List[str]
    legal_options: List[Dict[str, str]]
    state_specific_notes: str
    steps_to_take: List[str]
    documents_needed: List[str]
    estimated_costs: str
    do_it_yourself_options: str
    when_to_hire_attorney: str


@dataclass
class NameChangeInstructions:
    """Step-by-step name change instructions."""
    state: str
    court_process: List[str]
    documents_to_update: List[Dict[str, str]]
    timeline: str
    estimated_cost: str


@dataclass
class IdentityTheftResponsePlan:
    """Comprehensive identity theft response plan."""
    immediate_steps: List[str]
    credit_bureau_steps: Dict[str, str]
    ftc_report_steps: str
    police_report_guidance: str
    disputing_fraudulent_accounts: str
    irs_protection: str
    ongoing_monitoring: List[str]
    resources: List[str]


@dataclass
class ConsumerRightsGuide:
    """Guide to consumer protection rights."""
    lemon_law_overview: str
    warranty_rights: str
    cooling_off_rule: str
    debt_collection_rights: str
    telemarketing_protections: str
    data_privacy_rights: str
    key_federal_laws: List[Dict[str, str]]


@dataclass
class EmploymentRightsAnalysis:
    """Analysis of employment rights."""
    employment_type: str
    at_will_analysis: str
    wrongful_termination_factors: List[str]
    wage_theft_rights: str
    non_compete_analysis: str
    unemployment_eligibility: str
    warn_act_applicability: str
    recommended_actions: List[str]


# ---------------------------------------------------------------------------
# State data
# ---------------------------------------------------------------------------

COMMUNITY_PROPERTY_STATES = ["AZ", "CA", "ID", "LA", "NM", "NV", "TX", "WA", "WI"]
EQUITABLE_DISTRIBUTION_STATES = [
    s for s in [
        "AL", "AK", "AR", "CO", "CT", "DE", "FL", "GA", "HI", "IL", "IN", "IA",
        "KS", "KY", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NH",
        "NJ", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN",
        "UT", "VT", "VA", "WV", "WY",
    ]
]

NON_COMPETE_ENFORCEABILITY: Dict[str, str] = {
    "CA": "NON-COMPETE VOID — California Business and Professions Code § 16600 bans non-competes entirely (with limited exceptions). Employees in CA cannot be bound by non-competes.",
    "ND": "Non-competes generally void — very limited enforceability.",
    "OK": "Non-competes generally void (with narrow exceptions for sale of business).",
    "MN": "Non-competes void for agreements signed after January 1, 2023.",
    "FL": "Strongly enforceable — courts routinely enforce; must have legitimate business interest.",
    "TX": "Enforceable if: ancillary to enforceable agreement, reasonable in time (2 yrs), geography, scope.",
    "NY": "Enforced if: protects legitimate employer interest, reasonable in scope, not unduly harsh.",
    "DEFAULT": "Enforced if: reasonable in duration (typically ≤2 years), geography (narrowly tailored), and scope (limited to competitive activities). Requires legitimate business interest.",
}

CHILD_SUPPORT_MODELS: Dict[str, str] = {
    "income_shares": ["AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DC", "FL", "GA", "HI", "ID", "IL", "IN",
                       "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV",
                       "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN",
                       "UT", "VT", "VA", "WA", "WV", "WI", "WY"],
    "percentage_of_income": ["TX", "WI"],
    "melson": ["DE", "HI", "MT"],
}


# ---------------------------------------------------------------------------
# Personal Legal Advisor
# ---------------------------------------------------------------------------

class PersonalLegalAdvisor:
    """
    Navigates personal legal situations: family law, consumer rights,
    employment rights, identity theft, and more.
    """

    def family_law_guide(self, situation: dict) -> FamilyLawStrategy:
        """
        Generate a family law strategy based on the situation.

        Args:
            situation: dict with 'type' (divorce, custody, support, prenup),
                       'state', 'married_years', 'children', 'assets',
                       'income_disparity', 'domestic_violence'
        """
        situation_type = situation.get("type", "divorce").lower()
        state = situation.get("state", "CA").upper()
        married_years = situation.get("married_years", 5)
        children = situation.get("children", [])
        income_disparity = situation.get("income_disparity", False)
        domestic_violence = situation.get("domestic_violence", False)
        has_minor_children = any(c.get("age", 18) < 18 for c in children)
        is_community_property = state in COMMUNITY_PROPERTY_STATES

        if situation_type == "divorce":
            overview = (
                f"Divorce in {state} ({'Community Property State' if is_community_property else 'Equitable Distribution State'}). "
                f"After {married_years} years of marriage"
                + (f" with {len(children)} child(ren)" if children else "")
                + ". Key issues: property division"
                + (", child custody and support" if has_minor_children else "")
                + (", spousal support (alimony)" if income_disparity else "")
                + "."
            )

            key_issues = ["Asset division — marital vs. separate property", "Debt allocation"]
            if has_minor_children:
                key_issues += ["Legal custody (decision-making)", "Physical custody (parenting schedule)", "Child support calculation"]
            if income_disparity:
                key_issues.append("Spousal support / alimony")
            key_issues += ["Retirement account division (QDRO)", "Tax implications", "Name change"]

            legal_options = [
                {"option": "Uncontested Divorce", "description": "Both parties agree on all terms. File jointly. Cost: $500-$3,000.", "best_for": "Short marriages, no children, minimal assets"},
                {"option": "Mediation", "description": "Neutral mediator helps reach agreement. Cost: $1,500-$8,000 total. Non-binding — still need attorney to review.", "best_for": "Cooperative parties who need help negotiating"},
                {"option": "Collaborative Divorce", "description": "Each party has attorney; all agree to stay out of court. Cost: $5,000-$30,000 each.", "best_for": "Complex assets, cooperative parties"},
                {"option": "Contested Litigation", "description": "Each party has attorney; judge decides disputed issues. Cost: $15,000-$100,000+ each.", "best_for": "Domestic violence, hidden assets, extreme conflict"},
            ]

            property_division = (
                f"In {state} ({'community property' if is_community_property else 'equitable distribution'}): "
                + (
                    "Community property states (CA, TX, AZ, NV, WA, etc.): Property acquired during marriage is OWNED 50/50 — divided equally."
                    if is_community_property else
                    "Equitable distribution: Courts divide marital property 'fairly' (not necessarily 50/50). Factors: marriage length, contributions, earning capacity, separate property."
                )
            )

            steps = [
                "1. Document all assets and debts (bank statements, tax returns, mortgage statements)",
                "2. Open individual bank account in your name only",
                "3. Pull credit reports to identify joint accounts",
                "4. Consult with a family law attorney in your state",
                "5. Consider mediation to reduce costs",
                "6. File Petition for Dissolution" + (f" (in {state}, minimum waiting period varies)" if True else ""),
                "7. Serve spouse with papers",
                "8. Attend mediation or negotiate settlement",
                "9. Finalize Marital Settlement Agreement",
                "10. Obtain Judgment of Dissolution from court",
            ]

            if domestic_violence:
                steps.insert(0, "PRIORITY: Safety first — contact National Domestic Violence Hotline: 1-800-799-7233")
                steps.insert(1, "File for a Domestic Violence Restraining Order (DVRO) immediately")
                steps.insert(2, "Contact a legal aid organization for free assistance")

            documents = [
                "Last 3 years tax returns",
                "Pay stubs (last 3 months)",
                "Bank/investment statements (last 3 years)",
                "Mortgage/property documents",
                "Retirement account statements",
                "Marriage certificate",
                "Birth certificates of children",
                "Prenuptial agreement (if any)",
                "Business financial statements (if applicable)",
                "Debt statements (credit cards, car loans, student loans)",
            ]

            return FamilyLawStrategy(
                situation=situation_type,
                overview=overview,
                key_issues=key_issues,
                legal_options=legal_options,
                state_specific_notes=property_division,
                steps_to_take=steps,
                documents_needed=documents,
                estimated_costs="Uncontested: $1,500-$5,000 | Mediated: $5,000-$15,000 | Litigated: $25,000-$150,000+",
                do_it_yourself_options="LegalZoom, CompleteCase, or court self-help center for uncontested divorces with no children and minimal assets",
                when_to_hire_attorney="Always if children involved, significant assets, business interests, pension/retirement accounts, or domestic violence. Get at minimum a consultation.",
            )

        elif situation_type in ["custody", "child_custody"]:
            overview = "Child custody involves two components: Legal custody (decision-making authority) and Physical custody (where child lives). Courts apply the 'Best Interests of the Child' standard."
            key_issues = [
                "Legal custody: Sole (one parent decides) vs. Joint (both parents decide together)",
                "Physical custody: Primary residence vs. shared custody (50/50 parenting schedule)",
                "Parenting plan: Specific schedule for weekdays, weekends, holidays, vacations",
                "Child support: Separate from custody; based on income and time with child",
                "Relocation restrictions: Typically require court approval or other parent's consent",
                "Modification: Can request modification if substantial change in circumstances",
            ]
            factors_courts_consider = [
                "Parent-child relationship quality with each parent",
                "Each parent's ability to provide stable home",
                "Child's adjustment to home, school, community",
                "Mental and physical health of parents and child",
                "Willingness of each parent to support child's relationship with other parent",
                "History of domestic violence or abuse",
                "Child's preference (especially teenagers)",
                "Geographic proximity of parents' homes",
                "Work schedules and child care availability",
            ]
            steps = [
                "1. Attempt to negotiate parenting plan directly or with mediator",
                "2. File for custody with family court (file in child's home state — UCCJEA applies)",
                "3. Submit proposed parenting plan",
                "4. Complete required parenting class (many courts require this)",
                "5. Attend mediation (often required before trial)",
                "6. Attend custody hearing if no agreement reached",
                "7. Judge issues custody order based on best interests of child",
            ]
            return FamilyLawStrategy(
                situation="child_custody",
                overview=overview,
                key_issues=key_issues,
                legal_options=[
                    {"option": "Agreement", "description": "Parents create parenting plan together; court approves", "best_for": "Cooperative parents"},
                    {"option": "Mediation", "description": "Neutral mediator helps create parenting plan", "best_for": "Some conflict but willing to negotiate"},
                    {"option": "Custody Evaluation", "description": "Mental health professional evaluates; recommends to court", "best_for": "High conflict; abuse allegations"},
                    {"option": "Litigation", "description": "Judge decides based on evidence and best interests", "best_for": "Abuse, severe conflict, safety concerns"},
                ],
                state_specific_notes=f"Factors courts consider in {state}: " + "; ".join(factors_courts_consider[:5]),
                steps_to_take=steps,
                documents_needed=["Proof of parent-child relationship", "Evidence of involvement in child's life", "Work schedule", "Proposed parenting plan", "Evidence of any abuse/domestic violence", "School and medical records"],
                estimated_costs="Agreed: $1,000-$5,000 | Mediation: $2,000-$8,000 | Litigation: $15,000-$75,000+",
                do_it_yourself_options="Court self-help centers often provide parenting plan forms for uncontested custody",
                when_to_hire_attorney="ALWAYS when there is domestic violence, abuse, international travel risk, or one parent seeks sole custody",
            )

        else:
            # Generic family law guide
            return FamilyLawStrategy(
                situation=situation_type,
                overview=f"Family law matter: {situation_type} in {state}",
                key_issues=["Property rights", "Parental rights", "Support obligations"],
                legal_options=[{"option": "Consult attorney", "description": "Get legal advice for your specific situation", "best_for": "All cases"}],
                state_specific_notes=f"{state} family law governed by state statutes and case law",
                steps_to_take=["1. Document your situation", "2. Consult a family law attorney", "3. Understand your rights and obligations"],
                documents_needed=["Identity documents", "Financial records", "Relevant agreements"],
                estimated_costs="Varies widely — free consultation at many family law firms",
                do_it_yourself_options="Court self-help center; LegalAid.org for income-qualified",
                when_to_hire_attorney="Always recommended for family law matters affecting children or significant assets",
            )

    def name_change_guide(self, state: str) -> NameChangeInstructions:
        """
        Generate step-by-step name change instructions.

        Args:
            state: Two-letter state code
        """
        state = state.upper()
        court_process = [
            f"1. Obtain Name Change Petition form from {state} Superior/District Court (or download from court website)",
            "2. Complete the petition: current name, desired new name, reason for change",
            "3. File with the clerk of court; pay filing fee ($150-$450 depending on state)",
            "4. In some states/counties: publish notice in newspaper (typically 4 consecutive weeks) — required for fraud prevention",
            "5. Attend court hearing (typically 4-6 weeks after filing) — brief, routine if no objections",
            "6. Receive signed court order granting name change — get 10+ certified copies (about $10-$20 each)",
            f"EXCEPTION: Divorce — name change can be included in divorce decree at no extra charge",
            "EXCEPTION: Minor child name change — both parents must consent or court approval required",
        ]

        documents_to_update = [
            {"document": "Social Security Card", "agency": "Social Security Administration (SSA.gov)", "time": "Same day at SSA office; new card in 10-14 days", "cost": "Free", "notes": "Update SSA FIRST — other agencies require SSA update"},
            {"document": "Driver's License / State ID", "agency": "State DMV", "time": "Same day at DMV", "cost": "$20-$35", "notes": "Bring: court order, current ID, proof of SSA update"},
            {"document": "US Passport", "agency": "US Department of State", "time": "6-8 weeks standard; 3-5 weeks expedited", "cost": "$130 (new book) or $30 (update within 1 year)", "notes": "Form DS-5504 (within 1 yr of issue) or DS-82 (renewal)"},
            {"document": "Voter Registration", "agency": "State election office or county clerk", "time": "Immediate online in most states", "cost": "Free", "notes": "Must update before next election"},
            {"document": "Bank Accounts", "agency": "Each financial institution", "time": "1-3 business days per bank", "cost": "Free (may charge for new checks)", "notes": "Bring court order and new ID to each bank"},
            {"document": "Credit Cards", "agency": "Each credit card issuer", "time": "Immediate by phone/app", "cost": "Free", "notes": "New cards issued with updated name"},
            {"document": "Employer / Payroll", "agency": "HR Department", "time": "Next pay cycle", "cost": "Free", "notes": "Required for W-2 accuracy; update Medicare/Social Security withholding"},
            {"document": "Insurance Policies", "agency": "Each insurer (health, auto, life, home)", "time": "1-5 business days", "cost": "Free", "notes": "Contact each insurer directly"},
            {"document": "Real Estate / Property Records", "agency": "County Recorder", "time": "1-3 weeks after recording", "cost": "$20-$50 per document", "notes": "May need to re-record deeds; consult real estate attorney"},
            {"document": "Vehicle Title / Registration", "agency": "State DMV", "time": "Same day or mail", "cost": "$20-$50", "notes": "Required to sell or transfer vehicle"},
            {"document": "Professional Licenses", "agency": "State licensing board", "time": "Varies", "cost": "May vary", "notes": "Required before practicing under new name"},
            {"document": "IRS / Tax Records", "agency": "IRS — update with new name on next year's tax return", "time": "Updated automatically when SSA updated", "cost": "Free", "notes": "Name on tax return must match SSA records"},
        ]

        return NameChangeInstructions(
            state=state,
            court_process=court_process,
            documents_to_update=documents_to_update,
            timeline=(
                "Week 1-2: File petition, pay fee. "
                "Week 2-6: Publish notice (if required). "
                "Week 4-8: Court hearing. "
                "Day of Hearing: Receive court order. "
                "Week 1 after order: Update SSA. "
                "Week 2: Update DMV. "
                "Month 1-3: Update all financial accounts, employer, licenses. "
                "Month 3-6: Passport (if needed)."
            ),
            estimated_cost=(
                f"Court filing fee: $150-$450 | "
                "Certified copies: $100-$200 (10 copies) | "
                "Newspaper publication (if required): $100-$400 | "
                "DMV: $20-$35 | "
                "Total: Approximately $400-$1,100"
            ),
        )

    def identity_theft_response(self, facts: dict) -> IdentityTheftResponsePlan:
        """
        Generate a comprehensive identity theft response plan.

        Args:
            facts: dict with 'discovery_date', 'accounts_affected',
                   'amount_lost', 'tax_fraud_suspected'
        """
        tax_fraud = facts.get("tax_fraud_suspected", False)
        accounts_affected = facts.get("accounts_affected", [])

        immediate_steps = [
            "HOUR 1 — Call your bank's fraud hotline immediately (number on back of card). Request temporary freeze on affected accounts.",
            "HOUR 1-2 — Place fraud alert with ONE credit bureau (they're required to notify the others):",
            "  → Equifax: 1-800-525-6285 | equifax.com/personal/credit-report-services",
            "  → Experian: 1-888-397-3742 | experian.com/fraud",
            "  → TransUnion: 1-800-680-7289 | transunion.com/fraud",
            "DAY 1 — Place credit freeze with ALL THREE bureaus (FREE — most powerful protection):",
            "  Freeze prevents new credit from being opened in your name.",
            "  Remember to UNFREEZE temporarily when you apply for credit.",
            "DAY 1 — File FTC Identity Theft Report at IdentityTheft.gov (creates official report with legal protections)",
            "DAY 1-3 — File police report with local police department (some creditors require this)",
            "DAY 1-7 — Review all three credit reports for unauthorized accounts (AnnualCreditReport.com)",
        ]

        credit_bureau_steps = {
            "fraud_alert": (
                "Initial Fraud Alert: Lasts 1 year. Requires creditors to take 'reasonable steps' to verify identity. "
                "Extended Fraud Alert: Lasts 7 years. Available to identity theft victims with FTC report. "
                "Active Duty Alert: For military service members."
            ),
            "credit_freeze": (
                "Security Freeze (Credit Freeze): Blocks access to your credit report entirely. FREE. "
                "Equifax: 1-800-349-9960 | Experian: 1-888-397-3742 | TransUnion: 1-800-916-8800 "
                "Also freeze: ChexSystems (banking), Innovis, NCTUE, SageStream, EARLY WARNING."
            ),
            "dispute_process": (
                "Dispute fraudulent accounts in writing (certified mail). "
                "Include: FTC report, police report, identity documents. "
                "Bureaus have 30 days to investigate. "
                "Furnisher (bank/creditor) also has 30 days. "
                "If identity theft, 4-day block on fraudulent info (submit FTC report + proof of ID)."
            ),
        }

        irs_protection = (
            "IRS IDENTITY PROTECTION PIN (IP PIN):\n"
            "If your SSN was compromised, apply for an IRS IP PIN.\n"
            "This 6-digit PIN is required to file your tax return and prevents fraudulent returns.\n"
            "Apply at: IRS.gov/ippin (available to all taxpayers — not just victims)\n"
            "IP PIN changes annually; IRS mails it to you in January.\n\n"
            "If fraudulent tax return already filed:\n"
            "1. File Form 14039 (Identity Theft Affidavit) with the IRS\n"
            "2. File your return by mail with Form 14039 attached\n"
            "3. IRS Identity Theft Victims Assistance: 1-800-908-4490\n"
            "4. Expect resolution to take 18-24 months (IRS is severely backlogged)"
        ) if tax_fraud else (
            "IRS Identity Protection PIN: Even without current tax fraud, consider enrolling at IRS.gov/ippin to prevent future tax identity theft."
        )

        return IdentityTheftResponsePlan(
            immediate_steps=immediate_steps,
            credit_bureau_steps=credit_bureau_steps,
            ftc_report_steps=(
                "GO TO IdentityTheft.gov — the ONLY official FTC identity theft website.\n"
                "1. Select the types of fraud that occurred\n"
                "2. Enter information about what happened\n"
                "3. Review your personalized recovery plan\n"
                "4. Download your official FTC Identity Theft Report (has legal significance)\n"
                "5. The site generates pre-filled letters to send to creditors and bureaus\n"
                "Note: FTC report gives you rights to: extended fraud alert (7 years), "
                "4-day credit block, stop collections on fraudulent debts, get free copies of fraudulent applications"
            ),
            police_report_guidance=(
                "File a police report at your local police department:\n"
                "1. Bring: government ID, proof of theft (FTC report, account statements showing fraud)\n"
                "2. Request a copy of the police report number\n"
                "3. Some departments allow online reporting for financial crimes\n"
                "Why file: Some creditors require police report to waive fraudulent charges. "
                "Also required for extended fraud alert and some insurance claims."
            ),
            disputing_fraudulent_accounts=(
                "DISPUTE FRAUDULENT ACCOUNTS:\n"
                "1. Send dispute letters to each credit bureau BY CERTIFIED MAIL (return receipt)\n"
                "2. Attach: FTC Identity Theft Report, police report, copy of government ID, copy of SSN card\n"
                "3. For each fraudulent account — also write to the creditor's fraud department directly\n"
                "4. Creditor's fraud department address: Google '[Bank Name] fraud department address'\n"
                "5. Keep copies of everything. Log dates of all communications.\n"
                "6. Credit bureaus must complete investigation in 30 days (sometimes 45 days).\n"
                "7. If not resolved: File CFPB complaint at consumerfinance.gov/complaint\n"
                "8. Consider identity theft attorney if major fraud not resolved"
            ),
            irs_protection=irs_protection,
            ongoing_monitoring=[
                "Monitor credit reports monthly (free via CreditKarma, Credit Sesame, or AnnualCreditReport.com)",
                "Set up fraud alerts on all bank and credit card accounts",
                "Enable 2-factor authentication on all financial accounts",
                "Consider identity theft monitoring service (LifeLock, Experian IdentityWorks, etc.)",
                "Review Social Security Statement annually at ssa.gov for fraudulent work history",
                "Check IRS transcript annually for fraudulent tax returns",
            ],
            resources=[
                "FTC: IdentityTheft.gov (primary resource)",
                "FTC Complaint: ReportFraud.ftc.gov",
                "CFPB Complaint: consumerfinance.gov/complaint",
                "Social Security Fraud: ssa.gov/fraud",
                "Medicare Fraud: 1-800-MEDICARE",
                "National Consumer Law Center: nclc.org",
            ],
        )

    def consumer_rights_guide(self) -> ConsumerRightsGuide:
        """Generate a comprehensive consumer rights guide."""
        return ConsumerRightsGuide(
            lemon_law_overview=(
                "LEMON LAWS — VEHICLE CONSUMER PROTECTION:\n"
                "Federal: Magnuson-Moss Warranty Act (all products)\n"
                "State lemon laws: Vary by state; most cover new vehicles\n"
                "California: One of strongest — covers used vehicles (up to 18 months/18,000 miles if original warranty)\n\n"
                "General rule (most states): Manufacturer must repurchase or replace if:\n"
                "- 4+ repair attempts for same defect, OR\n"
                "- 30+ days out of service within 1 year / warranty period\n"
                "- Defect substantially impairs use, value, or safety\n\n"
                "PROCESS: Notify manufacturer in writing → Allow final repair attempt → Demand arbitration (often required first) → File lemon law claim\n"
                "ATTORNEY FEES: Most state lemon laws require manufacturer to pay your attorney fees — many attorneys take these cases on contingency"
            ),
            warranty_rights=(
                "MAGNUSON-MOSS WARRANTY ACT (Federal):\n"
                "Full Warranty: Must repair/replace within reasonable time, no charge.\n"
                "Limited Warranty: Can restrict coverage but must be clear and conspicuous.\n"
                "Implied Warranty of Merchantability: Product must work as expected for its ordinary purpose — CANNOT be disclaimed if written warranty given.\n\n"
                "EXTENDED WARRANTIES / SERVICE CONTRACTS:\n"
                "Usually NOT worth it. Average claim < cost of contract.\n"
                "Exception: Electronics, appliances, vehicles with high repair costs.\n"
                "Tip: Credit cards often provide free extended warranty protection (Amex, Chase Sapphire, etc.)"
            ),
            cooling_off_rule=(
                "FTC COOLING-OFF RULE — 3-DAY RIGHT TO CANCEL:\n"
                "Applies to: Door-to-door sales, sales at temporary locations (fairs, hotels, restaurants), sales outside seller's regular place of business.\n"
                "Threshold: Sales of $25+ at your home; $130+ at temporary locations.\n"
                "You have until midnight of the 3rd business day to cancel.\n"
                "Seller MUST: Give you a dated copy of the contract, two cancellation forms, and notice of your right to cancel.\n"
                "How to cancel: Written notice (mail, email, fax). Keep proof of delivery.\n\n"
                "DOES NOT APPLY TO: Real estate, insurance, securities, vehicle sales at permanent location, arts/crafts fairs.\n\n"
                "STATE COOLING-OFF LAWS: Many states have additional rights. Check your state consumer protection office."
            ),
            debt_collection_rights=(
                "FAIR DEBT COLLECTION PRACTICES ACT (FDCPA):\n"
                "Covers: Third-party debt collectors (not original creditors)\n\n"
                "Collectors CANNOT:\n"
                "- Call before 8am or after 9pm\n"
                "- Call at work if you tell them not to\n"
                "- Harass, oppress, or abuse you\n"
                "- Use false or misleading statements\n"
                "- Threaten arrest (debt is civil, not criminal)\n"
                "- Discuss your debt with third parties (except spouse)\n"
                "- Continue calling after you send written cease communication letter\n\n"
                "YOUR RIGHTS:\n"
                "- Request debt validation (within 30 days of first contact)\n"
                "- Send cease communication letter (they can only contact to notify of action)\n"
                "- Dispute the debt in writing\n"
                "- Sue collector for violations: $1,000 statutory damages + actual damages + attorney fees\n"
                "- Class actions available\n\n"
                "STATUTE OF LIMITATIONS: After SOL expires, debt is 'time-barred' — collector cannot sue.\n"
                "SOL varies by state (typically 3-6 years); restarted if you make payment or acknowledge debt in writing."
            ),
            telemarketing_protections=(
                "TELEPHONE CONSUMER PROTECTION ACT (TCPA):\n"
                "National Do Not Call Registry: Register at donotcall.gov. Takes effect 31 days after registration.\n"
                "Exceptions: Charities, political calls, surveys, companies you have existing relationship with.\n"
                "Violations: $500-$1,500 per illegal call. Class actions common (major settlements).\n\n"
                "ROBOCALLS:\n"
                "Illegal without prior express written consent (for marketing).\n"
                "NEVER press '1' to opt out — confirms active number and may increase calls.\n"
                "Use: Nomorobo, Hiya, or carrier call-blocking services.\n"
                "Report to FTC at donotcall.gov or FCC at fcc.gov/consumers/guides/stop-unwanted-robocalls-and-texts"
            ),
            data_privacy_rights=(
                "US DATA PRIVACY RIGHTS:\n\n"
                "California (CCPA/CPRA) — Strongest state law:\n"
                "- Right to know what data is collected\n"
                "- Right to delete personal information\n"
                "- Right to opt out of sale/sharing\n"
                "- Right to correct inaccurate information\n"
                "- Right to limit use of sensitive personal information\n"
                "- No retaliation for exercising rights\n\n"
                "Other states with privacy laws: VA, CO, CT, UT, TX, OR, MT, TN, IN — similar rights\n\n"
                "Federal laws: HIPAA (health data), FERPA (education records), COPPA (children), GLBA (financial data)\n\n"
                "GDPR (Europe): If you interact with EU residents, must comply with GDPR.\n"
                "Data subject rights: Access, rectification, erasure ('right to be forgotten'), portability, objection\n\n"
                "HOW TO EXERCISE RIGHTS: Look for 'Privacy Policy' → 'Do Not Sell My Personal Information' on any website. Send written request via certified mail."
            ),
            key_federal_laws=[
                {"law": "FDCPA", "full_name": "Fair Debt Collection Practices Act", "protects": "Consumers from abusive debt collectors"},
                {"law": "FCRA", "full_name": "Fair Credit Reporting Act", "protects": "Accuracy of credit reports; right to dispute"},
                {"law": "TILA", "full_name": "Truth in Lending Act", "protects": "Disclosure of credit terms; right to rescind"},
                {"law": "RESPA", "full_name": "Real Estate Settlement Procedures Act", "protects": "Mortgage disclosure; prohibits kickbacks"},
                {"law": "TCPA", "full_name": "Telephone Consumer Protection Act", "protects": "Against unwanted calls/texts"},
                {"law": "CCPA", "full_name": "California Consumer Privacy Act", "protects": "CA residents' data privacy rights"},
                {"law": "Magnuson-Moss", "full_name": "Magnuson-Moss Warranty Act", "protects": "Product warranty disclosures and enforcement"},
                {"law": "UDAP", "full_name": "Unfair/Deceptive Acts and Practices (state versions)", "protects": "Against fraud and deceptive business practices"},
            ],
        )

    def employment_rights_guide(self, situation: dict) -> EmploymentRightsAnalysis:
        """
        Analyze employment rights for a given situation.

        Args:
            situation: dict with 'state', 'termination_reason', 'has_contract',
                       'wage_issues', 'non_compete', 'hours_worked', 'income'
        """
        state = situation.get("state", "CA").upper()
        termination_reason = situation.get("termination_reason", "").lower()
        has_contract = situation.get("has_contract", False)
        wage_issues = situation.get("wage_issues", False)
        non_compete = situation.get("non_compete", "")
        hours_worked = situation.get("hours_worked", 40)
        income = situation.get("income", 60_000)

        # At-will analysis
        at_will_states = [s for s in EQUITABLE_DISTRIBUTION_STATES]  # most states are at-will
        is_at_will = state != "MT"  # Montana is the only non-at-will state
        at_will_analysis = (
            f"{'AT-WILL EMPLOYMENT' if is_at_will else 'JUST CAUSE STATE'} in {state}. "
            + (
                "At-will means either party can end employment at any time for any reason (or no reason), "
                "EXCEPT for illegal reasons (discrimination, retaliation, etc.). "
                "Montana is the only state requiring just cause for termination after probationary period."
                if is_at_will else
                "Montana requires just cause for termination after the probationary period."
            )
        )

        # Wrongful termination
        wrongful_termination_factors = [
            "ILLEGAL REASONS FOR TERMINATION (wrongful termination regardless of at-will):",
            "Discrimination: Race, color, religion, sex, national origin, age (40+), disability (federal Title VII, ADEA, ADA)",
            "Retaliation: For filing workers' comp, OSHA complaint, discrimination complaint, whistleblowing",
            "Public policy violation: Fired for jury duty, military leave, voting",
            "Breach of implied contract: Employee handbook promises, verbal assurances of job security",
            "Constructive discharge: Employer makes working conditions intolerable to force resignation",
        ]

        if "discrimination" in termination_reason or "retaliation" in termination_reason:
            wrongful_termination_factors.append("DEADLINE ALERT: Must file EEOC charge within 180/300 days of termination — DO THIS IMMEDIATELY")

        # Wage theft rights
        wage_analysis = (
            "WAGE THEFT RIGHTS:\n"
            f"Federal minimum wage: $7.25/hour (your state may be higher)\n"
            f"Overtime: 1.5x regular rate for hours over 40/week (FLSA)\n"
            f"Estimated unpaid overtime: ${max(0, hours_worked - 40) * (income / 52 / 40) * 1.5 * 52:,.0f}/year (if regularly working {hours_worked} hrs/week)\n\n"
            "Common wage theft: Misclassification as exempt or contractor; off-the-clock work; tip theft; unauthorized deductions\n"
            "File complaint: US DOL Wage and Hour Division (dol.gov/agencies/whd) — free investigation\n"
            "Statute of limitations: 2 years (3 if willful)\n"
            "Recovery: Back wages + equal amount in liquidated damages + attorney fees"
        ) if wage_issues else "No current wage issues reported."

        # Non-compete analysis
        nc_state_rule = NON_COMPETE_ENFORCEABILITY.get(state, NON_COMPETE_ENFORCEABILITY["DEFAULT"])
        nc_analysis = (
            f"NON-COMPETE ENFORCEABILITY IN {state}:\n"
            f"{nc_state_rule}\n\n"
            f"Your agreement: {non_compete[:200] if non_compete else 'Not provided'}\n\n"
            "FTC Non-Compete Rule (2024): FTC issued rule banning non-competes nationally for most workers "
            "— this rule is being challenged in courts. Check current status at ftc.gov."
        ) if non_compete else f"Non-compete enforceability in {state}: {nc_state_rule}"

        # Unemployment
        unemployment = (
            "UNEMPLOYMENT ELIGIBILITY (general federal standards):\n"
            "Eligible if: Involuntary termination (layoff, company shutdown, fired without just cause)\n"
            "NOT eligible if: Quit voluntarily (except constructive discharge), fired for serious misconduct\n"
            "Benefit amount: Typically 40-50% of prior wages, up to state maximum\n"
            "Duration: 12-26 weeks depending on state\n"
            "File IMMEDIATELY — benefits paid from date of claim, not date of termination\n"
            "File at: State unemployment insurance website (varies by state)\n"
            "FIGHT DENIAL: Employer may contest — appeal all denials; you're often right"
        )

        # WARN Act
        warn = (
            "WARN ACT (Workers Adjustment and Retraining Notification Act):\n"
            "Requires 60-day advance notice for:\n"
            "- Plant closings affecting 50+ workers\n"
            "- Mass layoffs affecting 500+ workers (or 50+ if ≥33% of workforce)\n"
            "- Employers with 100+ full-time employees\n"
            "Violation: Up to 60 days back pay and benefits\n"
            "State WARN laws: CA, NY, NJ, and others have stronger state WARN acts"
        )

        return EmploymentRightsAnalysis(
            employment_type="At-Will" if is_at_will else "Just Cause",
            at_will_analysis=at_will_analysis,
            wrongful_termination_factors=wrongful_termination_factors,
            wage_theft_rights=wage_analysis,
            non_compete_analysis=nc_analysis,
            unemployment_eligibility=unemployment,
            warn_act_applicability=warn,
            recommended_actions=[
                "1. Document everything — save all emails, performance reviews, HR communications",
                "2. File for unemployment immediately (do not wait)",
                "3. Consult employment attorney — initial consultations often free",
                "4. File EEOC charge within 180/300 days if discrimination suspected",
                "5. Request personnel file from employer (right in most states)",
                "6. Review severance agreement carefully before signing (21-45 days to consider; 7 days to revoke for age discrimination releases)",
                "7. Check WARN Act compliance if part of mass layoff",
            ],
        )
