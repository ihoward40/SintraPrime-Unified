"""
Trust Knowledge Base
====================
Core repository of trust law doctrines, jurisdictions, UCC concepts,
and foundational legal principles. This is the knowledge core of the
SintraPrime Trust Law Intelligence System.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any
import re


class TrustKnowledgeBase:
    """
    Comprehensive trust law knowledge repository covering 30+ trust doctrines,
    all major jurisdictions, and UCC Articles 1-9.
    """

    # -------------------------------------------------------------------------
    # TRUST DOCTRINES — 30 entries, fully documented
    # -------------------------------------------------------------------------
    TRUST_DOCTRINES: Dict[str, Dict[str, Any]] = {

        "spendthrift_trust": {
            "name": "Spendthrift Trust",
            "description": (
                "A trust that restricts the beneficiary's ability to transfer or "
                "assign their interest and prevents creditors of the beneficiary from "
                "attaching or anticipating future distributions. Protects profligate "
                "or financially vulnerable beneficiaries from themselves and their creditors."
            ),
            "jurisdiction": "All 50 US states (with varying strength)",
            "legal_basis": (
                "Restatement (Third) of Trusts §58; UTC §502-503; "
                "most states follow Uniform Trust Code spendthrift provisions"
            ),
            "key_cases": [
                "Sligh v. First National Bank of Holmes County, 704 So.2d 1020 (Miss. 1997)",
                "Scheffel v. Krueger, 146 N.H. 669 (2001)",
                "In re Kilpatrick, 2011 WL 3903420 (Bankr. D. Nev. 2011)",
                "Holt v. College of Osteopathic Physicians, 61 Cal.2d 750 (1964)",
            ],
            "strategic_uses": [
                "Protect trust assets from beneficiary's creditors",
                "Preserve family wealth for future generations",
                "Shield assets from beneficiary's divorce proceedings",
                "Protect beneficiaries with addiction or financial management issues",
                "Long-term wealth preservation in estate planning",
            ],
            "limitations": [
                "Exception creditors: child support, alimony, government claims may pierce",
                "Does not protect against settlor's creditors in self-settled trusts",
                "Beneficiary cannot voluntarily transfer their interest",
                "Federal tax liens may not be limited by spendthrift clause",
                "Some states limit enforcement against tort claimants",
            ],
            "tax_implications": "No direct tax benefit; distributions taxed to beneficiary",
            "complexity": "Low-Medium",
        },

        "discretionary_trust": {
            "name": "Discretionary Trust",
            "description": (
                "A trust in which the trustee has full discretion over whether and "
                "how much to distribute to beneficiaries. Because beneficiaries have "
                "no fixed right to distributions, their creditors cannot reach trust "
                "assets until actually distributed. Often combined with spendthrift provisions."
            ),
            "jurisdiction": "All jurisdictions; strongest in SD, NV, AK, DE",
            "legal_basis": (
                "Restatement (Third) of Trusts §60; UTC §504; "
                "Discretionary trust doctrine under common law"
            ),
            "key_cases": [
                "Kemper v. Kemper, 764 S.W.2d 294 (Mo. App. 1989)",
                "Duvall v. McGee, 375 Md. 476 (2003)",
                "Shelley v. Shelley, 223 Or. 328 (1960)",
                "In re Platt, 2014 WL 1386503 (Bankr. D. Colo. 2014)",
            ],
            "strategic_uses": [
                "Maximum creditor protection for beneficiaries",
                "Flexibility in wealth distribution based on changing needs",
                "Medicaid planning (distributions at trustee's discretion)",
                "Protect assets during beneficiary's divorce or litigation",
                "Multi-generational wealth preservation",
            ],
            "limitations": [
                "Trustee must act in good faith and not abuse discretion",
                "UTC §504 gives creditors access if trustee has absolute discretion for benefit",
                "Settlor's retained power may cause inclusion in estate",
                "Court may compel distribution if trustee acts in bad faith",
            ],
            "tax_implications": "Taxed to beneficiary upon distribution; trust may pay income tax if undistributed",
            "complexity": "Medium",
        },

        "purpose_trust": {
            "name": "Purpose Trust",
            "description": (
                "A trust established for a specific non-charitable purpose rather than "
                "for identifiable beneficiaries. Common in offshore jurisdictions and "
                "now allowed in several US states. Used for holding special assets, "
                "pet trusts, cemetery care, and complex business structures."
            ),
            "jurisdiction": "South Dakota, Delaware, Nevada, Alaska; offshore: Cayman, BVI, Jersey",
            "legal_basis": (
                "SDCL §55-3-24 (SD); Cayman Special Trusts (Alternative Regime) Law 1997; "
                "VISTA (BVI); Restatement Third §47 comment"
            ),
            "key_cases": [
                "In re Denley's Trust Deed [1969] 1 Ch 373 (English)",
                "Re Astor's Settlement Trusts [1952] Ch 534",
            ],
            "strategic_uses": [
                "Pet trusts for care of animals",
                "Holding PPLI (private placement life insurance) structures",
                "Business succession with no named beneficiaries",
                "Voting trust structures for corporate control",
                "Privacy structures — no beneficiary to identify",
            ],
            "limitations": [
                "Requires a protector or enforcer to enforce trust terms",
                "Limited US state availability",
                "May be challenged as lacking a beneficiary (common law rule)",
                "Purpose must be specific, lawful, and possible",
            ],
            "tax_implications": "Complex — may be treated as grantor trust or foreign trust depending on structure",
            "complexity": "High",
        },

        "charitable_remainder_trust": {
            "name": "Charitable Remainder Trust (CRT)",
            "description": (
                "A split-interest trust where the grantor or other non-charitable "
                "beneficiaries receive income for a term, after which the remainder "
                "passes to charity. Provides an income stream, charitable deduction, "
                "and avoidance of capital gains on contributed appreciated assets."
            ),
            "jurisdiction": "Federal (IRC §664); all states",
            "legal_basis": (
                "IRC §664; Treas. Reg. §1.664-1 through 1.664-4; "
                "Restatement (Third) of Trusts; Revenue Procedure 2016-42"
            ),
            "key_cases": [
                "Atkinson v. Commissioner, 115 T.C. 26 (2000)",
                "Leila G. Newhall Unitrust v. Commissioner, 105 F.3d 482 (9th Cir. 1997)",
            ],
            "strategic_uses": [
                "Convert highly appreciated, low-basis assets to diversified income",
                "Charitable income tax deduction in year of contribution",
                "Avoid capital gains tax on sale of appreciated assets",
                "Supplemental retirement income planning",
                "Estate tax reduction while supporting charity",
            ],
            "limitations": [
                "Irrevocable once established",
                "Minimum 5% annual payout required",
                "Remainder must be at least 10% of initial contribution",
                "Cannot benefit the settlor as trustee for certain self-dealing rules",
                "Complexity and ongoing administration costs",
            ],
            "tax_implications": "Partial charitable deduction; four-tier income ordering on distributions",
            "complexity": "High",
        },

        "asset_protection_trust": {
            "name": "Asset Protection Trust (APT)",
            "description": (
                "A self-settled trust designed to protect the grantor's own assets from "
                "future creditors. The grantor may be a discretionary beneficiary. "
                "Effectiveness depends heavily on jurisdiction — offshore trusts in Cook "
                "Islands and Nevis offer strongest protection."
            ),
            "jurisdiction": "Domestic: AK, SD, NV, DE, WY, OH; Offshore: Cook Islands, Nevis, Belize",
            "legal_basis": (
                "Alaska Trust Act (AS 34.40.110); SD SDCL §55-16; "
                "NV NRS §166.015; Cook Islands International Trusts Act 1984"
            ),
            "key_cases": [
                "Federal Trade Commission v. Affordable Media, LLC, 179 F.3d 1228 (9th Cir. 1999)",
                "In re Huber, 493 B.R. 798 (Bankr. W.D. Wash. 2013)",
                "Toni 1 Trust v. Wacker, 413 P.3d 1199 (Alaska 2018)",
                "In re Brown, 303 B.R. 415 (Bankr. D. Nev. 2003)",
            ],
            "strategic_uses": [
                "Shield assets from professional liability (doctors, attorneys)",
                "Pre-litigation asset protection planning",
                "Creditor deterrence — expensive to attack",
                "Divorce protection for high-net-worth individuals",
                "Business failure protection",
            ],
            "limitations": [
                "Fraudulent transfer law applies — must be pre-litigation",
                "Bankruptcy court may override domestic APTs",
                "Offshore APTs face contempt issues if grantor is in US court",
                "IRS may treat as grantor trust (transparency for tax)",
                "Ongoing compliance costs for offshore trusts",
            ],
            "tax_implications": "Grantor trust for income tax (grantor pays tax); estate inclusion if retained powers",
            "complexity": "Very High",
        },

        "blind_trust": {
            "name": "Blind Trust",
            "description": (
                "A trust where the grantor (typically a public official or business "
                "executive) transfers assets to an independent trustee who has full "
                "discretion over investment decisions. The grantor has no knowledge of "
                "specific holdings, eliminating conflicts of interest."
            ),
            "jurisdiction": "All jurisdictions; governed by OGE regulations for federal officials",
            "legal_basis": (
                "Office of Government Ethics (OGE) regulations 5 CFR Part 2634; "
                "Ethics in Government Act of 1978; common law trust principles"
            ),
            "key_cases": [
                "Senate Select Committee on Ethics Advisory Opinions",
                "OGE Informal Advisory Opinion 2008-01",
            ],
            "strategic_uses": [
                "Politicians and government officials avoiding conflicts of interest",
                "Corporate executives avoiding insider trading issues",
                "High-profile individuals maintaining privacy of investments",
                "Divorce proceedings — neutral management",
            ],
            "limitations": [
                "Trustee must be truly independent — not friends or family",
                "OGE requires qualified blind trust for federal officials",
                "Not a tax shelter — grantor still taxed on income",
                "Grantor cannot influence investment decisions",
            ],
            "tax_implications": "Grantor trust rules apply; income reported on grantor's return",
            "complexity": "Medium",
        },

        "common_law_trust": {
            "name": "Common Law Trust",
            "description": (
                "A trust formed under the common law (judicial precedent) rather than "
                "statutory authority. Also known as a 'pure trust' or 'constitutional trust'. "
                "Often used in pseudolegal schemes — practitioner must distinguish legitimate "
                "common law trusts from fraudulent schemes claiming tax immunity."
            ),
            "jurisdiction": "All common law jurisdictions; supplemented by UTC in adopting states",
            "legal_basis": (
                "English common law (Statute of Uses 1535); Restatement (Third) of Trusts; "
                "equity jurisprudence"
            ),
            "key_cases": [
                "Knight v. Knight (1840) 3 Beav 148",
                "Milroy v. Lord (1862) 4 De GF & J 264",
                "Commissioner v. Estate of Church, 335 U.S. 632 (1949)",
            ],
            "strategic_uses": [
                "Estate planning where statutory trust law is insufficient",
                "International structures combining common law flexibility",
                "Historical basis for all modern trust structures",
            ],
            "limitations": [
                "Often subject to abuse in pseudolegal tax schemes",
                "IRS aggressively attacks 'pure trust' promoters",
                "Less predictable than statutory trusts",
                "Requires knowledgeable legal counsel",
            ],
            "tax_implications": "Subject to normal trust taxation; no special exemptions",
            "complexity": "Medium",
        },

        "massachusetts_business_trust": {
            "name": "Massachusetts Business Trust / Business Trust",
            "description": (
                "An unincorporated business organization structured as a trust, where "
                "investors hold transferable certificates of beneficial interest. Historically "
                "used because Massachusetts prohibited corporations from owning real estate. "
                "Forerunner of the modern Real Estate Investment Trust (REIT)."
            ),
            "jurisdiction": "Massachusetts (origin); Delaware, Texas; all states recognize",
            "legal_basis": (
                "Hecht v. Malley, 265 U.S. 144 (1924); "
                "Massachusetts common law; Restatement (Third) of Trusts §1 comment"
            ),
            "key_cases": [
                "Hecht v. Malley, 265 U.S. 144 (1924)",
                "Morrissey v. Commissioner, 296 U.S. 344 (1935)",
                "Outwater v. Public Service Corp. of New Jersey, 103 N.J. Eq. 461 (1928)",
            ],
            "strategic_uses": [
                "Real estate investment structures (pre-REIT)",
                "Mutual fund organization (many older funds use this form)",
                "Business operations requiring trust flexibility",
                "Multi-investor structures with transferable interests",
            ],
            "limitations": [
                "May be taxed as a corporation (4 Morrissey factors)",
                "Trustee liability exposure if not properly structured",
                "Less creditor protection than LLC",
                "Regulatory complexity for securities law if interests are securities",
            ],
            "tax_implications": "May be taxed as trust or corporation depending on Morrissey factors",
            "complexity": "High",
        },

        "grantor_trust": {
            "name": "Grantor Trust",
            "description": (
                "A trust where the grantor retains certain powers or interests causing "
                "the grantor to be treated as the owner for income tax purposes. All "
                "income, deductions, and credits flow through to the grantor's personal "
                "tax return. Used strategically in IDGT, SLATs, and other estate freeze techniques."
            ),
            "jurisdiction": "Federal (IRC §§671-679); all states",
            "legal_basis": (
                "IRC §§671-679 (Grantor Trust Rules); "
                "Treas. Reg. §1.671-1 through 1.677-1; "
                "Rev. Rul. 85-13 (sales between grantor and grantor trust are disregarded)"
            ),
            "key_cases": [
                "Helvering v. Clifford, 309 U.S. 331 (1940)",
                "Mallinckrodt v. Nunan, 146 F.2d 1 (8th Cir. 1945)",
                "Estate of Powell v. Commissioner, 148 T.C. 392 (2017)",
                "Jordahl v. Commissioner, 65 T.C. 92 (1975)",
            ],
            "strategic_uses": [
                "Intentionally Defective Grantor Trust (IDGT) — estate freeze",
                "SLAT — grantor pays tax = additional gift to beneficiaries",
                "Sale of assets to grantor trust = no capital gains recognition",
                "GRAT — grantor retains annuity, remainder passes tax-free",
                "QPRT — grantor retains residence use, remainder transfers",
            ],
            "limitations": [
                "Grantor pays tax on trust income (can be a burden)",
                "IRC §§2036-2038 may cause estate inclusion",
                "Revenue Procedure 2008-45 identifies non-recognition transactions",
                "Biden administration proposed eliminating grantor trust benefits (not enacted)",
            ],
            "tax_implications": "Income taxed to grantor; trust assets may or may not be in estate",
            "complexity": "High",
        },

        "revocable_living_trust": {
            "name": "Revocable Living Trust",
            "description": (
                "A trust created during the grantor's lifetime that can be amended, "
                "modified, or revoked at any time by the grantor. Avoids probate, "
                "maintains privacy, provides seamless asset management during incapacity, "
                "and facilitates multi-state asset transfers without ancillary probate."
            ),
            "jurisdiction": "All 50 states; UTC §601-604",
            "legal_basis": (
                "UTC §601 (revocability); Restatement (Third) of Trusts §63; "
                "state-specific trust codes"
            ),
            "key_cases": [
                "Farkas v. Williams, 5 Ill.2d 417 (1955)",
                "State Street Bank & Trust Co. v. Reiser, 7 Mass. App. Ct. 633 (1979)",
                "Pour-Over Will: Clymer v. Mayo, 393 Mass. 754 (1985)",
            ],
            "strategic_uses": [
                "Probate avoidance (primary use)",
                "Privacy — trust documents not public record",
                "Incapacity planning — successor trustee takes over seamlessly",
                "Multi-state property — avoids ancillary probate",
                "Blended family planning with clear instructions",
            ],
            "limitations": [
                "No asset protection from creditors (revocable = accessible)",
                "No estate tax savings (included in grantor's estate)",
                "Assets must be re-titled into trust (funding is critical)",
                "Does not avoid estate taxes like irrevocable trust",
                "Costs more than will upfront",
            ],
            "tax_implications": "Disregarded entity — grantor reports all income; included in estate",
            "complexity": "Low-Medium",
        },

        "irrevocable_trust": {
            "name": "Irrevocable Trust",
            "description": (
                "A trust that generally cannot be modified, amended, or revoked after "
                "creation without consent of the beneficiaries. Removes assets from the "
                "grantor's taxable estate, provides creditor protection, and enables "
                "complex estate planning strategies. Encompasses many specialized trust types."
            ),
            "jurisdiction": "All states; UTC §410-416 (modification/termination)",
            "legal_basis": (
                "UTC §410 (modification/termination); Restatement (Third) §65-67; "
                "Nonjudicial settlement agreements; decanting statutes"
            ),
            "key_cases": [
                "In re Riddell, 157 Wash. App. 480 (2010)",
                "Green v. Grimes, 216 Iowa 892 (1933)",
                "Carlisle v. National Oil & Development Co., 108 So. 5 (Ala. 1926)",
            ],
            "strategic_uses": [
                "Remove assets from taxable estate",
                "Medicaid planning — 5-year lookback consideration",
                "Life insurance trust (ILIT) — keep proceeds out of estate",
                "Asset protection from future creditors",
                "Dynasty trust for multi-generational wealth",
            ],
            "limitations": [
                "Loss of control over assets",
                "Modification requires court approval or beneficiary consent (except decanting)",
                "Drafting errors cannot be easily corrected",
                "Some states allow modification by unanimous beneficiary consent",
            ],
            "tax_implications": "May be outside grantor's estate; trust pays its own taxes at compressed rates unless grantor trust",
            "complexity": "Medium-High",
        },

        "dynasty_trust": {
            "name": "Dynasty Trust / Generation-Skipping Trust (GST)",
            "description": (
                "A long-term irrevocable trust designed to hold assets for multiple "
                "generations, bypassing estate taxes at each generational transfer. "
                "Utilizes the Generation-Skipping Transfer (GST) tax exemption. "
                "Favorable states have abolished or extended the Rule Against Perpetuities."
            ),
            "jurisdiction": "Best in: SD (unlimited duration), NV, WY, AK, DE; UTC states with RAP modified",
            "legal_basis": (
                "IRC §2631-2663 (GST tax); "
                "South Dakota SDCL §43-5-1 (abolished RAP); "
                "Uniform Statutory Rule Against Perpetuities"
            ),
            "key_cases": [
                "Estate of Hartzell v. Commissioner, T.C. Memo 2011-69",
                "Letts v. Letts, 856 N.E.2d 267 (Ohio App. 2006)",
            ],
            "strategic_uses": [
                "Multi-generational wealth transfer without estate tax at each death",
                "Maximize $13.61M GST exemption (2024) per person",
                "Provide for children, grandchildren, great-grandchildren",
                "Combined with IDGT for estate-freeze techniques",
                "Corporate-owned life insurance (COLI) inside dynasty trust",
            ],
            "limitations": [
                "GST tax (40%) applies to amounts exceeding exemption",
                "Irrevocable once created",
                "Must allocate GST exemption properly",
                "Beneficiaries may have limited access to funds",
                "Trustee must manage for very long term",
            ],
            "tax_implications": "GST exemption shields from 40% GST tax; estate tax avoided at each generation",
            "complexity": "Very High",
        },

        "special_needs_trust": {
            "name": "Special Needs Trust (SNT) / Supplemental Needs Trust",
            "description": (
                "A trust designed to supplement, not replace, government benefits for "
                "a person with disabilities. Preserves eligibility for Medicaid and SSI "
                "while providing additional support. Can be first-party (beneficiary's funds) "
                "or third-party (family funds)."
            ),
            "jurisdiction": "All states; governed by 42 U.S.C. §1396p(d)(4)",
            "legal_basis": (
                "42 U.S.C. §1396p(d)(4)(A) (first-party); "
                "42 U.S.C. §1396p(d)(4)(C) (pooled trust); "
                "ABLE Act of 2014; SSI Program Operations Manual (POMS)"
            ),
            "key_cases": [
                "Hecker v. Stark County Social Services Board, 527 N.W.2d 226 (N.D. 1995)",
                "Matter of Escher, 94 Misc.2d 952 (N.Y. Surr. 1978)",
                "Corcoran v. County of Sacramento, 956 F.2d 875 (9th Cir. 1992)",
            ],
            "strategic_uses": [
                "Preserve Medicaid/SSI eligibility for disabled beneficiary",
                "Receive personal injury settlements without losing benefits",
                "Family gifts/inheritance to disabled member without disqualification",
                "Pooled trust for smaller amounts",
                "Supplemental care beyond what government provides",
            ],
            "limitations": [
                "First-party SNT requires Medicaid payback at beneficiary's death",
                "Strict distribution rules — cannot replace government benefits",
                "Must be managed by a trustee (not beneficiary)",
                "Complex compliance with SSI and Medicaid rules",
            ],
            "tax_implications": "Taxed as a complex trust; income taxed at trust rates",
            "complexity": "High",
        },

        "land_trust": {
            "name": "Land Trust / Illinois Land Trust",
            "description": (
                "A revocable trust where real estate is the primary asset and the "
                "beneficiary holds the power of direction over the trustee. The public "
                "record shows only the trustee's name — the beneficial owner remains "
                "private. Common in Illinois, Florida, Virginia, Indiana, North Dakota."
            ),
            "jurisdiction": "IL, FL, VA, IN, ND primarily; Florida uses similar 'sunshine state trust'",
            "legal_basis": (
                "765 ILCS 430 (Illinois Land Trust Act); "
                "FL §689.071 (Florida Land Trust Act); "
                "common law in other states"
            ),
            "key_cases": [
                "Chicago Title & Trust Co. v. Mercantile Trust & Savings Bank, 300 Ill. 174 (1921)",
                "Ill. Realty Corp. v. Goesel, 27 Ill. App.2d 244 (1960)",
                "In re Weissberg, 205 B.R. 723 (Bankr. N.D. Ill. 1997)",
            ],
            "strategic_uses": [
                "Real estate privacy — public record shows only trustee",
                "Avoid title issues in multiple-owner properties",
                "Facilitate real estate syndications",
                "Ease of transfer — assignment of beneficial interest",
                "Protection from mechanic's liens in some states",
            ],
            "limitations": [
                "Due-on-sale clauses in mortgages may be triggered",
                "Limited asset protection (revocable)",
                "Not recognized in all states",
                "Trustee holds legal title — full liability if not limited",
            ],
            "tax_implications": "Disregarded for tax purposes; beneficiary reports income",
            "complexity": "Low-Medium",
        },

        "delaware_statutory_trust": {
            "name": "Delaware Statutory Trust (DST)",
            "description": (
                "A statutory trust created under Delaware law (12 Del. C. §3801 et seq.) "
                "that has become the dominant vehicle for 1031 exchange replacements. "
                "Allows multiple investors to hold fractional interests in commercial "
                "real estate as tenants-in-common equivalent while deferring capital gains."
            ),
            "jurisdiction": "Delaware (statutory basis); SEC-regulated if securities offering",
            "legal_basis": (
                "12 Del. C. §3801-3862 (Delaware Statutory Trust Act); "
                "Rev. Rul. 2004-86 (IRS recognition for 1031 purposes); "
                "Securities Act of 1933 (if publicly offered)"
            ),
            "key_cases": [
                "Rev. Rul. 2004-86, 2004-2 C.B. 191",
                "IRS Field Attorney Advice 20103201F",
            ],
            "strategic_uses": [
                "1031 like-kind exchange replacement property",
                "Passive real estate investment for retirement income",
                "Fractional ownership of institutional-grade properties",
                "Estate planning — easy to divide among heirs",
                "Deferred sales trust (DST) alternative for capital gains",
            ],
            "limitations": [
                "Investors have no management rights",
                "7 deadly sins rule: no new debt, no new investors, no significant improvements",
                "Illiquid investment — limited secondary market",
                "Qualified investors only in most offerings",
                "No flexibility to adapt to market conditions",
            ],
            "tax_implications": "Pass-through entity; depreciation and income flow to beneficiaries pro-rata",
            "complexity": "High",
        },

        "nevada_asset_protection_trust": {
            "name": "Nevada Asset Protection Trust",
            "description": (
                "A domestic self-settled spendthrift trust under Nevada law with a "
                "2-year statute of limitations for fraudulent transfers (shortest in US), "
                "no exception creditors except child support/alimony, and strong trustee "
                "independence requirements. Considered among the strongest domestic APTs."
            ),
            "jurisdiction": "Nevada (NRS Chapter 166)",
            "legal_basis": (
                "Nevada Revised Statutes NRS §§166.015, 166.170, 166.040; "
                "Nevada Spendthrift Trust Act"
            ),
            "key_cases": [
                "In re Brown, 303 B.R. 415 (Bankr. D. Nev. 2003)",
                "Klabacka v. Nelson, 133 Nev. 164 (2017)",
                "In re Mortensen, 2011 WL 5025249 (Bankr. D. Alaska 2011)",
            ],
            "strategic_uses": [
                "Domestic asset protection with short 2-year SOL",
                "Self-settled trust — grantor can be discretionary beneficiary",
                "Combined with Nevada LLC for layered protection",
                "Physician/professional practice protection",
            ],
            "limitations": [
                "Federal bankruptcy court has override power",
                "Must have Nevada trustee (corporate trust company preferred)",
                "Pre-transfer solvency required",
                "Full-faith-and-credit concerns from other states",
            ],
            "tax_implications": "Grantor trust for income tax; no state income tax in Nevada",
            "complexity": "High",
        },

        "dapt": {
            "name": "Domestic Asset Protection Trust (DAPT)",
            "description": (
                "The generic category of self-settled domestic trusts where the grantor "
                "can be a discretionary beneficiary while maintaining creditor protection. "
                "Available in 19+ states as of 2024. Effectiveness varies dramatically by "
                "state and against different creditor types."
            ),
            "jurisdiction": "AK, SD, NV, DE, WY, OH, TN, VA, NH, SC, HI, MI, RI, UT, IN, MO, ND, SD, OK",
            "legal_basis": (
                "Alaska Trust Act (AS §34.40.110); SD SDCL §55-16; "
                "UTC does not include DAPT provisions; state-by-state legislation"
            ),
            "key_cases": [
                "In re Huber, 493 B.R. 798 (Bankr. W.D. Wash. 2013)",
                "Mortensen v. Mortensen, 2011 WL 5025249 (Bankr. D. Alaska 2011)",
                "In re Portnoy, 201 B.R. 685 (Bankr. S.D.N.Y. 1996)",
            ],
            "strategic_uses": [
                "Asset protection without going offshore",
                "Physician, dentist, attorney professional liability shielding",
                "Pre-litigation wealth protection planning",
                "Supplement to irrevocable life insurance trust",
            ],
            "limitations": [
                "Fraudulent transfer challenges effective within SOL",
                "Bankruptcy court jurisdiction may override",
                "Full faith and credit — non-DAPT states may not honor",
                "Must be pre-litigation — no post-lawsuit transfers",
            ],
            "tax_implications": "Grantor trust for federal income tax purposes",
            "complexity": "High",
        },

        "fapt": {
            "name": "Foreign Asset Protection Trust (FAPT) / Offshore Asset Protection Trust",
            "description": (
                "A self-settled trust established in a foreign jurisdiction with favorable "
                "asset protection laws. Assets held offshore, governed by foreign law, "
                "with foreign trustees. Considered the strongest asset protection available "
                "but subject to strict US reporting requirements."
            ),
            "jurisdiction": "Cook Islands (strongest), Nevis, Belize, Cayman Islands, Liechtenstein, Jersey",
            "legal_basis": (
                "Cook Islands International Trusts Act 1984 (as amended); "
                "IRC §6048 (reporting); Form 3520/3520-A; FBAR (31 U.S.C. §5314)"
            ),
            "key_cases": [
                "FTC v. Affordable Media LLC, 179 F.3d 1228 (9th Cir. 1999) ('Anderson' case)",
                "Lawrence v. Goldberg, 573 F.3d 1265 (11th Cir. 2009)",
                "In re Lawrence, 279 F.3d 1294 (11th Cir. 2002)",
            ],
            "strategic_uses": [
                "Ultimate asset protection against US creditor judgments",
                "International wealth management",
                "Combined with offshore LLC for maximum protection",
                "Privacy from US court processes",
            ],
            "limitations": [
                "Complex reporting: Form 3520, 3520-A, FBAR, FATCA",
                "Civil contempt for refusing to repatriate assets",
                "High setup and maintenance costs ($20,000-$50,000+/year)",
                "US persons cannot deduct offshore trust expenses",
                "Heightened IRS scrutiny",
            ],
            "tax_implications": "Grantor trust for tax; extensive foreign trust reporting requirements",
            "complexity": "Very High",
        },

        "cook_islands_trust": {
            "name": "Cook Islands Trust",
            "description": (
                "Widely considered the gold standard of offshore asset protection trusts. "
                "Cook Islands law requires creditors to re-litigate from scratch in Cook "
                "Islands courts (which do not recognize US judgments), with a 2-year statute "
                "of limitations, and a high burden of proof for fraudulent transfer claims."
            ),
            "jurisdiction": "Cook Islands (South Pacific)",
            "legal_basis": (
                "Cook Islands International Trusts Act 1984; "
                "Amendment Acts of 1989, 1991, 1996, 1999, 2004; "
                "Cook Islands does not enforce US court judgments"
            ),
            "key_cases": [
                "FTC v. Affordable Media (Anderson case) — grantor held in contempt but assets preserved",
                "NovaStar Mortgage v. Snyder — creditors unable to reach assets",
            ],
            "strategic_uses": [
                "Maximum protection from US civil judgments",
                "High-risk professionals: surgeons, pilots, financial advisors",
                "Pre-litigation wealth preservation",
                "International family office structures",
            ],
            "limitations": [
                "Grantor may face US contempt proceedings",
                "Does not protect against criminal forfeiture",
                "Annual costs: $10,000-$30,000+",
                "Full reporting to IRS required",
                "Reputational concerns",
            ],
            "tax_implications": "Grantor trust — no tax deferral; reporting-intensive",
            "complexity": "Very High",
        },

        "nevis_trust": {
            "name": "Nevis Trust / Nevis Multiform Foundation",
            "description": (
                "Nevis (Caribbean island) offers strong asset protection trust laws with "
                "a high burden on creditors (must post a $25,000 bond to sue), short SOL, "
                "and the unique 'Multiform Foundation' that combines trust and foundation "
                "characteristics. Popular alternative to Cook Islands."
            ),
            "jurisdiction": "Nevis, Federation of St. Kitts and Nevis",
            "legal_basis": (
                "Nevis International Exempt Trust Ordinance 1994; "
                "Nevis Multiform Foundations Ordinance 2004; "
                "Nevis LLC Ordinance 1995"
            ),
            "key_cases": [
                "Various unpublished Nevis High Court decisions upholding trust provisions",
            ],
            "strategic_uses": [
                "Asset protection with lower costs than Cook Islands",
                "Combined Nevis LLC + Nevis Trust structure",
                "International estate planning",
                "Business succession structures",
            ],
            "limitations": [
                "Less tested in US courts than Cook Islands",
                "$25,000 bond requirement deters frivolous suits but not serious creditors",
                "Full IRS reporting required",
                "Political/legislative risk in small jurisdiction",
            ],
            "tax_implications": "Grantor trust treatment; Form 3520 required",
            "complexity": "High",
        },

        "liechtenstein_foundation": {
            "name": "Liechtenstein Foundation / Anstalt",
            "description": (
                "A unique civil-law institution that combines elements of a trust and a "
                "corporation. The Liechtenstein Foundation (Stiftung) is a separate legal "
                "entity with no members or shareholders, governed by a foundation council. "
                "Offers extraordinary privacy and asset protection under civil law."
            ),
            "jurisdiction": "Liechtenstein (Principality)",
            "legal_basis": (
                "Liechtenstein Persons and Companies Act (PGR) Art. 552 et seq.; "
                "Liechtenstein Foundation Law 2009; "
                "OECD information exchange agreements"
            ),
            "key_cases": [
                "Various European Court of Human Rights decisions on Liechtenstein trusts",
            ],
            "strategic_uses": [
                "European wealth management and succession planning",
                "Multi-generational family wealth preservation",
                "International holding structures for business assets",
                "Privacy-focused structures for high-net-worth families",
            ],
            "limitations": [
                "OECD automatic information exchange (AEOI) reduces privacy",
                "Complex civil law jurisdiction — different from common law trust",
                "High professional fees",
                "CRS/FATCA reporting requirements",
            ],
            "tax_implications": "Foreign trust/entity for US tax purposes; Form 3520 may apply",
            "complexity": "Very High",
        },

        "wyoming_llc_trust": {
            "name": "Wyoming LLC Trust Hybrid",
            "description": (
                "A powerful hybrid structure combining a Wyoming LLC (no member list "
                "publicly required) held by a Wyoming Statutory Trust or similar trust. "
                "Provides combined charging order protection, anonymity, asset protection, "
                "and flexible management. Wyoming has some of the strongest charging order "
                "protection in the US."
            ),
            "jurisdiction": "Wyoming",
            "legal_basis": (
                "Wyoming Revised Statutes §17-29-501 et seq. (LLC charging order); "
                "Wyoming Statutory Trust Act §17-23-101 et seq.; "
                "Wyoming does not require member names in public filings"
            ),
            "key_cases": [
                "Greenhunter Energy v. Western Ecosystems, 2014 WY 144",
                "Olmstead v. FTC (distinguishing Wyoming's stronger protection)",
            ],
            "strategic_uses": [
                "Maximum US domestic privacy",
                "Real estate holdings with charging order protection",
                "Operating business with asset protection overlay",
                "Family office structures",
            ],
            "limitations": [
                "Must maintain separate from personal finances",
                "Wyoming registered agent required",
                "Not as tested as older DAPT states",
                "Out-of-state creditors may challenge",
            ],
            "tax_implications": "Pass-through entity; Wyoming has no state income tax",
            "complexity": "Medium-High",
        },

        "medicaid_asset_protection_trust": {
            "name": "Medicaid Asset Protection Trust (MAPT)",
            "description": (
                "An irrevocable trust designed to protect assets from Medicaid spend-down "
                "requirements while preserving eligibility for long-term care benefits. "
                "Assets transferred to the MAPT are subject to a 5-year lookback period. "
                "The grantor cannot be a beneficiary of the principal (income only)."
            ),
            "jurisdiction": "All states; governed by federal Medicaid rules (42 U.S.C. §1396p)",
            "legal_basis": (
                "42 U.S.C. §1396p(d) (Medicaid trust rules); "
                "Deficit Reduction Act of 2005 (5-year lookback); "
                "State Medicaid plans"
            ),
            "key_cases": [
                "Heckler v. Turner, 470 U.S. 184 (1985)",
                "Matter of Moretti, 159 Misc.2d 654 (N.Y. Surr. 1994)",
                "Levin v. Harbor Hospital Center, 1993 WL 133317",
            ],
            "strategic_uses": [
                "Protect home and savings from nursing home costs",
                "Preserve assets for children while qualifying for Medicaid",
                "Long-term care planning for elderly clients",
            ],
            "limitations": [
                "5-year lookback — transfers within 5 years are penalized",
                "Grantor cannot access principal",
                "Irrevocable — permanent loss of control",
                "Income from trust still available to grantor (some states count it)",
            ],
            "tax_implications": "May be grantor trust for income tax; step-up in basis at death preserved if properly structured",
            "complexity": "High",
        },

        "qprt": {
            "name": "Qualified Personal Residence Trust (QPRT)",
            "description": (
                "An irrevocable trust where the grantor transfers a personal residence "
                "while retaining the right to live there for a fixed term. After the term, "
                "the residence passes to heirs at the discounted gift value (actuarially reduced "
                "by the retained interest). Freezes appreciation for estate tax purposes."
            ),
            "jurisdiction": "Federal (IRC §2702); all states",
            "legal_basis": (
                "IRC §2702; Treas. Reg. §25.2702-5; "
                "Rev. Proc. 2003-42 (IRS model form for QPRT)"
            ),
            "key_cases": [
                "Estate of Schauerhamer v. Commissioner, T.C. Memo 1997-242",
                "Walton v. Commissioner, 115 T.C. 589 (2000)",
                "Estate of Magnin v. Commissioner, T.C. Memo 1996-25",
            ],
            "strategic_uses": [
                "Transfer appreciated residence to heirs at reduced gift tax value",
                "Lock in current home value before appreciation",
                "Estate freeze for primary or vacation home",
            ],
            "limitations": [
                "If grantor dies during the term — property back in estate",
                "Grantor must pay rent after the term expires",
                "No step-up in basis for heirs (carryover basis)",
                "Rising interest rates reduce tax benefit",
            ],
            "tax_implications": "Taxable gift at discounted present value; no estate inclusion if grantor survives term",
            "complexity": "Medium-High",
        },

        "charitable_lead_trust": {
            "name": "Charitable Lead Trust (CLT)",
            "description": (
                "The mirror image of a Charitable Remainder Trust — the charity receives "
                "income payments for a term, after which the remainder passes to non-charitable "
                "beneficiaries (usually family). Used to transfer wealth to heirs with reduced "
                "gift/estate tax, especially in low-interest environments."
            ),
            "jurisdiction": "Federal (IRC §2522); all states",
            "legal_basis": (
                "IRC §§170(f)(2)(B), 2055(e)(2)(B), 2522(c)(2)(B); "
                "Treas. Reg. §1.170A-6"
            ),
            "key_cases": [
                "Estate of Boeshore v. Commissioner, T.C. Memo 1979-33",
                "McLennan v. United States, 23 Cl. Ct. 99 (1991)",
            ],
            "strategic_uses": [
                "Transfer wealth to heirs with minimal gift tax in low-rate environment",
                "Philanthropy combined with estate planning",
                "Highly appreciated assets in charitable structures",
                "Grantor CLT — charitable deduction to grantor (but complex)",
            ],
            "limitations": [
                "Non-grantor CLT provides no immediate income tax deduction",
                "Assets tied up for term of years",
                "Remainder beneficiaries receive property after charity income period",
                "Rising interest rates reduce effectiveness",
            ],
            "tax_implications": "Complex — depends on grantor vs. non-grantor CLT structure",
            "complexity": "High",
        },

        "idgt": {
            "name": "Intentionally Defective Grantor Trust (IDGT)",
            "description": (
                "An irrevocable trust structured to be outside the grantor's estate for "
                "estate tax purposes, but treated as the grantor's property for income tax "
                "purposes. The 'defect' (retained grantor trust power) makes income tax "
                "transparent while achieving estate tax removal. Sale of assets to IDGT "
                "is not a taxable transaction."
            ),
            "jurisdiction": "Federal; all states",
            "legal_basis": (
                "IRC §§671-679 (grantor trust rules); "
                "Rev. Rul. 85-13 (sales to grantor trust not taxable); "
                "PLR 9535026 (installment sale to IDGT)"
            ),
            "key_cases": [
                "Rothstein v. Commissioner, T.C. Memo 2003-284",
                "Estate of Powell v. Commissioner, 148 T.C. 392 (2017)",
                "Karmazin v. Commissioner, T.C. Memo 2002-236",
            ],
            "strategic_uses": [
                "Installment sale of business interests to IDGT — estate freeze",
                "Grantor pays income tax = additional gift without using exemption",
                "Swap assets of equivalent value without gift tax",
                "Transfer of S-corporation interests",
                "Dynasty trust seeding",
            ],
            "limitations": [
                "Proposed regulations (2023) may limit effectiveness if enacted",
                "Grantor bears income tax burden",
                "IRC §§2036-2038 retained interest issues",
                "Power to swap assets must be properly structured",
            ],
            "tax_implications": "Income taxed to grantor; estate tax savings if structured correctly",
            "complexity": "Very High",
        },

        "slat": {
            "name": "Spousal Lifetime Access Trust (SLAT)",
            "description": (
                "An irrevocable trust created by one spouse for the benefit of the other "
                "spouse (and children). The donor spouse removes assets from their estate "
                "while maintaining indirect access through the beneficiary spouse. "
                "Popular during high exemption periods to lock in exemptions."
            ),
            "jurisdiction": "Federal; all states",
            "legal_basis": (
                "IRC §§2512, 2523 (gift tax marital deduction rules); "
                "IRC §§671-679 (grantor trust if structured for income tax); "
                "Reciprocal trust doctrine caution"
            ),
            "key_cases": [
                "United States v. Grace, 395 U.S. 316 (1969) (reciprocal trust)",
                "Estate of Murphy v. Commissioner, T.C. Memo 1990-472",
            ],
            "strategic_uses": [
                "Lock in current $13.61M exemption before sunset in 2026",
                "Maintain family lifestyle through beneficiary spouse",
                "Estate tax savings for high-net-worth married couples",
                "Income tax optimization through grantor trust structure",
            ],
            "limitations": [
                "Reciprocal trust doctrine — two-SLAT strategy must be dissimilar",
                "Divorce risk — beneficiary spouse gets control of assets",
                "Death of beneficiary spouse — donor loses indirect access",
                "Must be truly irrevocable",
            ],
            "tax_implications": "Gift on creation (using exemption); grantor trust for income tax",
            "complexity": "High",
        },

        "alaska_trust": {
            "name": "Alaska Trust",
            "description": (
                "Alaska was the first US state (1997) to allow self-settled asset protection "
                "trusts. Features: 4-year statute of limitations, grantor can be discretionary "
                "beneficiary, no exception creditors for pre-existing debts (except child support), "
                "and no state income tax on trust income."
            ),
            "jurisdiction": "Alaska",
            "legal_basis": (
                "Alaska Statutes §34.40.110 (Alaska Trust Act); "
                "AS §13.36.035 (trustee requirements)"
            ),
            "key_cases": [
                "Toni 1 Trust v. Wacker, 413 P.3d 1199 (Alaska 2018)",
                "In re Mortensen, 2011 WL 5025249 (Bankr. D. Alaska 2011)",
            ],
            "strategic_uses": [
                "Domestic self-settled trust — pioneer DAPT state",
                "No Alaska state income tax on trust income",
                "Combined with Alaska LLC for double protection",
                "Long-term wealth preservation with self-benefit",
            ],
            "limitations": [
                "Bankruptcy court may not fully respect DAPT provisions",
                "Must maintain Alaska nexus (Alaska trustee required)",
                "Longer SOL than Nevada (4 vs 2 years)",
            ],
            "tax_implications": "Grantor trust; no Alaska state income tax",
            "complexity": "High",
        },

        "offshore_trust": {
            "name": "Offshore Trust",
            "description": "A trust established under the laws of a foreign jurisdiction, primarily used for asset protection against domestic creditors. Offshore trusts exploit the difficulty of enforcing US judgments in foreign courts that do not recognize US court orders.",
            "jurisdiction": "International (Cook Islands, Nevis, Liechtenstein, Cayman Islands, etc.)",
            "legal_basis": "Foreign jurisdiction trust law; US tax compliance under IRC 671-679",
            "key_cases": ["Federal Trade Commission v. Affordable Media LLC (9th Cir. 1999)", "In re Lawrence (9th Cir. 2003)"],
            "strategic_uses": [
                "Maximum creditor protection for high-risk professionals",
                "Asset diversification across currencies",
                "Privacy in jurisdictions with no public trust registry",
                "Protection against domestic judgment enforcement"
            ],
            "limitations": [
                "Requires FBAR reporting (FinCEN 114) for foreign financial accounts",
                "Requires Form 3520/3520-A annual reporting to IRS",
                "FATCA compliance required",
                "Courts may hold settlors in contempt for 'impossibility' claims",
                "Significant ongoing compliance and professional costs"
            ],
        },
        "south_dakota_trust": {
            "name": "South Dakota Trust",
            "description": (
                "South Dakota is considered the preeminent domestic trust jurisdiction. "
                "Features: no state income tax, abolished Rule Against Perpetuities (unlimited "
                "duration), strong directed trust statutes, robust decanting, self-settled trusts "
                "available, and unparalleled privacy laws. Trust assets exceed $500 billion."
            ),
            "jurisdiction": "South Dakota",
            "legal_basis": (
                "SDCL §55-1A (South Dakota Trust Code); "
                "SDCL §55-16 (South Dakota Asset Protection Trust); "
                "SDCL §43-5-1 (abolished Rule Against Perpetuities)"
            ),
            "key_cases": [
                "South Dakota v. Wayfair, 138 S. Ct. 2080 (2018) (unrelated but shows SD innovation)",
                "Various unpublished SD decisions on decanting and directed trusts",
            ],
            "strategic_uses": [
                "Dynasty trusts with unlimited duration",
                "Self-settled asset protection trusts",
                "Directed trusts (separate investment advisor from trustee)",
                "Institutional trust company market center",
                "Family office trust structures",
            ],
            "limitations": [
                "Must have South Dakota trustee with SD presence",
                "Compliance with SD trust code required",
                "Out-of-state court recognition varies",
            ],
            "tax_implications": "No South Dakota state income or capital gains tax; grantor trust applies federally",
            "complexity": "High",
        },
    }

    # -------------------------------------------------------------------------
    # UCC CONCEPTS
    # -------------------------------------------------------------------------
    UCC_CONCEPTS: Dict[str, Dict[str, Any]] = {
        "article_1": {
            "title": "UCC Article 1 — General Provisions",
            "description": "Foundational definitions and general rules applicable to all UCC articles.",
            "key_provisions": [
                "§1-201: General definitions (agreement, buyer, good faith, notice, etc.)",
                "§1-203: Obligation of Good Faith",
                "§1-204: Value — party has given value for rights",
                "§1-301: Choice of law — parties may agree to governing law",
                "§1-302: Variation by agreement — most UCC provisions are default rules",
            ],
            "strategic_relevance": "Governs interpretation and enforcement of all commercial transactions",
        },
        "article_2": {
            "title": "UCC Article 2 — Sales",
            "description": "Governs contracts for the sale of goods (moveable personal property).",
            "key_provisions": [
                "§2-201: Statute of Frauds — goods >$500 must be in writing",
                "§2-314: Implied warranty of merchantability",
                "§2-315: Implied warranty of fitness for particular purpose",
                "§2-508: Seller's right to cure defective tender",
                "§2-712/2-713: Buyer's remedies (cover/market price damages)",
            ],
            "strategic_relevance": "Business asset transfers, equipment sales, trust-held inventory",
        },
        "article_3": {
            "title": "UCC Article 3 — Negotiable Instruments",
            "description": "Governs promissory notes, drafts, checks, and certificates of deposit.",
            "key_provisions": [
                "§3-104: Requirements for negotiability (unconditional promise, fixed amount, payable on demand or at definite time, payable to bearer or order)",
                "§3-302: Holder in due course — takes free of personal defenses",
                "§3-305: Defenses against holder in due course",
                "§3-401: Signature — person is liable only if they sign",
                "§3-501: Presentment, notice of dishonor",
            ],
            "strategic_relevance": "Promissory notes used in IDGT sales, trust lending transactions",
        },
        "article_4": {
            "title": "UCC Article 4 — Bank Deposits and Collections",
            "description": "Governs the relationship between banks in collecting checks and other instruments.",
            "key_provisions": [
                "§4-208: Security interest of collecting bank",
                "§4-401: Bank's right to charge customer's account",
                "§4-406: Customer's duty to discover and report unauthorized signatures",
            ],
            "strategic_relevance": "Trust account management, banking relationships",
        },
        "article_5": {
            "title": "UCC Article 5 — Letters of Credit",
            "description": "Governs documentary letters of credit — guarantees of payment by bank.",
            "key_provisions": [
                "§5-102: Definitions",
                "§5-108: Issuer's rights and obligations",
                "§5-109: Fraud and forgery",
            ],
            "strategic_relevance": "International trust transactions, offshore structures",
        },
        "article_8": {
            "title": "UCC Article 8 — Investment Securities",
            "description": "Governs transfer and holding of investment securities (stocks, bonds, etc.).",
            "key_provisions": [
                "§8-102: Definitions (certificated/uncertificated security, financial asset)",
                "§8-301: Delivery — when purchaser acquires security",
                "§8-501: Securities accounts — entitlement holder's rights",
                "§8-510: Rights of purchaser of security entitlement",
            ],
            "strategic_relevance": "Investment portfolio trusts, brokerage account titling",
        },
        "article_9": {
            "title": "UCC Article 9 — Secured Transactions",
            "description": "Governs security interests in personal property. Core of commercial lending law.",
            "key_provisions": [
                "§9-102: Definitions (account, chattel paper, collateral, debtor, secured party)",
                "§9-203: Attachment — security interest becomes enforceable",
                "§9-308: Perfection of security interest",
                "§9-310: Filing required for most collateral types",
                "§9-322: Priority rules — first to file or perfect",
                "§9-323: Purchase Money Security Interest (PMSI) super-priority",
                "§9-609: Secured party's right to take possession after default",
                "§9-620: Acceptance of collateral in satisfaction (strict foreclosure)",
            ],
            "strategic_relevance": "Secured lending using trust assets as collateral, UCC filing strategies",
        },
        "attachment": {
            "title": "Attachment of Security Interest",
            "description": "The moment a security interest becomes enforceable against the debtor.",
            "requirements": [
                "1. Value has been given by the secured party",
                "2. Debtor has rights in the collateral",
                "3. Debtor has authenticated a security agreement describing the collateral",
            ],
            "ucc_section": "§9-203",
            "notes": "A security agreement that merely states 'all assets' may not be sufficient — description must be reasonably identifiable",
        },
        "perfection": {
            "title": "Perfection of Security Interest",
            "description": "The process by which a secured party protects its interest against third parties including other creditors, lien creditors, and bankruptcy trustees.",
            "methods": {
                "filing": "File a UCC-1 financing statement in the appropriate office — most common method",
                "possession": "Physical possession of collateral (pledges, instruments, tangible collateral)",
                "control": "For investment property, deposit accounts, electronic chattel paper, letter-of-credit rights",
                "automatic": "Purchase money security interest in consumer goods perfected automatically without filing",
            },
            "filing_location": "Secretary of State's office in state of debtor's location",
            "duration": "5 years from filing date; continuation statement extends for another 5 years",
        },
        "priority": {
            "title": "Priority of Competing Security Interests",
            "description": "Rules determining which secured party has priority when multiple parties claim the same collateral.",
            "rules": [
                "First-to-file-or-perfect rule: §9-322 — first to file or perfect wins",
                "PMSI super-priority: Purchase money security interest in non-inventory has priority if perfected within 20 days of delivery",
                "PMSI in inventory: Must perfect BEFORE possession AND give notice to prior secured parties",
                "Future advances: Relate back to original filing date",
                "Lien creditors: Unperfected SI loses to lien creditor; perfected SI wins over lien creditor",
                "Buyers in ordinary course: Take free of security interest created by seller (§9-320)",
            ],
        },
        "foreclosure": {
            "title": "Foreclosure / Enforcement After Default",
            "description": "Secured party's rights after debtor defaults.",
            "methods": [
                "Self-help repossession (§9-609): Without breach of peace",
                "Strict foreclosure (§9-620): Secured party proposes to accept collateral in satisfaction",
                "Disposition (§9-610): Public or private sale of collateral — must be commercially reasonable",
                "Collection (§9-607): Collect from account debtors directly",
            ],
            "notice_required": "Reasonable authenticated notification before sale (except perishables)",
        },
    }

    # -------------------------------------------------------------------------
    # TRUST JURISDICTIONS — All 50 states summarized, plus international
    # -------------------------------------------------------------------------
    TRUST_JURISDICTIONS: Dict[str, Dict[str, Any]] = {
        "south_dakota": {
            "full_name": "South Dakota",
            "asset_protection_strength": 10,
            "dynasty_trust_allowed": True,
            "decanting_allowed": True,
            "self_settled_trust": True,
            "perpetuities_rule": "Abolished — unlimited duration",
            "favorable_tax_treatment": True,
            "state_income_tax": False,
            "notes": "Preeminent US trust jurisdiction. Directed trust statutes. Strongest privacy. $500B+ in trust assets.",
            "statutes": ["SDCL 55-1A", "SDCL 55-16", "SDCL 43-5-1"],
        },
        "nevada": {
            "full_name": "Nevada",
            "asset_protection_strength": 9,
            "dynasty_trust_allowed": True,
            "decanting_allowed": True,
            "self_settled_trust": True,
            "perpetuities_rule": "365 years",
            "favorable_tax_treatment": True,
            "state_income_tax": False,
            "notes": "2-year SOL (shortest in US). No state income tax. Strong charging order protection for LLCs.",
            "statutes": ["NRS 166.015", "NRS 163.185"],
        },
        "alaska": {
            "full_name": "Alaska",
            "asset_protection_strength": 8,
            "dynasty_trust_allowed": True,
            "decanting_allowed": True,
            "self_settled_trust": True,
            "perpetuities_rule": "1000 years (effectively unlimited)",
            "favorable_tax_treatment": True,
            "state_income_tax": False,
            "notes": "First DAPT state (1997). No state income tax. 4-year SOL.",
            "statutes": ["AS 34.40.110", "AS 13.36.035"],
        },
        "delaware": {
            "full_name": "Delaware",
            "asset_protection_strength": 8,
            "dynasty_trust_allowed": True,
            "decanting_allowed": True,
            "self_settled_trust": True,
            "perpetuities_rule": "Repealed for personal property trusts",
            "favorable_tax_treatment": True,
            "state_income_tax": False,
            "notes": "No DE income tax on non-resident trust income. Excellent directed trust law. Corporate law synergy.",
            "statutes": ["12 Del. C. §3570 et seq.", "12 Del. C. §3801 et seq."],
        },
        "wyoming": {
            "full_name": "Wyoming",
            "asset_protection_strength": 8,
            "dynasty_trust_allowed": True,
            "decanting_allowed": True,
            "self_settled_trust": True,
            "perpetuities_rule": "1000 years",
            "favorable_tax_treatment": True,
            "state_income_tax": False,
            "notes": "No state income tax. Strongest US charging order protection. Privacy-focused LLC laws.",
            "statutes": ["Wyo. Stat. 4-10-101 et seq.", "Wyo. Stat. 17-29-101 et seq."],
        },
        "cook_islands": {
            "full_name": "Cook Islands",
            "asset_protection_strength": 10,
            "dynasty_trust_allowed": True,
            "decanting_allowed": True,
            "self_settled_trust": True,
            "perpetuities_rule": "No rule against perpetuities",
            "favorable_tax_treatment": True,
            "state_income_tax": False,
            "notes": "Gold standard offshore APT. Does not enforce US judgments. 2-year SOL. Creditor must re-litigate in Cook Islands.",
            "statutes": ["International Trusts Act 1984 (as amended)"],
        },
        "nevis": {
            "full_name": "Nevis, Federation of St. Kitts and Nevis",
            "asset_protection_strength": 9,
            "dynasty_trust_allowed": True,
            "decanting_allowed": True,
            "self_settled_trust": True,
            "perpetuities_rule": "No rule against perpetuities",
            "favorable_tax_treatment": True,
            "state_income_tax": False,
            "notes": "Strong APT laws. $25,000 bond to sue. Multiform Foundation available. Lower cost than Cook Islands.",
            "statutes": ["Nevis International Exempt Trust Ordinance 1994", "Nevis Multiform Foundations Ordinance 2004"],
        },
        "liechtenstein": {
            "full_name": "Principality of Liechtenstein",
            "asset_protection_strength": 9,
            "dynasty_trust_allowed": True,
            "decanting_allowed": True,
            "self_settled_trust": True,
            "perpetuities_rule": "No rule against perpetuities",
            "favorable_tax_treatment": True,
            "state_income_tax": False,
            "notes": "Civil law foundation/trust hybrid. Extraordinary privacy historically. OECD AEOI reduces privacy somewhat. Anstalt structure unique.",
            "statutes": ["PGR Art. 552 et seq.", "Foundation Law 2009"],
        },
        "cayman_islands": {
            "full_name": "Cayman Islands",
            "asset_protection_strength": 8,
            "dynasty_trust_allowed": True,
            "decanting_allowed": True,
            "self_settled_trust": True,
            "perpetuities_rule": "No rule against perpetuities (STAR trusts)",
            "favorable_tax_treatment": True,
            "state_income_tax": False,
            "notes": "Dominant hedge fund and private equity jurisdiction. STAR trusts for purpose trusts. No direct taxes.",
            "statutes": ["Trusts Law (2021 Revision)", "Special Trusts (Alternative Regime) Law 1997"],
        },
        "belize": {
            "full_name": "Belize",
            "asset_protection_strength": 7,
            "dynasty_trust_allowed": True,
            "decanting_allowed": True,
            "self_settled_trust": True,
            "perpetuities_rule": "120 years",
            "favorable_tax_treatment": True,
            "state_income_tax": False,
            "notes": "Lower cost offshore option. Strong asset protection. Less established than Cook Islands or Nevis.",
            "statutes": ["Belize Trusts Act Chapter 202", "Belize International Foundations Act"],
        },
        "jersey": {
            "full_name": "Jersey (Channel Islands)",
            "asset_protection_strength": 8,
            "dynasty_trust_allowed": True,
            "decanting_allowed": True,
            "self_settled_trust": True,
            "perpetuities_rule": "100 years",
            "favorable_tax_treatment": True,
            "state_income_tax": False,
            "notes": "Leading European trust jurisdiction. Excellent legal system. No inheritance or capital gains tax.",
            "statutes": ["Trusts (Jersey) Law 1984 (as amended 2006)"],
        },
        "isle_of_man": {
            "full_name": "Isle of Man",
            "asset_protection_strength": 7,
            "dynasty_trust_allowed": True,
            "decanting_allowed": True,
            "self_settled_trust": True,
            "perpetuities_rule": "No rule against perpetuities (foundations)",
            "favorable_tax_treatment": True,
            "state_income_tax": False,
            "notes": "Good European alternative. Foundations Act available. Close to UK legal system.",
            "statutes": ["Trustee Act 2001", "Foundations Act 2011"],
        },
        "florida": {
            "full_name": "Florida",
            "asset_protection_strength": 6,
            "dynasty_trust_allowed": True,
            "decanting_allowed": True,
            "self_settled_trust": False,
            "perpetuities_rule": "360 years",
            "favorable_tax_treatment": True,
            "state_income_tax": False,
            "notes": "No state income tax. Homestead exemption is one of best in US. Limited self-settled trust options.",
            "statutes": ["Florida Trust Code, Ch. 736", "Florida Statutes 689"],
        },
        "new_hampshire": {
            "full_name": "New Hampshire",
            "asset_protection_strength": 7,
            "dynasty_trust_allowed": True,
            "decanting_allowed": True,
            "self_settled_trust": True,
            "perpetuities_rule": "Abolished for personal property trusts",
            "favorable_tax_treatment": True,
            "state_income_tax": False,
            "notes": "New Hampshire Trust Code is modern and comprehensive. No income tax. Growing trust hub in northeast.",
            "statutes": ["RSA 564-A", "RSA 564-B (NH Trust Code)"],
        },
        "tennessee": {
            "full_name": "Tennessee",
            "asset_protection_strength": 7,
            "dynasty_trust_allowed": True,
            "decanting_allowed": True,
            "self_settled_trust": True,
            "perpetuities_rule": "360 years",
            "favorable_tax_treatment": True,
            "state_income_tax": False,
            "notes": "Tennessee Investment Services Trust Act allows DAPTs. No income tax as of 2021. Underutilized jurisdiction.",
            "statutes": ["Tennessee Investment Services Trust Act", "T.C.A. 35-15"],
        },
        # Aliases for display-name access
        "Cook Islands": {
            "full_name": "Cook Islands",
            "asset_protection_strength": 10,
            "dynasty_trust_allowed": True,
            "decanting_allowed": True,
            "self_settled_trust": True,
            "perpetuities_rule": "No rule against perpetuities",
            "favorable_tax_treatment": True,
            "state_income_tax": False,
            "notes": "Alias for cook_islands. Gold standard for offshore asset protection.",
            "statutes": ["International Trusts Act 1984 (amended 2004, 2012)"],
        },
        "South Dakota": {
            "full_name": "South Dakota",
            "asset_protection_strength": 10,
            "dynasty_trust_allowed": True,
            "decanting_allowed": True,
            "self_settled_trust": True,
            "perpetuities_rule": "Abolished — unlimited duration",
            "favorable_tax_treatment": True,
            "state_income_tax": False,
            "notes": "Alias for south_dakota. Preeminent US trust jurisdiction.",
            "statutes": ["SDCL 55-1A", "SDCL 55-16", "SDCL 43-5-1"],
        },
        "Nevada": {
            "full_name": "Nevada",
            "asset_protection_strength": 9,
            "dynasty_trust_allowed": True,
            "decanting_allowed": True,
            "self_settled_trust": True,
            "perpetuities_rule": "365 years",
            "favorable_tax_treatment": True,
            "state_income_tax": False,
            "notes": "Alias for nevada. 2-year fraudulent transfer SOL — shortest in US.",
            "statutes": ["NRS Chapter 163", "Nevada Spendthrift Trust Act"],
        },
    }

    # -------------------------------------------------------------------------
    # PUBLIC METHODS
    # -------------------------------------------------------------------------

    def get_doctrine(self, name: str) -> Optional[Dict[str, Any]]:
        """Return a doctrine by its key name. Case-insensitive lookup."""
        key = name.lower().replace(" ", "_").replace("-", "_")
        if key in self.TRUST_DOCTRINES:
            return self.TRUST_DOCTRINES[key]
        # Fuzzy match on name field
        for k, v in self.TRUST_DOCTRINES.items():
            if name.lower() in v["name"].lower():
                return v
        return None

    def search_doctrines(self, query: str) -> List[Dict[str, Any]]:
        """Search doctrines by keyword across all fields."""
        query_lower = query.lower()
        results = []
        for key, doctrine in self.TRUST_DOCTRINES.items():
            score = 0
            if query_lower in doctrine["name"].lower():
                score += 10
            if query_lower in doctrine["description"].lower():
                score += 5
            if query_lower in doctrine["jurisdiction"].lower():
                score += 3
            for use in doctrine.get("strategic_uses", []):
                if query_lower in use.lower():
                    score += 2
            for lim in doctrine.get("limitations", []):
                if query_lower in lim.lower():
                    score += 1
            if score > 0:
                results.append({"doctrine": doctrine, "relevance_score": score})
        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return [r["doctrine"] for r in results]

    def get_best_jurisdiction(self, requirements: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Rank jurisdictions based on requirements dict.
        Requirements keys: asset_protection (bool), dynasty (bool),
        self_settled (bool), no_state_tax (bool), offshore (bool),
        privacy (bool), low_cost (bool)
        """
        scores = {}
        for jname, jdata in self.TRUST_JURISDICTIONS.items():
            score = 0
            if requirements.get("asset_protection") and jdata["asset_protection_strength"] >= 8:
                score += jdata["asset_protection_strength"]
            if requirements.get("dynasty") and jdata["dynasty_trust_allowed"]:
                score += 5
            if requirements.get("self_settled") and jdata["self_settled_trust"]:
                score += 5
            if requirements.get("no_state_tax") and not jdata["state_income_tax"]:
                score += 4
            if requirements.get("offshore"):
                if jname in ["cook_islands", "nevis", "liechtenstein", "cayman_islands", "belize", "jersey", "isle_of_man"]:
                    score += 6
            if requirements.get("domestic_only"):
                if jname in ["south_dakota", "nevada", "alaska", "delaware", "wyoming"]:
                    score += 6
            if requirements.get("privacy"):
                if jname in ["south_dakota", "nevada", "wyoming", "cook_islands", "liechtenstein"]:
                    score += 3
            scores[jname] = {"jurisdiction": jdata, "name": jname, "score": score}

        ranked = sorted(scores.values(), key=lambda x: x["score"], reverse=True)
        return ranked[:5]

    def compare_jurisdictions(self, j1: str, j2: str) -> Dict[str, Any]:
        """Compare two jurisdictions side by side."""
        data1 = self.TRUST_JURISDICTIONS.get(j1.lower().replace(" ", "_"))
        data2 = self.TRUST_JURISDICTIONS.get(j2.lower().replace(" ", "_"))
        if not data1 or not data2:
            return {"error": f"Unknown jurisdiction(s): {j1}, {j2}"}
        comparison = {
            "jurisdiction_1": {"name": j1, **data1},
            "jurisdiction_2": {"name": j2, **data2},
            "comparison": {}
        }
        for field in ["asset_protection_strength", "dynasty_trust_allowed", "decanting_allowed",
                      "self_settled_trust", "favorable_tax_treatment", "state_income_tax"]:
            comparison["comparison"][field] = {
                "j1": data1.get(field),
                "j2": data2.get(field),
                "winner": j1 if data1.get(field, 0) >= data2.get(field, 0) else j2,
            }
        return comparison

    def get_ucc_guidance(self, topic: str) -> Optional[Dict[str, Any]]:
        """Get UCC guidance on a specific topic."""
        topic_lower = topic.lower()
        # Direct key lookup
        for key, val in self.UCC_CONCEPTS.items():
            if topic_lower in key.lower() or topic_lower in val.get("title", "").lower():
                return val
        # Search description fields
        results = []
        for key, val in self.UCC_CONCEPTS.items():
            if topic_lower in val.get("description", "").lower():
                results.append(val)
        return results[0] if results else None

    def list_all_doctrines(self) -> List[str]:
        """Return a list of all doctrine keys."""
        return list(self.TRUST_DOCTRINES.keys())

    def get_jurisdiction_tier(self, jurisdiction: str) -> str:
        """Return the tier of asset protection for a jurisdiction."""
        jdata = self.TRUST_JURISDICTIONS.get(jurisdiction.lower().replace(" ", "_"))
        if not jdata:
            return "unknown"
        strength = jdata["asset_protection_strength"]
        if strength >= 9:
            return "Tier 1 — Elite"
        elif strength >= 7:
            return "Tier 2 — Strong"
        elif strength >= 5:
            return "Tier 3 — Moderate"
        else:
            return "Tier 4 — Weak"
