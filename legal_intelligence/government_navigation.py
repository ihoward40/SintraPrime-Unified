"""
Government Navigator — SintraPrime Legal Intelligence System

Comprehensive guide to navigating federal and state government agencies,
FOIA requests, benefits programs, regulatory compliance, and government contracting.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class FOIARequest:
    """
    A properly formatted Freedom of Information Act request.

    Example:
        >>> request = FOIARequest(
        ...     agency="FBI",
        ...     foia_office_address="FBI FOIA/PA Request, Record/Information Dissemination Section, 170 Marcel Drive, Winchester, VA 22602",
        ...     subject="Records related to John Doe, DOB 01/01/1980",
        ...     fee_waiver_language="Requester qualifies for fee waiver as a member of the news media",
        ...     expedited_processing=False
        ... )
    """
    agency: str
    foia_office_address: str
    subject: str
    fee_waiver_language: str
    expedited_processing: bool
    request_text: str = ""
    legal_basis: str = "5 U.S.C. § 552 (Freedom of Information Act)"
    response_deadline: str = "20 business days (basic); 10 days for expedited"
    appeal_rights: str = "Appeal denial within 90 days to agency head; then federal court"
    tips: List[str] = field(default_factory=list)


@dataclass
class BenefitsAnalysis:
    """
    Analysis of government benefits eligibility.

    Example:
        >>> analysis = BenefitsAnalysis(
        ...     eligible_programs=["SSDI", "Medicare"],
        ...     likely_disqualified=["SSI (over income limit)"],
        ...     monthly_benefit_estimate={"SSDI": "$1,450/month", "Medicare": "After 24 months SSDI"},
        ...     application_tips=["Apply for SSDI immediately — retroactive benefits possible"]
        ... )
    """
    eligible_programs: List[str]
    likely_disqualified: List[str]
    monthly_benefit_estimate: Dict[str, str]
    application_tips: List[str]
    appeal_rights: Dict[str, str] = field(default_factory=dict)
    priority_order: List[str] = field(default_factory=list)


@dataclass
class AppealStrategy:
    """
    Strategy for appealing a government agency decision.

    Example:
        >>> strategy = AppealStrategy(
        ...     agency="Social Security Administration",
        ...     decision="Denial of SSDI",
        ...     appeal_stages=["Reconsideration", "ALJ Hearing", "Appeals Council", "Federal District Court"],
        ...     deadlines={"Reconsideration": "60 days from denial"},
        ...     key_arguments=["Treating physician opinion", "RFC limitations", "Listing criteria"]
        ... )
    """
    agency: str
    decision: str
    appeal_stages: List[str]
    deadlines: Dict[str, str]
    key_arguments: List[str]
    success_rates: Dict[str, str] = field(default_factory=dict)
    tips: List[str] = field(default_factory=list)
    legal_basis: str = ""


@dataclass
class ComplianceChecklist:
    """
    Regulatory compliance checklist for a business.

    Example:
        >>> checklist = ComplianceChecklist(
        ...     business_type="Restaurant",
        ...     state="California",
        ...     federal_requirements=["EIN (IRS)", "FLSA compliance", "OSHA food service standards"],
        ...     state_requirements=["State food handler's license", "CA labor law posters"],
        ...     licenses_needed=["Local health permit", "Business license"],
        ...     annual_filings=["Form 940 (FUTA)", "Form 941 (Payroll taxes quarterly)"]
        ... )
    """
    business_type: str
    state: str
    federal_requirements: List[str]
    state_requirements: List[str]
    licenses_needed: List[str]
    annual_filings: List[str]
    penalties_for_noncompliance: Dict[str, str] = field(default_factory=dict)
    priority_action_items: List[str] = field(default_factory=list)


@dataclass
class ContractingStrategy:
    """
    Government contracting strategy.

    Example:
        >>> strategy = ContractingStrategy(
        ...     business_size="Small",
        ...     applicable_set_asides=["Small Business Set-Aside", "8(a) if eligible"],
        ...     registration_steps=["Register in SAM.gov", "Obtain DUNS/UEI number"],
        ...     key_opportunities=["GSA Schedule", "SBIR grants"]
        ... )
    """
    business_size: str
    applicable_set_asides: List[str]
    registration_steps: List[str]
    key_opportunities: List[str]
    certification_programs: List[str] = field(default_factory=list)
    gsa_schedule_applicable: bool = False
    timeline: str = ""
    annual_revenue_thresholds: Dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Government Navigator
# ---------------------------------------------------------------------------

class GovernmentNavigator:
    """
    Complete guide to navigating federal and state government — FOIA, benefits,
    agency appeals, regulatory compliance, and government contracting.

    Example:
        >>> nav = GovernmentNavigator()
        >>> request = nav.foia_request_generator("FBI", "All records on John Doe")
        >>> "552" in request.legal_basis
        True
    """

    FOIA_OFFICES: Dict[str, Dict[str, str]] = {
        "FBI": {
            "address": "FBI FOIA/PA Request, Record/Information Dissemination Section, 170 Marcel Drive, Winchester, VA 22602",
            "online": "https://efoia.fbi.gov/",
            "email": "foiparequest@ic.fbi.gov",
            "fee_schedule": "First 100 pages free; thereafter $0.10/page",
        },
        "CIA": {
            "address": "Information and Privacy Coordinator, Central Intelligence Agency, Washington, D.C. 20505",
            "online": "https://www.cia.gov/resources/foia/",
            "email": "cia-foia@cia.gov",
            "fee_schedule": "2 hours search; 100 pages duplication free",
        },
        "DHS": {
            "address": "DHS Privacy Office, FOIA Office, 245 Murray Lane SW, Stop-0655, Washington DC 20528",
            "online": "https://www.dhs.gov/foia",
            "email": "foia@hq.dhs.gov",
            "fee_schedule": "Per DHS FOIA regulation, 6 CFR Part 5",
        },
        "DOJ": {
            "address": "Office of Information Policy (OIP), 441 G Street NW, 6th Floor, Washington DC 20530",
            "online": "https://www.justice.gov/oip/make-your-request",
            "email": "OIP.FOIA@usdoj.gov",
            "fee_schedule": "Per DOJ FOIA regulation, 28 CFR § 16.11",
        },
        "IRS": {
            "address": "IRS FOIA Request, Stop 211, Attn: Disclosure Scanning Project, 201 W. Rivercenter Blvd., Covington, KY 41011",
            "online": "https://www.irs.gov/privacy-disclosure/foia-guidelines",
            "email": "N/A — mail or fax preferred",
            "fee_schedule": "Per 26 CFR § 601.702",
        },
        "EPA": {
            "address": "EPA National FOIA Office, 1200 Pennsylvania Ave NW, Washington DC 20460",
            "online": "https://www.epa.gov/foia/submit-foia-request",
            "email": "hq.foia@epa.gov",
            "fee_schedule": "Per 40 CFR Part 2",
        },
        "SEC": {
            "address": "Office of FOIA Services, 100 F Street, NE, Washington, DC 20549",
            "online": "https://efts.sec.gov/LATEST/search-index?q=%22foia%22&dateRange=custom",
            "email": "foiapa@sec.gov",
            "fee_schedule": "Per 17 CFR § 200.80(d)",
        },
        "DOD": {
            "address": "Varies by component — submit to component with custodial records",
            "online": "https://www.defense.gov/Resources/",
            "email": "Varies by component",
            "fee_schedule": "Per 32 CFR Part 286",
        },
        "USCIS": {
            "address": "National Records Center, FOIA/PA Office, PO Box 648010, Lee's Summit, MO 64064-8010",
            "online": "https://www.uscis.gov/records/request-records-through-the-freedom-of-information-privacy-act",
            "email": "uscis.foia@uscis.dhs.gov",
            "fee_schedule": "No fee for immigration records requests",
        },
        "DEFAULT": {
            "address": "FOIA Officer, [Agency Name], Washington, DC",
            "online": "See agency website — FOIA page",
            "email": "See agency FOIA page",
            "fee_schedule": "Per agency-specific FOIA regulations",
        },
    }

    def foia_request_generator(self, agency: str, information_sought: str) -> FOIARequest:
        """
        Generate a properly formatted FOIA request with fee waiver language.

        Args:
            agency: Federal agency name (e.g., "FBI", "EPA", "IRS").
            information_sought: Description of records sought.

        Returns:
            FOIARequest with complete request text and instructions.

        Example:
            >>> nav = GovernmentNavigator()
            >>> req = nav.foia_request_generator("FBI", "All records on John Doe, SSN 123-45-6789")
            >>> "552" in req.legal_basis
            True
        """
        agency_upper = agency.upper()
        office_info = self.FOIA_OFFICES.get(agency_upper, self.FOIA_OFFICES["DEFAULT"])

        fee_waiver = (
            "Pursuant to 5 U.S.C. § 552(a)(4)(A)(iii), I request a waiver of all fees associated "
            "with this request because disclosure of the information is in the public interest as it "
            "is likely to contribute significantly to public understanding of the operations or "
            "activities of the government and is not primarily in my commercial interest. "
            "In the alternative, please categorize me as a 'non-commercial requester' and waive "
            "search and duplication fees pursuant to 5 U.S.C. § 552(a)(4)(A)(ii)(III)."
        )

        request_text = f"""
FREEDOM OF INFORMATION ACT REQUEST

VIA: [Mail / Email / Online Portal]
DATE: [Date of Submission]

FOIA Officer
{agency} FOIA Office
{office_info['address']}

RE: FOIA Request — {information_sought[:80]}

Dear FOIA Officer:

Pursuant to the Freedom of Information Act (FOIA), 5 U.S.C. § 552, and the {agency} implementing
regulations, I hereby request access to and copies of the following agency records:

RECORDS REQUESTED:
{information_sought}

Please search all record systems, databases, files, and locations likely to contain responsive records,
including but not limited to electronic records, email, memoranda, reports, and correspondence.

DATE RANGE: [Insert applicable date range, or "All records regardless of date"]

TIME PERIOD: I request that you expedite processing of this request because [insert basis for expedited
processing, if applicable — e.g., "compelling need involving imminent threat to life or safety" or
"urgency to inform the public concerning actual or alleged Federal Government activity"].

FEE WAIVER REQUEST:
{fee_waiver}

If fees cannot be waived, please notify me before incurring charges exceeding $25.00 and provide an
itemized estimate of anticipated costs.

EXPEDITED PROCESSING:
[If applicable: "I request expedited processing pursuant to 5 U.S.C. § 552(a)(6)(E) because:
[state basis — imminent threat to life, or urgency to inform public about government activity].
I certify that this statement is true and correct to the best of my knowledge and belief."]

DELIVERY FORMAT: Please provide records in electronic format (PDF) via email if possible.

CERTIFICATION: I certify that I am not seeking the requested records for commercial purposes.

If any responsive records are withheld in whole or in part, please identify each such record,
state the specific FOIA exemption(s) relied upon, and provide a Vaughn index so that I may
assess the applicability of the claimed exemption(s).

I expect to receive your determination within 20 business days as required by 5 U.S.C. § 552(a)(6)(A).
If this request is denied in whole or in part, I will appeal the denial to the appropriate official.

Thank you for your assistance.

Sincerely,
[Requester Name]
[Address]
[Email]
[Phone]
[Date]
"""

        tips = [
            f"Submit online at: {office_info.get('online', 'See agency website')}",
            f"Email option: {office_info.get('email', 'See agency FOIA page')}",
            "Keep confirmation number and track request at FOIAonline.gov or agency portal",
            "If no response in 20 days, you may file suit in federal district court (5 U.S.C. § 552(a)(6)(C))",
            "Request Vaughn index if records are withheld — required in litigation",
            "FOIA exemptions: (b)(1) classified, (b)(3) other statutes, (b)(5) deliberative process, (b)(6) personal privacy, (b)(7) law enforcement",
            "Privacy Act request (5 U.S.C. § 552a) may be more effective for records about yourself",
            "File appeal within 90 days of denial to agency head before suing in federal court",
        ]

        return FOIARequest(
            agency=agency,
            foia_office_address=office_info["address"],
            subject=information_sought,
            fee_waiver_language=fee_waiver,
            expedited_processing=False,
            request_text=request_text.strip(),
            legal_basis="5 U.S.C. § 552 (Freedom of Information Act)",
            response_deadline="20 business days; 10 days for expedited",
            appeal_rights="Appeal denial within 90 days to agency head; then file in federal district court",
            tips=tips,
        )

    def government_benefits_analyzer(self, facts: dict) -> BenefitsAnalysis:
        """
        Analyze eligibility for federal and state government benefits.

        Args:
            facts: Dict with individual facts (disabled, income, assets, veteran, age,
                   citizenship_status, children, etc.).

        Returns:
            BenefitsAnalysis with eligible programs and tips.

        Example:
            >>> nav = GovernmentNavigator()
            >>> result = nav.government_benefits_analyzer({
            ...     "disabled": True, "worked_5_of_last_10_years": True,
            ...     "age": 45, "income": 0
            ... })
            >>> "SSDI" in result.eligible_programs
            True
        """
        eligible = []
        disqualified = []
        estimates: Dict[str, str] = {}
        tips = []

        disabled = facts.get("disabled", False)
        income = facts.get("income", 0)
        assets = facts.get("assets", 0)
        age = facts.get("age", 40)
        veteran = facts.get("veteran", False)
        children = facts.get("children", 0)
        citizen = facts.get("citizen_or_qualified_alien", True)
        worked = facts.get("worked_5_of_last_10_years", False)
        household_size = facts.get("household_size", 1)

        # SSDI — Social Security Disability Insurance
        if disabled and worked:
            eligible.append("SSDI (Social Security Disability Insurance)")
            estimates["SSDI"] = "Average ~$1,537/month (2024); based on earnings record"
            tips.append("Apply for SSDI online at SSA.gov or call 1-800-772-1213 immediately — 5-month waiting period")
            tips.append("SSDI approval rate: ~35% initially; ~55% with ALJ hearing — ALWAYS appeal denials")
        elif disabled and not worked:
            disqualified.append("SSDI (insufficient work history — less than 5 of last 10 years)")

        # SSI — Supplemental Security Income
        if disabled and income < 1971 and assets < 2000:  # 2024 limits approx
            eligible.append("SSI (Supplemental Security Income)")
            estimates["SSI"] = "Up to $943/month (2024 federal benefit rate); state supplement may add more"
            tips.append("SSI asset limit: $2,000 individual / $3,000 couple (not counting home or car)")
        elif income > 1971 or assets > 2000:
            disqualified.append("SSI (over income or asset limit)")

        # Medicare
        if disabled and worked:
            eligible.append("Medicare (after 24 months on SSDI)")
            estimates["Medicare"] = "Automatic after 24 months of SSDI — Part A, B, D available"
        if age >= 65:
            eligible.append("Medicare (age 65+)")
            estimates["Medicare"] = "Part A (free if 40 quarters), Part B (~$174.70/month in 2024)"

        # Medicaid
        federal_poverty_138pct = 20783 * 1.38  # 138% FPL for individual (2024 approx)
        if income < federal_poverty_138pct and citizen:
            eligible.append("Medicaid / CHIP (if expanded state)")
            estimates["Medicaid"] = "Free or low-cost health coverage; income threshold varies by state"
            tips.append("Check eligibility at Healthcare.gov or your state Medicaid office")

        # VA Benefits
        if veteran:
            eligible.append("VA Disability Compensation (if service-connected disability)")
            eligible.append("VA Pension (if wartime veteran, low income, disabled)")
            eligible.append("GI Bill / VA Education Benefits (if applicable)")
            eligible.append("VA Healthcare")
            estimates["VA Disability"] = "$171 - $3,737+/month depending on disability rating (10%-100%)"
            tips.append("File VA disability claim at VA.gov or call 1-800-827-1000; get VSO help (free)")
            tips.append("VA disability claims: gather all service records, medical records, buddy statements")

        # SNAP (Food Stamps)
        snap_gross_limit = {1: 2248, 2: 3047, 3: 3845, 4: 4643}
        snap_limit = snap_gross_limit.get(household_size, 2248 + (household_size - 1) * 798)
        if income < snap_limit and citizen:
            eligible.append("SNAP (Food Stamps / EBT)")
            estimates["SNAP"] = f"Average ~$281/month/person; up to $291/month for individual (2024)"
            tips.append("Apply for SNAP at your county Department of Social Services")
        else:
            disqualified.append("SNAP (over income limit)")

        # HUD / Housing
        if income < 50000:  # Very rough threshold for HUD programs
            eligible.append("Section 8 Housing Choice Voucher (if available — long waitlists)")
            eligible.append("Public Housing (if available)")
            tips.append("WARNING: Section 8 waitlists are typically 2-10 years; apply immediately")

        # TANF
        if children > 0 and income < 24000 and citizen:
            eligible.append("TANF (Temporary Assistance for Needy Families)")
            estimates["TANF"] = "Varies widely by state: $200-$900/month; 60-month lifetime limit"
            tips.append("TANF: 60-month federal lifetime limit; work requirements apply")

        # Social Security Retirement
        if age >= 62 and worked:
            eligible.append("Social Security Retirement (reduced at 62; full at 67)")
            estimates["SS Retirement"] = "Based on earnings record; average ~$1,907/month at full retirement age (2024)"

        # SBA Programs
        if facts.get("small_business", False):
            eligible.append("SBA Loans (7(a), 504, Microloan)")
            eligible.append("SBA EIDL (if disaster declaration)")
            tips.append("Apply for SBA loans at SBA.gov; free counseling at SCORE.org")

        priority = [p for p in eligible if p in ["SSDI", "SSI", "VA Disability Compensation", "Medicare", "Medicaid / CHIP"]]
        priority.extend([p for p in eligible if p not in priority])

        appeal_rights = {
            "SSDI/SSI": "60 days to request reconsideration; 60 days to request ALJ hearing; 60 days to Appeals Council; Federal court",
            "VA": "1 year from decision — Notice of Disagreement (NOD); Board of Veterans Appeals; CAVC",
            "SNAP": "90 days — state fair hearing; state court",
            "Medicaid": "90 days — state fair hearing",
            "HUD/Section 8": "Informal hearing with housing authority; then federal court",
        }

        return BenefitsAnalysis(
            eligible_programs=eligible,
            likely_disqualified=disqualified,
            monthly_benefit_estimate=estimates,
            application_tips=tips,
            appeal_rights=appeal_rights,
            priority_order=priority,
        )

    def agency_appeal_navigator(self, agency: str, decision: str) -> AppealStrategy:
        """
        Navigate the appeal process for a government agency decision.

        Args:
            agency: Agency that made the adverse decision (e.g., "SSA", "VA", "IRS").
            decision: Description of the adverse decision.

        Returns:
            AppealStrategy with stages, deadlines, and tips.

        Example:
            >>> nav = GovernmentNavigator()
            >>> strategy = nav.agency_appeal_navigator("SSA", "Denial of SSDI")
            >>> len(strategy.appeal_stages) >= 3
            True
        """
        agency_upper = agency.upper()

        appeal_frameworks: Dict[str, AppealStrategy] = {
            "SSA": AppealStrategy(
                agency="Social Security Administration",
                decision=decision,
                appeal_stages=[
                    "1. Reconsideration (file within 60 days of denial + 5 days mail)",
                    "2. ALJ Hearing (request within 60 days of reconsideration denial — MOST IMPORTANT STAGE)",
                    "3. SSA Appeals Council (60 days from ALJ decision)",
                    "4. Federal District Court (60 days from Appeals Council denial — 42 U.S.C. § 405(g))",
                    "5. Circuit Court of Appeals",
                ],
                deadlines={
                    "Reconsideration": "60 days + 5 days mail from denial date",
                    "ALJ Hearing Request": "60 days + 5 days from reconsideration denial",
                    "Appeals Council": "60 days + 5 days from ALJ decision",
                    "Federal Court": "60 days + 5 days from Appeals Council action",
                },
                key_arguments=[
                    "Treating physician opinion (RFC limitations, diagnosis, prognosis)",
                    "Listing of Impairments match (20 CFR Part 404, Subpart P, Appendix 1)",
                    "Vocational expert testimony — no jobs exist in national economy",
                    "Credibility of subjective pain/symptom testimony",
                    "Grid rules (age, education, work experience)",
                    "Step 5: transferability of skills",
                ],
                success_rates={
                    "Initial application": "~35%",
                    "Reconsideration": "~13%",
                    "ALJ Hearing": "~55% (varies by ALJ)",
                    "Appeals Council": "~10%",
                    "Federal Court": "Varies — often remanded for new hearing",
                },
                tips=[
                    "NEVER miss a deadline — file for good cause extension if needed",
                    "Get medical evidence from ALL treating sources",
                    "Consider hiring SSDI attorney (no upfront cost — contingency fee, max $7,200)",
                    "ALJ hearing is the most important stage — prepare thoroughly",
                    "Obtain vocational expert's testimony and challenge with DOT cross-reference",
                ],
                legal_basis="42 U.S.C. § 405 (SSA); 20 CFR Part 404 (SSDI); 20 CFR Part 416 (SSI)",
            ),
            "VA": AppealStrategy(
                agency="Department of Veterans Affairs",
                decision=decision,
                appeal_stages=[
                    "1. Supplemental Claim (new and relevant evidence — no deadline)",
                    "2. Higher-Level Review (HLR — 1 year from decision; different adjudicator)",
                    "3. Board of Veterans Appeals (BVA) — Direct Review, Evidence Submission, or Hearing",
                    "4. Court of Appeals for Veterans Claims (CAVC) — 120 days from BVA",
                    "5. Federal Circuit Court of Appeals",
                    "6. U.S. Supreme Court",
                ],
                deadlines={
                    "Supplemental Claim/HLR": "1 year from rating decision for continuous service connection",
                    "BVA Appeal": "1 year from rating decision",
                    "CAVC": "120 days from BVA final decision",
                    "Federal Circuit": "60 days from CAVC",
                },
                key_arguments=[
                    "Nexus between current disability and military service",
                    "Competent lay evidence (buddy statements, personal statements)",
                    "Medical opinions — IME/IMO from private doctor",
                    "CUE (Clear and Unmistakable Error) for old final decisions",
                    "TDIU (Total Disability Individual Unemployability)",
                    "Effective date errors",
                ],
                success_rates={
                    "HLR": "~30% grant some increase",
                    "BVA": "~40% grant or remand",
                    "CAVC": "~75% result in remand or reversal",
                },
                tips=[
                    "Get VSO (Veterans Service Organization) help — free",
                    "Private medical opinion (nexus letter) often key to success",
                    "Request C-file (complete service record file) before any appeal",
                    "TDIU can provide 100% rating even if combined rating is lower",
                    "CAVC is article I court — represented by accredited VA attorney; attorneys work on contingency",
                ],
                legal_basis="38 U.S.C. § 511; 38 CFR Parts 3 and 20; Veterans Appeals Improvement Act (AMA)",
            ),
            "IRS": AppealStrategy(
                agency="Internal Revenue Service",
                decision=decision,
                appeal_stages=[
                    "1. IRS Office of Appeals (Independent review — 30 days from notice typically)",
                    "2. Tax Court (file petition within 90 days of Notice of Deficiency)",
                    "3. U.S. District Court (pay tax first, sue for refund — 2 years from IRS denial)",
                    "4. Court of Federal Claims (alternative to District Court)",
                    "5. Circuit Court of Appeals",
                    "6. U.S. Supreme Court",
                ],
                deadlines={
                    "IRS Appeals": "30 days from CP2000/audit report typically; request within protest period",
                    "Tax Court": "90 days from Notice of Deficiency (150 days if outside US)",
                    "Refund Suit": "2 years from IRS formal denial of refund claim",
                    "Refund Claim": "3 years from original return filing OR 2 years from tax payment (whichever is later)",
                },
                key_arguments=[
                    "Substantiation of deductions (receipts, contemporaneous records)",
                    "Business purpose documentation",
                    "Reasonable cause for penalties (IRC § 6664)",
                    "Substantial authority position (avoid accuracy penalty)",
                    "Innocent spouse relief (IRC § 6015)",
                    "Offer in Compromise (OIC) if legitimate doubt as to collectability",
                ],
                success_rates={
                    "IRS Appeals": "~40% of cases settle at Appeals",
                    "Tax Court": "Most cases settle before trial",
                    "Small Tax Case": "More informal; limited appeal rights",
                },
                tips=[
                    "DO NOT ignore IRS notices — response deadlines are absolute",
                    "Tax Court requires NO payment before filing petition",
                    "District Court requires full payment first (then refund suit)",
                    "IRS Appeals is genuinely independent — use it",
                    "CAP (Collection Appeals Program) for liens/levies",
                    "CDP (Collection Due Process) hearing — request within 30 days of lien/levy notice",
                ],
                legal_basis="IRC § 6212, § 6213, § 6330, § 7441; 26 CFR Part 601",
            ),
            "EEOC": AppealStrategy(
                agency="Equal Employment Opportunity Commission",
                decision=decision,
                appeal_stages=[
                    "1. EEOC Investigation and Mediation (voluntary)",
                    "2. Right to Sue Letter (request after 180 days or upon EEOC determination)",
                    "3. Federal District Court Lawsuit (90 days from Right to Sue letter)",
                    "4. Circuit Court of Appeals",
                    "5. U.S. Supreme Court",
                ],
                deadlines={
                    "EEOC Charge": "180 days from discriminatory act (300 days in deferral states with state agency)",
                    "Right to Sue Request": "180 days after filing charge (may request early)",
                    "Federal Suit": "90 days from receipt of Right to Sue Letter — STRICT DEADLINE",
                },
                key_arguments=[
                    "McDonnell Douglas burden-shifting (disparate treatment)",
                    "Griggs disparate impact analysis",
                    "Comparator evidence (similarly situated employees treated differently)",
                    "Statistical evidence of discrimination",
                    "Temporal proximity (retaliation claims)",
                    "Pretext — legitimate reason is false or insufficient",
                ],
                tips=[
                    "90-day deadline to file suit after Right to Sue is JURISDICTIONAL in most circuits",
                    "File EEOC charge BEFORE consulting about lawsuit — it is a prerequisite",
                    "Request EEOC file (investigative file) via FOIA before filing suit",
                    "State agency (FEP) charge may toll or extend time periods",
                    "Document all discriminatory acts contemporaneously",
                ],
                legal_basis="42 U.S.C. § 2000e-5; 29 CFR Part 1601",
            ),
        }

        for key, strategy in appeal_frameworks.items():
            if key in agency_upper or agency_upper in key:
                return strategy

        # Generic framework
        return AppealStrategy(
            agency=agency,
            decision=decision,
            appeal_stages=[
                "1. Request informal reconsideration with agency",
                "2. Formal administrative appeal to agency board/office",
                "3. Administrative Law Judge (ALJ) Hearing (if available)",
                "4. Appeals to agency head or Appeals Board",
                "5. Federal court review under Administrative Procedure Act (5 U.S.C. § 706)",
            ],
            deadlines={
                "Administrative Appeal": "Typically 30-60 days from adverse decision — check agency regulations",
                "APA Federal Court Review": "6 years from final agency action (28 U.S.C. § 2401(a)) — exceptions apply",
            },
            key_arguments=[
                "Agency decision was arbitrary and capricious (5 U.S.C. § 706(2)(A))",
                "Agency exceeded statutory authority",
                "Agency violated procedural requirements (notice and comment, APA § 553)",
                "Decision not supported by substantial evidence",
                "Constitutional violation",
            ],
            tips=[
                "Exhaust all administrative remedies before federal court",
                "Preserve all arguments in administrative record — cannot raise new issues in court",
                "Request the administrative record in full",
                "Consider seeking a stay of agency action pending appeal",
            ],
            legal_basis="5 U.S.C. §§ 551-706 (Administrative Procedure Act)",
        )

    def regulatory_compliance_checker(self, business_type: str, state: str) -> ComplianceChecklist:
        """
        Generate a regulatory compliance checklist for a business.

        Args:
            business_type: Type of business (e.g., "Restaurant", "Law Firm", "Construction").
            state: State where business operates (e.g., "California", "Texas").

        Returns:
            ComplianceChecklist with federal and state requirements.

        Example:
            >>> nav = GovernmentNavigator()
            >>> checklist = nav.regulatory_compliance_checker("Restaurant", "California")
            >>> len(checklist.federal_requirements) > 0
            True
        """
        # Universal federal requirements
        federal_base = [
            "Employer Identification Number (EIN) — IRS Form SS-4 (free at IRS.gov)",
            "Federal income tax — Form 1120 (Corp), 1065 (Partnership), Schedule C (Sole Prop)",
            "FLSA compliance — minimum wage ($7.25 federal; higher in many states), overtime, recordkeeping",
            "FUTA — Federal Unemployment Tax (Form 940) — 6% on first $7,000 wages",
            "FICA — Social Security and Medicare payroll taxes (Form 941 quarterly)",
            "OSHA compliance — workplace safety standards (29 CFR Parts 1910, 1926 for construction)",
            "ADA compliance — physical access, website accessibility (if applicable)",
            "I-9 verification for all employees",
            "Equal Employment Opportunity — EEOC compliance (15+ employees: Title VII, ADA, ADEA)",
            "ERISA compliance if offering retirement plan",
        ]

        # Industry-specific federal
        industry_specific: Dict[str, List[str]] = {
            "restaurant": [
                "FDA Food Safety Modernization Act (FSMA) compliance",
                "HACCP plan (if processing)",
                "Food Labeling requirements (21 CFR Part 101)",
                "Alcohol: TTB license if manufacturing; state liquor license required",
                "DOL tip credit rules (29 CFR § 531)",
            ],
            "construction": [
                "OSHA 1926 Construction Standards (hard hats, fall protection, scaffolding)",
                "Davis-Bacon Act compliance (federal contracts — prevailing wages)",
                "Contractor licensing requirements vary by state",
                "EPA lead paint and asbestos regulations (40 CFR Parts 745, 61)",
                "CERCLA liability if environmental contamination (42 U.S.C. § 9601)",
            ],
            "healthcare": [
                "HIPAA Privacy and Security Rules (45 CFR Parts 160, 164)",
                "State medical licensing for all practitioners",
                "CMS Medicare/Medicaid enrollment and conditions of participation",
                "DEA registration for controlled substances",
                "FDA device and drug regulations if applicable",
                "EMTALA compliance (emergency treatment requirements) if hospital",
                "Stark Law / Anti-Kickback Statute compliance",
            ],
            "law firm": [
                "State bar admission for all attorneys",
                "IOLTA (Interest on Lawyers Trust Accounts) — required in most states",
                "Malpractice insurance — required in some states; prudent everywhere",
                "Client trust accounting requirements (state bar rules)",
                "Data privacy compliance (client records)",
            ],
            "financial": [
                "SEC registration (if broker-dealer, investment adviser)",
                "FINRA membership (if broker-dealer)",
                "Bank Secrecy Act / AML program (FinCEN requirements)",
                "State money transmitter license (if applicable)",
                "CFPB regulations (if consumer financial products)",
                "Sarbanes-Oxley (if public company)",
            ],
        }

        # Find matching industry
        biz_lower = business_type.lower()
        industry_reqs = []
        for key, reqs in industry_specific.items():
            if key in biz_lower or any(word in biz_lower for word in key.split()):
                industry_reqs.extend(reqs)

        federal_requirements = federal_base + industry_reqs

        # State-specific (key states with notable requirements)
        state_reqs_map: Dict[str, List[str]] = {
            "california": [
                "California EDD — payroll taxes (UI, SDI, ETT, PIT withholding)",
                "California WARN Act (60 days notice for mass layoffs — 75+ employees)",
                "CCPA / CPRA (California Consumer Privacy Act) if applicable",
                "Cal/OSHA compliance (stricter than federal OSHA)",
                "California minimum wage ($16/hour 2024; fast food: $20/hour)",
                "CFRA / PDL leave (California Family Rights Act — 5+ employees)",
                "CA pay transparency law — salary ranges in job postings",
                "SB 1162 — pay data reporting",
                "California workplace harassment training requirement (SB 1343)",
            ],
            "new york": [
                "NYS Department of Labor — UI and payroll compliance",
                "NY minimum wage ($16/hour NYC; $15/hour other areas 2024)",
                "NY Human Rights Law (NYHRL) — 4+ employees",
                "NY WARN Act (90 days notice — stricter than federal)",
                "Paid Family Leave — NY PFL (employees contribute via payroll deduction)",
                "NYC-specific: NYC Human Rights Law (most protective in US)",
                "Spread of hours pay requirement (hospitality)",
            ],
            "texas": [
                "Texas Workforce Commission — UI compliance",
                "Texas minimum wage = federal ($7.25/hour)",
                "Texas Workers' Compensation — opt-in system",
                "No state income tax (no state income tax withholding)",
                "Texas Comptroller — sales tax collection and reporting",
                "Texas Business Organizations Code — entity maintenance",
            ],
            "florida": [
                "Florida DEO — reemployment tax",
                "Florida minimum wage ($13/hour 2024; rising annually to $15)",
                "Florida sales tax — Department of Revenue",
                "No state income tax",
                "Florida PEO Act if using Professional Employer Organization",
            ],
        }

        state_requirements = state_reqs_map.get(state.lower(), [
            f"Register with {state} Department of Revenue for state tax",
            f"Obtain {state} business license / certificate of authority",
            f"Comply with {state} labor law (minimum wage, leave laws)",
            f"Register with {state} unemployment insurance agency",
            f"Check {state}-specific industry licensing requirements",
        ])

        licenses = [
            "Business license (city/county — required in most jurisdictions)",
            "State business registration / Certificate of Authority",
            "Federal tax ID (EIN)",
            f"Industry-specific license for {business_type}",
        ]

        filings = [
            "Form 941 — Federal payroll taxes (quarterly)",
            "Form 940 — FUTA (annually, deposits quarterly if >$500)",
            "Form W-2 / W-3 — Employee wage reports (January 31)",
            "Form 1099-NEC — Contractor payments $600+ (January 31)",
            "State sales tax returns (monthly/quarterly depending on volume)",
            "State income tax returns (if applicable)",
            "Annual report to state Secretary of State (for corporations/LLCs)",
            "OSHA 300 log — injury/illness recordkeeping (10+ employees)",
        ]

        penalties = {
            "FLSA violations": "$2,008/violation willful; double back wages; criminal for willful",
            "OSHA serious violation": "Up to $15,625/violation (2024)",
            "HIPAA breach": "$100 - $50,000+/violation; up to $1.9M annually per violation type",
            "I-9 violations": "$272 - $27,894/violation",
            "Tax non-compliance": "Failure to deposit penalties 2-15% of tax owed; civil fraud 75%",
        }

        priority_actions = [
            f"1. Register business entity with {state} Secretary of State",
            "2. Obtain EIN from IRS (free, same day online)",
            "3. Open separate business bank account",
            "4. Set up payroll system with federal/state tax withholding",
            "5. Obtain required business licenses and permits",
            "6. Purchase business insurance (general liability, workers comp)",
            "7. Post required federal and state labor law posters in workplace",
            "8. Implement I-9 verification process for all new hires",
        ]

        return ComplianceChecklist(
            business_type=business_type,
            state=state,
            federal_requirements=federal_requirements,
            state_requirements=state_requirements,
            licenses_needed=licenses,
            annual_filings=filings,
            penalties_for_noncompliance=penalties,
            priority_action_items=priority_actions,
        )

    def government_contracting_guide(self, business_size: str, naics_code: str) -> ContractingStrategy:
        """
        Guide for winning federal government contracts.

        Args:
            business_size: Business size classification ("small", "large", "micro").
            naics_code: Primary NAICS code for the business.

        Returns:
            ContractingStrategy with set-asides, registration, and opportunities.

        Example:
            >>> nav = GovernmentNavigator()
            >>> strategy = nav.government_contracting_guide("small", "541511")
            >>> "SAM.gov" in " ".join(strategy.registration_steps)
            True
        """
        size_lower = business_size.lower()

        registration_steps = [
            "1. Obtain DUNS Number (now replaced by SAM UEI — Unique Entity Identifier)",
            "2. Register in SAM.gov (System for Award Management) — free, required for all federal contractors",
            "   a. Create account at SAM.gov",
            "   b. Enter NAICS codes, business information, financial information",
            "   c. Complete representations and certifications",
            "   d. Renew annually — lapse will disqualify you from receiving contracts",
            "3. Get your CAGE Code (assigned automatically through SAM.gov)",
            "4. Register in SBA Dynamic Small Business Search (DSBS) if small business",
            "5. Obtain PTAC assistance — free government contracting help (ptacusa.org)",
            f"6. Research opportunities at SAM.gov/opp (formerly FedBizOpps)",
            "7. Use USASpending.gov to research agency spending in your NAICS code",
            "8. Attend industry days, pre-solicitation conferences, matchmaking events",
        ]

        set_asides = []
        certifications = []

        if size_lower in ["small", "micro", "small business"]:
            set_asides.extend([
                "Small Business Set-Aside (contracts $250,000+ must be set aside if 2 small businesses can compete)",
                "Total Small Business Set-Aside",
                "Partial Small Business Set-Aside",
            ])
            certifications.extend([
                "SBA Self-Certification as Small Business (based on SBA size standards by NAICS code)",
            ])

        # Socioeconomic certifications
        set_asides.extend([
            "8(a) Business Development Program (minority-owned, economically/socially disadvantaged — SBA certification)",
            "Woman-Owned Small Business (WOSB) — SBA certification required",
            "Economically Disadvantaged WOSB (EDWOSB) — additional set-aside",
            "Service-Disabled Veteran-Owned Small Business (SDVOSB) — VA VOSB verification",
            "HUBZone (Historically Underutilized Business Zone) — SBA certification based on location and employees",
        ])

        certifications.extend([
            "8(a) Certification: 9-year program, sole-source contracts up to $4.5M (goods/services) / $22.5M (manufacturing)",
            "WOSB Certification: Contracts up to $10M in designated NAICS codes",
            "HUBZone Certification: 10% price evaluation preference; competitive and sole-source awards",
            "SDVOSB: Verified by SBA (since 2023); set-asides in all agencies including VA",
        ])

        gsa_schedule = False
        opportunities = [
            f"SAM.gov — Search opportunities by NAICS code {naics_code}",
            "Subcontracting — Large prime contractors have subcontracting plans (search at SBA SubNet)",
            "GSA Multiple Award Schedules (MAS) — pre-competed vehicles for commercial products/services",
            "Government-Wide Acquisition Contracts (GWACs) — IT: CIO-SP4, Alliant 2, OASIS",
            "IDIQs (Indefinite Delivery/Indefinite Quantity) — on-ramp opportunities",
            "SBIR/STTR (Small Business Innovation Research) — R&D contracts, up to $2M Phase II",
        ]

        # NAICS-specific guidance
        if naics_code.startswith("54"):  # Professional services
            gsa_schedule = True
            opportunities.append("GSA Schedule 541 (Professional Services) — high volume")
        elif naics_code.startswith("23"):  # Construction
            opportunities.append("Army Corps of Engineers, PBS-GSA construction opportunities")
            opportunities.append("SBA Surety Bond Guarantee Program")
        elif naics_code.startswith("33") or naics_code.startswith("34"):  # Manufacturing
            opportunities.append("DLA (Defense Logistics Agency) — major buyer of manufactured goods")

        return ContractingStrategy(
            business_size=business_size,
            applicable_set_asides=set_asides,
            registration_steps=registration_steps,
            key_opportunities=opportunities,
            certification_programs=certifications,
            gsa_schedule_applicable=gsa_schedule,
            timeline=(
                "SAM.gov registration: 10-14 days. "
                "8(a) certification: 90-120 days. "
                "WOSB/HUBZone: 30-60 days. "
                "First contract: typically 6-18 months from start of outreach."
            ),
            annual_revenue_thresholds={
                "Micro-purchase": "Under $10,000 — no competition required",
                "Simplified Acquisition": "$10,000 - $250,000 — simplified procedures",
                "Over $250,000": "Full competition or set-aside required",
                "8(a) sole-source limit": "$4.5M services / $22.5M manufacturing",
                "Small Business size": f"Varies by NAICS {naics_code} — check SBA.gov/size-standards",
            },
        )
