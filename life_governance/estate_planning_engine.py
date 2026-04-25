"""
Estate Planning Engine — Comprehensive Estate and Succession Planning
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
class EstatePlan:
    """Comprehensive estate plan for an individual or family."""
    documents_needed: List[str]
    total_estate_value: float
    estate_tax_exposure: float
    probate_avoidance_strategies: List[str]
    asset_distribution_plan: Dict[str, Any]
    trust_recommendations: List[str]
    beneficiary_designations: List[Dict[str, str]]
    digital_asset_plan: str
    incapacity_plan: str
    estimated_attorney_cost: float
    priority_actions: List[str]


@dataclass
class LastWillAndTestament:
    """A complete Last Will and Testament document."""
    testator_name: str
    state: str
    document_text: str
    witness_requirements: str
    notarization_required: bool
    self_proving_affidavit: str
    storage_instructions: str


@dataclass
class LivingTrustPackage:
    """Complete revocable living trust package."""
    trust_name: str
    trust_agreement: str
    certificate_of_trust: str
    pour_over_will: str
    asset_transfer_instructions: str
    real_property_deed_guidance: str
    financial_account_retitling: str
    funding_checklist: List[str]


@dataclass
class PowerOfAttorney:
    """Durable Power of Attorney documents."""
    principal_name: str
    financial_poa: str
    healthcare_poa: str
    living_will: str
    polst_guidance: str
    mental_health_directive: str
    state_specific_requirements: str


@dataclass
class AdvanceDirective:
    """State-specific Advance Healthcare Directive."""
    state: str
    directive_text: str
    life_support_decisions: str
    organ_donation_instructions: str
    disposition_of_remains: str
    religious_preferences_section: str
    witness_requirements: str


@dataclass
class EstateTaxStrategy:
    """Estate tax minimization strategy."""
    current_estate_value: float
    federal_exemption_used: float
    taxable_estate: float
    estimated_tax_liability: float
    strategies: List[Dict[str, Any]]
    annual_gifting_plan: Dict[str, Any]
    trust_strategies: List[str]
    projected_savings: float
    implementation_priority: List[str]


@dataclass
class SuccessionPlan:
    """Business succession plan."""
    business_name: str
    valuation_methodology: str
    buy_sell_agreement_type: str
    buy_sell_document: str
    life_insurance_analysis: str
    key_person_analysis: str
    esop_analysis: str
    family_succession_strategies: List[str]
    implementation_timeline: List[str]


@dataclass
class DigitalEstatePlan:
    """Digital asset estate planning guide."""
    cryptocurrency_plan: str
    social_media_instructions: str
    password_manager_guide: str
    domain_and_website_plan: str
    digital_business_assets: str
    nft_collectibles_plan: str
    master_digital_inventory_template: str
    storage_recommendations: str


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FEDERAL_ESTATE_TAX_EXEMPTION_2025 = 13_610_000  # per individual
MARRIED_EXEMPTION_2025 = 27_220_000             # with portability
ANNUAL_GIFT_EXCLUSION_2024 = 18_000             # per recipient
ESTATE_TAX_RATE = 0.40                          # flat top rate above exemption


# ---------------------------------------------------------------------------
# Estate Planning Engine
# ---------------------------------------------------------------------------

class EstatePlanningEngine:
    """
    Comprehensive estate and succession planning engine.

    Handles wills, trusts, powers of attorney, advance directives,
    estate tax planning, business succession, and digital asset estate planning.
    """

    # -----------------------------------------------------------------------
    # Master Estate Plan
    # -----------------------------------------------------------------------

    def create_complete_estate_plan(self, facts: dict) -> EstatePlan:
        """
        Generate a comprehensive estate plan based on client facts.

        Args:
            facts: dict with 'name', 'age', 'state', 'marital_status',
                   'children', 'total_assets', 'asset_breakdown',
                   'existing_documents', 'special_needs_beneficiaries',
                   'charitable_intent', 'business_interests'
        """
        name = facts.get("name", "[CLIENT NAME]")
        age = facts.get("age", 45)
        state = facts.get("state", "CA")
        marital_status = facts.get("marital_status", "married")
        children = facts.get("children", [])
        total_assets = facts.get("total_assets", 1_000_000)
        charitable_intent = facts.get("charitable_intent", False)
        business_interests = facts.get("business_interests", False)
        has_minor_children = any(c.get("age", 18) < 18 for c in children)

        # Document list
        documents_needed = [
            "Last Will and Testament",
            "Durable Financial Power of Attorney",
            "Healthcare Power of Attorney / Healthcare Proxy",
            "Living Will / Advance Healthcare Directive",
        ]

        if total_assets > 200_000 or marital_status == "married":
            documents_needed.append("Revocable Living Trust")
            documents_needed.append("Pour-Over Will")
            documents_needed.append("Certificate of Trust")
            documents_needed.append("Property Transfer Deed (to fund trust)")

        if has_minor_children:
            documents_needed.append("Testamentary Trust for Minor Children")
            documents_needed.append("Guardianship Designation")

        if total_assets > FEDERAL_ESTATE_TAX_EXEMPTION_2025:
            documents_needed += [
                "Irrevocable Life Insurance Trust (ILIT)",
                "Grantor Retained Annuity Trust (GRAT)",
            ]

        if business_interests:
            documents_needed += [
                "Buy-Sell Agreement",
                "Business Succession Plan",
            ]

        if charitable_intent:
            documents_needed.append("Charitable Remainder Trust (CRT) or Donor Advised Fund")

        # Estate tax exposure
        married = marital_status == "married"
        exemption = MARRIED_EXEMPTION_2025 if married else FEDERAL_ESTATE_TAX_EXEMPTION_2025
        taxable_estate = max(0, total_assets - exemption)
        estate_tax_exposure = taxable_estate * ESTATE_TAX_RATE

        # Probate avoidance
        probate_avoidance = [
            "Revocable Living Trust (transfers all assets outside probate)",
            "Joint Tenancy with Right of Survivorship (real estate)",
            "Beneficiary designations on retirement accounts and life insurance",
            "Transfer-on-Death (TOD) deed for real estate (available in 30+ states)",
            "Payable-on-Death (POD) designations on bank accounts",
            "Transfer-on-Death for brokerage accounts",
        ]

        # Asset distribution plan
        asset_distribution = {
            "primary_beneficiary": "Spouse (if married), then children equally",
            "contingent_beneficiary": "Children in equal shares",
            "per_stirpes": True,
            "trust_for_minors": has_minor_children,
            "distribution_age_for_minors": 25,
            "special_bequests": [],
        }

        # Trust recommendations
        trust_recs = []
        if total_assets > 200_000:
            trust_recs.append("Revocable Living Trust — avoids probate, provides incapacity management")
        if has_minor_children:
            trust_recs.append("Testamentary Trust — holds assets for minors until age 25")
        if total_assets > FEDERAL_ESTATE_TAX_EXEMPTION_2025:
            trust_recs.append("Irrevocable Life Insurance Trust (ILIT) — removes life insurance from taxable estate")
            trust_recs.append("GRAT — transfers appreciation to heirs with minimal gift tax")
        if charitable_intent:
            trust_recs.append("Charitable Remainder Trust (CRT) — income stream + charitable deduction")

        # Beneficiary designations
        beneficiary_designations = [
            {"account": "Life Insurance", "primary": "Spouse", "contingent": "Children equally"},
            {"account": "401(k)/IRA", "primary": "Spouse", "contingent": "Children equally"},
            {"account": "Bank accounts (POD)", "primary": "Spouse", "contingent": "Children equally"},
            {"account": "Brokerage (TOD)", "primary": "Spouse", "contingent": "Children equally"},
        ]

        priority_actions = [
            "1. Execute Last Will and Testament IMMEDIATELY (can do this week)",
            "2. Execute Financial and Healthcare Powers of Attorney",
            "3. Update all beneficiary designations on retirement accounts and life insurance",
            "4. Draft and fund Revocable Living Trust",
            "5. Review and retitle assets into trust",
            "6. Create digital asset inventory and instructions",
            "7. Review life insurance coverage adequacy",
            "8. Discuss with CPA about gift tax annual exclusion planning",
        ]

        return EstatePlan(
            documents_needed=documents_needed,
            total_estate_value=total_assets,
            estate_tax_exposure=estate_tax_exposure,
            probate_avoidance_strategies=probate_avoidance,
            asset_distribution_plan=asset_distribution,
            trust_recommendations=trust_recs,
            beneficiary_designations=beneficiary_designations,
            digital_asset_plan=self._digital_asset_summary(),
            incapacity_plan="Durable Financial POA + Healthcare POA + Living Will + POLST (if needed)",
            estimated_attorney_cost=3500 if total_assets < 500_000 else 7500,
            priority_actions=priority_actions,
        )

    def _digital_asset_summary(self) -> str:
        return (
            "Create encrypted password document stored in fireproof safe. "
            "Include password manager master password and 2FA backup codes. "
            "List all cryptocurrency wallets with seed phrases stored separately. "
            "Grant trustee/executor digital asset authority in POA and Will."
        )

    # -----------------------------------------------------------------------
    # Will
    # -----------------------------------------------------------------------

    def draft_will(self, facts: dict) -> LastWillAndTestament:
        """
        Draft a comprehensive Last Will and Testament.

        Args:
            facts: dict with 'name', 'state', 'address', 'executor',
                   'alternate_executor', 'beneficiaries', 'children',
                   'guardian', 'specific_bequests'
        """
        name = facts.get("name", "[TESTATOR NAME]")
        state = facts.get("state", "CA")
        address = facts.get("address", "[TESTATOR ADDRESS]")
        executor = facts.get("executor", "[EXECUTOR NAME]")
        alternate_executor = facts.get("alternate_executor", "[ALTERNATE EXECUTOR]")
        beneficiaries = facts.get("beneficiaries", [{"name": "[BENEFICIARY]", "share": "100%"}])
        children = facts.get("children", [])
        guardian = facts.get("guardian", "[GUARDIAN NAME]")
        specific_bequests = facts.get("specific_bequests", [])
        date = datetime.date.today().isoformat()

        minors = [c for c in children if c.get("age", 18) < 18]

        bequests_text = ""
        for b in specific_bequests:
            bequests_text += f"\nI give {b.get('item','[ITEM]')} to {b.get('recipient','[RECIPIENT]')}."

        residuary_text = "\n".join(
            f"  {b['name']}: {b.get('share','equal share')}"
            for b in beneficiaries
        )

        guardian_clause = ""
        if minors:
            minor_names = ", ".join(c.get("name", "[CHILD]") for c in minors)
            guardian_clause = f"""
ARTICLE IV — GUARDIAN OF MINOR CHILDREN
If my spouse does not survive me or is unable to serve as guardian, I nominate
{guardian} as guardian of the person and property of my minor children: {minor_names}.
If {guardian} is unable or unwilling to serve, I nominate [ALTERNATE GUARDIAN] as successor guardian.
"""

        document_text = f"""
LAST WILL AND TESTAMENT
OF {name.upper()}

I, {name}, residing at {address}, State of {state}, being of sound and disposing
mind and memory, and not acting under duress, menace, fraud, or undue influence,
do hereby make, publish, and declare this to be my Last Will and Testament,
hereby expressly revoking all former Wills and Codicils made by me.

ARTICLE I — DECLARATION AND REVOCATION
I hereby revoke all prior Wills, Codicils, and testamentary dispositions
previously made by me.

ARTICLE II — PERSONAL INFORMATION
I am currently [MARITAL STATUS]. My [spouse/partner]'s name is [SPOUSE NAME].
I have the following children: {"None" if not children else ", ".join(c.get("name","[CHILD]") for c in children)}.

ARTICLE III — PERSONAL PROPERTY AND SPECIFIC BEQUESTS
{bequests_text if bequests_text else "I make no specific bequests of personal property at this time."}

I give my personal effects, household furnishings, jewelry, automobiles, and other
tangible personal property not otherwise specifically bequeathed to my [spouse/partner],
or if my [spouse/partner] does not survive me, to my children in equal shares.
{guardian_clause}

ARTICLE V — RESIDUARY ESTATE
All the rest, residue, and remainder of my estate, both real and personal, of whatever
kind and wherever situated, which I own at the time of my death, I give, devise, and
bequeath to the following beneficiaries:
{residuary_text}

If any beneficiary fails to survive me by thirty (30) days, their share shall pass
per stirpes to their issue, or if none, shall be divided among the surviving beneficiaries
in proportion to their shares.

ARTICLE VI — EXECUTOR
I nominate and appoint {executor} as Executor of this Will. If {executor} is unable
or unwilling to serve, I nominate {alternate_executor} as successor Executor.

I grant my Executor full power and authority, without court order, to:
(a) Collect, manage, and invest the assets of my estate
(b) Sell, lease, mortgage, or otherwise encumber real or personal property
(c) Pay debts, taxes, and expenses of administration
(d) Settle, compromise, or abandon claims
(e) Employ attorneys, accountants, and other professionals
(f) Distribute assets in cash or in kind
(g) Sign documents and take all actions necessary to administer the estate
No bond shall be required of any Executor named herein.

ARTICLE VII — TRUSTS FOR MINOR BENEFICIARIES
If any beneficiary is under the age of twenty-five (25) years at the time of my death,
their share shall be held in trust by the Trustee named herein until they reach age 25.
The Trustee may distribute income and principal for the beneficiary's health, education,
maintenance, and support. I nominate {executor} as Trustee.

ARTICLE VIII — NO-CONTEST CLAUSE
If any beneficiary contests this Will or any provision thereof, or institutes or joins
any proceeding to contest the validity of this Will, or to prevent any provision hereof
from being carried out in accordance with its terms, any gift to such beneficiary
shall be revoked and such beneficiary shall receive nothing from my estate.

ARTICLE IX — SIMULTANEOUS DEATH
If any beneficiary and I die simultaneously or in a common disaster, or if it cannot
be determined which of us survived the other, it shall be presumed that such beneficiary
predeceased me.

ARTICLE X — DEFINITIONS
References to "children" include legally adopted children. References to "issue" or
"descendants" are per stirpes. All gender pronouns are interchangeable.

IN WITNESS WHEREOF, I, {name}, subscribe my name to this Last Will and Testament
this ____ day of _____________, 20___, and declare it to be my Last Will and Testament
in the presence of the witnesses signing below.

____________________________
{name}, Testator

ATTESTATION CLAUSE
We, the undersigned witnesses, each being of legal age, declare that:
The Testator signed this Will in our presence and in the presence of each other.
At the time of signing, the Testator appeared to be of sound mind and over 18 years of age.
We sign as witnesses in the presence of the Testator and of each other.

Witness 1:
Signature: ____________________________  Date: ____________
Name (print): _________________________  Address: _____________________________

Witness 2:
Signature: ____________________________  Date: ____________
Name (print): _________________________  Address: _____________________________
""".strip()

        witness_requirements = self._will_witness_requirements(state)

        self_proving_affidavit = f"""
SELF-PROVING AFFIDAVIT
State of {state}
County of ________________

Before me, the undersigned authority, personally appeared {name}, the Testator,
and [WITNESS 1] and [WITNESS 2], witnesses, known to me to be the Testator and the
witnesses whose names are signed to the foregoing Will, who being duly sworn, the
Testator declared to me and to the witnesses that the foregoing instrument is the
Testator's Last Will and Testament and that the Testator had willingly signed and
executed it as the Testator's free and voluntary act. Each of the witnesses stated
that they signed the Will as witness in the presence and at the request of the
Testator, and in the presence of each other.

____________________________
Testator

____________________________
Witness 1

____________________________
Witness 2

Subscribed and sworn to before me this ____ day of _____________, 20___.

____________________________
Notary Public
My Commission Expires: _________
""".strip()

        return LastWillAndTestament(
            testator_name=name,
            state=state,
            document_text=document_text,
            witness_requirements=witness_requirements,
            notarization_required=state in ["LA"],  # Louisiana requires notarization
            self_proving_affidavit=self_proving_affidavit,
            storage_instructions=(
                "Store original Will in a fireproof safe or safe deposit box. "
                "Give copies (NOT originals) to executor and attorney. "
                "Register with state Will registry if available. "
                "NEVER store original Will in a safe deposit box that only you can access — "
                "your executor may not be able to retrieve it after your death."
            ),
        )

    def _will_witness_requirements(self, state: str) -> str:
        requirements = {
            "CA": "2 witnesses required; witnesses must be present when testator signs; witnesses must sign in presence of testator and each other; witnesses should NOT be beneficiaries",
            "NY": "2 witnesses required; must sign within 30 days of each other; testator must declare it is their Will",
            "FL": "2 witnesses required; self-proving affidavit recommended; notary required for self-proving",
            "TX": "2 witnesses required; holographic Will (entirely handwritten) also valid",
            "WA": "2 witnesses required; must be signed at the end",
            "IL": "2 witnesses required; witnesses cannot be beneficiaries",
            "PA": "2 witnesses required; no specific form required",
            "OH": "2 witnesses required",
            "GA": "2 witnesses required; notary for self-proving affidavit",
            "LA": "Notarial Will requires 2 witnesses AND notary; holographic Will must be entirely handwritten",
        }
        return requirements.get(state, f"2 witnesses required in most states (verify {state} specific requirements with a local attorney). Witnesses should be adults who are NOT beneficiaries under the Will.")

    # -----------------------------------------------------------------------
    # Revocable Living Trust
    # -----------------------------------------------------------------------

    def draft_revocable_living_trust(self, facts: dict) -> LivingTrustPackage:
        """
        Draft a comprehensive revocable living trust package.

        Args:
            facts: dict with 'grantor_name', 'state', 'trustee',
                   'successor_trustee', 'beneficiaries', 'children',
                   'trust_name', 'marital_status'
        """
        grantor_name = facts.get("grantor_name", "[GRANTOR NAME]")
        state = facts.get("state", "CA")
        trustee = facts.get("trustee", grantor_name)
        successor_trustee = facts.get("successor_trustee", "[SUCCESSOR TRUSTEE]")
        beneficiaries = facts.get("beneficiaries", [{"name": "[BENEFICIARY]", "share": "100%"}])
        trust_name = facts.get("trust_name", f"The {grantor_name} Revocable Living Trust")
        marital_status = facts.get("marital_status", "single")
        date = datetime.date.today().isoformat()

        trust_agreement = f"""
THE {trust_name.upper()}
A Revocable Living Trust

Dated: {date}

TRUST AGREEMENT

This Trust Agreement is entered into by {grantor_name} ("Grantor" and initial "Trustee").

ARTICLE 1 — CREATION OF TRUST
1.1 Trust Name. This Trust shall be known as {trust_name}.
1.2 Grantor. The Grantor is {grantor_name}.
1.3 Initial Trustee. The initial Trustee is {grantor_name}.
1.4 Successor Trustees. Upon the Grantor's incapacity or death, {successor_trustee} shall serve
    as Successor Trustee. If {successor_trustee} is unable to serve, [ALTERNATE TRUSTEE] shall serve.
1.5 Trust Property. The Grantor has transferred to the Trustee the property described in
    Exhibit A (the "Trust Estate"), which shall be held, administered, and distributed
    pursuant to this Agreement.

ARTICLE 2 — REVOCABILITY
2.1 Right to Revoke. During the Grantor's lifetime and while competent, the Grantor may
    revoke or amend this Trust at any time, in whole or in part, by a signed written instrument.
2.2 Irrevocability on Death. Upon the Grantor's death, this Trust becomes irrevocable.

ARTICLE 3 — ADMINISTRATION DURING GRANTOR'S LIFETIME
3.1 Income and Principal. During the Grantor's lifetime and while competent, the Trustee shall
    distribute to the Grantor so much of the income and principal as the Grantor requests.
3.2 Control. The Grantor retains complete control over Trust assets during their lifetime.
3.3 Tax Reporting. This Trust is a grantor trust under IRC § 676; all income is reported
    on the Grantor's personal income tax return. No separate trust tax return is required
    during the Grantor's lifetime.

ARTICLE 4 — INCAPACITY PROVISIONS
4.1 Determination of Incapacity. The Grantor shall be deemed incapacitated upon:
    (a) A written certification by two licensed physicians; OR
    (b) A court adjudication of incompetency.
4.2 Administration During Incapacity. If the Grantor becomes incapacitated, the Successor
    Trustee shall administer the Trust for the Grantor's benefit, applying income and
    principal for the Grantor's health, education, maintenance, and support.
4.3 Restoration. If the Grantor recovers competency (as certified by two physicians),
    the Grantor shall resume acting as Trustee.

ARTICLE 5 — DISTRIBUTION ON DEATH
5.1 Payment of Obligations. Following the Grantor's death, the Trustee shall pay:
    (a) Grantor's legally enforceable debts
    (b) Funeral and burial expenses
    (c) Trust administration costs
    (d) Estate and inheritance taxes
5.2 Specific Distributions. [Specific bequests if any]
5.3 Residuary Distribution. The remaining Trust Estate shall be distributed:
{"".join(chr(10) + f'    {b["name"]}: {b.get("share","equal share")}' for b in beneficiaries)}
5.4 Per Stirpes. If any beneficiary predeceases the Grantor, their share passes per stirpes.
5.5 Trust for Minors. If a beneficiary is under age 25, their share is held in continuing trust.

ARTICLE 6 — TRUSTEE POWERS
The Trustee shall have full power and authority, without court order, to:
6.1 Collect, hold, manage, and invest Trust assets
6.2 Sell, exchange, or otherwise dispose of Trust property
6.3 Lease property for any period, including beyond the trust term
6.4 Borrow money and mortgage Trust property
6.5 Vote stock and exercise all rights of security ownership
6.6 Employ attorneys, CPAs, investment advisors, and other agents
6.7 Open and maintain bank and brokerage accounts in the Trust's name
6.8 Make distributions in cash or in kind, at valuations determined by the Trustee
6.9 Settle, compromise, or abandon claims
6.10 Execute all documents necessary to carry out the Trust's purposes
6.11 Engage in any business activity permitted by law

ARTICLE 7 — TRUSTEE COMPENSATION AND LIABILITY
7.1 Compensation. [Grantor serving as own Trustee receives no compensation].
    A successor corporate Trustee may charge reasonable fees per published schedule.
7.2 Liability. A Trustee shall not be personally liable for any act or omission
    taken in good faith.
7.3 Bond. No bond shall be required of any Trustee named herein.

ARTICLE 8 — TRUST ACCOUNTING
8.1 Records. The Trustee shall maintain complete records of all Trust transactions.
8.2 Accounting. The Trustee shall provide an accounting to each adult beneficiary annually.
8.3 Tax Returns. After the Grantor's death, the Trust shall obtain a new EIN and file
    Form 1041 (Trust Income Tax Return) annually.

ARTICLE 9 — PERPETUITIES AND SPENDTHRIFT
9.1 Rule Against Perpetuities. All trust interests must vest within 21 years of the death
    of the last surviving beneficiary alive at the Grantor's death (or as applicable per state law).
9.2 Spendthrift Provision. No beneficiary may assign, pledge, or encumber their interest
    in this Trust. No creditor of any beneficiary may reach Trust assets before distribution.

ARTICLE 10 — MISCELLANEOUS
10.1 Governing Law. This Trust is governed by the laws of {state}.
10.2 Severability. If any provision is invalid, the remaining provisions continue.
10.3 Headings. Article headings are for convenience only.
10.4 Gender and Number. Pronouns apply regardless of gender or number.
10.5 Entire Agreement. This document constitutes the complete Trust Agreement.

IN WITNESS WHEREOF, the Grantor and Trustee have executed this Trust Agreement.

____________________________
{grantor_name}, Grantor

____________________________
{grantor_name}, Trustee

State of {state}
County of ____________

On ________________, before me, ________________________, a Notary Public,
personally appeared {grantor_name}, known to me to be the person whose name is subscribed
to the foregoing instrument, and acknowledged to me that they executed the same.

____________________________
Notary Public
My Commission Expires: _________

EXHIBIT A — INITIAL TRUST PROPERTY
[List all assets transferred to trust at formation]
""".strip()

        certificate_of_trust = f"""
CERTIFICATE OF TRUST

{trust_name}

Pursuant to [State] Probate Code Section [XXXX], the following information
is certified regarding {trust_name}:

1. Trust Name: {trust_name}
2. Date of Trust: {date}
3. Grantor: {grantor_name}
4. Trustee(s): {grantor_name} (initial); {successor_trustee} (successor)
5. Trust Powers: The Trustee has full power to buy, sell, lease, mortgage,
   and otherwise deal with real and personal property.
6. Trust Status: The Trust is currently revocable and in full force and effect.
7. Tax ID: [Use Grantor's SSN during lifetime; new EIN after death]

The undersigned Trustee certifies under penalty of perjury that the above
information is true and correct.

____________________________
{grantor_name}, Trustee

Date: ________________________

Notarized:
____________________________
Notary Public
""".strip()

        pour_over_will = f"""
POUR-OVER WILL OF {grantor_name.upper()}

I, {grantor_name}, being of sound mind, hereby make this my Last Will and Testament.

ARTICLE I — REVOCATION
I revoke all prior Wills and Codicils.

ARTICLE II — POUR-OVER TO TRUST
I give, devise, and bequeath all of my estate, both real and personal, of whatever
kind and wherever situated, which I own at the time of my death and which is NOT
already held in {trust_name}, to the then-acting Trustee of {trust_name},
to be administered and distributed pursuant to the terms of that Trust as it may
be amended and in effect at the time of my death.

ARTICLE III — EXECUTOR
I appoint {successor_trustee} as Executor of this Will.

ARTICLE IV — GUARDIAN
[If applicable: Guardian designation for minor children]

IN WITNESS WHEREOF, I sign this Will on _________________.

____________________________
{grantor_name}, Testator

[Witness signatures as required by {state} law]
""".strip()

        asset_transfer_instructions = f"""
HOW TO FUND YOUR REVOCABLE LIVING TRUST
{trust_name}

CRITICAL: A Living Trust only protects assets that are IN the trust.
An unfunded trust does NOT avoid probate. Complete this checklist!

REAL ESTATE:
- Prepare a new deed transferring property FROM "[Your Name]"
  TO "[Your Name], Trustee of {trust_name}, dated {date}"
- Record the deed with the county recorder's office (fee: $15-$50 per property)
- Notify your title insurance company and mortgage servicer
- Obtain a new Certificate of Trust to provide to title companies
- See Lady Bird deed or TOD deed options if available in {state}

FINANCIAL ACCOUNTS:
- Contact each bank/credit union/brokerage
- Request account title change to: "{trust_name}, dated {date},
  [Your Name], Trustee"
- Bring Certificate of Trust to bank branch
- Some institutions require their own form
- Alternative: Add Trust as POD (payable on death) beneficiary

RETIREMENT ACCOUNTS (IRA, 401k, 403b):
- DO NOT retitle retirement accounts in trust name — this is a taxable event!
- Instead, update BENEFICIARY DESIGNATIONS:
  Primary: Spouse (if married)
  Contingent: {trust_name}

LIFE INSURANCE:
- Update beneficiary designation:
  Primary: Spouse (if married)
  Contingent: {trust_name}
- If estate tax planning: Consider Irrevocable Life Insurance Trust (ILIT)

VEHICLES:
- Generally NOT worth titling in trust (insurance complications)
- Exception: Classic cars, boats, aircraft of significant value
- Alternative: Add beneficiary or use TOD title if available in {state}

BUSINESS INTERESTS:
- Transfer LLC membership interest or corporate stock to Trust
- Amend Operating Agreement or stock ledger
- Issue new membership certificate or stock certificate to Trust

PERSONAL PROPERTY:
- Execute an Assignment of Personal Property to Trust
- Comprehensive personal property transfers to Trust collectively

ANNUAL MAINTENANCE:
- Review trust funding after major asset purchases or dispositions
- Update Trust if family circumstances change (birth, death, divorce)
- Trust amendment must be notarized in most states
""".strip()

        return LivingTrustPackage(
            trust_name=trust_name,
            trust_agreement=trust_agreement,
            certificate_of_trust=certificate_of_trust,
            pour_over_will=pour_over_will,
            asset_transfer_instructions=asset_transfer_instructions,
            real_property_deed_guidance=(
                "Prepare a Grant Deed (CA) or Warranty Deed transferring property to '[Grantor Name], "
                "Trustee of [Trust Name] dated [Date]'. Record with County Recorder. "
                "Proposition 13 (CA) and similar laws generally allow transfers to revocable trusts "
                "without reassessment. Inform mortgage lender (typically a Garn-St. Germain Act exception applies)."
            ),
            financial_account_retitling=(
                "Bring Certificate of Trust to each financial institution. Request title change to trust. "
                "Most major banks (Chase, Bank of America, Wells Fargo) have dedicated trust account teams. "
                "Brokerage accounts: Contact Fidelity, Schwab, Vanguard's trust services departments."
            ),
            funding_checklist=[
                "☐ Real estate deeds transferred",
                "☐ Bank accounts retitled",
                "☐ Brokerage accounts retitled",
                "☐ Retirement account beneficiaries updated",
                "☐ Life insurance beneficiaries updated",
                "☐ Business interests transferred",
                "☐ Assignment of personal property executed",
                "☐ Certificate of Trust copies made (keep 5+)",
                "☐ Pour-over Will executed",
                "☐ Attorney and financial advisor have trust copy",
            ],
        )

    # -----------------------------------------------------------------------
    # Power of Attorney
    # -----------------------------------------------------------------------

    def draft_power_of_attorney(self, facts: dict) -> PowerOfAttorney:
        """
        Draft comprehensive Durable Power of Attorney documents.

        Args:
            facts: dict with 'principal_name', 'state', 'agent_name',
                   'alternate_agent', 'healthcare_agent', 'special_powers'
        """
        principal_name = facts.get("principal_name", "[PRINCIPAL NAME]")
        state = facts.get("state", "CA")
        agent_name = facts.get("agent_name", "[AGENT NAME]")
        alternate_agent = facts.get("alternate_agent", "[ALTERNATE AGENT]")
        healthcare_agent = facts.get("healthcare_agent", agent_name)
        date = datetime.date.today().isoformat()

        financial_poa = f"""
DURABLE POWER OF ATTORNEY
FOR FINANCIAL AND PROPERTY MATTERS

Principal: {principal_name}
Agent: {agent_name}
State: {state}
Date: {date}

NOTICE: THIS IS AN IMPORTANT LEGAL DOCUMENT. BY SIGNING THIS DOCUMENT,
YOU ARE AUTHORIZING ANOTHER PERSON TO ACT ON YOUR BEHALF AND TO MAKE
DECISIONS ABOUT YOUR PROPERTY. THIS DOCUMENT WILL CONTINUE TO BE EFFECTIVE
EVEN IF YOU BECOME INCAPACITATED.

1. DESIGNATION OF AGENT
I, {principal_name}, appoint {agent_name} as my Attorney-in-Fact (Agent).
If {agent_name} is unable or unwilling to act, I appoint {alternate_agent} as my Agent.

2. DURABILITY
This Power of Attorney shall not be affected by my incapacity or mental incompetence.
It is intended to be a Durable Power of Attorney under {state} law.

3. EFFECTIVE DATE
This Power of Attorney is effective immediately upon signing [OR: upon my incapacity].

4. AGENT'S POWERS
My Agent has full authority to act on my behalf in all financial and property matters,
including the power to:

(a) BANKING AND FINANCIAL ACCOUNTS
    - Open, maintain, and close checking, savings, and money market accounts
    - Make deposits and withdrawals
    - Access safe deposit boxes
    - Write checks and authorize electronic transfers
    - Manage online banking

(b) INVESTMENTS
    - Buy, sell, and manage stocks, bonds, mutual funds, and other securities
    - Manage brokerage accounts
    - Exercise options and other investment rights
    - Manage retirement accounts (subject to applicable law)

(c) REAL ESTATE
    - Buy, sell, lease, mortgage, and manage real property
    - Sign deeds, mortgages, leases, and other real property documents
    - Collect rent and enforce lease terms
    - Make repairs and improvements

(d) BUSINESS OPERATIONS
    - Manage any business interest I own
    - Sign contracts, checks, and other business documents
    - Hire and discharge employees

(e) TAXES
    - Prepare and file federal, state, and local tax returns
    - Pay taxes owed and claim refunds
    - Represent me before the IRS and state taxing authorities
    - Make tax elections

(f) LEGAL MATTERS
    - Employ attorneys and settle claims
    - Pursue or defend litigation
    - Accept service of process

(g) GOVERNMENT BENEFITS
    - Apply for and manage Social Security, Medicare, Medicaid, and VA benefits

(h) ESTATE PLANNING (if granted)
    - Make gifts up to the annual gift exclusion amount ($18,000/recipient/year)
    - Fund and manage trusts established by me
    - Disclaim interests in property

5. COMPENSATION
My Agent shall be entitled to reimbursement for reasonable expenses. Agent shall
[or shall not] be entitled to reasonable compensation.

6. THIRD PARTY RELIANCE
Third parties who act in reliance on this Power of Attorney shall be protected.

7. REVOCATION
This Power of Attorney may be revoked by me at any time while competent by
a signed, notarized written notice to my Agent.

IN WITNESS WHEREOF, I have executed this Durable Power of Attorney.

____________________________
{principal_name}, Principal

Date: ____________________

Acknowledged before me: ____________________________
Notary Public, State of {state}
My Commission Expires: _________
""".strip()

        healthcare_poa = f"""
HEALTHCARE POWER OF ATTORNEY / HEALTHCARE PROXY

Principal: {principal_name}
Healthcare Agent: {healthcare_agent}
State: {state}

I, {principal_name}, appoint {healthcare_agent} as my Healthcare Agent.
If {healthcare_agent} is unable to act, I appoint {alternate_agent}.

MY AGENT'S AUTHORITY:
My Healthcare Agent has authority to make all healthcare decisions for me
when I am unable to make them, including:
- Consent to, refuse, or withdraw medical treatment
- Authorize surgery, anesthesia, and medical procedures
- Select and discharge healthcare providers and facilities
- Authorize pain management, including palliative sedation
- Gain access to my medical records (HIPAA authorization)
- Make anatomical gifts
- Make decisions about hospitalization, nursing home, and home health care
- Apply for Medicare, Medicaid, and health insurance benefits

LIMITATIONS:
My Agent does NOT have authority to: [specify any limitations]

GUIDANCE FOR MY AGENT:
I want my Agent to consider my personal values, religious beliefs, and
wishes regarding quality of life. I prefer: [describe preferences].

____________________________
{principal_name}     Date: ____________

Witnesses:
____________________________     ____________________________
Witness 1                         Witness 2
""".strip()

        living_will = f"""
LIVING WILL / ADVANCE HEALTHCARE DIRECTIVE

I, {principal_name}, of sound mind, willfully and voluntarily direct that:

1. TERMINAL CONDITION
   If I am in a terminal condition from which death is imminent, I direct
   that life-sustaining treatment [be withheld/withdrawn] [OR: be continued].

2. PERSISTENT VEGETATIVE STATE
   If I am in a persistent vegetative state with no reasonable expectation
   of recovery, I direct that life-sustaining treatment be withheld or withdrawn.

3. END-STAGE CONDITION
   If I am in an end-stage condition, I direct that life-sustaining treatment
   [be withheld/withdrawn].

4. PAIN MANAGEMENT
   In all circumstances, I direct that I receive adequate pain relief and
   comfort care, even if this may hasten my death.

5. ARTIFICIAL NUTRITION AND HYDRATION
   [Check one]:
   ☐ I DO want artificial nutrition and hydration to be continued
   ☐ I do NOT want artificial nutrition and hydration if it only prolongs dying

6. ANTIBIOTICS AND OTHER TREATMENTS
   ☐ Provide all potentially life-prolonging treatment
   ☐ Provide only comfort care

7. ORGAN DONATION
   ☐ I wish to be an organ donor for: ☐ any needed organs ☐ specific: _______
   ☐ I do NOT wish to donate organs

8. DISPOSITION OF REMAINS
   ☐ Burial at: _________________________________
   ☐ Cremation. Ashes: _________________________
   ☐ Donate body to medical science

____________________________
{principal_name}     Date: ____________
""".strip()

        return PowerOfAttorney(
            principal_name=principal_name,
            financial_poa=financial_poa,
            healthcare_poa=healthcare_poa,
            living_will=living_will,
            polst_guidance=(
                "POLST (Physician Orders for Life-Sustaining Treatment) is a medical order "
                "signed by a physician based on a patient's wishes. Unlike a Living Will, POLST "
                "is actionable immediately by EMS and all healthcare providers. Complete POLST "
                "if you are seriously ill or elderly. Available at polst.org by state."
            ),
            mental_health_directive=(
                "A Mental Health Advance Directive allows you to specify treatment preferences "
                "for mental health crises when you may lack capacity. Specify: preferred medications, "
                "medications to avoid, hospitalization preferences, crisis intervention instructions. "
                "Available in most states — check NAMI.org for state-specific forms."
            ),
            state_specific_requirements=(
                f"In {state}: Ensure compliance with state-specific POA statute. "
                "Most states require notarization and/or 2 witnesses for POA documents. "
                "Healthcare POA may have different witness requirements than financial POA. "
                "Consult a {state} estate planning attorney for state-specific requirements."
            ),
        )

    # -----------------------------------------------------------------------
    # Advance Directive
    # -----------------------------------------------------------------------

    def draft_advance_directive(self, facts: dict) -> AdvanceDirective:
        """
        Draft a state-specific Advance Healthcare Directive.

        Args:
            facts: dict with 'name', 'state', 'organ_donation',
                   'disposition_of_remains', 'religious_preferences',
                   'life_support_wishes'
        """
        name = facts.get("name", "[NAME]")
        state = facts.get("state", "CA")
        organ_donation = facts.get("organ_donation", True)
        disposition = facts.get("disposition_of_remains", "burial")
        religious = facts.get("religious_preferences", "")
        life_support = facts.get("life_support_wishes", "comfort care only if terminal")

        directive_text = f"""
ADVANCE HEALTHCARE DIRECTIVE
State of {state}

Principal: {name}

This Advance Healthcare Directive is made pursuant to {state} law.

PART 1 — POWER OF ATTORNEY FOR HEALTHCARE
[See Healthcare POA section above]

PART 2 — INSTRUCTIONS FOR HEALTHCARE
A. Life Support: If I am in a terminal condition, persistent vegetative state, or
   end-stage condition, my wish is: {life_support}

B. Pain Management: Always provide adequate pain relief, even if it may shorten my life.

C. Hospitalization: [Specify preferences about hospitalization, ICU, etc.]

D. Cardiopulmonary Resuscitation (CPR):
   ☐ Attempt CPR in all circumstances
   ☐ Do NOT attempt CPR (DNR) — I prefer natural death

PART 3 — ORGAN DONATION
{"I WISH to donate: ☐ Any needed organ ☐ Specific organs: _____________" if organ_donation else "I do NOT wish to donate organs."}

PART 4 — DISPOSITION OF REMAINS
My preference for disposition of remains: {disposition}
Specific instructions: [Additional details]

PART 5 — RELIGIOUS/SPIRITUAL PREFERENCES
{religious if religious else "No specific religious requirements noted."}

PART 6 — PRIMARY PHYSICIAN
My primary physician is: [DR. NAME AND CONTACT]

Signed: ____________________________
{name}     Date: ____________

WITNESSES: [Both witnesses certify that the Principal signed voluntarily and appeared competent]
Witness 1: ____________________________
Witness 2: ____________________________
""".strip()

        witness_requirements = {
            "CA": "2 adult witnesses; neither can be healthcare provider or agent; at least one not related by blood/marriage or heir",
            "FL": "2 witnesses; witnesses cannot be: healthcare provider, agent, or heir",
            "TX": "2 witnesses; neither can be: healthcare provider, agent, or heir",
            "NY": "2 witnesses; witnesses 18+; cannot be agent or person who signed for principal",
            "WA": "2 witnesses or notary",
        }.get(state, f"2 adult witnesses required in most states. Check {state} specific requirements.")

        return AdvanceDirective(
            state=state,
            directive_text=directive_text,
            life_support_decisions=life_support,
            organ_donation_instructions=(
                "Register at RegisterMe.org or your state's donor registry. "
                "Notify your healthcare agent and family of your wishes. "
                "List in your Advance Directive. Note on driver's license."
            ),
            disposition_of_remains=disposition,
            religious_preferences_section=religious or "No specific preferences noted.",
            witness_requirements=witness_requirements,
        )

    # -----------------------------------------------------------------------
    # Estate Tax Planning
    # -----------------------------------------------------------------------

    def estate_tax_planning(self, estate: dict) -> EstateTaxStrategy:
        """
        Develop a comprehensive estate tax minimization strategy.

        Args:
            estate: dict with 'total_value', 'married', 'num_children',
                    'has_life_insurance', 'has_business', 'charitable_intent',
                    'annual_income', 'age'
        """
        total_value = estate.get("total_value", 15_000_000)
        married = estate.get("married", True)
        num_children = estate.get("num_children", 2)
        has_life_insurance = estate.get("has_life_insurance", True)
        has_business = estate.get("has_business", False)
        charitable_intent = estate.get("charitable_intent", False)
        age = estate.get("age", 60)
        annual_income = estate.get("annual_income", 500_000)

        exemption = MARRIED_EXEMPTION_2025 if married else FEDERAL_ESTATE_TAX_EXEMPTION_2025
        taxable_estate = max(0, total_value - exemption)
        baseline_tax = taxable_estate * ESTATE_TAX_RATE

        strategies: List[Dict[str, Any]] = []
        projected_savings = 0.0

        # Annual gifting
        annual_gifting_capacity = ANNUAL_GIFT_EXCLUSION_2024 * num_children * (2 if married else 1)
        strategies.append({
            "name": "Annual Gift Exclusion",
            "description": f"Gift ${ANNUAL_GIFT_EXCLUSION_2024:,}/year per recipient (${ANNUAL_GIFT_EXCLUSION_2024 * 2:,}/year with gift splitting if married)",
            "annual_savings": annual_gifting_capacity * ESTATE_TAX_RATE,
            "complexity": "Low",
            "action": f"Establish annual gifting program to {num_children} children. Gift ${ANNUAL_GIFT_EXCLUSION_2024:,} per child per year.",
        })
        projected_savings += annual_gifting_capacity * ESTATE_TAX_RATE

        # 529 superfunding
        superfunding = ANNUAL_GIFT_EXCLUSION_2024 * 5 * num_children * (2 if married else 1)
        strategies.append({
            "name": "529 Superfunding (5-Year Election)",
            "description": f"Front-load 5 years of gifts into 529 plans: ${superfunding:,.0f} total, removed from estate immediately",
            "one_time_savings": superfunding * ESTATE_TAX_RATE,
            "complexity": "Low",
            "action": "Open 529 plans for each grandchild. Make 5-year election on Form 709.",
        })
        projected_savings += superfunding * ESTATE_TAX_RATE

        if has_life_insurance:
            strategies.append({
                "name": "Irrevocable Life Insurance Trust (ILIT)",
                "description": "Transfer life insurance to ILIT — removes death benefit from taxable estate",
                "tax_savings": "Death benefit * 40%",
                "complexity": "Medium",
                "action": "Create ILIT. Transfer policy ownership or have ILIT purchase new policy. Use annual exclusion for premium payments ('Crummey' notices to beneficiaries).",
            })

        if taxable_estate > 0:
            grat_strategy = min(total_value * 0.2, 5_000_000)
            strategies.append({
                "name": "Grantor Retained Annuity Trust (GRAT)",
                "description": "Transfer appreciation above IRS hurdle rate to heirs with minimal gift tax. Zeroed-out GRAT = no gift tax.",
                "transfer_potential": f"${grat_strategy * 0.10:,.0f}+ in appreciation (assuming 10% growth above AFR)",
                "complexity": "Medium-High",
                "action": "Establish 2-year rolling GRATs. Fund with appreciating assets (business interests, appreciated securities). Zeroed-out GRAT = no taxable gift.",
            })

        if charitable_intent:
            strategies.append({
                "name": "Charitable Remainder Trust (CRT)",
                "description": "Donate appreciated assets to CRT; receive income stream + charitable deduction; avoids capital gains on sale",
                "complexity": "Medium",
                "action": "Fund CRT with low-basis appreciated assets. Receive income stream for life. Remainder to charity. Immediate charitable deduction + avoid capital gains.",
            })
            strategies.append({
                "name": "Qualified Personal Residence Trust (QPRT)",
                "description": "Transfer primary residence to trust at discounted gift tax value; continue living there for term",
                "complexity": "Medium",
                "action": "Transfer home to QPRT for 10-year term. Save estate taxes on future appreciation. Must outlive QPRT term.",
            })

        if has_business:
            strategies.append({
                "name": "Family Limited Partnership (FLP) / Valuation Discounts",
                "description": "Transfer business/investment assets to FLP; apply 20-40% valuation discounts for lack of control and marketability",
                "complexity": "High",
                "action": "Form FLP. Transfer assets. Gift limited partnership interests at discount. Requires business purpose and proper documentation to withstand IRS scrutiny.",
            })

        # Portability
        if married:
            strategies.insert(0, {
                "name": "Portability Election",
                "description": f"Surviving spouse can use deceased spouse's unused exemption (up to ${FEDERAL_ESTATE_TAX_EXEMPTION_2025:,.0f} additional)",
                "complexity": "Low",
                "action": "File estate tax return (Form 706) for first spouse to die — EVEN IF NO TAX IS OWED — to preserve portability. Must file within 9 months of death (18 with extension).",
            })

        return EstateTaxStrategy(
            current_estate_value=total_value,
            federal_exemption_used=min(total_value, exemption),
            taxable_estate=taxable_estate,
            estimated_tax_liability=baseline_tax,
            strategies=strategies,
            annual_gifting_plan={
                "annual_exclusion_per_recipient": ANNUAL_GIFT_EXCLUSION_2024,
                "total_annual_gifts": annual_gifting_capacity,
                "estate_tax_saved_annually": annual_gifting_capacity * ESTATE_TAX_RATE,
                "529_superfunding": superfunding,
            },
            trust_strategies=[s["name"] for s in strategies if "Trust" in s["name"] or "GRAT" in s["name"]],
            projected_savings=projected_savings,
            implementation_priority=[
                "1. Maximize annual exclusion gifts immediately",
                "2. Update beneficiary designations (no-cost, high-impact)",
                "3. Portability election upon first spouse's death",
                "4. Establish ILIT if large life insurance policy exists",
                "5. Implement GRAT strategy for appreciating assets",
                "6. Evaluate FLP if business assets included",
            ],
        )

    # -----------------------------------------------------------------------
    # Business Succession Plan
    # -----------------------------------------------------------------------

    def business_succession_plan(self, business: dict) -> SuccessionPlan:
        """
        Develop a comprehensive business succession plan.

        Args:
            business: dict with 'name', 'value', 'owners', 'industry',
                      'family_business', 'num_key_employees', 'annual_revenue'
        """
        business_name = business.get("name", "[BUSINESS NAME]")
        value = business.get("value", 5_000_000)
        owners = business.get("owners", [{"name": "[OWNER]", "ownership": "100%"}])
        family_business = business.get("family_business", False)
        annual_revenue = business.get("annual_revenue", 2_000_000)

        buy_sell_doc = f"""
BUY-SELL AGREEMENT — {business_name}

PARTIES: {"".join(o['name'] + ', ' for o in owners)}and {business_name} (the "Company")

TRIGGERING EVENTS:
1. Death of an owner
2. Permanent disability (definition: unable to perform material duties for 12+ months)
3. Retirement (age 65 or after 20 years of service)
4. Voluntary sale or transfer
5. Involuntary transfer (bankruptcy, divorce, creditor attachment)
6. Termination of employment

BUY-SELL STRUCTURE:
☑ Hybrid Structure (Company + Owners): Company has first right to purchase.
If Company cannot purchase, remaining owners have secondary right to purchase.

PURCHASE PRICE — VALUATION:
Valuation Method: [Choose one]
□ Agreed Value (updated annually in December)
□ Book Value
□ EBITDA Multiple (Industry multiple: {annual_revenue / value:.1f}x revenue)
■ Independent Appraiser (Fair Market Value by certified business appraiser)

PAYMENT TERMS:
□ Lump sum cash payment
■ Down payment (25%) + installment note (75% over 5 years at prime +1%)
□ Insurance-funded (immediate lump sum)

LIFE INSURANCE FUNDING:
Each owner should maintain a life insurance policy equal to their ownership value:
{"".join(chr(10) + f'  {o["name"]}: ${value * 0.33:,.0f} policy recommended' for o in owners)}
""".strip()

        return SuccessionPlan(
            business_name=business_name,
            valuation_methodology=(
                f"For {business_name} with ${annual_revenue:,.0f} revenue and ${value:,.0f} estimated value: "
                "Use an average of 3 methods: (1) EBITDA multiple (industry-specific, typically 3-8x), "
                "(2) Revenue multiple (0.5-3x depending on profitability), "
                "(3) Asset-based approach (tangible book value + goodwill). "
                "Get certified appraisal (NACVA or ASA credentialed appraiser) every 3-5 years."
            ),
            buy_sell_agreement_type=(
                "Hybrid Buy-Sell (Recommended): Combines cross-purchase (surviving owners buy) "
                "and entity redemption (company buys). Company has first right; if it cannot exercise, "
                "surviving owners buy pro-rata. Provides flexibility and tax optimization."
            ),
            buy_sell_document=buy_sell_doc,
            life_insurance_analysis=(
                f"Fund buy-sell with life insurance. Each owner needs ${value / len(owners):,.0f} "
                "in coverage. Use term (20-30 year) or permanent (whole life/universal) based on "
                "permanence of business. If entity-owned policy: Corporate-owned life insurance (COLI). "
                "If owner-owned: Cross-purchase arrangement (each owner buys policy on other owners)."
            ),
            key_person_analysis=(
                "Key person insurance protects the business if a critical employee dies or becomes disabled. "
                "Coverage amount: 3-5x the key person's annual compensation, or estimated revenue impact. "
                "Company pays premiums; company is beneficiary. Proceeds used to recruit/train replacement "
                "and cover business disruption costs."
            ),
            esop_analysis=(
                "ESOP (Employee Stock Ownership Plan): A viable exit strategy if business has >20 employees "
                f"and ${value:,.0f} in value. ESOP can purchase business at fair market value. "
                "Tax benefits: Owner can defer capital gains via Section 1042 rollover (C-Corp only). "
                "ESOP-owned S-Corp pays no corporate income tax on ESOP's share. "
                "Requires ERISA compliance, annual valuations, and significant legal/admin costs."
            ),
            family_succession_strategies=[
                "Installment Sale to Intentionally Defective Grantor Trust (IDGT) — transfers appreciation out of estate",
                "GRAT funded with business interests — transfers growth above AFR to children",
                "Annual gifting of minority interests with valuation discounts (FLP/LLC structure)",
                "Intra-family loan at AFR to fund purchase by next generation",
                "Gradual transition: 5-10 year management transition before ownership transfer",
            ] if family_business else ["Consider ESOP or third-party sale for non-family succession"],
            implementation_timeline=[
                "Month 1-3: Business valuation; select succession team (attorney, CPA, financial advisor)",
                "Month 3-6: Draft and execute Buy-Sell Agreement",
                "Month 6-9: Obtain life insurance policies to fund buy-sell",
                "Month 9-12: Begin family succession training or identify key management team",
                "Year 2-3: Begin formal ownership transition if family succession",
                "Year 3-5: Complete ownership transition",
                "Annually: Update business valuation; review buy-sell agreement",
            ],
        )

    # -----------------------------------------------------------------------
    # Digital Asset Estate Plan
    # -----------------------------------------------------------------------

    def digital_asset_estate_plan(self, digital_assets: dict) -> DigitalEstatePlan:
        """
        Create a comprehensive digital asset estate plan.

        Args:
            digital_assets: dict with 'has_crypto', 'has_business_accounts',
                            'has_nfts', 'platforms', 'estimated_value'
        """
        has_crypto = digital_assets.get("has_crypto", False)
        has_nfts = digital_assets.get("has_nfts", False)
        estimated_value = digital_assets.get("estimated_value", 0)

        crypto_plan = """
CRYPTOCURRENCY INHERITANCE PLAN:

SEED PHRASE STORAGE:
- Write seed phrase on CRYPTOSTEEL or similar fireproof, waterproof metal backup
- NEVER store seed phrase digitally (email, cloud, phone)
- Store in separate location from hardware wallet
- Consider Shamir's Secret Sharing (split seed phrase among multiple trusted people)

HARDWARE WALLET:
- Use Ledger or Trezor hardware wallet for significant holdings
- Store hardware wallet in fireproof safe
- Leave written PIN instructions (encrypted) with estate documents

EXECUTOR ACCESS INSTRUCTIONS:
1. Location of hardware wallet: [DESCRIBE LOCATION]
2. PIN: [Store securely — not in this document]
3. Seed phrase location: [DESCRIBE SECURE STORAGE LOCATION]
4. Exchange accounts: [List all exchanges — Coinbase, Kraken, etc.]
5. Contact: [Crypto attorney or service like Coinbase for institutional accounts]

EXCHANGE ACCOUNTS:
- File inheritance claims with major exchanges (Coinbase, Kraken have processes)
- Enable trusted contact designation where available
- Document account usernames and registered email addresses

TAX CONSIDERATIONS:
- Crypto receives step-up in basis at death — NO CAPITAL GAINS TAX for heirs
- Executor must report value at date of death for estate tax purposes
- 1099-DA reporting beginning 2025 from exchanges
""" if has_crypto else "No cryptocurrency assets — N/A"

        nft_plan = """
NFT AND DIGITAL COLLECTIBLES:
- Document all NFT holdings (platform, wallet address, token IDs)
- Provide wallet access instructions (same as cryptocurrency)
- Note which NFTs have commercial rights vs. display rights only
- Consider NFT-specific platforms: OpenSea, Foundation, Rarible
- Some NFTs have ongoing royalty rights — document these revenue streams
""" if has_nfts else "No NFT holdings — N/A"

        return DigitalEstatePlan(
            cryptocurrency_plan=crypto_plan,
            social_media_instructions="""
SOCIAL MEDIA ACCOUNTS:
Facebook/Meta: Designate a "Legacy Contact" in settings (will manage memorial page)
  OR request account removal after death
Google: Set up "Inactive Account Manager" (google.com/settings/account/inactiveaccount)
Instagram: Request memorialization or removal via Instagram Help Center
Twitter/X: Request account deactivation via Twitter support
LinkedIn: LinkedIn has a process for deceased member removal

ACTION REQUIRED: Review and configure each platform's death/inactivity settings NOW.
Include account list with usernames (not passwords) in estate documents.
""",
            password_manager_guide="""
PASSWORD MANAGER INHERITANCE:
1. Use a reputable password manager: 1Password (Emergency Kit), Bitwarden, or LastPass
2. 1Password Emergency Kit: Print and store in fireproof safe — provides vault access
3. Create master recovery document listing:
   - Password manager service name
   - Username/email
   - Master password (store in fireproof safe, NOT digitally)
   - Recovery codes / 2FA backup codes
4. Grant estate attorney access to recovery document location
5. Review Emergency Access features (Bitwarden and 1Password offer this)

CRITICAL: Without password manager access, your executor cannot access most of your digital life.
""",
            domain_and_website_plan="""
DOMAIN NAMES AND WEBSITES:
- List all domains with registrar (GoDaddy, Namecheap, Google Domains, etc.)
- Document annual renewal dates and costs
- Add executor as account contact or co-owner
- Document website platforms (WordPress, Squarespace, etc.) and hosting providers
- If business domain: Part of business succession plan
- Transfer instructions: Requires registrar login and authorization codes
""",
            digital_business_assets="""
DIGITAL BUSINESS ASSETS:
- Software licenses and subscriptions (list with usernames and renewal dates)
- Cloud storage accounts (Google Drive, Dropbox, Box)
- Email accounts (business and personal)
- Customer databases and CRM systems
- Proprietary software or code repositories (GitHub, GitLab)
- Digital content libraries (stock photos, templates, etc.)
- Online course platforms, digital products
These assets have significant business value and must be addressed in business succession.
""",
            nft_collectibles_plan=nft_plan,
            master_digital_inventory_template="""
DIGITAL ASSET MASTER INVENTORY TEMPLATE
(Print and store in fireproof safe — UPDATE ANNUALLY)

Date Created: ___________  Last Updated: ___________

FINANCIAL ACCOUNTS:
Account Type | Institution | Username | Notes
------------ | ----------- | -------- | -----
Checking     |             |          |
Savings      |             |          |
Investment   |             |          |
Crypto       |             |          |

SOCIAL MEDIA:
Platform | Username | Notes
-------- | -------- | -----
         |          |

DOMAINS/WEBSITES:
Domain | Registrar | Hosting | Expiry | Monthly Cost
------ | --------- | ------- | ------ | ------------

SUBSCRIPTIONS:
Service | Purpose | Login Email | Monthly Cost
------- | ------- | ----------- | ------------

IMPORTANT LOCATIONS:
Password Manager: ___________________________
Master Password Location: ___________________
Hardware Wallet Location: ___________________
Seed Phrase Location: _______________________
""",
            storage_recommendations="""
STORAGE RECOMMENDATIONS:
1. Fireproof Safe at home: Store master inventory, hardware wallet, seed phrase backup
2. Bank Safe Deposit Box: Store estate documents, property deeds, financial account list
3. With Estate Attorney: Store executed Will, Trust Agreement, POA originals
4. Digital Backup: Encrypted (AES-256) USB drive with scanned estate documents
   Password to encrypted drive: [Store separately from drive]
5. Trusted Family Member: Share location of safe and attorney contact information

NEVER STORE: Seed phrases, passwords, or PINs in the cloud, email, or unencrypted files.
""",
        )
