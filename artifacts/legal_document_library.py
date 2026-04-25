"""
Legal Document Library — Comprehensive template library for every major legal document type.
All templates are complete, properly formatted, and use [BRACKET] notation for fillable fields.
"""

from __future__ import annotations

from typing import Dict, Optional


class LegalDocumentLibrary:
    """
    Comprehensive library of professional legal document templates.
    Templates span trust law, corporate, employment, real estate,
    demand letters, estate planning, and business operations.
    """

    _templates: Dict[str, str] = {}

    def __init__(self):
        self._build_index()

    def _build_index(self):
        self._templates = {
            # Trust Documents
            "revocable_living_trust": self._revocable_living_trust(),
            "irrevocable_trust": self._irrevocable_trust(),
            "special_needs_trust": self._special_needs_trust(),
            "charitable_remainder_trust": self._charitable_remainder_trust(),
            # Corporate
            "llc_operating_agreement_single": self._llc_operating_agreement_single(),
            "llc_operating_agreement_multi": self._llc_operating_agreement_multi(),
            "corporate_bylaws": self._corporate_bylaws(),
            "shareholder_agreement": self._shareholder_agreement(),
            "buy_sell_agreement": self._buy_sell_agreement(),
            "board_resolutions": self._board_resolutions(),
            "annual_meeting_minutes": self._annual_meeting_minutes(),
            # Employment
            "employment_agreement": self._employment_agreement(),
            "independent_contractor_agreement": self._independent_contractor_agreement(),
            "nda": self._nda(),
            "non_compete_agreement": self._non_compete_agreement(),
            "offer_letter": self._offer_letter(),
            "separation_agreement": self._separation_agreement(),
            # Real Estate
            "residential_lease": self._residential_lease(),
            "commercial_lease": self._commercial_lease(),
            "month_to_month_rental": self._month_to_month_rental(),
            "lease_addendum": self._lease_addendum(),
            "pet_addendum": self._pet_addendum(),
            "roommate_agreement": self._roommate_agreement(),
            "notice_to_vacate_landlord": self._notice_to_vacate_landlord(),
            "notice_to_vacate_tenant": self._notice_to_vacate_tenant(),
            "pay_or_quit": self._pay_or_quit(),
            "cure_or_quit": self._cure_or_quit(),
            "unconditional_quit": self._unconditional_quit(),
            # Demand Letters
            "demand_letter_payment": self._demand_letter_payment(),
            "cease_and_desist_general": self._cease_and_desist_general(),
            "cease_and_desist_ip": self._cease_and_desist_ip(),
            "fdcpa_debt_validation": self._fdcpa_debt_validation(),
            "fcra_credit_dispute": self._fcra_credit_dispute(),
            "goodwill_letter": self._goodwill_letter(),
            "pay_for_delete": self._pay_for_delete(),
            # Estate Planning
            "last_will_simple": self._last_will_simple(),
            "last_will_with_trust": self._last_will_with_trust(),
            "durable_power_of_attorney": self._durable_power_of_attorney(),
            "healthcare_power_of_attorney": self._healthcare_power_of_attorney(),
            "living_will": self._living_will(),
            "transfer_on_death_deed": self._transfer_on_death_deed(),
            # Business Operations
            "invoice_template": self._invoice_template(),
            "contractor_invoice": self._contractor_invoice(),
            "business_proposal": self._business_proposal(),
            "mou": self._mou(),
            "loi": self._loi(),
            "confidentiality_agreement": self._confidentiality_agreement(),
            "terms_of_service": self._terms_of_service(),
            "privacy_policy": self._privacy_policy(),
        }

    def get_template(self, doc_type: str) -> str:
        """Return the complete template for the given document type."""
        template = self._templates.get(doc_type)
        if template is None:
            available = ", ".join(sorted(self._templates.keys()))
            raise KeyError(
                f"No template found for '{doc_type}'. "
                f"Available templates: {available}"
            )
        return template

    def list_templates(self) -> list:
        """Return list of all available template keys."""
        return sorted(self._templates.keys())

    # ------------------------------------------------------------------
    # TRUST DOCUMENTS
    # ------------------------------------------------------------------

    def _revocable_living_trust(self) -> str:
        return """\
                    REVOCABLE LIVING TRUST AGREEMENT

This Revocable Living Trust Agreement (this "Trust") is made this [DATE] day of
[MONTH], [YEAR], by [TRUSTOR FULL LEGAL NAME] (the "Trustor"), residing at
[TRUSTOR ADDRESS], [CITY], [STATE] [ZIP CODE].

                              RECITALS

WHEREAS, Trustor desires to create a revocable living trust for the management
of Trustor's assets during Trustor's lifetime and for the disposition of Trustor's
assets upon Trustor's death; and

WHEREAS, [TRUSTEE FULL NAME] (the "Trustee") has agreed to act as Trustee
in accordance with the terms of this Trust;

NOW, THEREFORE, Trustor declares as follows:

ARTICLE I — TRUST NAME AND IDENTIFICATION

  1.1 Trust Name. This trust shall be known as "The [TRUSTOR LAST NAME] Family
      Revocable Living Trust, dated [DATE]."

  1.2 Trust Purpose. This Trust is established to hold, manage, invest, and
      distribute the Trust Estate for the benefit of the beneficiaries named herein.

  1.3 Governing Law. This Trust shall be governed by the laws of the State of
      [STATE], without regard to conflicts of law provisions.

ARTICLE II — TRUST ESTATE

  2.1 Initial Transfer. Trustor hereby transfers, assigns, and conveys to Trustee
      all property described in Schedule A, attached hereto and incorporated herein
      by reference.

  2.2 Additional Transfers. Trustor may from time to time transfer additional
      property to this Trust by delivering such property to Trustee with a written
      assignment or by other means acceptable to Trustee.

  2.3 Title to Property. All property transferred to and accepted by Trustee shall
      be titled in the name of "[TRUSTOR NAME], Trustee of The [TRUSTOR LAST NAME]
      Family Revocable Living Trust, dated [DATE]."

ARTICLE III — REVOCABILITY

  3.1 Right to Revoke or Amend. During Trustor's lifetime and while Trustor has
      legal capacity, Trustor reserves the right, without the consent of any
      beneficiary or Trustee:
      (a) To revoke this Trust in whole or in part;
      (b) To amend this Trust in any manner;
      (c) To withdraw any property from the Trust Estate; and
      (d) To remove and replace the Trustee.

  3.2 Method of Revocation. Any revocation or amendment shall be made by written
      instrument signed by Trustor and delivered to Trustee.

ARTICLE IV — TRUSTEE PROVISIONS

  4.1 Initial Trustee. [TRUSTEE FULL NAME] shall serve as the initial Trustee.

  4.2 Successor Trustee. If the initial Trustee is unable or unwilling to serve,
      [SUCCESSOR TRUSTEE NAME] shall serve as Successor Trustee.

  4.3 Second Successor Trustee. If the Successor Trustee is unable or unwilling
      to serve, [SECOND SUCCESSOR TRUSTEE NAME] shall serve as Second Successor Trustee.

  4.4 Trustee Compensation. The Trustee shall be entitled to receive reasonable
      compensation for services rendered, consistent with prevailing rates in
      [STATE] for corporate fiduciaries.

  4.5 Trustee Powers. The Trustee shall have all powers granted under [STATE] law,
      including without limitation:
      (a) To retain any property transferred to the Trust;
      (b) To invest and reinvest Trust assets;
      (c) To sell, exchange, or lease Trust property;
      (d) To borrow money and mortgage Trust property;
      (e) To employ agents, advisors, and professionals;
      (f) To make distributions to beneficiaries;
      (g) To execute any instruments necessary to carry out Trust purposes;
      (h) To maintain and operate real estate;
      (i) To vote shares of stock and exercise options;
      (j) To settle or abandon claims.

ARTICLE V — BENEFICIARIES AND DISTRIBUTIONS DURING TRUSTOR'S LIFETIME

  5.1 Primary Beneficiary. During Trustor's lifetime, Trustor shall be the
      primary beneficiary of this Trust.

  5.2 Income and Principal. During Trustor's lifetime, Trustee shall distribute
      to Trustor such amounts of income and principal as Trustor directs. In the
      event Trustor is incapacitated, Trustee shall distribute income and principal
      as needed for Trustor's health, education, maintenance, and support.

  5.3 Incapacity. If Trustor is determined to be incapacitated by [NUMBER] licensed
      physicians, the Trustee shall manage the Trust Estate for the benefit of Trustor
      and Trustor's dependents.

ARTICLE VI — DISTRIBUTION UPON TRUSTOR'S DEATH

  6.1 Payment of Debts and Expenses. Upon Trustor's death, Trustee shall pay from
      the Trust Estate:
      (a) All legally enforceable debts of Trustor;
      (b) Reasonable funeral and burial expenses;
      (c) Costs of administration of the Trust.

  6.2 Specific Gifts. Trustee shall distribute the following specific gifts:
      (a) [SPECIFIC ITEM OR AMOUNT] to [BENEFICIARY NAME], if living;
      (b) [SPECIFIC ITEM OR AMOUNT] to [BENEFICIARY NAME], if living.

  6.3 Residuary Distribution. After payment of debts and specific gifts, the
      remaining Trust Estate (the "Residuary Estate") shall be distributed as follows:
      (a) [PERCENTAGE]% to [PRIMARY BENEFICIARY NAME], if living;
      (b) [PERCENTAGE]% to [PRIMARY BENEFICIARY NAME], if living.

  6.4 Per Stirpes Distribution. If any beneficiary predeceases Trustor, that
      beneficiary's share shall pass to such beneficiary's then-living descendants,
      per stirpes.

  6.5 Ultimate Beneficiary. If no beneficiaries survive Trustor, the Residuary
      Estate shall be distributed to [ULTIMATE BENEFICIARY OR CHARITY].

ARTICLE VII — CHILDREN'S TRUSTS

  7.1 Minors' Shares. Any share passing to a minor beneficiary shall be retained
      in a separate trust for such beneficiary until age [AGE, e.g., 25].

  7.2 Distribution Standards. While held in trust for a minor, Trustee may
      distribute income and principal for such beneficiary's health, education,
      maintenance, and support.

  7.3 Distribution at Majority. Upon such beneficiary reaching age [AGE], the
      remaining trust shall be distributed outright to such beneficiary.

ARTICLE VIII — SPENDTHRIFT PROVISIONS

  8.1 Spendthrift Restriction. No interest of any beneficiary under this Trust
      shall be subject to the claims of creditors, assignment, attachment, or
      alienation before actual receipt by such beneficiary.

ARTICLE IX — NO-CONTEST CLAUSE

  9.1 In Terrorem. Any beneficiary who contests or challenges this Trust or any
      of its provisions shall forfeit all benefits and receive nothing from
      the Trust Estate.

ARTICLE X — TRUSTEE LIABILITY

  10.1 Standard of Care. Trustee shall exercise the degree of care, skill, and
       caution that a prudent investor would exercise.

  10.2 Limitation of Liability. Trustee shall not be liable for any loss or
       depreciation in the value of Trust assets except for Trustee's willful
       misconduct or gross negligence.

ARTICLE XI — POUR-OVER PROVISION

  11.1 Pour-Over. Any assets not otherwise transferred to this Trust that are
       directed to this Trust by Trustor's Last Will and Testament shall be
       added to and administered as part of this Trust.

ARTICLE XII — MISCELLANEOUS

  12.1 Severability. If any provision of this Trust is found invalid or
       unenforceable, the remaining provisions shall remain in full force.

  12.2 Entire Agreement. This Trust constitutes the entire agreement with
       respect to its subject matter.

  12.3 Amendments Must Be Written. No oral amendment to this Trust shall
       be effective.

IN WITNESS WHEREOF, Trustor and Trustee have executed this Revocable Living
Trust Agreement as of the date first written above.

TRUSTOR:

_________________________________        Date: ________________
[TRUSTOR FULL LEGAL NAME]


TRUSTEE:

_________________________________        Date: ________________
[TRUSTEE FULL NAME]


STATE OF [STATE]       )
                       ) ss.
COUNTY OF [COUNTY]     )

On this ___ day of [MONTH], [YEAR], before me, the undersigned Notary Public,
personally appeared [TRUSTOR FULL NAME], known to me to be the person whose
name is subscribed to the foregoing instrument, and acknowledged to me that
he/she executed the same for the purposes therein contained.

_________________________________
Notary Public
My Commission Expires: ____________

                            SCHEDULE A
                    PROPERTY TRANSFERRED TO TRUST

[LIST OF PROPERTY TRANSFERRED — e.g., real property, bank accounts, investments]
1. Real Property located at: [PROPERTY ADDRESS]
2. Financial Account No. [ACCOUNT NUMBER] at [INSTITUTION NAME]
3. [DESCRIBE ADDITIONAL PROPERTY]
"""

    def _irrevocable_trust(self) -> str:
        return """\
                    IRREVOCABLE TRUST AGREEMENT

This Irrevocable Trust Agreement (the "Trust") is entered into as of [DATE],
by and between [GRANTOR FULL NAME] (the "Grantor"), residing at [ADDRESS],
and [TRUSTEE FULL NAME] (the "Trustee"), residing at [TRUSTEE ADDRESS].

WITNESSETH:

WHEREAS, Grantor desires to establish an irrevocable trust for the benefit
of the persons named herein, for the purposes set forth herein; and

WHEREAS, Trustee has agreed to accept and administer the Trust Estate
subject to the terms herein;

NOW, THEREFORE, in consideration of the mutual covenants and agreements
contained herein, and other good and valuable consideration, the parties
agree as follows:

ARTICLE I — CREATION OF IRREVOCABLE TRUST

  1.1 Trust Name. This trust shall be known as "The [GRANTOR LAST NAME]
      Irrevocable Trust, dated [DATE]."

  1.2 Irrevocability. This Trust is IRREVOCABLE and may not be revoked,
      amended, or modified by Grantor or any other person without the
      consent of all beneficiaries and Trustee, except as permitted by law.

  1.3 Purpose. This Trust is established for the following purposes:
      [DESCRIBE TRUST PURPOSES — e.g., asset protection, estate planning,
      Medicaid planning, gift tax exclusion, charitable purposes]

ARTICLE II — TRUST ESTATE

  2.1 Initial Transfer. Grantor hereby irrevocably transfers and assigns
      to Trustee the property described in Schedule A hereto.

  2.2 Acceptance by Trustee. Trustee hereby accepts the Trust Estate and
      agrees to hold, manage, and distribute it pursuant to this Trust.

ARTICLE III — BENEFICIARIES

  3.1 Primary Beneficiaries. The primary beneficiaries of this Trust are:
      (a) [PRIMARY BENEFICIARY 1 NAME], born [DOB], relation: [RELATION];
      (b) [PRIMARY BENEFICIARY 2 NAME], born [DOB], relation: [RELATION].

  3.2 Contingent Beneficiaries. In the event a primary beneficiary predeceases
      the termination of this Trust, such beneficiary's share shall pass to:
      [CONTINGENT BENEFICIARY NAME].

ARTICLE IV — DISTRIBUTIONS

  4.1 Distribution Standards. Trustee shall distribute income and/or principal
      to or for the benefit of the beneficiaries for:
      (a) Health and medical expenses;
      (b) Education and tuition;
      (c) Maintenance and support;
      (d) [OTHER DISTRIBUTION STANDARD].

  4.2 Accumulation. Trustee may accumulate income not distributed.

ARTICLE V — TRUSTEE PROVISIONS

  5.1 Powers. Trustee shall have all powers provided under [STATE] law.

  5.2 Successor Trustee. If Trustee resigns or is incapacitated,
      [SUCCESSOR TRUSTEE NAME] shall serve as successor.

ARTICLE VI — SPENDTHRIFT CLAUSE

  6.1 No beneficiary may assign, encumber, or anticipate any interest in
      this Trust, and no creditor may attach or execute upon any Trust interest
      before distribution.

ARTICLE VII — TERMINATION

  7.1 This Trust shall terminate upon the earlier of:
      (a) [TERMINATION CONDITION, e.g., the death of last surviving beneficiary]; or
      (b) [DATE OR EVENT].

  7.2 Upon termination, the remaining Trust Estate shall be distributed to
      [FINAL DISTRIBUTION BENEFICIARY].

IN WITNESS WHEREOF, the parties have executed this Agreement.

GRANTOR:                                    TRUSTEE:
_____________________________               _____________________________
[GRANTOR FULL NAME]                         [TRUSTEE FULL NAME]
Date: _______________________               Date: _______________________

NOTARIZATION:
[STANDARD NOTARY BLOCK — STATE OF [STATE], COUNTY OF [COUNTY]]
"""

    def _special_needs_trust(self) -> str:
        return """\
                     SPECIAL NEEDS TRUST AGREEMENT
               (Supplemental Needs Trust — Third Party)

This Special Needs Trust (the "Trust") is established this [DATE] by
[GRANTOR NAME] (the "Grantor") for the benefit of [BENEFICIARY FULL NAME]
(the "Beneficiary"), who has [DESCRIBE DISABILITY].

PURPOSE: This Trust is intended to supplement, not replace, government
benefits available to the Beneficiary including, but not limited to,
Supplemental Security Income (SSI), Medicaid, Section 8 housing assistance,
and any other public benefit program. Distributions from this Trust shall
be used exclusively for expenses NOT covered by such programs.

ARTICLE I — CREATION AND FUNDING

  1.1 This Trust is irrevocable and is funded with assets described in
      Schedule A.

  1.2 Additional contributions may be made by any person other than
      the Beneficiary.

ARTICLE II — TRUSTEE

  2.1 Initial Trustee: [TRUSTEE NAME]
  2.2 Successor Trustee: [SUCCESSOR TRUSTEE NAME]
  2.3 Trustee shall have no obligation to advocate for the Beneficiary
      to receive public benefits, but shall not take actions to jeopardize
      such benefits.

ARTICLE III — DISTRIBUTIONS

  3.1 Permissible Distributions. Trustee may make distributions for:
      (a) Supplemental medical care, dental, and vision not covered by Medicaid;
      (b) Education, training, and vocational rehabilitation;
      (c) Transportation and vehicle expenses;
      (d) Recreation, entertainment, and travel;
      (e) Electronic equipment, computers, and communication devices;
      (f) Clothing, grooming, and personal care items;
      (g) Legal fees and advocacy services;
      (h) [OTHER SUPPLEMENTAL NEEDS].

  3.2 Prohibited Distributions. Trustee shall NOT make distributions that
      would disqualify the Beneficiary from receiving public benefits,
      including direct cash payments for food or shelter (unless permitted
      under applicable law).

ARTICLE IV — DISABILITY DETERMINATION

  4.1 "Disability" means a physical or mental impairment that substantially
      limits one or more major life activities as defined under the Americans
      with Disabilities Act and/or Social Security Act.

ARTICLE V — TERMINATION

  5.1 This Trust terminates upon the death of the Beneficiary or when
      Trust assets are exhausted.

  5.2 Upon termination, remaining assets shall be distributed to:
      [REMAINDER BENEFICIARY], subject to any Medicaid payback requirements
      under applicable state law.

ARTICLE VI — MEDICAID PAYBACK

  6.1 This is a THIRD-PARTY Special Needs Trust. Medicaid payback provisions
      [DO / DO NOT] apply per [STATE] law. [CONSULT ELDER LAW ATTORNEY]

SIGNED: [GRANTOR NAME]                    Date: ________________
TRUSTEE: [TRUSTEE NAME]                   Date: ________________
[NOTARY BLOCK]
"""

    def _charitable_remainder_trust(self) -> str:
        return """\
              CHARITABLE REMAINDER UNITRUST AGREEMENT (CRUT)

This Charitable Remainder Unitrust Agreement (the "Trust") is made this [DATE]
by [GRANTOR NAME] (the "Grantor") and [TRUSTEE NAME] (the "Trustee").

ARTICLE I — CREATION

  1.1 Grantor hereby irrevocably transfers to Trustee the property in Schedule A.
  1.2 This Trust qualifies as a Charitable Remainder Unitrust under
      Internal Revenue Code Section 664.

ARTICLE II — UNITRUST AMOUNT

  2.1 Trustee shall pay to [INCOME BENEFICIARY NAME] (the "Income Beneficiary")
      [PERCENTAGE, e.g., 5]% of the net fair market value of the Trust assets,
      valued annually, for the life of the Income Beneficiary / a term of
      [NUMBER] years (not to exceed 20 years).

  2.2 Payments shall be made [quarterly / annually] on [PAYMENT DATE(S)].

ARTICLE III — CHARITABLE REMAINDER

  3.1 Upon termination of the unitrust interest, the remaining Trust Estate
      shall be distributed to [CHARITABLE ORGANIZATION NAME], a 501(c)(3)
      organization, EIN: [EIN NUMBER].

  3.2 If the named charity ceases to qualify, Trustee shall select a
      comparable 501(c)(3) organization.

ARTICLE IV — TRUSTEE

  4.1 Initial Trustee: [TRUSTEE NAME]
  4.2 The Trustee shall file IRS Form 5227 annually.

ARTICLE V — TAX PROVISIONS

  5.1 Grantor intends this Trust to qualify for the federal charitable
      deduction under IRC Section 170.
  5.2 [CONSULT TAX COUNSEL FOR APPLICABLE DEDUCTION CALCULATION]

SIGNED: [GRANTOR NAME]                     Date: ________________
TRUSTEE: [TRUSTEE NAME]                    Date: ________________
[NOTARY BLOCK]
"""

    # ------------------------------------------------------------------
    # CORPORATE DOCUMENTS
    # ------------------------------------------------------------------

    def _llc_operating_agreement_single(self) -> str:
        return """\
              SINGLE-MEMBER LIMITED LIABILITY COMPANY
                      OPERATING AGREEMENT

                   [COMPANY NAME], LLC

This Operating Agreement (this "Agreement") of [COMPANY NAME], LLC
(the "Company") is entered into as of [DATE] by [MEMBER FULL NAME]
(the "Member"), the sole member of the Company.

ARTICLE 1 — FORMATION

  1.1 Organization. The Company was organized as a limited liability company
      under the laws of the State of [STATE] on [FORMATION DATE], pursuant
      to the [STATE] Limited Liability Company Act (the "Act"), by filing
      the Articles of Organization with the [STATE] Secretary of State.

  1.2 Name. The name of the Company is [COMPANY NAME], LLC.

  1.3 Principal Office. The principal office of the Company is located at
      [PRINCIPAL ADDRESS], [CITY], [STATE] [ZIP].

  1.4 Registered Agent. The Company's registered agent in [STATE] is
      [REGISTERED AGENT NAME], located at [REGISTERED AGENT ADDRESS].

  1.5 Term. The Company shall continue perpetually unless dissolved in
      accordance with this Agreement or applicable law.

  1.6 Purpose. The purpose of the Company is to engage in any lawful
      business activity permitted under [STATE] law, including but not
      limited to: [DESCRIBE BUSINESS PURPOSE].

ARTICLE 2 — MEMBER

  2.1 Sole Member. [MEMBER FULL NAME] is the sole Member of the Company.
  2.2 Member's Interest. The Member holds 100% of the membership interest
      in the Company.
  2.3 No Other Members. No other persons are members of the Company.

ARTICLE 3 — CAPITAL CONTRIBUTIONS

  3.1 Initial Contribution. The Member has contributed to the Company
      the following: [DESCRIBE INITIAL CONTRIBUTION — cash, property, services].
  3.2 Additional Contributions. The Member may make additional contributions
      at any time.
  3.3 No Interest on Contributions. No interest shall be paid on contributions.

ARTICLE 4 — MANAGEMENT

  4.1 Member-Managed. The Company shall be managed by the Member.
  4.2 Authority. The Member has full authority to:
      (a) Execute contracts on behalf of the Company;
      (b) Open and manage bank accounts;
      (c) Hire and terminate employees;
      (d) Purchase and sell assets;
      (e) Borrow money and execute loans;
      (f) Make all business decisions.

ARTICLE 5 — OFFICERS

  5.1 The Member may appoint the following officers:
      (a) President / CEO: [NAME]
      (b) Secretary: [NAME]
      (c) Treasurer / CFO: [NAME]
  5.2 The Member may remove any officer at any time.

ARTICLE 6 — ALLOCATIONS AND DISTRIBUTIONS

  6.1 Allocations. All items of income, gain, loss, deduction, and credit
      shall be allocated 100% to the Member.
  6.2 Distributions. The Member may withdraw funds from the Company at
      any time, subject to the Company's ability to pay its obligations.
  6.3 Tax Treatment. The Company shall be treated as a disregarded entity
      for federal income tax purposes (sole proprietorship), unless the
      Member elects otherwise.

ARTICLE 7 — BOOKS, RECORDS, AND ACCOUNTING

  7.1 The Company shall maintain complete and accurate books and records.
  7.2 Fiscal Year. The fiscal year shall end on [FISCAL YEAR END — e.g., December 31].
  7.3 Accounting Method. The Company shall use the [cash / accrual] method
      of accounting.

ARTICLE 8 — TAX MATTERS

  8.1 The Member shall be responsible for all federal and state income taxes
      on Company income, reported on the Member's personal return.
  8.2 The Company's EIN is: [EIN NUMBER].

ARTICLE 9 — BANK ACCOUNTS

  9.1 The Company shall maintain a separate business bank account(s) in the
      name of the Company.
  9.2 Authorized Signatories: [AUTHORIZED SIGNATORIES].

ARTICLE 10 — INDEMNIFICATION

  10.1 The Company shall indemnify and hold harmless the Member from any
       claims arising from actions taken in good faith on behalf of the Company.

ARTICLE 11 — LIABILITY

  11.1 The Member shall not be personally liable for the debts, obligations,
       or liabilities of the Company solely by reason of being a Member.

ARTICLE 12 — DISSOLUTION

  12.1 The Company may be dissolved by the Member at any time.
  12.2 Upon dissolution, assets shall be applied to: (a) Company debts;
       (b) Member contributions; (c) remaining balance to Member.

ARTICLE 13 — AMENDMENT

  13.1 This Agreement may be amended only by written instrument signed by the Member.

ARTICLE 14 — GOVERNING LAW

  14.1 This Agreement is governed by the laws of [STATE].

ARTICLE 15 — ENTIRE AGREEMENT

  15.1 This Agreement constitutes the entire operating agreement of the Company.

IN WITNESS WHEREOF, the Member has executed this Operating Agreement.

MEMBER:

_________________________________            Date: ________________
[MEMBER FULL NAME]

[COMPANY NAME], LLC
EIN: [EIN NUMBER]
State of Formation: [STATE]
Date of Formation: [DATE]
"""

    def _llc_operating_agreement_multi(self) -> str:
        return """\
              MULTI-MEMBER LIMITED LIABILITY COMPANY
                      OPERATING AGREEMENT

                   [COMPANY NAME], LLC

This Operating Agreement (this "Agreement") of [COMPANY NAME], LLC
(the "Company") is entered into as of [DATE] by and among the persons
listed on Exhibit A attached hereto (collectively, the "Members").

ARTICLE 1 — ORGANIZATION

  1.1 Formation. The Company was formed under the [STATE] LLC Act on [DATE].
  1.2 Name. [COMPANY NAME], LLC.
  1.3 Principal Office. [PRINCIPAL ADDRESS], [CITY], [STATE] [ZIP].
  1.4 Registered Agent. [REGISTERED AGENT], [ADDRESS].
  1.5 Term. Perpetual unless otherwise dissolved.
  1.6 Purpose. [BUSINESS PURPOSE].

ARTICLE 2 — MEMBERS AND MEMBERSHIP INTERESTS

  2.1 Members and Initial Interests (see Exhibit A for complete list):
      [MEMBER 1 NAME]       [PERCENTAGE]%   Class [A/B] Units
      [MEMBER 2 NAME]       [PERCENTAGE]%   Class [A/B] Units
      [MEMBER 3 NAME]       [PERCENTAGE]%   Class [A/B] Units

  2.2 Capital Accounts. A separate Capital Account shall be maintained
      for each Member in accordance with Treasury Regulations.

  2.3 No Member shall transfer, sell, or assign membership interest without
      prior written consent of [MAJORITY / SUPERMAJORITY / ALL] of Members.

ARTICLE 3 — CAPITAL CONTRIBUTIONS

  3.1 Initial Contributions. Members' initial capital contributions are
      set forth in Exhibit A.
  3.2 Additional Contributions. Additional contributions require unanimous
      written consent of all Members.
  3.3 No member is obligated to make additional contributions.

ARTICLE 4 — ALLOCATIONS

  4.1 Profits and Losses. Profits and losses shall be allocated pro rata
      in proportion to each Member's Percentage Interest.
  4.2 Special Allocations. Notwithstanding Section 4.1, special allocations
      may be made as required by Treasury Regulations Sections 1.704-1 and
      1.704-2 (qualified income offset, minimum gain chargeback, etc.).

ARTICLE 5 — DISTRIBUTIONS

  5.1 Timing. Distributions shall be made at such times as determined by
      [Majority Vote / Management].
  5.2 Order of Distributions:
      (a) Return of preferred capital contributions;
      (b) Pro rata to all Members per Percentage Interest.
  5.3 Tax Distributions. The Company shall distribute to each Member
      [PERCENTAGE]% of such Member's allocable income to cover tax obligations.

ARTICLE 6 — MANAGEMENT

  6.1 Manager-Managed. The Company shall be managed by [MANAGER NAME(S)].
  6.2 Manager Authority. Manager(s) have authority to bind the Company in
      ordinary business transactions.
  6.3 Major Decisions Requiring Member Vote (specify % threshold):
      (a) Admit new members — [THRESHOLD]%;
      (b) Sell substantially all assets — [THRESHOLD]%;
      (c) Merge or dissolve Company — [THRESHOLD]%;
      (d) Amend this Agreement — [THRESHOLD]%;
      (e) Incur debt exceeding $[AMOUNT] — [THRESHOLD]%.

ARTICLE 7 — MEETINGS AND VOTING

  7.1 Annual Meeting. Members shall meet annually on [DATE/MONTH].
  7.2 Special Meetings. Called by any Member holding [PERCENTAGE]% interest.
  7.3 Quorum. [PERCENTAGE]% of membership interests.
  7.4 Voting. Each Member votes in proportion to Percentage Interest.

ARTICLE 8 — TRANSFER RESTRICTIONS AND RIGHT OF FIRST REFUSAL

  8.1 Right of First Refusal. Before transferring any interest, the selling
      Member must first offer the interest to existing Members pro rata at
      the same price and terms.
  8.2 Buy-Out Option. If a Member dies, becomes incapacitated, or wishes
      to withdraw, the Company and/or other Members may purchase such
      interest at fair market value.
  8.3 Drag-Along Right. Members holding [PERCENTAGE]% may require all
      Members to sell in a company sale transaction.
  8.4 Tag-Along Right. Each Member may participate pro rata in any sale.

ARTICLE 9 — MEMBER WITHDRAWAL AND EXPULSION

  9.1 Voluntary Withdrawal. A Member may withdraw upon [NUMBER] days
      written notice. Withdrawn Member receives fair market value of interest.
  9.2 Involuntary Expulsion. A Member may be expelled by [UNANIMOUS / SUPERMAJORITY]
      vote for: (a) material breach; (b) conviction of felony; (c) bankruptcy.

ARTICLE 10 — BOOKS, RECORDS, AND FINANCIAL MATTERS

  10.1 Books and records shall be maintained at the principal office.
  10.2 Each Member has the right to inspect and copy records.
  10.3 Fiscal Year: [FISCAL YEAR END].
  10.4 Accounting Method: [CASH / ACCRUAL].

ARTICLE 11 — TAX MATTERS

  11.1 Tax Representative. [MEMBER NAME] is designated as the Tax Matters
       Partner / Partnership Representative.
  11.2 The Company shall be treated as a partnership for federal income
       tax purposes. Schedule K-1 shall be provided to each Member.

ARTICLE 12 — INDEMNIFICATION

  12.1 The Company shall indemnify Managers and Members for actions taken
       in good faith on behalf of the Company.

ARTICLE 13 — DISSOLUTION AND WINDING UP

  13.1 Dissolution Events:
       (a) Unanimous consent of Members;
       (b) Judicial dissolution;
       (c) Entry of decree of dissolution.
  13.2 Winding Up Order:
       (a) Pay Company debts and liabilities;
       (b) Return Member capital contributions;
       (c) Distribute remaining assets pro rata.

ARTICLE 14 — GOVERNING LAW

  14.1 [STATE] law governs this Agreement.

ARTICLE 15 — DISPUTE RESOLUTION

  15.1 Disputes shall be resolved by [MEDIATION / ARBITRATION / LITIGATION]
       in [COUNTY], [STATE].

ARTICLE 16 — MISCELLANEOUS

  16.1 Counterparts. This Agreement may be executed in counterparts.
  16.2 Amendments. Require [SUPERMAJORITY / UNANIMOUS] written consent.
  16.3 Entire Agreement. This Agreement is the entire agreement.

IN WITNESS WHEREOF, the Members execute this Agreement as of the date above.

MEMBERS:

_________________________________            Date: ________________
[MEMBER 1 FULL NAME]

_________________________________            Date: ________________
[MEMBER 2 FULL NAME]

_________________________________            Date: ________________
[MEMBER 3 FULL NAME]

                           EXHIBIT A
                     MEMBERS AND INTERESTS

NAME                    ADDRESS                 CONTRIBUTION    INTEREST
[MEMBER 1 NAME]         [ADDRESS]               $[AMOUNT]       [%]
[MEMBER 2 NAME]         [ADDRESS]               $[AMOUNT]       [%]
[MEMBER 3 NAME]         [ADDRESS]               $[AMOUNT]       [%]
"""

    def _corporate_bylaws(self) -> str:
        return """\
                        BYLAWS OF
                  [CORPORATION NAME], INC.
            A [STATE] Corporation

                    ARTICLE I — OFFICES

  Section 1.1 Principal Office. The principal office shall be at
  [PRINCIPAL ADDRESS], [CITY], [STATE] [ZIP].

  Section 1.2 Registered Office. The registered office in [STATE] is
  [REGISTERED AGENT ADDRESS].

                 ARTICLE II — SHAREHOLDERS

  Section 2.1 Annual Meeting. The annual meeting of shareholders shall
  be held on [DATE] of each year.

  Section 2.2 Special Meetings. Called by Board, President, or
  holders of [%]% of shares.

  Section 2.3 Notice. Written notice [NUMBER] days before each meeting.

  Section 2.4 Quorum. Holders of majority of outstanding shares.

  Section 2.5 Voting. Each share entitles the holder to one vote.

                  ARTICLE III — BOARD OF DIRECTORS

  Section 3.1 Number. The Board shall consist of [NUMBER] directors.

  Section 3.2 Election. Directors elected annually by shareholders.

  Section 3.3 Term. Directors serve one-year terms.

  Section 3.4 Removal. Directors may be removed with or without cause
  by majority vote of shareholders.

  Section 3.5 Vacancies. Filled by majority vote of remaining directors.

  Section 3.6 Meetings. Board meets [FREQUENCY]. Special meetings called
  by [CHAIR / PRESIDENT / NUMBER OF DIRECTORS].

  Section 3.7 Quorum. Majority of directors constitutes quorum.

  Section 3.8 Compensation. Directors receive $[AMOUNT] per meeting /
  annual retainer of $[AMOUNT].

                    ARTICLE IV — OFFICERS

  Section 4.1 Officers. The corporation shall have: President/CEO,
  Vice President, Secretary, and Treasurer/CFO.

  Section 4.2 Election. Officers elected by the Board annually.

  Section 4.3 President/CEO. Chief executive officer; manages operations.

  Section 4.4 Secretary. Maintains records, minutes, and corporate filings.

  Section 4.5 Treasurer/CFO. Custodian of funds; maintains financial records.

                ARTICLE V — STOCK AND SHAREHOLDERS

  Section 5.1 Authorized Shares. [NUMBER] shares of common stock, par
  value $[AMOUNT] per share.

  Section 5.2 Certificates. Stock certificates shall be issued to shareholders.

  Section 5.3 Transfer Restrictions. Transfers subject to right of first
  refusal held by corporation.

               ARTICLE VI — INDEMNIFICATION

  Section 6.1 The corporation shall indemnify directors and officers
  to the fullest extent permitted by [STATE] law.

               ARTICLE VII — AMENDMENTS

  Section 7.1 These Bylaws may be amended by majority vote of the
  Board or by majority vote of shareholders.

              ARTICLE VIII — FISCAL YEAR AND RECORDS

  Section 8.1 Fiscal Year: [FISCAL YEAR END].

  Section 8.2 Records kept at principal office; available for
  shareholder inspection.

Adopted by the Board of Directors on [DATE].

_________________________________        _________________________________
[DIRECTOR NAME], Chairman                [SECRETARY NAME], Secretary
"""

    def _shareholder_agreement(self) -> str:
        return """\
                    SHAREHOLDERS AGREEMENT
               [CORPORATION NAME], INC.

This Shareholders Agreement (this "Agreement") is entered into as of [DATE]
by and among [CORPORATION NAME], Inc. (the "Company") and the shareholders
listed on Exhibit A (the "Shareholders").

ARTICLE 1 — PURPOSE
  The parties enter this Agreement to promote harmony among shareholders,
  protect each Shareholder's investment, and provide for orderly transfer
  of shares.

ARTICLE 2 — RESTRICTIONS ON TRANSFER
  2.1 No Shareholder may sell, transfer, assign, pledge, or encumber any
      shares without prior written consent of Shareholders holding
      [PERCENTAGE]% of outstanding shares.
  2.2 Right of First Refusal. Selling Shareholder must first offer shares
      to Company, then pro rata to other Shareholders.
  2.3 Tag-Along Rights. Non-selling Shareholders may sell on same terms.
  2.4 Drag-Along Rights. [PERCENTAGE]% shareholders may require all to sell.

ARTICLE 3 — MANAGEMENT AND VOTING
  3.1 Board Composition. The Board shall include [NUMBER] directors.
  3.2 Each Shareholder class shall have the right to nominate [NUMBER] directors.
  3.3 Supermajority Vote Required for: [LIST MAJOR DECISIONS].

ARTICLE 4 — BUY-SELL PROVISIONS
  4.1 On death, disability, or termination of employment of a Shareholder,
      Company may purchase shares at [FAIR MARKET VALUE / BOOK VALUE /
      FORMULA: ________________].
  4.2 Funding. Company shall maintain [life insurance / buy-sell reserve fund]
      to fund buyouts.

ARTICLE 5 — INFORMATION RIGHTS
  Each Shareholder holding [PERCENTAGE]% or more shall receive:
  (a) Annual audited financial statements;
  (b) Quarterly unaudited financials;
  (c) Annual budget and business plan.

ARTICLE 6 — NON-COMPETE / NON-SOLICITATION
  During ownership and for [NUMBER] years after, no Shareholder shall:
  (a) Compete with the Company within [GEOGRAPHIC AREA];
  (b) Solicit Company employees or customers.

ARTICLE 7 — DISPUTE RESOLUTION
  Disputes resolved by [ARBITRATION / MEDIATION] in [CITY, STATE].

Signed by all parties on [DATE]:
[SIGNATURE BLOCKS FOR ALL SHAREHOLDERS]
"""

    def _buy_sell_agreement(self) -> str:
        return """\
                       BUY-SELL AGREEMENT

This Buy-Sell Agreement is entered into as of [DATE] by and among
[OWNER 1 NAME], [OWNER 2 NAME] (collectively, "Owners"), and
[COMPANY NAME] (the "Company").

1. PURPOSE. To ensure orderly transition of ownership upon a
   "Triggering Event."

2. TRIGGERING EVENTS. A "Triggering Event" occurs upon:
   (a) Death of an Owner;
   (b) Permanent disability of an Owner;
   (c) Retirement of an Owner;
   (d) Voluntary withdrawal of an Owner;
   (e) Bankruptcy or insolvency of an Owner;
   (f) Involuntary transfer (divorce, judgment lien).

3. PURCHASE OBLIGATION. Upon a Triggering Event, the surviving/remaining
   Owner(s) or Company MUST purchase the departing Owner's interest.

4. VALUATION METHOD. Purchase price shall be determined by:
   [CHOOSE: Fixed price $[AMOUNT] / Agreed formula / Independent appraisal /
   Capitalization of earnings at [MULTIPLE]x]

5. PAYMENT TERMS. Purchase price paid: [LUMP SUM / INSTALLMENTS over
   [NUMBER] years at [INTEREST RATE]% interest].

6. LIFE INSURANCE FUNDING. Company shall maintain life insurance policies
   on each Owner in the amount of $[AMOUNT].
   Policies: [INSURER], Policy No. [POLICY NUMBER].

7. DISABILITY FUNDING. Disability buyout funded by [METHOD].

8. DISPUTE RESOLUTION. Any dispute regarding valuation submitted to
   independent appraisal by CPA agreed upon by parties.

Signed: [OWNER 1], [OWNER 2], [COMPANY AUTHORIZED OFFICER]
Date: [DATE]
"""

    def _board_resolutions(self) -> str:
        return """\
               WRITTEN CONSENT OF THE BOARD OF DIRECTORS
                        OF [CORPORATION NAME], INC.

        (Unanimous Written Consent in Lieu of Meeting)

The undersigned, being all the directors of [CORPORATION NAME], Inc.,
a [STATE] corporation (the "Corporation"), hereby consent to and adopt
the following resolutions pursuant to [STATE] Corporations Code Section [CODE]:

RESOLVED, that [DESCRIBE ACTION 1];

FURTHER RESOLVED, that [DESCRIBE ACTION 2];

FURTHER RESOLVED, that the officers of the Corporation are authorized
and directed to take any and all actions necessary to carry out and
give effect to the foregoing resolutions;

FURTHER RESOLVED, that any actions taken prior to the date hereof
consistent with the foregoing resolutions are hereby ratified, confirmed,
and approved.

This Written Consent may be executed in counterparts.

Dated: [DATE]

_________________________________          _________________________________
[DIRECTOR 1 NAME]                          [DIRECTOR 2 NAME]
Director                                   Director

_________________________________
[DIRECTOR 3 NAME]
Director
"""

    def _annual_meeting_minutes(self) -> str:
        return """\
          MINUTES OF THE ANNUAL MEETING OF SHAREHOLDERS
                  OF [CORPORATION NAME], INC.

DATE:     [DATE]
TIME:     [TIME]
PLACE:    [LOCATION OR "Held via video conference"]

CALL TO ORDER

  The annual meeting of shareholders was called to order by [CHAIR NAME],
  Chairman of the Board, at [TIME] [AM/PM].

ATTENDANCE

  The following shareholders, representing [PERCENTAGE]% of outstanding shares,
  were present in person or by proxy:

  NAME                    SHARES HELD    PRESENT / PROXY
  [SHAREHOLDER 1]         [NUMBER]       [Present / Proxy]
  [SHAREHOLDER 2]         [NUMBER]       [Present / Proxy]

  A quorum was [present / not present]. [IF QUORUM PRESENT, CONTINUE.]

APPROVAL OF MINUTES

  MOTION by [NAME] to approve minutes of the prior annual meeting.
  SECONDED by [NAME]. VOTE: [UNANIMOUS / TALLY]. APPROVED.

ELECTION OF DIRECTORS

  The following were nominated and elected as directors for the ensuing year:

  DIRECTOR                  VOTES FOR    VOTES AGAINST    ABSTAIN
  [DIRECTOR 1 NAME]         [NUMBER]     [NUMBER]         [NUMBER]

OFFICER ELECTIONS

  MOTION to elect the following officers:
  President:  [NAME]
  Secretary:  [NAME]
  Treasurer:  [NAME]
  VOTE: UNANIMOUS. APPROVED.

FINANCIAL REPORT

  [TREASURER NAME] presented the financial report for fiscal year [YEAR].
  [SUMMARIZE KEY FINANCIALS].
  Shareholders asked questions; [TREASURER NAME] responded.

OLD BUSINESS

  [DESCRIBE ANY PENDING ITEMS FROM PRIOR MEETING]

NEW BUSINESS

  [DESCRIBE NEW BUSINESS ITEMS]

ADJOURNMENT

  There being no further business, the meeting was adjourned at [TIME] [AM/PM].

Respectfully submitted,

_________________________________
[SECRETARY NAME], Secretary
"""

    # ------------------------------------------------------------------
    # EMPLOYMENT DOCUMENTS
    # ------------------------------------------------------------------

    def _employment_agreement(self) -> str:
        return """\
                      EMPLOYMENT AGREEMENT

This Employment Agreement (the "Agreement") is entered into as of [START DATE]
by and between [EMPLOYER NAME], a [STATE] [entity type] ("Employer"), and
[EMPLOYEE FULL NAME] ("Employee").

1. POSITION AND DUTIES
   1.1 Position: [JOB TITLE]
   1.2 Department: [DEPARTMENT]
   1.3 Reports To: [SUPERVISOR TITLE]
   1.4 Duties: Employee shall perform the following duties: [JOB DESCRIPTION].
   1.5 Full-Time: Employee shall devote substantially all business time to duties.

2. TERM
   2.1 Start Date: [START DATE]
   2.2 Term: [AT-WILL / FIXED TERM OF [NUMBER] YEARS, ending [END DATE]].
   2.3 At-Will Employment: [IF AT-WILL] Either party may terminate at any time
       with or without cause, with or without notice.

3. COMPENSATION
   3.1 Base Salary: $[AMOUNT] per [year / month / hour], paid [bi-weekly / monthly].
   3.2 Bonus: Eligible for annual bonus up to [PERCENTAGE]% of base salary,
       based on performance metrics: [DESCRIBE METRICS].
   3.3 Equity: [NONE / OPTIONS for [NUMBER] shares, vesting per Exhibit A].
   3.4 Increases: Subject to annual review.

4. BENEFITS
   4.1 Health Insurance: Employer pays [PERCENTAGE]% of premiums.
   4.2 Dental and Vision: [COVERED / NOT COVERED].
   4.3 401(k): Eligible after [NUMBER] days; Employer matches [PERCENTAGE]%.
   4.4 Paid Time Off: [NUMBER] days PTO per year; [NUMBER] sick days.
   4.5 Holidays: [NUMBER] paid holidays per year.
   4.6 [OTHER BENEFITS].

5. CONFIDENTIALITY
   Employee agrees to keep all Confidential Information strictly confidential
   during and after employment. "Confidential Information" includes trade secrets,
   client lists, financial data, business strategies, and proprietary information.

6. INTELLECTUAL PROPERTY
   All inventions, works of authorship, and innovations created during employment
   relating to Employer's business are the exclusive property of Employer.
   Employee assigns all rights therein to Employer.

7. NON-SOLICITATION
   For [NUMBER] years after termination, Employee shall not:
   (a) Solicit Employer's clients or customers;
   (b) Solicit or hire Employer's employees.

8. NON-COMPETE
   [IF APPLICABLE] For [NUMBER] months after termination, Employee shall not
   engage in [DESCRIBE COMPETITIVE ACTIVITY] within [GEOGRAPHIC AREA].
   [Note: Enforceability varies by state — consult employment attorney]

9. TERMINATION
   9.1 By Employer for Cause: Upon [NOTICE PERIOD] notice.
   9.2 By Employer Without Cause: With [NUMBER] weeks severance.
   9.3 By Employee: Upon [NUMBER] weeks written notice.
   9.4 For Cause includes: dishonesty, insubordination, policy violation, etc.

10. GOVERNING LAW AND DISPUTE RESOLUTION
    Governed by [STATE] law. Disputes resolved by [arbitration / litigation]
    in [COUNTY], [STATE].

11. ENTIRE AGREEMENT
    This Agreement supersedes all prior agreements regarding employment.

Signed:
EMPLOYER: _____________________________ Date: __________
By: [AUTHORIZED SIGNATORY NAME], [TITLE]

EMPLOYEE: _____________________________ Date: __________
[EMPLOYEE FULL NAME]
"""

    def _independent_contractor_agreement(self) -> str:
        return """\
           INDEPENDENT CONTRACTOR AGREEMENT (1099)

This Independent Contractor Agreement (the "Agreement") is entered into
as of [DATE] by and between [CLIENT/COMPANY NAME] ("Client") and
[CONTRACTOR FULL NAME / COMPANY NAME] ("Contractor").

1. SERVICES. Contractor shall provide the following services ("Services"):
   [DETAILED DESCRIPTION OF SERVICES]

2. INDEPENDENT CONTRACTOR STATUS
   2.1 Contractor is an INDEPENDENT CONTRACTOR, not an employee.
   2.2 Contractor controls the means and manner of performing Services.
   2.3 Client shall not withhold taxes; Contractor is solely responsible for
       all federal and state taxes, including self-employment tax.
   2.4 Contractor shall receive IRS Form 1099 if compensation exceeds $600.
   2.5 Contractor is not entitled to employee benefits.

3. COMPENSATION
   3.1 Rate: $[AMOUNT] per [hour / project / milestone].
   3.2 Invoicing: Contractor submits invoices [FREQUENCY].
   3.3 Payment: Client pays within [NUMBER] days of invoice.
   3.4 Expenses: Client [will / will not] reimburse pre-approved expenses.

4. TERM
   4.1 Start Date: [DATE]
   4.2 End Date: [DATE / "Upon completion of project" / "Month-to-month"]
   4.3 Either party may terminate with [NUMBER] days written notice.

5. DELIVERABLES AND DEADLINES
   [DESCRIBE DELIVERABLES AND DUE DATES]

6. INTELLECTUAL PROPERTY
   All work product, deliverables, and inventions created under this Agreement
   shall be considered "work made for hire" and are the exclusive property of
   Client. If not work-made-for-hire, Contractor assigns all rights to Client.

7. CONFIDENTIALITY
   Contractor shall keep all Client information confidential and not disclose
   to third parties without Client's written consent.

8. INSURANCE
   Contractor shall maintain: [GENERAL LIABILITY / PROFESSIONAL LIABILITY /
   WORKERS COMP] insurance with limits of $[AMOUNT].

9. GOVERNING LAW. [STATE] law governs.

10. ENTIRE AGREEMENT. This is the entire agreement between the parties.

CLIENT:
Signature: _________________ Date: _________
Name: [AUTHORIZED REPRESENTATIVE]
Title: [TITLE]

CONTRACTOR:
Signature: _________________ Date: _________
Name: [CONTRACTOR NAME]
SSN/EIN: [TAX ID]
Address: [ADDRESS]
"""

    def _nda(self) -> str:
        return """\
                NON-DISCLOSURE AGREEMENT (NDA)

This Non-Disclosure Agreement (this "Agreement") is entered into as of [DATE]
by and between [DISCLOSING PARTY NAME] ("Disclosing Party") and
[RECEIVING PARTY NAME] ("Receiving Party") (collectively, the "Parties").

1. PURPOSE
   The Parties wish to explore [DESCRIBE BUSINESS PURPOSE] (the "Purpose")
   and may exchange Confidential Information in connection therewith.

2. DEFINITION OF CONFIDENTIAL INFORMATION
   "Confidential Information" means any non-public information disclosed by
   Disclosing Party to Receiving Party, including but not limited to:
   trade secrets, business plans, financial data, customer lists, technical
   specifications, product roadmaps, pricing, and any information marked
   "Confidential" or that a reasonable person would understand to be confidential.

3. OBLIGATIONS
   3.1 Receiving Party shall: (a) keep Confidential Information strictly
       confidential; (b) use Confidential Information solely for the Purpose;
       (c) disclose only to employees/advisors with need-to-know who are bound
       by confidentiality obligations at least as protective as this Agreement.
   3.2 Receiving Party shall use at least the same degree of care as it uses
       to protect its own confidential information (but no less than reasonable care).

4. EXCLUSIONS
   Obligations do NOT apply to information that:
   (a) Is or becomes publicly known through no breach of this Agreement;
   (b) Was rightfully known to Receiving Party before disclosure;
   (c) Is rightfully obtained from a third party without restriction;
   (d) Is independently developed without use of Confidential Information;
   (e) Is required to be disclosed by law (with notice to Disclosing Party).

5. TERM
   This Agreement is effective for [NUMBER] years from the date above. The
   obligation to protect trade secrets continues indefinitely.

6. RETURN OF INFORMATION
   Upon request, Receiving Party shall return or destroy all Confidential
   Information and certify destruction in writing.

7. NO LICENSE
   Nothing in this Agreement grants any license or rights in intellectual
   property beyond the Purpose.

8. REMEDIES
   Breach of this Agreement will cause irreparable harm for which monetary
   damages are inadequate. Disclosing Party shall be entitled to injunctive
   relief in addition to other remedies.

9. GOVERNING LAW. [STATE] law governs. Courts of [COUNTY], [STATE] have
   exclusive jurisdiction.

10. ENTIRE AGREEMENT. This is the entire NDA between the Parties.

DISCLOSING PARTY:                       RECEIVING PARTY:
__________________________              __________________________
[NAME], [TITLE]                         [NAME], [TITLE]
[COMPANY NAME]                          [COMPANY NAME]
Date: ____________________              Date: ____________________
"""

    def _non_compete_agreement(self) -> str:
        return """\
                    NON-COMPETE AGREEMENT

IMPORTANT NOTE: Non-compete enforceability varies significantly by state.
California, North Dakota, Oklahoma, and Minnesota generally prohibit them.
Many states require consideration, reasonable scope, and duration limits.
Consult a licensed employment attorney before relying on this agreement.

This Non-Compete Agreement (the "Agreement") is entered into as of [DATE]
by and between [COMPANY NAME] ("Company") and [EMPLOYEE/CONTRACTOR NAME]
("Covenantor").

1. CONSIDERATION. This Agreement is entered into in connection with
   [EMPLOYMENT / PROMOTION / ACCESS TO CONFIDENTIAL INFORMATION / SEVERANCE PAYMENT
   OF $[AMOUNT]].

2. RESTRICTED ACTIVITIES. During the Restricted Period, Covenantor shall not,
   directly or indirectly:
   (a) Own, manage, operate, or be employed by any Competing Business;
   (b) Solicit or serve Company's customers;
   (c) Solicit Company's employees.

3. COMPETING BUSINESS means any business that [DESCRIBE COMPETING ACTIVITIES].

4. RESTRICTED PERIOD. [NUMBER] months/years after termination of employment.

5. GEOGRAPHIC SCOPE. Within [CITY / COUNTY / STATE / RADIUS OF [NUMBER] MILES
   FROM [ADDRESS]].

6. REASONABLENESS. Covenantor acknowledges these restrictions are reasonable
   in scope, geography, and duration, and are necessary to protect Company's
   legitimate business interests, trade secrets, and customer relationships.

7. SEVERABILITY / BLUE PENCILING. If any provision is unenforceable, court
   may modify to the minimum extent necessary to make it enforceable.

8. INJUNCTIVE RELIEF. Breach will cause irreparable harm; Company may seek
   injunctive relief without bond.

9. GOVERNING LAW. [STATE] law governs.

COMPANY:                                COVENANTOR:
__________________________              __________________________
[AUTHORIZED OFFICER]                    [COVENANTOR NAME]
Date: ____________________              Date: ____________________
"""

    def _offer_letter(self) -> str:
        return """\
[COMPANY LETTERHEAD]
[DATE]

[CANDIDATE NAME]
[CANDIDATE ADDRESS]
[CITY, STATE ZIP]

Dear [CANDIDATE NAME]:

  Re: Offer of Employment — [JOB TITLE]

We are delighted to offer you the position of [JOB TITLE] with [COMPANY NAME]
("Company"). This letter summarizes the terms of your employment:

  POSITION:        [JOB TITLE], [DEPARTMENT]
  REPORTS TO:      [SUPERVISOR NAME], [SUPERVISOR TITLE]
  START DATE:      [START DATE]
  EMPLOYMENT TYPE: [FULL-TIME / PART-TIME] | [AT-WILL / TERM]
  LOCATION:        [WORK LOCATION / REMOTE / HYBRID]

COMPENSATION:
  Base Salary:     $[AMOUNT] per year, paid bi-weekly
  Sign-On Bonus:   $[AMOUNT] (repayable if you leave within [MONTHS] months)
  Annual Bonus:    Eligible for up to [PERCENTAGE]% of base, at Company discretion

BENEFITS:
  Health Insurance: [COMPANY] pays [PERCENTAGE]% of employee premium
  Dental & Vision:  [INCLUDED / AVAILABLE]
  401(k):           Eligible after [NUMBER] days; Company matches [PERCENTAGE]%
  PTO:              [NUMBER] days per year
  Holidays:         [NUMBER] paid holidays

CONDITIONS OF EMPLOYMENT:
  This offer is contingent upon:
  (a) Satisfactory background check;
  (b) Verification of right to work in the United States (I-9);
  (c) Signing Company's [Confidentiality / IP Assignment / Non-Compete] agreement.

AT-WILL NOTICE: Your employment with Company is at-will, meaning either party
may terminate the relationship at any time, with or without cause or notice.

Please indicate your acceptance by signing below and returning by [DEADLINE DATE].

We look forward to welcoming you to our team!

Sincerely,

_________________________________
[HIRING MANAGER NAME]
[TITLE]
[COMPANY NAME]
[PHONE]
[EMAIL]


ACCEPTED AND AGREED:

_________________________________        Date: ________________
[CANDIDATE FULL NAME]
"""

    def _separation_agreement(self) -> str:
        return """\
             SEPARATION AGREEMENT AND GENERAL RELEASE
                  (ADEA / OWBPA Compliant)

This Separation Agreement and General Release (this "Agreement") is entered
into as of [DATE] by and between [EMPLOYER NAME] ("Employer") and
[EMPLOYEE FULL NAME] ("Employee").

RECITALS

  WHEREAS, Employee's employment with Employer terminated effective [LAST DAY];
  WHEREAS, the parties desire to resolve all claims and disputes;

AGREEMENT

1. SEPARATION. Employee's employment ended on [LAST DATE OF EMPLOYMENT].

2. SEVERANCE PAYMENT. In consideration of Employee's execution of this
   Agreement, Employer shall pay Employee:
   (a) Lump sum severance of $[AMOUNT], less applicable withholdings;
   (b) Continued health insurance under COBRA paid by Employer for [NUMBER] months;
   (c) [OTHER CONSIDERATION].
   Payment shall be made within [NUMBER] days after expiration of revocation period.

3. GENERAL RELEASE. Employee, on behalf of Employee and Employee's heirs,
   executors, and assigns, RELEASES AND FOREVER DISCHARGES Employer and its
   affiliates, officers, directors, employees, and agents from any and all claims,
   known or unknown, including but not limited to:
   (a) Claims for wrongful termination;
   (b) Claims under Title VII, ADA, FMLA, FLSA;
   (c) Claims under state anti-discrimination laws;
   (d) ADEA (Age Discrimination in Employment Act) claims [if 40+];
   (e) Contract claims; and
   (f) Any other claim arising from Employee's employment.

4. ADEA / OLDER WORKERS BENEFIT PROTECTION ACT (OWBPA) DISCLOSURES
   [Required if Employee is age 40 or older:]
   (a) Employee has [21 / 45] days to consider this Agreement;
   (b) Employee is advised to consult an attorney;
   (c) Employee has 7 days after signing to revoke this Agreement;
   (d) [If group layoff: attach decisional unit information per OWBPA].

5. NO ADMISSION. This Agreement is not an admission of wrongdoing.

6. CONFIDENTIALITY. Employee shall not disclose the terms of this Agreement
   except to Employee's attorney, spouse, or as required by law.

7. NON-DISPARAGEMENT. Employee and Employer shall not make disparaging
   statements about each other.

8. RETURN OF PROPERTY. Employee has returned all Company property.

9. COOPERATION. Employee agrees to cooperate in any Company legal matters
   related to Employee's work.

10. GOVERNING LAW. [STATE] law governs.

READ THIS AGREEMENT CAREFULLY. BY SIGNING, YOU GIVE UP IMPORTANT LEGAL RIGHTS.
YOU ARE ADVISED TO CONSULT AN ATTORNEY.

EMPLOYER:                               EMPLOYEE:
__________________________              __________________________
[AUTHORIZED OFFICER]                    [EMPLOYEE FULL NAME]
[TITLE]                                 Date: ____________________
Date: ____________________
"""

    # ------------------------------------------------------------------
    # REAL ESTATE
    # ------------------------------------------------------------------

    def _residential_lease(self) -> str:
        return """\
                  RESIDENTIAL LEASE AGREEMENT

This Residential Lease Agreement ("Lease") is entered into as of [DATE]
by and between [LANDLORD FULL NAME] ("Landlord") and [TENANT(S) FULL NAME(S)]
("Tenant").

1. PROPERTY. Landlord leases to Tenant the property located at:
   [PROPERTY ADDRESS], [CITY], [STATE] [ZIP CODE]
   (the "Premises"), consisting of [DESCRIBE: bed/bath/sqft].

2. TERM. This Lease commences on [START DATE] and expires on [END DATE].

3. RENT.
   3.1 Monthly Rent: $[AMOUNT], due on the [1st / 15th] of each month.
   3.2 Payment Method: [CHECK / ONLINE PORTAL / VENMO / etc.]
   3.3 Late Fee: $[AMOUNT] if rent not received by [DATE] of month.
   3.4 Returned Check Fee: $[AMOUNT].
   3.5 Rent paid by: [TENANT NAMES].

4. SECURITY DEPOSIT.
   4.1 Amount: $[AMOUNT] (equivalent to [NUMBER] month[s] rent).
   4.2 Held at: [BANK NAME], Account No. [ACCOUNT NUMBER] (if required by state).
   4.3 Return: Within [NUMBER] days after Tenant vacates, per [STATE] law.
   4.4 Deductions: For unpaid rent, damages beyond normal wear and tear.

5. UTILITIES. Tenant is responsible for:
   [☑ Electricity] [☑ Gas] [☑ Water] [☑ Internet] [☑ Trash]
   Landlord is responsible for: [LIST LANDLORD-PAID UTILITIES].

6. OCCUPANCY.
   6.1 Authorized Occupants: Only the following may reside in Premises:
       [TENANT 1], [TENANT 2], [MINOR CHILDREN NAMES].
   6.2 Guests: May stay no more than [NUMBER] consecutive days.
   6.3 Subletting: Not permitted without Landlord's written consent.

7. PETS.
   [NO PETS PERMITTED / PETS PERMITTED per Pet Addendum attached.]
   Pet deposit: $[AMOUNT]; Monthly pet rent: $[AMOUNT].

8. MAINTENANCE AND REPAIRS.
   8.1 Tenant shall maintain Premises in clean and sanitary condition.
   8.2 Tenant shall promptly notify Landlord of any damage or needed repairs.
   8.3 Tenant is responsible for: [minor repairs under $[AMOUNT] / lawn care /
       snow removal / other].
   8.4 Landlord is responsible for: major repairs, HVAC, plumbing, structural.

9. LANDLORD'S RIGHT TO ENTER.
   Landlord may enter Premises with [NUMBER] hours notice for inspection,
   repairs, or showing, except in emergencies.

10. ALTERATIONS. Tenant shall not make alterations without Landlord's
    prior written consent.

11. PROHIBITED ACTIVITIES.
    (a) No illegal activities on Premises;
    (b) No smoking [inside / anywhere on property];
    (c) No storage of hazardous materials;
    (d) Noise must be kept at reasonable levels.

12. PARKING. Tenant receives [NUMBER] parking space(s): [DESCRIBE].

13. RENTER'S INSURANCE. Tenant [MUST / SHOULD] obtain renter's insurance
    with minimum $[AMOUNT] liability coverage.

14. MOVE-IN CONDITION. Tenant acknowledges Premises is in [CONDITION].
    Tenant shall document move-in condition on Move-In Checklist within
    [NUMBER] days.

15. MOVE-OUT.
    15.1 Tenant shall give [NUMBER] days written notice before vacating.
    15.2 Premises shall be returned in same condition as received, minus
         normal wear and tear.
    15.3 All keys, access cards, and garage openers must be returned.

16. HOLDING OVER. If Tenant remains after lease expiration without renewal,
    tenancy converts to month-to-month at [SAME / 125%] of rent.

17. EARLY TERMINATION.
    17.1 Military Clause (SCRA). Active duty Tenant may terminate with
         30 days notice per Servicemembers Civil Relief Act.
    17.2 Other early termination fee: [AMOUNT / FORMULA].

18. DEFAULT AND REMEDIES.
    18.1 Tenant default includes: non-payment of rent; material breach.
    18.2 Landlord shall provide written notice per [STATE] law before
         initiating eviction proceedings.

19. LEAD-BASED PAINT DISCLOSURE.
    [If built before 1978] Landlord has disclosed known lead hazards.
    Tenant has received the EPA Lead Paint pamphlet.

20. MOLD DISCLOSURE. [PER STATE REQUIREMENTS]

21. GOVERNING LAW. This Lease is governed by the laws of [STATE].

22. ENTIRE AGREEMENT. This Lease constitutes the entire agreement.

LANDLORD:
_________________________________        Date: ________________
[LANDLORD FULL NAME]

TENANT:
_________________________________        Date: ________________
[TENANT 1 FULL NAME]

_________________________________        Date: ________________
[TENANT 2 FULL NAME]
"""

    def _commercial_lease(self) -> str:
        return """\
                  COMMERCIAL LEASE AGREEMENT

This Commercial Lease Agreement ("Lease") is entered into as of [DATE]
by and between [LANDLORD/OWNER NAME] ("Landlord") and [TENANT BUSINESS NAME],
a [STATE] [entity type] ("Tenant").

1. PREMISES. [SUITE/UNIT], [BUILDING NAME], [FULL ADDRESS] ([NUMBER] sq. ft.)

2. TERM. Commencement: [DATE]. Expiration: [DATE]. ([NUMBER] months/years).

3. BASE RENT. $[AMOUNT]/month ([PRICE] per sq. ft./year).
   Annual escalations: [PERCENTAGE]% per year / CPI adjustment.

4. OPERATING EXPENSES (NNN LEASE).
   Tenant pays proportionate share ([PERCENTAGE]%) of:
   (a) Property taxes; (b) Insurance; (c) Common area maintenance (CAM).
   Estimated NNN: $[AMOUNT]/month. Annual reconciliation.

5. SECURITY DEPOSIT. $[AMOUNT] (equivalent to [NUMBER] months rent).

6. USE. Premises to be used for [PERMITTED USE ONLY] and no other purpose.

7. TENANT IMPROVEMENTS. [LANDLORD / TENANT] provides [DESCRIBE TI ALLOWANCE
   of $[AMOUNT] per sq. ft.]. Tenant improvements per approved plan.

8. SIGNAGE. Tenant rights to signage: [DESCRIBE].

9. PARKING. [NUMBER] reserved spaces at $[AMOUNT]/month plus [NUMBER]
   unreserved spaces.

10. ASSIGNMENT AND SUBLETTING. Tenant may [not / with Landlord consent]
    assign or sublease.

11. PERSONAL GUARANTEE. [GUARANTOR NAME] personally guarantees Tenant's
    obligations. [ATTACH PERSONAL GUARANTEE]

12. RENEWAL OPTION. Tenant has [NUMBER] option(s) to renew for [TERM]
    years at [MARKET / FORMULA] rent, with [NUMBER] months prior notice.

13. RIGHT OF FIRST REFUSAL. Tenant has right of first refusal on
    [adjacent space / building purchase] on same terms offered to third parties.

14. GOVERNING LAW. [STATE] law governs.

Signatures: [LANDLORD], [TENANT AUTHORIZED OFFICER]
"""

    def _month_to_month_rental(self) -> str:
        return """\
              MONTH-TO-MONTH RENTAL AGREEMENT

This Month-to-Month Rental Agreement is entered into as of [DATE] by and between
[LANDLORD NAME] ("Landlord") and [TENANT NAME(S)] ("Tenant").

PROPERTY: [FULL ADDRESS]
RENT: $[AMOUNT] per month, due on the [1ST] of each month
DEPOSIT: $[AMOUNT]
TERM: Month-to-month, commencing [START DATE]
NOTICE TO TERMINATE: Either party may terminate with [30/60] days written notice

[All other terms mirror the standard Residential Lease Agreement above, with
month-to-month provisions substituted for fixed-term provisions.]

LANDLORD: _____________________    Date: ________
TENANT:   _____________________    Date: ________
"""

    def _lease_addendum(self) -> str:
        return """\
                        LEASE ADDENDUM

This Addendum is entered into as of [DATE] and is incorporated into
the Lease Agreement dated [ORIGINAL LEASE DATE] for property at [ADDRESS].

ADDENDUM SUBJECT: [DESCRIBE — e.g., Home Office Use, Short-Term Rental,
Storage, Parking, Appliance, etc.]

ADDITIONAL TERMS:
1. [ADDITIONAL TERM 1]
2. [ADDITIONAL TERM 2]
3. [ADDITIONAL TERM 3]

This Addendum modifies the Lease only to the extent specified herein.
All other terms remain in full force.

LANDLORD: _____________________    Date: ________
TENANT:   _____________________    Date: ________
"""

    def _pet_addendum(self) -> str:
        return """\
                         PET ADDENDUM

This Pet Addendum is incorporated into the Lease at [ADDRESS].

PET(S) AUTHORIZED:
  Name: [PET NAME]       Type/Breed: [BREED]    Weight: [LBS]

PET DEPOSIT: $[AMOUNT] (refundable / non-refundable per state law)
MONTHLY PET RENT: $[AMOUNT]

TENANT AGREES TO:
  (a) Keep pet leashed or contained at all times;
  (b) Clean up all pet waste immediately;
  (c) Maintain pet vaccinations and license (provide proof);
  (d) Pay for any damage caused by pet;
  (e) Notify Landlord if pet is involved in any incident.

UNAUTHORIZED PETS will result in immediate notice to cure or quit.

LANDLORD: _____________________    TENANT: _____________________
"""

    def _roommate_agreement(self) -> str:
        return """\
                      ROOMMATE AGREEMENT

This Roommate Agreement ("Agreement") is entered into as of [DATE] by and among
the following roommates (collectively, "Roommates") at:
[PROPERTY ADDRESS]

ROOMMATES:
  1. [NAME 1]
  2. [NAME 2]
  3. [NAME 3]

1. RENT SPLIT. Total rent: $[AMOUNT]/month
   [NAME 1]: $[AMOUNT]  |  [NAME 2]: $[AMOUNT]  |  [NAME 3]: $[AMOUNT]

2. UTILITIES. [DESCRIBE HOW UTILITIES SPLIT]

3. CHORES. [ROTATING / ASSIGNED RESPONSIBILITIES]

4. QUIET HOURS. [TIME] to [TIME] on weekdays; [TIME] to [TIME] weekends.

5. GUESTS. Overnight guests limited to [NUMBER] consecutive nights.

6. KITCHEN AND COMMON AREAS. [RULES FOR SHARED SPACES]

7. PARKING. [ASSIGNMENT OF PARKING SPACES]

8. FOOD. [SHARED / NOT SHARED]

9. MOVE-OUT. [NUMBER] days advance notice required.

10. DISPUTE RESOLUTION. Roommates shall attempt to resolve disputes by
    [MEDIATION / MAJORITY VOTE].

ALL ROOMMATES AGREE:
_____________________    _____________________    _____________________
"""

    def _notice_to_vacate_landlord(self) -> str:
        return """\
                  NOTICE TO VACATE (Landlord to Tenant)

Date: [DATE]

To: [TENANT NAME(S)]
    [PROPERTY ADDRESS]
    [CITY, STATE ZIP]

PLEASE TAKE NOTICE that you are required to vacate and surrender possession
of the premises at [PROPERTY ADDRESS] on or before [VACATE DATE].

Reason for Notice: [SELECT ONE]
  [ ] Lease expiration (lease expires [DATE])
  [ ] No-fault termination (month-to-month)
  [ ] Owner move-in
  [ ] Substantial renovation
  [ ] Other: [DESCRIBE]

You must remove all personal property and return all keys by [DATE/TIME].
The Premises must be left in clean condition.

Failure to vacate by the required date may result in legal eviction proceedings.

If you have questions, contact: [LANDLORD NAME], [PHONE], [EMAIL].

                              _________________________________
                              [LANDLORD NAME]
                              [LANDLORD ADDRESS]
                              Date: [DATE]
"""

    def _notice_to_vacate_tenant(self) -> str:
        return """\
                  NOTICE TO VACATE (Tenant to Landlord)

Date: [DATE]

To: [LANDLORD NAME]
    [LANDLORD ADDRESS]

RE: Premises at [PROPERTY ADDRESS]

PLEASE TAKE NOTICE that I/we, [TENANT NAME(S)], intend to vacate and
surrender possession of the Premises at [PROPERTY ADDRESS] on or before
[VACATE DATE], providing [NUMBER] days notice as required by the Lease.

I/We request:
  (a) A move-out inspection scheduled for approximately [DATE];
  (b) Return of security deposit in the amount of $[AMOUNT] within
      the time required by [STATE] law.

Forwarding Address: [FORWARDING ADDRESS]

                              _________________________________
                              [TENANT NAME]
                              Date: [DATE]
"""

    def _pay_or_quit(self) -> str:
        return """\
           [NUMBER]-DAY NOTICE TO PAY RENT OR QUIT

Date: [DATE]

To: [TENANT NAME(S)]
    [PROPERTY ADDRESS]
    [CITY, STATE ZIP]

PLEASE TAKE NOTICE that you are in default of your lease for failure
to pay rent as follows:

  Rent Due For:          [MONTH(S)]
  Amount Due:            $[AMOUNT]
  Late Fees:             $[AMOUNT]
  TOTAL PAST DUE:        $[AMOUNT]

You are hereby required, within [3 / 5 / 14] DAYS from service of this
notice, to either:

  (1) PAY the total amount of $[AMOUNT] to [LANDLORD / PROPERTY MANAGER]
      at [ADDRESS / PAYMENT METHOD]; OR

  (2) QUIT and deliver possession of the Premises.

Failure to pay or quit within the required time will result in
commencement of unlawful detainer (eviction) proceedings against you.

This notice does not waive any additional amounts that may become due.

                              _________________________________
                              [LANDLORD NAME]
                              [CONTACT INFORMATION]
"""

    def _cure_or_quit(self) -> str:
        return """\
             [NUMBER]-DAY NOTICE TO CURE OR QUIT

Date: [DATE]
To: [TENANT NAME(S)], [PROPERTY ADDRESS]

You are in VIOLATION of your lease as follows:
VIOLATION: [DESCRIBE VIOLATION — e.g., unauthorized pet, noise, subletting]

You are required within [3 / 5] DAYS to CURE this violation
OR vacate the Premises.

If you fail to cure or quit, eviction proceedings will commence.

                              _________________________________
                              [LANDLORD NAME], [DATE]
"""

    def _unconditional_quit(self) -> str:
        return """\
                [NUMBER]-DAY UNCONDITIONAL NOTICE TO QUIT

Date: [DATE]
To: [TENANT NAME(S)], [PROPERTY ADDRESS]

Due to [SERIOUS / REPEATED] violations of your tenancy including:
[DESCRIBE — e.g., repeated late payment, criminal activity, substantial damage]

You are REQUIRED TO VACATE the Premises within [3 / 5 / 30] DAYS.
You are NOT offered the opportunity to cure this violation.

Failure to vacate will result in immediate eviction proceedings.

                              _________________________________
                              [LANDLORD NAME], [DATE]
"""

    # ------------------------------------------------------------------
    # DEMAND LETTERS AND NOTICES
    # ------------------------------------------------------------------

    def _demand_letter_payment(self) -> str:
        return """\
[SENDER NAME / LAW FIRM]
[ADDRESS]
[CITY, STATE ZIP]
[DATE]

VIA CERTIFIED MAIL — RETURN RECEIPT REQUESTED

[DEBTOR/RECIPIENT NAME]
[DEBTOR ADDRESS]

  Re: DEMAND FOR PAYMENT — $[AMOUNT]

Dear [DEBTOR NAME / "Sir or Madam"]:

  This office represents [CLIENT NAME] ("Client") in connection with
  amounts owed by you in the sum of $[AMOUNT].

  BACKGROUND. [DESCRIBE — e.g., on [DATE], Client provided [SERVICES/GOODS]
  pursuant to [CONTRACT/INVOICE NO.]. Payment was due on [DUE DATE].
  Despite repeated requests, payment has not been received.]

  AMOUNT DUE:
    Principal:           $[AMOUNT]
    Interest ([RATE]%):  $[AMOUNT]
    Late Fees:           $[AMOUNT]
    TOTAL DUE:           $[AMOUNT]

  DEMAND. You are hereby demanded to remit the total sum of $[AMOUNT]
  within TEN (10) DAYS of the date of this letter. Payment shall be made
  payable to [CLIENT NAME] by [CHECK / WIRE / CERTIFIED FUNDS] to:
  [PAYMENT INSTRUCTIONS].

  CONSEQUENCES OF NON-PAYMENT. If payment is not received within the
  stated time, Client is prepared to commence legal proceedings against
  you for: (a) the full amount owed; (b) pre- and post-judgment interest;
  (c) attorney's fees; and (d) court costs.

  This letter is a demand for payment and is not intended to harass,
  abuse, or oppress you. Your rights are protected under applicable law.

  Please govern yourself accordingly.

                              Sincerely,
                              [ATTORNEY NAME]
                              [BAR NUMBER]
                              Attorney for [CLIENT NAME]
"""

    def _cease_and_desist_general(self) -> str:
        return """\
[SENDER NAME]
[ADDRESS]
[DATE]

VIA CERTIFIED MAIL

[RECIPIENT NAME]
[RECIPIENT ADDRESS]

  Re: CEASE AND DESIST DEMAND

To [RECIPIENT NAME]:

  You are hereby legally notified to IMMEDIATELY CEASE AND DESIST from
  the following activities:

  [DESCRIBE ACTIVITIES — e.g., harassment, defamation, trespassing,
  unauthorized use of property, breach of contract, tortious interference]

  LEGAL BASIS. Your conduct constitutes: [LIST LEGAL CLAIMS — e.g.,
  defamation, harassment, tortious interference, breach of contract].

  DEMAND. You are required to immediately:
  1. STOP [DESCRIBE ACTIVITY];
  2. [DESTROY / REMOVE / RETURN] [DESCRIBE MATERIAL];
  3. Confirm in writing within [10] days that you have complied.

  CONSEQUENCES. Failure to comply will result in legal proceedings
  seeking: injunctive relief, monetary damages, and attorney's fees.
  Legal action will be commenced without further notice.

                              [SENDER NAME / ATTORNEY]
                              [DATE]
"""

    def _cease_and_desist_ip(self) -> str:
        return """\
[LAW FIRM NAME]
[DATE]

VIA CERTIFIED MAIL AND EMAIL

[INFRINGER NAME]
[ADDRESS]

  Re: CEASE AND DESIST — INTELLECTUAL PROPERTY INFRINGEMENT

To [INFRINGER NAME]:

  This firm represents [IP OWNER NAME], owner of the following
  intellectual property rights:

  [☑ Trademark]: [MARK], Reg. No. [REG. NO.], covering [GOODS/SERVICES]
  [☑ Copyright]: "[WORK TITLE]", Reg. No. [REG. NO.]
  [☑ Patent]:    U.S. Patent No. [PATENT NO.], titled "[TITLE]"

  INFRINGEMENT. We have determined that you are infringing our client's
  intellectual property rights through: [DESCRIBE INFRINGING ACTIVITIES].

  DEMAND. You are required to IMMEDIATELY:
  1. CEASE all infringing activities;
  2. REMOVE all infringing materials from [WEBSITE/STORE/etc.];
  3. PROVIDE a full accounting of profits from infringing use;
  4. CONFIRM compliance in writing within 10 days.

  Our client reserves all rights and remedies, including statutory damages
  up to $150,000 per willful copyright infringement, and triple damages
  for willful patent infringement.

                              [ATTORNEY NAME / FIRM]
"""

    def _fdcpa_debt_validation(self) -> str:
        return """\
[YOUR NAME]
[YOUR ADDRESS]
[DATE]

VIA CERTIFIED MAIL — RETURN RECEIPT REQUESTED

[COLLECTION AGENCY NAME]
[COLLECTION AGENCY ADDRESS]

  Re: DEBT VALIDATION REQUEST — Account No. [ACCOUNT NUMBER]

To Whom It May Concern:

  I am writing in response to your communication dated [DATE] regarding
  an alleged debt of $[AMOUNT].

  Pursuant to the Fair Debt Collection Practices Act (FDCPA), 15 U.S.C.
  § 1692g, I hereby DISPUTE this debt and REQUEST VALIDATION.

  Please provide the following within 30 days:
  1. Name and address of original creditor;
  2. Copy of original signed agreement creating the alleged debt;
  3. Complete payment history from inception;
  4. Proof you are licensed to collect in [STATE];
  5. Verification that the debt is within the statute of limitations;
  6. Amount of debt including all fees and interest breakdown.

  Until validation is provided, you must CEASE collection activities
  per 15 U.S.C. § 1692g(b). Do not contact me by phone; all
  communications must be in writing.

  If you furnish negative information to credit bureaus without
  validating this debt, I will pursue all legal remedies including
  FDCPA claims for statutory damages of $1,000 per violation.

                              _________________________________
                              [YOUR NAME]
"""

    def _fcra_credit_dispute(self) -> str:
        return """\
[YOUR NAME]
[YOUR ADDRESS]
[YOUR SSN — LAST 4 ONLY: XXX-XX-[LAST 4]]
[DATE]

VIA CERTIFIED MAIL — RETURN RECEIPT REQUESTED

[CREDIT BUREAU — Equifax / Experian / TransUnion]
[BUREAU ADDRESS]

  Re: FORMAL CREDIT REPORT DISPUTE — Account No. [ACCOUNT NO.]

Dear Dispute Department:

  I am writing to dispute inaccurate information on my credit report
  (Report Date: [DATE], Report No. [REPORT NO.]) pursuant to the Fair
  Credit Reporting Act (FCRA), 15 U.S.C. § 1681i.

DISPUTED ITEM(S):
  Creditor:          [CREDITOR NAME]
  Account No.:       [ACCOUNT NUMBER]
  Reported Amount:   $[AMOUNT]
  Reported Status:   [LATE / COLLECTION / CHARGE-OFF / etc.]
  Reason for Dispute: [DESCRIBE — e.g., not my account / paid / discharged in
                       bankruptcy / incorrect amount / identity theft]

  ENCLOSED DOCUMENTATION:
  [ ] Copy of credit report with disputed items circled
  [ ] [PAYMENT RECEIPTS / BANKRUPTCY DISCHARGE / FTC IDENTITY THEFT REPORT]
  [ ] Copy of photo ID
  [ ] Copy of proof of address

  Per FCRA § 1681i, you have 30 days to investigate and correct or delete
  inaccurate information. I request written confirmation of the investigation
  results and a corrected credit report.

  Failure to investigate and correct inaccuracies may result in a lawsuit
  for actual damages, statutory damages up to $1,000, plus attorney's fees.

                              _________________________________
                              [YOUR NAME]
"""

    def _goodwill_letter(self) -> str:
        return """\
[YOUR NAME]
[YOUR ADDRESS]
[DATE]

[CREDITOR NAME] — Customer Service / Credit Department
[CREDITOR ADDRESS]

  Re: Account No. [ACCOUNT NUMBER] — Goodwill Adjustment Request

Dear [CREDITOR NAME] Customer Relations Team:

  I am writing to respectfully request removal of a late payment notation
  reported on [DATE] for Account No. [ACCOUNT NUMBER].

  I have been a loyal customer since [YEAR] and have maintained an excellent
  payment history, with this single exception occurring due to:
  [EXPLAIN REASON — e.g., unexpected medical emergency / job loss / oversight].

  Since that time, I have [DESCRIBE POSITIVE STEPS — e.g., enrolled in
  autopay / resolved the financial issue / maintained on-time payments for
  [NUMBER] months].

  I understand this late payment was my error, and I sincerely apologize.
  I am requesting that you make a goodwill adjustment to remove this negative
  notation as a gesture of customer appreciation.

  This adjustment would significantly help my credit profile and I would
  continue to be a loyal, on-time customer.

  Thank you for your consideration. I can be reached at [PHONE] or [EMAIL].

                              Respectfully,
                              _________________________________
                              [YOUR NAME]
"""

    def _pay_for_delete(self) -> str:
        return """\
[YOUR NAME]
[YOUR ADDRESS]
[DATE]

VIA CERTIFIED MAIL

[COLLECTION AGENCY NAME]
[ADDRESS]

  Re: Pay-for-Delete Offer — Account No. [ACCOUNT NO.]

Dear Collection Manager:

  This letter is to notify you of my willingness to resolve the above-
  referenced account under the following terms:

  OFFER: I offer to pay $[AMOUNT] (representing [PERCENTAGE]% of the
  alleged balance of $[TOTAL AMOUNT]) in exchange for COMPLETE DELETION
  of this account from all three credit bureaus — Equifax, Experian,
  and TransUnion.

  TERMS:
  (a) You must agree IN WRITING to delete this account from all bureaus;
  (b) Deletion must occur within 30 days of payment;
  (c) Payment by [CERTIFIED CHECK / MONEY ORDER] upon receipt of written agreement;
  (d) This settlement does not constitute an admission of liability.

  Please respond in writing. I will not send payment until I receive
  written confirmation of deletion.

  This offer expires [DATE]. If not accepted, I will pursue other remedies
  including debt validation under the FDCPA.

                              _________________________________
                              [YOUR NAME]
"""

    # ------------------------------------------------------------------
    # ESTATE PLANNING
    # ------------------------------------------------------------------

    def _last_will_simple(self) -> str:
        return """\
                    LAST WILL AND TESTAMENT
                    OF [TESTATOR FULL NAME]

I, [TESTATOR FULL LEGAL NAME], a resident of [CITY], [STATE], being of
sound mind and legal capacity, and not acting under duress, menace, fraud,
or undue influence, declare this to be my Last Will and Testament. I hereby
revoke all prior wills and codicils.

ARTICLE I — IDENTIFICATION
  My full name: [FULL NAME]
  My Social Security Number (last 4): XXX-XX-[LAST 4]
  My date of birth: [DATE OF BIRTH]
  My spouse (if any): [SPOUSE NAME]
  My children: [LIST CHILDREN'S NAMES AND DATES OF BIRTH]

ARTICLE II — PAYMENT OF DEBTS AND EXPENSES
  My Personal Representative shall pay from my estate all of my legally
  enforceable debts, funeral expenses, and costs of administration.

ARTICLE III — SPECIFIC GIFTS
  I give and bequeath:
  (a) [SPECIFIC ITEM OR AMOUNT] to [BENEFICIARY NAME];
  (b) [SPECIFIC ITEM OR AMOUNT] to [BENEFICIARY NAME].

ARTICLE IV — RESIDUARY ESTATE
  I give all the rest, residue, and remainder of my estate (the "Residuary
  Estate"), real and personal, wherever located, to:
  (a) [PRIMARY BENEFICIARY NAME], if surviving me;
  (b) If [PRIMARY BENEFICIARY] does not survive me, then to [ALTERNATE];
  (c) Per stirpes to descendants of any predeceased beneficiary.

ARTICLE V — PERSONAL REPRESENTATIVE
  I appoint [PERSONAL REPRESENTATIVE FULL NAME] as Personal Representative
  (Executor) of this Will. If unable to serve, I appoint [ALTERNATE].

  My Personal Representative shall serve without bond (if permitted by law)
  and shall have all powers provided under [STATE] law.

ARTICLE VI — GUARDIAN OF MINOR CHILDREN
  If I am the surviving parent of minor children, I appoint [GUARDIAN NAME]
  as Guardian of my minor children's person and estate. If unable to serve,
  I appoint [ALTERNATE GUARDIAN].

ARTICLE VII — DIGITAL ASSETS
  My Personal Representative is authorized to access, manage, and distribute
  my digital assets, including online accounts, cryptocurrency, and digital
  files, pursuant to the Revised Uniform Fiduciary Access to Digital Assets Act.

ARTICLE VIII — NO-CONTEST
  Any beneficiary who contests this Will shall receive nothing from my estate.

ARTICLE IX — GOVERNING LAW
  This Will shall be governed by the laws of [STATE].

IN WITNESS WHEREOF, I subscribe my name to this Will on [DATE].

_________________________________
[TESTATOR FULL NAME], Testator

                    WITNESSES

We, the undersigned witnesses, each being of legal age, declare that the
Testator signed this Will in our presence, and we sign as witnesses in
the Testator's presence and in the presence of each other.

_________________________________        _________________________________
[WITNESS 1 NAME]                         [WITNESS 2 NAME]
[WITNESS 1 ADDRESS]                      [WITNESS 2 ADDRESS]
Date: ___________________________        Date: ___________________________

                     SELF-PROVING AFFIDAVIT

[COMPLETE NOTARIZED SELF-PROVING AFFIDAVIT PER [STATE] LAW]

_________________________________
Notary Public
My Commission Expires: ____________
"""

    def _last_will_with_trust(self) -> str:
        return """\
                LAST WILL AND TESTAMENT WITH TRUST PROVISIONS
                         OF [TESTATOR FULL NAME]

[All provisions of the Simple Will apply here, PLUS:]

ARTICLE X — TESTAMENTARY TRUST
  10.1 Creation. If any beneficiary is a minor or under age [AGE] at
       my death, such beneficiary's share shall be held in trust by
       [TRUSTEE NAME] ("Trustee") until such beneficiary reaches age [AGE].

  10.2 Distributions. Trustee may distribute income and principal for
       beneficiary's health, education, maintenance, and support.

  10.3 Final Distribution. At age [AGE], Trustee shall distribute
       remaining trust assets to the beneficiary.

ARTICLE XI — POUR-OVER TRUST
  If I have established a Revocable Living Trust, I direct that any
  property not otherwise transferred to such Trust be poured over
  and added to such Trust.

[SIGNATURE AND WITNESS BLOCKS — SAME AS SIMPLE WILL]
"""

    def _durable_power_of_attorney(self) -> str:
        return """\
                   DURABLE POWER OF ATTORNEY
                   FOR FINANCIAL MATTERS

IMPORTANT: This is an important legal document. Before signing, read it
carefully. It gives your agent broad power to act for you. This power
does not terminate upon your incapacity.

I, [PRINCIPAL FULL NAME], residing at [ADDRESS], [CITY], [STATE] [ZIP],
appoint [AGENT FULL NAME] as my Attorney-in-Fact (Agent).

1. DURABILITY. This Power of Attorney shall NOT be affected by my
   subsequent disability or incapacity. It IS a durable power of attorney.

2. EFFECTIVE DATE. This Power of Attorney is: [IMMEDIATELY EFFECTIVE /
   SPRINGING — effective only upon my incapacity as certified by
   [NUMBER] licensed physicians].

3. GRANT OF AUTHORITY. I grant my Agent the authority to:
   (a) Bank transactions (open, close, deposit, withdraw);
   (b) Real estate transactions (buy, sell, mortgage);
   (c) Investment and securities transactions;
   (d) Tax matters (file returns, respond to IRS);
   (e) Business operations;
   (f) Government benefits (Social Security, Medicare/Medicaid);
   (g) Gifts up to annual exclusion amount;
   (h) Trust transactions;
   (i) Legal claims and litigation;
   (j) Insurance transactions;
   (k) Estate planning on my behalf (ONLY if expressly granted).

4. SUCCESSOR AGENT. If [AGENT NAME] cannot serve, I appoint
   [SUCCESSOR AGENT NAME] as successor Agent.

5. REVOCATION. This Power of Attorney may be revoked by me at any time
   while I have capacity by written notice.

6. THIRD PARTY RELIANCE. Third parties may rely on this document.

7. COMPENSATION. Agent [shall / shall not] be compensated.

8. GOVERNING LAW. [STATE] law governs.

SIGNED this [DATE].

_________________________________
[PRINCIPAL FULL NAME]

STATE OF [STATE]    )
COUNTY OF [COUNTY]  )

Before me personally appeared [PRINCIPAL NAME], who acknowledged this
Power of Attorney.

_________________________________
Notary Public
Commission Expires: ______________
"""

    def _healthcare_power_of_attorney(self) -> str:
        return """\
                HEALTHCARE POWER OF ATTORNEY
           (Health Care Proxy / Medical Power of Attorney)

I, [PRINCIPAL FULL NAME], designate [AGENT FULL NAME] as my Health Care
Agent with authority to make healthcare decisions on my behalf if I lack
capacity to do so.

1. AUTHORITY. My Health Care Agent is authorized to:
   (a) Consent to or refuse medical treatment;
   (b) Access my medical records (HIPAA authorization);
   (c) Hire and discharge medical personnel;
   (d) Make decisions regarding life-sustaining treatment;
   (e) Make decisions regarding artificial nutrition and hydration;
   (f) Arrange for my care, hospitalization, or hospice;
   (g) Make organ donation decisions.

2. SUCCESSOR AGENT. If [AGENT NAME] cannot serve, I appoint
   [SUCCESSOR NAME].

3. INCAPACITY DETERMINATION. My incapacity shall be determined by
   [NUMBER] licensed physicians.

4. HIPAA AUTHORIZATION. I authorize all healthcare providers to disclose
   my health information to my Agent for purposes of this document.

5. LIMITATIONS. My Agent may NOT: [DESCRIBE ANY LIMITATIONS].

6. ORGAN DONATION. I [DO / DO NOT] consent to organ donation.

7. RELIGIOUS/PERSONAL BELIEFS REGARDING CARE:
   [DESCRIBE ANY PREFERENCES].

SIGNED: ___________________________   Date: ____________
[PRINCIPAL FULL NAME]

WITNESSES:
We are not the Agent, healthcare provider, or beneficiaries of Principal.

_____________________________        _____________________________
[WITNESS 1 NAME, ADDRESS]            [WITNESS 2 NAME, ADDRESS]

NOTARIZATION: [PER STATE REQUIREMENTS]
"""

    def _living_will(self) -> str:
        return """\
               LIVING WILL / ADVANCE HEALTHCARE DIRECTIVE
            (Declaration of Wishes for End-of-Life Care)

I, [YOUR FULL NAME], being of sound mind, make this declaration as a
directive to be followed if I become permanently unconscious or if I am in
a terminal condition and no longer able to make or communicate decisions.

1. LIFE-SUSTAINING TREATMENT. If I am in a terminal condition or persistent
   vegetative state with no reasonable expectation of recovery, I direct that:

   [ ] Life-sustaining treatment BE WITHHELD or WITHDRAWN, including
       artificial nutrition, hydration, and resuscitation (DNR).

   [ ] Life-sustaining treatment be PROVIDED to extent possible.

2. ARTIFICIAL NUTRITION AND HYDRATION. In a terminal or persistent
   vegetative state:
   [ ] Do NOT provide artificial nutrition or hydration.
   [ ] Provide artificial nutrition and hydration.

3. PAIN MANAGEMENT. I direct that reasonable measures be taken to keep
   me comfortable and free from pain, even if such measures shorten my life.

4. ORGAN DONATION. I [DO / DO NOT] authorize donation of my organs and tissue
   for: [ ] Transplantation [ ] Research [ ] Education [ ] Any purpose.

5. COMFORT CARE PREFERENCES: [DESCRIBE]

6. RELIGIOUS GUIDANCE: [DESCRIBE IF ANY]

7. ADDITIONAL WISHES: [DESCRIBE]

SIGNED: ___________________________   Date: ____________
[YOUR FULL NAME]

WITNESSES (must be adults; may not be heirs, healthcare agents, or providers):
_____________________________        _____________________________

NOTARIZATION: [PER STATE REQUIREMENTS]
"""

    def _transfer_on_death_deed(self) -> str:
        return """\
                   TRANSFER ON DEATH DEED
                  (Beneficiary Deed)

NOTE: Transfer on Death Deeds are only available in states that have
enacted enabling legislation. Check your state's law before using.
States include: CA, CO, IL, MO, NV, OH, TX, and others.

GRANTOR: [OWNER FULL NAME]
PROPERTY ADDRESS: [FULL PROPERTY ADDRESS]
LEGAL DESCRIPTION: [LEGAL DESCRIPTION FROM COUNTY RECORDS]
APN/Parcel No.: [PARCEL NUMBER]

BENEFICIARY(IES): [BENEFICIARY FULL NAME(S)]
  Percentage: [PERCENTAGE]% each

Upon Grantor's death, title to the above-described property shall
automatically transfer to the named Beneficiary(ies).

GRANTOR RETAINS: Full ownership and right to revoke, sell, mortgage,
and encumber during Grantor's lifetime. Beneficiary has NO current interest.

REVOCATION: This deed may be revoked by recording a revocation or a
subsequent transfer on death deed prior to Grantor's death.

Signed: ___________________________   Date: ____________
[GRANTOR FULL NAME]

NOTARIZATION: [REQUIRED — SEE STATE-SPECIFIC REQUIREMENTS]
RECORDING: MUST BE RECORDED in the County Recorder's office before Grantor's death.
"""

    # ------------------------------------------------------------------
    # BUSINESS OPERATIONS
    # ------------------------------------------------------------------

    def _invoice_template(self) -> str:
        return """\
╔══════════════════════════════════════════════════════════════════╗
║                         INVOICE                                  ║
╠══════════════════════════════════════════════════════════════════╣
║  BILLED FROM:                       INVOICE DETAILS:            ║
║  [YOUR COMPANY NAME]                Invoice No.: [INVOICE #]    ║
║  [YOUR ADDRESS]                     Date:        [DATE]         ║
║  [CITY, STATE ZIP]                  Due Date:    [DUE DATE]     ║
║  [PHONE]  [EMAIL]                   Terms:       Net [30/60]    ║
╠══════════════════════════════════════════════════════════════════╣
║  BILLED TO:                                                      ║
║  [CLIENT/COMPANY NAME]                                           ║
║  [CLIENT ADDRESS]                                                ║
║  [CITY, STATE ZIP]                                               ║
╠══════╦════════════════════════════╦═══════════╦══════════════════╣
║  #   ║  DESCRIPTION               ║   QTY     ║  AMOUNT          ║
╠══════╬════════════════════════════╬═══════════╬══════════════════╣
║  1   ║  [SERVICE/PRODUCT 1]       ║  [QTY]    ║  $[AMOUNT]       ║
║  2   ║  [SERVICE/PRODUCT 2]       ║  [QTY]    ║  $[AMOUNT]       ║
║  3   ║  [SERVICE/PRODUCT 3]       ║  [QTY]    ║  $[AMOUNT]       ║
╠══════╩════════════════════════════╩═══════════╬══════════════════╣
║                                    Subtotal:   ║  $[AMOUNT]       ║
║                                    Tax ([%]):   ║  $[AMOUNT]       ║
║                                    TOTAL DUE:  ║  $[AMOUNT]       ║
╚═══════════════════════════════════════════════╩══════════════════╝

PAYMENT INSTRUCTIONS:
  [ ] Check payable to: [COMPANY NAME]
  [ ] Bank Transfer: Routing [ROUTING #]  Account [ACCOUNT #]
  [ ] Online: [PAYMENT LINK]
  [ ] Zelle/Venmo: [HANDLE]

NOTES: [ANY ADDITIONAL NOTES]

Thank you for your business!
"""

    def _contractor_invoice(self) -> str:
        return """\
╔══════════════════════════════════════════════════════════╗
║           INDEPENDENT CONTRACTOR INVOICE                ║
╠══════════════════════════════════════════════════════════╣
║  Contractor: [CONTRACTOR NAME]                          ║
║  EIN/SSN:    [EIN or last 4 of SSN]                     ║
║  Address:    [ADDRESS]                                  ║
║  Invoice #:  [NUMBER]     Date: [DATE]                  ║
╠══════════════════════════════════════════════════════════╣
║  Billed To: [CLIENT NAME]                               ║
║  Project:   [PROJECT NAME]                              ║
╠═══════════════════════════════╦═══════════╦═════════════╣
║  DESCRIPTION OF SERVICES      ║  HOURS    ║  AMOUNT     ║
╠═══════════════════════════════╬═══════════╬═════════════╣
║  [WORK PERFORMED — DATE RANGE]║  [HOURS]  ║  $[AMOUNT]  ║
╠═══════════════════════════════╩═══════════╬═════════════╣
║                                TOTAL DUE: ║  $[AMOUNT]  ║
╚══════════════════════════════════════════╩═════════════╝
Note: Contractor is responsible for all applicable taxes.
Form 1099 will be issued if compensation exceeds $600.

Signature: ___________________________  Date: ____________
"""

    def _business_proposal(self) -> str:
        return """\
                      BUSINESS PROPOSAL

Prepared by: [YOUR NAME / COMPANY]
Prepared for: [PROSPECT NAME]
Date: [DATE]
Proposal Valid Through: [EXPIRATION DATE]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EXECUTIVE SUMMARY
  [BRIEF 2-3 sentence overview of your proposal and value proposition]

UNDERSTANDING OF YOUR NEEDS
  Based on our discussion on [DATE], we understand you need:
  • [NEED 1]
  • [NEED 2]
  • [NEED 3]

PROPOSED SOLUTION
  We propose to provide: [DESCRIBE SERVICES/PRODUCTS IN DETAIL]

SCOPE OF WORK
  Phase 1: [DESCRIPTION] — [TIMELINE]
  Phase 2: [DESCRIPTION] — [TIMELINE]
  Phase 3: [DESCRIPTION] — [TIMELINE]

INVESTMENT SUMMARY
  Phase 1:               $[AMOUNT]
  Phase 2:               $[AMOUNT]
  Phase 3:               $[AMOUNT]
  ─────────────────────────────────
  TOTAL INVESTMENT:      $[AMOUNT]
  Payment Terms:         [DESCRIBE]

WHY CHOOSE US
  • [DIFFERENTIATOR 1]
  • [DIFFERENTIATOR 2]
  • [DIFFERENTIATOR 3]

TIMELINE. Work begins within [NUMBER] days of signed agreement.
Completion: [ESTIMATED DATE].

TERMS AND CONDITIONS
  [PAYMENT TERMS / REVISIONS POLICY / CANCELLATION / IP OWNERSHIP]

ACCEPTANCE
  This proposal is accepted by:

  Client: _____________________  Date: __________
  [YOUR NAME]: ________________  Date: __________
"""

    def _mou(self) -> str:
        return """\
                  MEMORANDUM OF UNDERSTANDING (MOU)

This Memorandum of Understanding ("MOU") is entered into as of [DATE]
by and between [PARTY 1 NAME] ("Party 1") and [PARTY 2 NAME] ("Party 2").

PURPOSE. This MOU sets forth the mutual understanding and intent of the
parties regarding [DESCRIBE PURPOSE].

NOTE: This MOU is NOT legally binding unless specifically stated below.
It represents the parties' good faith intent to negotiate in good faith.

1. BACKGROUND. [DESCRIBE BACKGROUND AND CONTEXT]

2. SCOPE OF COLLABORATION. The parties intend to:
   (a) [DESCRIBE ACTIVITY 1]
   (b) [DESCRIBE ACTIVITY 2]
   (c) [DESCRIBE ACTIVITY 3]

3. RESPONSIBILITIES.
   Party 1 shall: [DESCRIBE RESPONSIBILITIES]
   Party 2 shall: [DESCRIBE RESPONSIBILITIES]

4. TIMELINE. Target completion: [DATE]. Milestones: [LIST].

5. FINANCIAL ARRANGEMENTS. [DESCRIBE OR STATE "NONE AT THIS TIME"]

6. CONFIDENTIALITY. Both parties shall treat this MOU and discussions
   as confidential.

7. DURATION. This MOU is effective until [DATE] unless extended in writing.

8. NO BINDING OBLIGATION. [SELECT ONE]
   [ ] This MOU is NOT legally binding.
   [ ] The following sections ARE legally binding: [LIST SECTIONS].

9. GOVERNING LAW. [STATE] law governs.

PARTY 1:                              PARTY 2:
__________________________            __________________________
[NAME, TITLE, DATE]                   [NAME, TITLE, DATE]
"""

    def _loi(self) -> str:
        return """\
                       LETTER OF INTENT (LOI)

[DATE]

[RECIPIENT NAME]
[RECIPIENT TITLE]
[COMPANY NAME]
[ADDRESS]

  Re: Letter of Intent — [DESCRIBE PROPOSED TRANSACTION]

Dear [RECIPIENT NAME]:

  This Letter of Intent ("LOI") is submitted by [BUYER/PARTY NAME]
  ("Buyer/Party") and sets forth the principal terms upon which Buyer
  proposes to [purchase / invest in / partner with] [SELLER/PARTY NAME]
  ("Seller/Party"), subject to the terms set forth herein.

PROPOSED TRANSACTION
  Type: [Acquisition / Asset Purchase / Partnership / Investment]
  Purchase Price: $[AMOUNT] / Valuation: $[AMOUNT]
  Consideration: [CASH / EQUITY / SELLER FINANCING / COMBINATION]
  Structure: [DESCRIBE]

KEY TERMS
  1. Exclusivity Period: [NUMBER] days from LOI signing
  2. Due Diligence Period: [NUMBER] days
  3. Closing Target Date: [DATE]
  4. Conditions to Close: [FINANCING / REGULATORY APPROVAL / OTHER]

BINDING AND NON-BINDING PROVISIONS
  NON-BINDING: The transaction terms in this LOI are non-binding.
  BINDING: The following are legally binding:
  (a) Exclusivity/No-Shop (Seller will not negotiate with third parties
      during exclusivity period);
  (b) Confidentiality;
  (c) Expenses (each party bears own expenses).

This LOI expires unless signed by both parties by [DATE].

BUYER/PARTY:                          SELLER/PARTY:
__________________________            __________________________
[NAME, TITLE]                         [NAME, TITLE]
Date: ____________________            Date: ____________________
"""

    def _confidentiality_agreement(self) -> str:
        return """\
                  MUTUAL CONFIDENTIALITY AGREEMENT

This Mutual Confidentiality Agreement is entered into as of [DATE]
by [PARTY 1 NAME] and [PARTY 2 NAME] for the purpose of [DESCRIBE].

Both parties may share confidential information. Each party agrees to:
(a) Keep the other's Confidential Information strictly confidential;
(b) Use it solely for the stated purpose;
(c) Disclose only to those with need-to-know under confidentiality obligations.

CONFIDENTIAL INFORMATION means any non-public business, financial, technical,
or proprietary information.

EXCLUSIONS: publicly known information, independently developed information,
information received from third parties without restriction.

TERM: [NUMBER] years from signing. Trade secrets protected indefinitely.

REMEDIES: Injunctive relief available for breach.

GOVERNING LAW: [STATE].

PARTY 1:                              PARTY 2:
__________________________            __________________________
[NAME, TITLE, DATE]                   [NAME, TITLE, DATE]
"""

    def _terms_of_service(self) -> str:
        return """\
                        TERMS OF SERVICE

Last Updated: [DATE]

PLEASE READ THESE TERMS OF SERVICE CAREFULLY BEFORE USING [WEBSITE/APP NAME].

1. ACCEPTANCE OF TERMS
   By accessing or using [WEBSITE/SERVICE] ("Service"), you agree to be bound
   by these Terms of Service ("Terms"). If you do not agree, do not use the Service.

2. USE OF SERVICE
   2.1 You must be at least [18 / 13] years old to use the Service.
   2.2 You agree to use the Service only for lawful purposes.
   2.3 You agree not to: [LIST PROHIBITED USES — spam, illegal activity, etc.]

3. USER ACCOUNTS
   3.1 You are responsible for maintaining the security of your account.
   3.2 You are responsible for all activity under your account.
   3.3 We may terminate accounts that violate these Terms.

4. INTELLECTUAL PROPERTY
   The Service and its content are owned by [COMPANY NAME] and protected by
   copyright, trademark, and other laws.

5. USER CONTENT
   You retain ownership of content you submit. You grant us a license to use,
   display, and distribute your content in connection with the Service.

6. PRIVACY
   Use of the Service is subject to our Privacy Policy, incorporated herein.

7. DISCLAIMERS
   THE SERVICE IS PROVIDED "AS IS" WITHOUT WARRANTIES OF ANY KIND.

8. LIMITATION OF LIABILITY
   TO THE MAXIMUM EXTENT PERMITTED BY LAW, [COMPANY NAME] SHALL NOT BE
   LIABLE FOR INDIRECT, INCIDENTAL, OR CONSEQUENTIAL DAMAGES.

9. GOVERNING LAW
   These Terms are governed by [STATE] law. Disputes resolved in [COUNTY, STATE].

10. CHANGES TO TERMS
    We may modify these Terms at any time. Continued use constitutes acceptance.

Contact: [LEGAL@COMPANY.COM]
"""

    def _privacy_policy(self) -> str:
        return """\
                         PRIVACY POLICY

Last Updated: [DATE]
Effective Date: [DATE]

[COMPANY NAME] ("Company," "we," "us") respects your privacy. This Privacy
Policy explains how we collect, use, disclose, and protect your information.

1. INFORMATION WE COLLECT
   (a) Information you provide: name, email, phone, address, payment info;
   (b) Automatically collected: IP address, device type, browser, cookies;
   (c) From third parties: social media, analytics, advertising partners.

2. HOW WE USE YOUR INFORMATION
   (a) Provide and improve our services;
   (b) Process transactions and send related information;
   (c) Send marketing communications (with opt-out);
   (d) Comply with legal obligations;
   (e) Prevent fraud.

3. SHARING YOUR INFORMATION
   We may share information with:
   (a) Service providers (payment processors, hosting, analytics);
   (b) Business partners (with your consent);
   (c) Law enforcement (when required by law);
   (d) In connection with business transfers.

4. COOKIES AND TRACKING
   We use cookies and similar technologies. You may opt out via browser settings.

5. YOUR RIGHTS (CCPA / GDPR where applicable)
   (a) Access and portability of your data;
   (b) Correction of inaccurate data;
   (c) Deletion of your data ("right to be forgotten");
   (d) Opt-out of sale of personal information;
   (e) Non-discrimination for exercising rights.

6. DATA RETENTION
   We retain data for [NUMBER] years or as required by law.

7. SECURITY
   We implement reasonable security measures. No system is 100% secure.

8. CHILDREN'S PRIVACY (COPPA)
   We do not knowingly collect information from children under [13].

9. CONTACT US
   Privacy Officer: [NAME]
   Email: [PRIVACY@COMPANY.COM]
   Address: [COMPANY ADDRESS]

10. CHANGES
    We will notify you of material changes by email or prominent notice.
"""
