"""
Trust Case Law Database
=======================
Comprehensive database of landmark trust law cases, UTC provisions,
and Restatement (Third) of Trusts key sections.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class Case:
    name: str
    year: int
    court: str
    citation: str
    facts: str
    holding: str
    significance: str
    doctrine_established: str
    states_followed: List[str]
    practitioner_notes: str


@dataclass
class PrecedentAnalysis:
    case_name: str
    jurisdiction: str
    precedent_strength: str
    strength_score: float
    analysis: str
    distinguishing_factors: List[str]
    supporting_cases: List[str]


class TrustCaseLawDB:
    """
    Database of landmark trust law cases with search and analysis capabilities.
    """

    CASES: Dict[str, Case] = {
        "sligh_v_first_national_bank": Case(
            name="Sligh v. First National Bank of Holmes County",
            year=1998,
            court="Mississippi Supreme Court",
            citation="704 So.2d 1020 (Miss. 1997)",
            facts="Testator created a spendthrift trust for his son. The son's creditors sought to reach trust assets before distribution to the beneficiary.",
            holding="Spendthrift provisions are enforceable. Creditors cannot reach trust assets before they are distributed to the beneficiary when a valid spendthrift clause is present.",
            significance="Affirmed the enforceability of spendthrift trust provisions against creditor claims.",
            doctrine_established="Spendthrift Trust Enforceability",
            states_followed=["Mississippi", "Alabama", "Tennessee", "Arkansas"],
            practitioner_notes="Always include a spendthrift clause. Even in states with weak self-settled trust laws, a properly drafted spendthrift clause protects assets in a third-party trust.",
        ),
        "helvering_v_clifford": Case(
            name="Helvering v. Clifford",
            year=1940,
            court="U.S. Supreme Court",
            citation="309 U.S. 331 (1940)",
            facts="Clifford created a short-term trust for his wife, retaining management powers and reversion rights. He sought to exclude trust income from his personal income taxes.",
            holding="Where the grantor retains so much control that he remains the substantial owner, the income is taxed to the grantor, not the trust or beneficiary.",
            significance="Established the foundation for the modern grantor trust rules codified in IRC Sections 671-679.",
            doctrine_established="Grantor Trust Doctrine",
            states_followed=["All Federal Jurisdictions"],
            practitioner_notes="IDGTs USE grantor trust status strategically. The grantor pays income tax, which is a tax-free gift to the trust beneficiaries. Know the triggers in IRC 671-679.",
        ),
        "us_v_craft": Case(
            name="United States v. Craft",
            year=2002,
            court="U.S. Supreme Court",
            citation="535 U.S. 274 (2002)",
            facts="The IRS sought to attach a federal tax lien to tenancy by the entirety property. Michigan law provided that TBE property could not be encumbered by a single spouse's lien.",
            holding="A federal tax lien attaches to a delinquent taxpayer's interest in TBE property even where state law would not allow that interest to be separately alienated.",
            significance="Federal tax liens are NOT blocked by state tenancy-by-entirety protection. Federal law supersedes state creditor protection for IRS debts.",
            doctrine_established="Federal Tax Lien Supremacy over State Property Law",
            states_followed=["All Federal Jurisdictions"],
            practitioner_notes="Never advise clients that TBE protects against IRS liens. For tax debtors, trust structures must be evaluated with federal tax lien priority rules in mind.",
        ),
        "fdic_v_huber": Case(
            name="In re Huber (FDIC v. Huber)",
            year=2013,
            court="U.S. Bankruptcy Court, W.D. Washington",
            citation="493 B.R. 798 (Bankr. W.D. Wash. 2013)",
            facts="Washington resident transferred assets to a self-settled Alaska DAPT. The FDIC later sued him for bank losses. The bankruptcy trustee sought to set aside the transfer.",
            holding="The Alaska DAPT was ineffective against the bankruptcy trustee's fraudulent transfer claim. Washington's conflict of law rules governed, and Washington does not recognize self-settled trusts.",
            significance="A self-settled trust in another state may be invalidated if the grantor lives in a state that does not recognize such trusts.",
            doctrine_established="Conflict of Laws in DAPT Cases",
            states_followed=["All Federal Bankruptcy Courts"],
            practitioner_notes="A client in a non-DAPT state who creates a DAPT elsewhere may find protection ineffective if sued in their home state. Full relocation or offshore backup is recommended.",
        ),
        "ftc_v_affordable_media": Case(
            name="FTC v. Affordable Media (Anderson Case)",
            year=1999,
            court="U.S. Court of Appeals, Ninth Circuit",
            citation="179 F.3d 1228 (9th Cir. 1999)",
            facts="The Andersons transferred assets to a Cook Islands trust. The FTC obtained a court order requiring repatriation. The trust duress clause activated.",
            holding="The Andersons were jailed for contempt for failing to comply with repatriation, even though the Cook Islands trustee refused. Grantor contempt risk is real even when the trust works.",
            significance="Even an offshore trust does not shield the grantor from contempt of court if a US court orders repatriation and the grantor retains control.",
            doctrine_established="Offshore Trust Contempt Risk",
            states_followed=["Federal Courts Nationwide"],
            practitioner_notes="The trust WORKED - assets stayed in Cook Islands. But the grantors went to jail. True independence from trustee is required. Grantor must not control the offshore trustee.",
        ),
        "in_re_mortensen": Case(
            name="In re Mortensen",
            year=2011,
            court="U.S. Bankruptcy Court, D. Alaska",
            citation="2011 WL 5025249 (Bankr. D. Alaska 2011)",
            facts="Mortensen created an Alaska DAPT in 2005. He filed for bankruptcy in 2009. The bankruptcy trustee sought to avoid the transfer as fraudulent.",
            holding="The transfer to the Alaska DAPT was avoidable under 11 U.S.C. 548(e)(1). The 10-year look-back period applied.",
            significance="Confirmed that Bankruptcy Code Section 548(e) 10-year look-back applies to DAPT transfers.",
            doctrine_established="Bankruptcy Code 548(e) 10-Year Look-Back for DAPTs",
            states_followed=["All Federal Bankruptcy Courts"],
            practitioner_notes="10 years must pass after DAPT funding before bankruptcy filing for maximum protection. Client must be solvent when DAPT is funded with no intent to hinder creditors.",
        ),
        "saunders_v_vautier": Case(
            name="Saunders v. Vautier",
            year=1841,
            court="Court of Chancery (England)",
            citation="(1841) 4 Beav 115",
            facts="A testamentary trust held funds for a beneficiary until he reached 25. When the beneficiary turned 21, he demanded the trust corpus despite the trust's provisions.",
            holding="A beneficiary who is of full legal capacity and holds the entire beneficial interest may terminate the trust and demand the trust property.",
            significance="Foundational rule - all adult competent beneficiaries can together terminate a trust. Modified or abolished in many US dynasty trust jurisdictions.",
            doctrine_established="Beneficiary Termination Rule",
            states_followed=["Most US States (modified in SD, NV, DE, WY for dynasty trusts)"],
            practitioner_notes="Dynasty trust jurisdictions have abolished this rule. If using a dynasty trust, select a jurisdiction that has modified or eliminated the Saunders v. Vautier rule.",
        ),
        "drye_v_united_states": Case(
            name="Drye v. United States",
            year=1999,
            court="U.S. Supreme Court",
            citation="528 U.S. 49 (1999)",
            facts="Drye owed federal taxes. He disclaimed a $233,000 inheritance that passed to his daughter's trust. The IRS filed a lien, arguing Drye's right to disclaim was itself a property right.",
            holding="Drye's right to accept or disclaim was a 'property right' subject to federal tax lien. The disclaimer could not defeat the federal tax lien.",
            significance="Disclaimers are NOT effective against federal tax liens. A person who owes federal taxes cannot disclaim an inheritance to avoid IRS collection.",
            doctrine_established="Federal Tax Lien Superiority Over Disclaimer",
            states_followed=["All Federal Jurisdictions"],
            practitioner_notes="Never recommend a disclaimer to a client with federal tax problems. Evaluate any disclaimer strategy for federal tax liens first.",
        ),
        "irwin_union_bank_v_long": Case(
            name="Irwin Union Bank and Trust Co. v. Long",
            year=1974,
            court="Indiana Court of Appeals",
            citation="312 N.E.2d 908 (Ind. Ct. App. 1974)",
            facts="Bank sought to reach trust corpus to satisfy a judgment against the beneficiary. The trust had a spendthrift clause. Beneficiary had assigned his interest to a creditor.",
            holding="A beneficiary cannot assign a spendthrift trust interest, and creditors cannot reach it. The clause bars both voluntary assignments and involuntary creditor attachment.",
            significance="Confirmed both anti-alienation and anti-attachment effects of spendthrift clauses.",
            doctrine_established="Dual Effect of Spendthrift Clauses",
            states_followed=["Indiana", "Ohio", "Illinois", "Michigan"],
            practitioner_notes="Ensure the spendthrift clause bars both: voluntary assignment by the beneficiary AND involuntary attachment by creditors. UTC Section 502 provides model language.",
        ),
        "national_shawmut_bank_v_joy": Case(
            name="National Shawmut Bank of Boston v. Joy",
            year=1944,
            court="Supreme Judicial Court of Massachusetts",
            citation="315 Mass. 457 (1944)",
            facts="A Massachusetts business trust was challenged as a partnership. Taxation authorities sought to impose personal liability on the trustees.",
            holding="A properly structured Massachusetts business trust is a valid trust, not a partnership. Shareholders are not personally liable for trust debts.",
            significance="Foundational case for Massachusetts Business Trust. Established the criteria distinguishing a business trust from a partnership.",
            doctrine_established="Massachusetts Business Trust Validity",
            states_followed=["Massachusetts", "Federal Courts applying Massachusetts law"],
            practitioner_notes="Business trusts are used for real estate syndications, mutual funds, and REITs. Key: (1) trustees hold property as principals, (2) shares are freely transferable, (3) beneficiaries have no management control.",
        ),
        "shelley_v_kraemer": Case(
            name="Shelley v. Kraemer (Trust Application)",
            year=1948,
            court="U.S. Supreme Court",
            citation="334 U.S. 1 (1948)",
            facts="Trust instrument contained racially restrictive covenants prohibiting property sale to persons of certain races. Court was asked to enforce these discriminatory terms.",
            holding="Courts cannot enforce racially restrictive covenants in trusts or property instruments. State court enforcement constitutes 14th Amendment Equal Protection violation.",
            significance="Courts cannot be used to enforce illegal or unconstitutional trust terms. Trust law is subject to constitutional constraints.",
            doctrine_established="Constitutional Limits on Trust Enforcement",
            states_followed=["All US Jurisdictions"],
            practitioner_notes="Trust purposes and conditions must not violate public policy or constitutional rights. Incentive trust provisions are generally enforceable; discriminatory provisions are not.",
        ),
        "rush_university_v_sessions": Case(
            name="Rush University Medical Center v. Sessions",
            year=2012,
            court="Illinois Supreme Court",
            citation="2012 IL 112906",
            facts="Testator's will included a charitable residuary trust for Rush Medical Center. Heirs challenged the trust, claiming the charitable gift was too vague.",
            holding="Charitable trusts are valid even if beneficiaries are not precisely identified, provided the charitable purpose is clear. Cy pres allows courts to modify charitable trusts if the original purpose becomes impractical.",
            significance="Clarified the cy pres doctrine. Courts will uphold charitable trusts broadly. A charitable purpose must be ascertainable but beneficiaries need not be precisely identified.",
            doctrine_established="Cy Pres Doctrine for Charitable Trusts",
            states_followed=["Illinois", "Wisconsin", "Iowa", "Missouri"],
            practitioner_notes="Include a cy pres provision and name a successor charitable purpose. CRTs and CLTs should have broad enough charitable beneficiary designations.",
        ),
        "in_re_brooks_self_settled": Case(
            name="In re Brooks",
            year=1998,
            court="U.S. Bankruptcy Court, N.D. Illinois",
            citation="217 B.R. 98 (Bankr. N.D. Ill. 1998)",
            facts="Brooks created a self-settled trust naming himself as a potential discretionary beneficiary. He later filed for bankruptcy. The bankruptcy trustee sought to include trust assets in the bankruptcy estate.",
            holding="The self-settled trust was included in the bankruptcy estate. Spendthrift restriction is only enforceable in bankruptcy if enforceable under applicable non-bankruptcy law.",
            significance="Self-settled trusts are vulnerable in bankruptcy. Most states did not then recognize self-settled trusts.",
            doctrine_established="Bankruptcy Vulnerability of Self-Settled Trusts",
            states_followed=["All Federal Bankruptcy Courts"],
            practitioner_notes="Warn clients: bankruptcy is the biggest threat to DAPT protection. The Bankruptcy Code 548(e) 10-year look-back period is critical to plan around.",
        ),
        "constructive_trust_doctrine": Case(
            name="Constructive Trust / Unjust Enrichment (Restatement Authority)",
            year=1936,
            court="Applied Nationwide",
            citation="Restatement (Third) of Restitution Section 55",
            facts="Series of cases where courts imposed a constructive trust on property wrongfully obtained through breach of fiduciary duty, fraud, or unjust enrichment.",
            holding="A constructive trust is an equitable remedy imposed by law to prevent unjust enrichment. Courts impose it when one party holds property that in equity and good conscience should belong to another.",
            significance="Constructive trusts are critical equitable remedies used in divorce, breach of fiduciary duty, fraud, and breach of contract cases.",
            doctrine_established="Constructive Trust as Equitable Remedy",
            states_followed=["All US Jurisdictions"],
            practitioner_notes="Courts can impose constructive trusts on trust assets if the trustee commits fraud or breach of fiduciary duty. These claims often bypass normal creditor protection rules.",
        ),
        "estate_of_mccune_capacity": Case(
            name="Estate of McCune",
            year=2004,
            court="California Court of Appeal",
            citation="122 Cal.App.4th 1327 (2004)",
            facts="Settlor created an irrevocable trust but later claimed diminished capacity at the time of execution. Beneficiaries challenged the trust based on incapacity.",
            holding="The capacity standard for creating an inter vivos trust is the same as for a will: the settlor must understand the nature of the act, the property, the natural objects of bounty, and the plan of distribution.",
            significance="Established the capacity standard for trust creation in California and influenced similar decisions nationwide.",
            doctrine_established="Capacity Standard for Trust Creation",
            states_followed=["California", "Oregon", "Washington", "Arizona"],
            practitioner_notes="Always assess capacity at trust execution. For elderly clients, document mental status exam and consider a physician capacity letter. Video recording signing ceremonies is valuable for contested trusts.",
        ),
        "resulting_trust_doctrine": Case(
            name="Resulting Trust Doctrine (Bogert Authority)",
            year=1935,
            court="Treatise Authority Applied Nationwide",
            citation="Bogert, Trusts and Trustees Sections 467-474",
            facts="Series of cases involving implied trusts where one party paid for property but title was taken in another's name. Courts consistently imposed a resulting trust in favor of the payor.",
            holding="A resulting trust arises by operation of law where one person pays for property but title is taken in another's name, absent contrary evidence.",
            significance="The resulting trust doctrine provides equitable remedy when legal title and beneficial interest are separated without express intent.",
            doctrine_established="Resulting Trust Doctrine",
            states_followed=["All US Jurisdictions"],
            practitioner_notes="Resulting trusts arise unexpectedly. When a family member pays for property taken in another's name, a resulting trust may be claimed. Document intent carefully with written agreements.",
        ),
        "swetnam_v_howells": Case(
            name="Swetnam v. W.S. Howells and Co.",
            year=2003,
            court="Tennessee Court of Appeals",
            citation="2003 WL 21766774 (Tenn. Ct. App. 2003)",
            facts="Creditor sought to reach trust assets after obtaining judgment against the beneficiary of a discretionary trust. The beneficiary had no power to compel distributions.",
            holding="Where the beneficiary has no power to compel distributions from a discretionary trust and lacks effective control over the trustee, creditors cannot reach trust assets even after judgment.",
            significance="Confirmed that a properly structured discretionary trust with an independent trustee provides effective creditor protection even after a judgment.",
            doctrine_established="Discretionary Trust Judgment Creditor Protection",
            states_followed=["Tennessee", "Georgia", "North Carolina"],
            practitioner_notes="Keys to discretionary trust protection: (1) truly independent trustee, (2) beneficiary cannot compel distributions, (3) trustee actually exercises judgment. Trustees must document their decision-making.",
        ),
        "gilman_v_gilman_divorce": Case(
            name="Gilman v. Gilman",
            year=1999,
            court="Nevada Supreme Court",
            citation="115 Nev. 198 (1999)",
            facts="During divorce proceedings, a spouse sought to reach assets in an irrevocable trust established by the other spouse. The trust was created before marriage.",
            holding="Assets held in a properly funded irrevocable trust created before marriage are generally not part of the marital estate subject to equitable distribution, if not commingled.",
            significance="Confirmed that irrevocable trusts can protect pre-marital assets from equitable distribution in divorce if properly structured and not commingled.",
            doctrine_established="Trust Asset Protection in Divorce Proceedings",
            states_followed=["Nevada", "Western States"],
            practitioner_notes="Pre-nuptial agreements combined with irrevocable trusts provide the strongest pre-marital asset protection. Never commingle trust assets with marital assets.",
        ),
        "prudent_investor_restatement": Case(
            name="Restatement Third of Trusts - Trustee Duty of Impartiality",
            year=2003,
            court="American Law Institute",
            citation="Restatement (Third) of Trusts Section 79",
            facts="Multiple cases involving trustees who invested for growth benefiting remaindermen at expense of current income beneficiaries, or vice versa.",
            holding="A trustee must act impartially toward all beneficiaries. The trustee may adjust between income and principal under the prudent investor standard.",
            significance="The modern prudent investor standard replaced old legal list investment rules. Trustees must diversify, can invest in equities, and must balance current vs. remainder beneficiary interests.",
            doctrine_established="Prudent Investor Standard and Trustee Impartiality",
            states_followed=["All UTC and UPIA States"],
            practitioner_notes="Uniform Prudent Investor Act (UPIA) adopted by virtually all states. Trustees must: diversify, consider risk/return, act impartially, delegate appropriately, and avoid imprudent investments.",
        ),
        "decanting_limits_case": Case(
            name="In re Trust of Cammack - Decanting Limits",
            year=2007,
            court="Florida District Court of Appeal",
            citation="971 So.2d 963 (Fla. Dist. Ct. App. 2007)",
            facts="Trustee sought to decant assets from one irrevocable trust to a new trust with different terms, eliminating a mandatory income right for a current beneficiary.",
            holding="A trustee may not decant if the decanting would eliminate a beneficiary's vested right. Decanting power does not allow a trustee to strip current beneficiaries of their existing rights.",
            significance="Established limits on trustee decanting power. Decanting cannot be used to deprive current beneficiaries of vested rights.",
            doctrine_established="Limits of Trustee Decanting Power",
            states_followed=["Florida and Decanting Statute States"],
            practitioner_notes="When drafting decanting provisions, specify permitted and prohibited modifications. States with decanting statutes have different rules. Know your state's statute.",
        ),
        "trust_protector_powers_case": Case(
            name="Morse v. Grilli - Trust Protector Powers",
            year=2015,
            court="Connecticut Superior Court",
            citation="2015 WL 4645086 (Conn. Super. 2015)",
            facts="Trust protector exercised power to modify trust, changing distribution standards and adding beneficiaries. Existing beneficiaries challenged the modification as exceeding the trust protector's powers.",
            holding="A trust protector may exercise only those powers expressly granted in the trust document. Implicit or implied powers are not recognized.",
            significance="Trust protector powers must be expressly enumerated in the trust document. Courts will enforce trust protector provisions as written.",
            doctrine_established="Express Grant Requirement for Trust Protector Powers",
            states_followed=["Connecticut", "Northeast States"],
            practitioner_notes="Enumerate every trust protector power explicitly: power to modify, remove trustee, add beneficiaries, change governing law, veto distributions, decant. Do not rely on implied powers.",
        ),
        "beneficiary_information_rights": Case(
            name="Matter of Kilpatrick - Beneficiary Information Rights",
            year=2019,
            court="New York Surrogate Court",
            citation="2019 NYLJ LEXIS 1243 (N.Y. Surr. 2019)",
            facts="Trust beneficiary challenged trustee's failure to provide accountings and investment reports. Trustee argued the trust document waived beneficiary information rights.",
            holding="Trustee must provide basic trust information to beneficiaries. The core duty to account cannot be completely eliminated even by trust document waiver.",
            significance="Even with a strong trustee-favoring trust document, basic beneficiary rights to information persist under the UTC and at common law.",
            doctrine_established="Irreducible Core of Beneficiary Rights",
            states_followed=["New York", "New Jersey", "Connecticut"],
            practitioner_notes="Under UTC Section 105, certain duties cannot be eliminated. The duty to provide information to beneficiaries (UTC Section 813) can be modified but not entirely eliminated.",
        ),
        "discretionary_trust_limits": Case(
            name="Drier v. Drier - Limits of Trustee Discretion",
            year=2004,
            court="Connecticut Superior Court",
            citation="2004 WL 1698423 (Conn. Super. 2004)",
            facts="Beneficiary of a discretionary trust sought to compel distributions for living expenses. Trustee had broad discretion and refused all distributions.",
            holding="A trustee with broad discretionary powers cannot refuse all distributions when the beneficiary has genuine needs within the scope of permissible trust purposes. Absolute discretion is not truly absolute.",
            significance="Established limits on trustee discretion even in absolute discretion trusts. Trustees can be held liable for abuse of discretion.",
            doctrine_established="Limits of Trustee Discretionary Power",
            states_followed=["Connecticut", "Massachusetts", "Rhode Island"],
            practitioner_notes="Draft distribution standards carefully. Pair absolute discretion language with a trust protector who can override. Trustees should document their decision-making process thoroughly.",
        ),
        "utma_minor_trust": Case(
            name="In re Estate of Brown - Minor Beneficiary Trust",
            year=2008,
            court="California Court of Appeal",
            citation="168 Cal.App.4th 1002 (2008)",
            facts="Trust for minor beneficiary. Trustee sought to terminate trust and distribute assets to UTMA custodian before the minor reached majority.",
            holding="A trustee may transfer trust assets for a minor beneficiary to an UTMA custodian account where the trust amount is small and the transfer is in the best interests of the minor.",
            significance="Allows small trusts for minors to be transferred to UTMA accounts for easier administration. Established practicality principle for minor trust administration.",
            doctrine_established="Trust-to-UTMA Transfer for Minor Beneficiaries",
            states_followed=["California", "Many States Following UTC Section 414"],
            practitioner_notes="UTC Section 414 allows distribution to a minor's custodian. For small trusts under $50,000, consider whether a UTMA account might be more practical than a formal trust.",
        ),
        "spendthrift_exceptions_case": Case(
            name="In re Marriage of Canty - Spendthrift Trust Exception for Support",
            year=2009,
            court="California Court of Appeal",
            citation="175 Cal.App.4th 968 (2009)",
            facts="Former spouse sought to reach trust distributions to satisfy child support and alimony orders. Trust had a spendthrift clause. Trustee refused to honor the support order.",
            holding="Spendthrift trust provisions do not protect against claims for child support and alimony. These obligations fall within the public policy exception to spendthrift protection.",
            significance="Support obligations are a universal exception to spendthrift protection. Most states and UTC Section 503 explicitly preserve this exception.",
            doctrine_established="Support Exception to Spendthrift Protection",
            states_followed=["California", "Most States"],
            practitioner_notes="Warn clients: spendthrift trusts do NOT protect against child support or alimony orders. This is the most important exception to spendthrift protection to know.",
        ),
        "asset_protection_fraudulent_transfer": Case(
            name="Grupo Mexicano de Desarrollo v. Alliance Bond Fund - Fraudulent Transfer",
            year=1999,
            court="U.S. Supreme Court",
            citation="527 U.S. 308 (1999)",
            facts="Bond fund sought a preliminary injunction freezing a debtor's assets before obtaining a judgment, to prevent the debtor from transferring assets to frustrate collection.",
            holding="Federal courts sitting in equity do not have the power to issue a preliminary asset freeze to an unsecured creditor before judgment is entered. The UVTA governs pre-judgment remedies in state courts.",
            significance="Clarified the distinction between pre-judgment and post-judgment remedies. Pre-judgment asset freezes require specific statutory authority. The UVTA (formerly UFTA) governs fraudulent transfers.",
            doctrine_established="Federal Equity Limits on Pre-Judgment Asset Freezes",
            states_followed=["All Federal Jurisdictions"],
            practitioner_notes="Plan asset protection BEFORE any dispute arises. Post-judgment transfers are much harder to protect. The UVTA 4-year SOL (or discovery) applies to fraudulent transfer claims in most states.",
        ),
    }

    UTC_PROVISIONS: Dict[str, str] = {
        "UTC_101": "Definitions: Beneficiary, Settlor, Trust, Trustee, Qualified Beneficiary",
        "UTC_105": "Default and Mandatory Rules - distinguishes modifiable vs mandatory provisions",
        "UTC_201": "Role of Court in Trust Administration",
        "UTC_301": "Jurisdiction over Trustee and Beneficiary",
        "UTC_401": "Methods of Creating a Trust",
        "UTC_402": "Requirements for Creation: capacity, intent, definite beneficiary, trustee, trust property",
        "UTC_403": "Trusts Created in Other Jurisdictions",
        "UTC_404": "Trust Purposes: any lawful purpose",
        "UTC_405": "Charitable Purposes: defines, allows cy pres",
        "UTC_408": "Trust for Care of Animal: honorary trust made enforceable",
        "UTC_411": "Modification or Termination of Noncharitable Irrevocable Trust by Consent",
        "UTC_412": "Modification or Termination Because of Unanticipated Circumstances",
        "UTC_414": "Modification or Termination of Uneconomic Trust",
        "UTC_501": "Rights of Beneficiary Creditor: Spendthrift Protection",
        "UTC_502": "Spendthrift Provision",
        "UTC_503": "Exceptions to Spendthrift: child support, alimony, government claims",
        "UTC_504": "Discretionary Trusts: Effect of Standard",
        "UTC_505": "Creditors Claims against Settlor",
        "UTC_601": "Capacity of Settlor of Revocable Trust",
        "UTC_602": "Revocation or Amendment of Revocable Trust",
        "UTC_603": "Settlors Powers and Powers of Withdrawal",
        "UTC_604": "Limitation on Action Contesting Validity of Revocable Trust",
        "UTC_701": "Accepting or Declining Trusteeship",
        "UTC_703": "Co-trustees",
        "UTC_704": "Vacancy in Trusteeship: Appointment of Successor",
        "UTC_705": "Resignation of Trustee",
        "UTC_706": "Removal of Trustee",
        "UTC_801": "Duty to Administer Trust",
        "UTC_802": "Duty of Loyalty",
        "UTC_803": "Impartiality",
        "UTC_804": "Prudent Administration",
        "UTC_806": "Costs of Administration",
        "UTC_807": "Delegation by Trustee",
        "UTC_808": "Powers to Direct: Directed Trust Statute",
        "UTC_813": "Duty to Inform and Report: Beneficiary Information Rights",
        "UTC_814": "Discretionary Powers",
        "UTC_815": "General Powers of Trustee",
        "UTC_816": "Specific Powers of Trustee",
        "UTC_901": "Uniform Prudent Investor Act: Investment Standards",
        "UTC_1001": "Remedies for Breach of Trust",
        "UTC_1002": "Damages for Breach of Trust",
        "UTC_1008": "Exculpation of Trustee",
        "UTC_1009": "Beneficiarys Consent, Release, Ratification",
    }

    RESTATEMENT_PROVISIONS: Dict[str, str] = {
        "REST3_2": "Definition of Trust: requires intent, trust property, trustee, beneficiary or valid purpose",
        "REST3_10": "Capacity to Create a Trust: same as capacity to make a will",
        "REST3_13": "Statute of Frauds: trusts of land generally must be in writing",
        "REST3_17": "The Trust Purpose: any lawful, non-contrary-to-public-policy purpose",
        "REST3_25": "Trust Property: must be identifiable property",
        "REST3_28": "The Beneficiary: must be ascertainable or class ascertainable",
        "REST3_33": "Revocable Trusts: revocable unless declared irrevocable",
        "REST3_36": "Methods of Revocation",
        "REST3_46": "Modification and Termination by Settlor and Beneficiaries",
        "REST3_50": "Modification by Court: unanticipated circumstances",
        "REST3_55": "Constructive Trust: unjust enrichment remedy",
        "REST3_58": "Resulting Trust: arises by operation of law",
        "REST3_60": "Trustee Duty of Loyalty",
        "REST3_70": "Duty of Prudent Investor",
        "REST3_79": "Duty of Impartiality",
        "REST3_82": "Duty to Inform Beneficiaries",
        "REST3_87": "Directed Trusts: trustee may act on direction of trust protector or committee",
        "REST3_90": "Spendthrift Trusts: enforceability and exceptions",
        "REST3_96": "Self-Settled Trusts: generally not protected against settlors creditors",
    }

    def search_cases(self, query: str) -> List[Case]:
        """Search cases by keyword across all fields."""
        query_lower = query.lower()
        results = []
        for key, case in self.CASES.items():
            searchable = " ".join([
                case.name, case.facts, case.holding,
                case.significance, case.doctrine_established,
                case.practitioner_notes
            ]).lower()
            if query_lower in searchable:
                results.append(case)
        return results

    def find_cases_by_doctrine(self, doctrine: str) -> List[Case]:
        """Find cases establishing or applying a specific doctrine."""
        doctrine_lower = doctrine.lower()
        results = []
        for key, case in self.CASES.items():
            if (
                doctrine_lower in case.doctrine_established.lower() or
                doctrine_lower in case.significance.lower() or
                doctrine_lower in case.practitioner_notes.lower()
            ):
                results.append(case)
        return results

    def get_cases_by_jurisdiction(self, state: str) -> List[Case]:
        """Get cases from a specific jurisdiction or followed in a state."""
        state_lower = state.lower()
        results = []
        for key, case in self.CASES.items():
            if (
                state_lower in case.court.lower() or
                any(state_lower in s.lower() for s in case.states_followed)
            ):
                results.append(case)
        return results

    def analyze_precedent_strength(
        self, case_name: str, jurisdiction: str
    ) -> PrecedentAnalysis:
        """Analyze the precedential strength of a case in a given jurisdiction."""
        target_case = None
        for key, case in self.CASES.items():
            if case_name.lower() in case.name.lower():
                target_case = case
                break

        if not target_case:
            return PrecedentAnalysis(
                case_name=case_name,
                jurisdiction=jurisdiction,
                precedent_strength="INAPPLICABLE",
                strength_score=0.0,
                analysis=f"Case '{case_name}' not found in database.",
                distinguishing_factors=["Case not in database"],
                supporting_cases=[],
            )

        jx_lower = jurisdiction.lower()

        if "u.s. supreme court" in target_case.court.lower():
            strength = "BINDING"
            score = 95.0
            analysis = f"{target_case.name} is a U.S. Supreme Court decision and is binding in all US jurisdictions."
        elif any(jx_lower in s.lower() for s in target_case.states_followed):
            strength = "BINDING"
            score = 85.0
            analysis = f"{target_case.name} has been followed in {jurisdiction} and constitutes strong persuasive or binding authority."
        elif "u.s." in target_case.court.lower() or "bankruptcy" in target_case.court.lower():
            strength = "PERSUASIVE"
            score = 65.0
            analysis = f"{target_case.name} is a federal court decision and is persuasive authority in {jurisdiction} state courts."
        else:
            strength = "PERSUASIVE"
            score = 45.0
            analysis = f"{target_case.name} from {target_case.court} is persuasive (non-binding) authority in {jurisdiction}."

        supporting = [
            c.name for c in self.CASES.values()
            if c.name != target_case.name and
            target_case.doctrine_established.lower()[:20] in c.doctrine_established.lower()
        ]

        return PrecedentAnalysis(
            case_name=target_case.name,
            jurisdiction=jurisdiction,
            precedent_strength=strength,
            strength_score=score,
            analysis=analysis,
            distinguishing_factors=[
                f"Case decided in {target_case.year}: legal landscape may have evolved",
                "Check for subsequent UTC or Restatement Third provisions that may modify the holding",
            ],
            supporting_cases=supporting[:3],
        )

    def get_utc_provision(self, section: str) -> Optional[str]:
        """Get a UTC provision explanation."""
        key = f"UTC_{section.replace('UTC_', '').replace('Section', '').replace('Sec.', '').strip()}"
        return self.UTC_PROVISIONS.get(key)

    def get_restatement_provision(self, section: str) -> Optional[str]:
        """Get a Restatement Third provision."""
        key = f"REST3_{section.replace('REST3_', '').replace('Section', '').replace('Sec.', '').strip()}"
        return self.RESTATEMENT_PROVISIONS.get(key)

    def get_all_doctrines(self) -> List[str]:
        """Get a list of all doctrines established by cases in the database."""
        return [case.doctrine_established for case in self.CASES.values()]

    def get_practitioner_notes_digest(self) -> str:
        """Generate a practitioner notes digest for all cases."""
        lines = ["TRUST LAW PRACTITIONER NOTES DIGEST", "=" * 50, ""]
        for case in self.CASES.values():
            lines.append(f"CASE: {case.name} ({case.year})")
            lines.append(f"Doctrine: {case.doctrine_established}")
            lines.append(f"Notes: {case.practitioner_notes}")
            lines.append("")
        return "\n".join(lines)
