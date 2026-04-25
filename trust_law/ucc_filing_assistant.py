"""
UCC Filing Assistant
====================
Prepares UCC-1 and UCC-3 forms, analyzes collateral descriptions,
checks priority rules, and provides state-by-state filing requirements.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime, date


@dataclass
class UCCForm:
    """A prepared UCC form."""
    form_type: str          # "UCC-1" or "UCC-3"
    debtor_name: str
    debtor_address: str
    secured_party_name: str
    secured_party_address: str
    collateral_description: str
    filing_state: str
    effective_date: str
    expiration_date: str    # 5 years from filing
    continuation_deadline: str  # 6 months before expiration
    form_text: str
    filing_instructions: List[str]
    estimated_fee: str


@dataclass
class CollateralAnalysis:
    """Analysis of a collateral description for a UCC filing."""
    original_description: str
    adequacy_score: float       # 0-100
    issues_found: List[str]
    improvements: List[str]
    collateral_types_identified: List[str]
    super_generic_warning: bool  # True if "all assets" used
    revised_description: str
    ucc_article_references: List[str]


@dataclass
class PriorityAnalysis:
    """Analysis of competing security interest priorities."""
    secured_party_1: str
    secured_party_2: str
    winner: str
    reasoning: str
    applicable_rule: str
    exceptions: List[str]
    risk_factors: List[str]


@dataclass
class FilingRequirements:
    """Filing requirements for a specific state."""
    state: str
    filing_office: str
    filing_fee: str
    online_filing_available: bool
    online_filing_url: str
    paper_form_required: bool
    standard_processing_time: str
    expedited_available: bool
    expedited_fee: str
    search_fee: str
    duration: str
    continuation_window: str
    indexing_method: str
    notes: List[str]


class UCCFilingAssistant:
    """
    Comprehensive UCC Article 9 filing preparation and analysis assistant.
    Covers all aspects of secured transactions from attachment to foreclosure.
    """

    # ── UCC Articles Reference ──────────────────────────────────────────────
    UCC_ARTICLES: Dict[str, Dict[str, Any]] = {
        "article_1": {
            "title": "Article 1 — General Provisions",
            "scope": "Definitions and general principles applicable to all UCC articles",
            "key_sections": {
                "1-201": "General definitions — 'agreement', 'good faith', 'notice', 'value', etc.",
                "1-203": "Obligation of good faith in performance and enforcement",
                "1-204": "Value — party gives value when receives a binding commitment, security interest, etc.",
                "1-301": "Choice of law — parties may select governing state law",
                "1-302": "Variation by agreement — most UCC rules are default, may be varied",
                "1-304": "Obligation of good faith — cannot be disclaimed",
                "1-305": "Remedies to be liberally administered",
            },
            "practitioner_notes": [
                "Good faith is objective: honest in fact AND observance of reasonable commercial standards",
                "Choice-of-law clauses in security agreements are generally effective",
                "'Value' is broad — includes promises to perform, preexisting claims",
            ],
        },
        "article_2": {
            "title": "Article 2 — Sales",
            "scope": "Contracts for sale of goods (moveable personal property)",
            "key_sections": {
                "2-201": "Statute of Frauds — contract for goods >$500 must be in writing",
                "2-202": "Parol evidence rule for written contracts",
                "2-314": "Implied warranty of merchantability",
                "2-315": "Implied warranty of fitness for particular purpose",
                "2-508": "Seller's right to cure defective tender",
                "2-609": "Right to adequate assurance of performance",
                "2-706": "Seller's remedy — resale",
                "2-712": "Buyer's remedy — cover",
                "2-714": "Buyer's damages for accepted goods",
            },
            "practitioner_notes": [
                "Article 2 governs 'goods' — tangible personal property that is moveable at time of identification",
                "Mixed goods/services contracts: predominant purpose test determines if UCC applies",
                "2019 Amendments to Article 2 not widely adopted — check your state",
            ],
        },
        "article_3": {
            "title": "Article 3 — Negotiable Instruments",
            "scope": "Promissory notes, drafts (including checks), and certificates of deposit",
            "key_sections": {
                "3-104": "Requirements for negotiability: unconditional promise, fixed amount, payable to bearer or order, payable on demand or definite time",
                "3-302": "Holder in due course — takes free of personal defenses",
                "3-305": "Real defenses vs. personal defenses",
                "3-306": "Claims to an instrument",
                "3-309": "Enforcement of lost, destroyed, or stolen instrument",
                "3-401": "Signature requirement — person only liable if they sign",
                "3-415": "Indorser liability",
                "3-501": "Presentment",
                "3-502": "Dishonor",
                "3-503": "Notice of dishonor",
                "3-601": "Discharge and payment",
            },
            "practitioner_notes": [
                "Trust promissory notes used in IDGT sales must meet negotiability requirements",
                "HDC status shields from defenses like fraud in the inducement",
                "Real defenses (infancy, duress, fraud in execution, discharge in bankruptcy) defeat HDC",
                "Interest-only demand notes commonly used in intrafamily loans — must be carefully documented",
            ],
        },
        "article_8": {
            "title": "Article 8 — Investment Securities",
            "scope": "Transfer and holding of investment securities (stocks, bonds, etc.)",
            "key_sections": {
                "8-102": "Definitions — 'certificated security', 'financial asset', 'security entitlement'",
                "8-106": "Control of investment property",
                "8-301": "Delivery of certificated security",
                "8-501": "Securities accounts",
                "8-503": "Property interest of entitlement holder",
                "8-510": "Rights of purchaser of security entitlement from entitlement holder",
            },
            "practitioner_notes": [
                "Article 8 works with Article 9 for perfection of security interests in investment property",
                "Control (§8-106) is generally the method for perfecting security interest in investment accounts",
                "Securities held in DTC (street name) require control agreement with broker",
                "Trust-owned brokerage accounts should have account control agreements for any pledged assets",
            ],
        },
        "article_9": {
            "title": "Article 9 — Secured Transactions",
            "scope": "Security interests in personal property and fixtures. Core of commercial lending law.",
            "key_sections": {
                "9-102": "Definitions — 'account', 'chattel paper', 'collateral', 'debtor', 'secured party', etc.",
                "9-109": "Scope — what Article 9 covers and what it excludes",
                "9-203": "Attachment of security interest — three requirements",
                "9-204": "After-acquired property and future advances",
                "9-301": "Where to file — generally debtor's location",
                "9-307": "Debtor's location — registered organization = state of organization",
                "9-308": "When security interest is perfected",
                "9-310": "Filing required for most personal property collateral",
                "9-313": "Perfection by possession",
                "9-314": "Perfection by control",
                "9-317": "Interests that take priority over unperfected security interest",
                "9-322": "Priority rules — first to file or perfect",
                "9-323": "Future advances priority",
                "9-324": "PMSI super-priority",
                "9-325": "Priority of security interests in transferred collateral",
                "9-331": "Priority of holder in due course",
                "9-501": "Filing office",
                "9-502": "Contents of financing statement",
                "9-503": "Name of debtor — exactness required",
                "9-504": "Indication of collateral",
                "9-509": "Persons entitled to file",
                "9-516": "What constitutes filing",
                "9-519": "Numbering, maintaining, and indexing records",
                "9-521": "Uniform form of financing statement",
                "9-601": "Rights after default",
                "9-609": "Secured party's right to possession after default",
                "9-610": "Disposition of collateral after default",
                "9-620": "Acceptance of collateral in satisfaction — strict foreclosure",
                "9-625": "Remedies for secured party's failure to comply",
            },
            "practitioner_notes": [
                "Debtor name must be EXACT legal name — slight errors can be seriously misleading",
                "'All assets' or 'all personal property' is sufficient for financing statement (§9-504) but not security agreement (§9-108)",
                "Individual debtor located at principal residence; registered org at state of organization",
                "PMSI in goods other than inventory — must perfect within 20 days of debtor taking possession",
                "PMSI in inventory — must perfect before debtor takes possession AND notify prior secured parties",
                "Continuation must be filed in last 6 months of 5-year period — not before, not after",
            ],
        },
    }

    # ── Perfection Methods ──────────────────────────────────────────────────
    PERFECTION_METHODS: Dict[str, Dict[str, Any]] = {
        "filing": {
            "name": "Filing (UCC-1 Financing Statement)",
            "description": "Most common method. File with Secretary of State in debtor's jurisdiction.",
            "applicable_collateral": [
                "Equipment", "Inventory", "Accounts and other rights to payment",
                "General intangibles (including intellectual property)", "Chattel paper",
                "Instruments (if not by possession)", "Documents",
                "Commercial tort claims (if covered by SA)",
                "Fixtures (file in real property records)", "Farm products",
            ],
            "ucc_section": "§9-310",
            "duration": "5 years; continue with UCC-3 within 6 months of expiration",
            "key_requirements": [
                "Debtor's exact legal name (§9-503)",
                "Secured party's name",
                "Collateral description (super-generic OK for FS)",
                "File in debtor's location (§9-301)",
            ],
        },
        "possession": {
            "name": "Perfection by Possession",
            "description": "Secured party takes physical possession of the collateral.",
            "applicable_collateral": [
                "Negotiable instruments", "Tangible chattel paper",
                "Money (exclusive perfection method)", "Certificated securities",
                "Goods", "Negotiable documents",
            ],
            "ucc_section": "§9-313",
            "duration": "Continuous — terminates when possession is surrendered",
            "key_requirements": [
                "Actual physical possession by secured party or its agent",
                "Possession must be exclusive",
                "Good faith required",
            ],
        },
        "control": {
            "name": "Perfection by Control",
            "description": "Secured party obtains control over the asset via agreement or dominion.",
            "applicable_collateral": [
                "Deposit accounts (exclusive method unless proceeds)",
                "Investment property (stocks, bonds, securities accounts)",
                "Electronic chattel paper",
                "Letter-of-credit rights",
                "Electronic documents of title",
            ],
            "ucc_section": "§9-314; §8-106; §9-104",
            "duration": "Continuous while control is maintained",
            "key_requirements": [
                "For deposit accounts: account control agreement with bank",
                "For investment property: control agreement with broker/DTC",
                "Secured party or its agent has power to instruct bank/broker",
            ],
        },
        "automatic": {
            "name": "Automatic Perfection (No Action Required)",
            "description": "Security interest is automatically perfected upon attachment in certain cases.",
            "applicable_collateral": [
                "Consumer goods (PMSI only — automatic, no filing needed)",
                "Assignment of beneficial interest in decedent's estate",
                "Assignment of claim for wages (limited cases)",
            ],
            "ucc_section": "§9-309",
            "duration": "Continuous",
            "key_requirements": [
                "PMSI: Secured party must have given value to enable debtor to acquire goods",
                "Consumer goods PMSI: goods bought for personal, family, or household use",
                "NOTE: Even though automatic, filing is still recommended for priority purposes",
            ],
        },
    }

    # ── Priority Rules ──────────────────────────────────────────────────────
    PRIORITY_RULES: Dict[str, Dict[str, Any]] = {
        "first_to_file_or_perfect": {
            "name": "First to File or Perfect Rule",
            "rule": "Between conflicting security interests in the same collateral, priority goes to the first to file a financing statement OR perfect, whichever occurs first.",
            "ucc_section": "§9-322(a)(1)",
            "example": "Secured Party A files UCC-1 on March 1. Secured Party B perfects by possession on February 1. B wins — B was first to perfect.",
            "exceptions": [
                "PMSI super-priority can trump first-to-file",
                "Buyers in ordinary course take free of security interests",
                "HDC takes free of unperfected security interest",
            ],
        },
        "pmsi_superpriority": {
            "name": "Purchase Money Security Interest (PMSI) Super-Priority",
            "rule": "A PMSI in goods (other than inventory or livestock) has priority over a conflicting security interest if the PMSI is perfected when the debtor receives possession or within 20 days thereafter.",
            "ucc_section": "§9-324(a)",
            "pmsi_definition": "A security interest in goods that is taken by the seller of the goods to secure all or part of their price, OR taken by a person who gives value to enable the debtor to acquire rights in the goods.",
            "special_rules": {
                "inventory_pmsi": "In inventory, PMSI holder must: (1) perfect before debtor takes possession, AND (2) send authenticated notice to each holder of conflicting SI who has filed a FS covering same inventory — §9-324(b)",
                "software_pmsi": "PMSI in software used in goods also applies",
                "dual_status_rule": "If proceeds used to acquire multiple items, PMSI applies only to goods purchased with those specific funds",
            },
            "example": "Lender gives Debtor $50,000 to buy equipment. Lender takes PMSI and perfects within 20 days. Prior lender with blanket lien loses priority in this equipment.",
        },
        "future_advances": {
            "name": "Future Advances Priority",
            "rule": "A security interest can secure future advances (obligations not yet incurred). Priority of SI for future advances relates back to the original filing date.",
            "ucc_section": "§9-323",
            "key_points": [
                "Dragnet clause in security agreement covers future advances",
                "Priority for future advances made within 45 days of lien creditor's creation is protected",
                "Priority for future advances committed before knowledge of lien creditor is protected",
            ],
        },
        "buyer_in_ordinary_course": {
            "name": "Buyer in Ordinary Course of Business",
            "rule": "A buyer in the ordinary course of business (BIOC) takes free of a security interest created by the seller, even if the security interest is perfected and the buyer knows of its existence.",
            "ucc_section": "§9-320(a)",
            "requirements": [
                "Buyer must be in ordinary course (not bulk sales)",
                "SI must be created by the seller (not a prior owner)",
                "Goods must be inventory of the seller",
            ],
        },
        "lien_creditor": {
            "name": "Security Interest vs. Lien Creditor",
            "rule": "An unperfected security interest is subordinate to a lien creditor. A perfected SI has priority over a lien creditor who becomes a lien creditor after perfection.",
            "ucc_section": "§9-317(a)(2)",
            "bankruptcy_note": "Bankruptcy trustee has the power of a hypothetical lien creditor as of the petition date — unperfected SI is avoidable in bankruptcy",
        },
    }

    # ── State Filing Requirements ───────────────────────────────────────────
    STATE_FILING_REQUIREMENTS: Dict[str, Dict[str, Any]] = {
        "delaware": {
            "filing_office": "Delaware Department of State, Division of Corporations",
            "filing_fee": "$25 (standard); $75 (expedited 24-hour); $200 (same-day)",
            "online_available": True,
            "online_url": "https://icis.corp.delaware.gov/Ecorp/EntitySearch/NameSearch.aspx",
            "processing_time": "3-5 business days standard",
            "search_fee": "$10 per debtor name",
            "notes": ["Delaware is common for registered organizations — file where organized, not where business operates"],
        },
        "nevada": {
            "filing_office": "Nevada Secretary of State",
            "filing_fee": "$25 base + $25 per additional debtor",
            "online_available": True,
            "online_url": "https://esos.nv.gov/",
            "processing_time": "1-2 business days",
            "search_fee": "$10",
            "notes": ["Nevada has no state income tax — common for holding entities"],
        },
        "wyoming": {
            "filing_office": "Wyoming Secretary of State",
            "filing_fee": "$30",
            "online_available": True,
            "online_url": "https://www.soswyo.gov/",
            "processing_time": "Same day online",
            "search_fee": "Free online search",
            "notes": ["Wyoming's privacy laws and charging order protection make it popular for LLCs"],
        },
        "south_dakota": {
            "filing_office": "South Dakota Secretary of State",
            "filing_fee": "$10",
            "online_available": True,
            "online_url": "https://sdsos.gov/",
            "processing_time": "1 business day",
            "search_fee": "$5",
            "notes": ["SD has some of the lowest filing fees in the US"],
        },
        "california": {
            "filing_office": "California Secretary of State, UCC Division",
            "filing_fee": "$20 paper; $14 online",
            "online_available": True,
            "online_url": "https://businesssearch.sos.ca.gov/",
            "processing_time": "5-10 business days",
            "search_fee": "$10",
            "notes": ["California has notoriously slow processing — file early", "Individual debtors: file where CA resident"],
        },
        "new_york": {
            "filing_office": "New York Department of State",
            "filing_fee": "$20 online; $40 paper",
            "online_available": True,
            "online_url": "https://www.dos.ny.gov/corps/ucc_online.asp",
            "processing_time": "Immediate online; 2-5 days paper",
            "search_fee": "$15",
            "notes": ["NY has additional local filing requirements for fixtures", "Farm products require county filing"],
        },
        "texas": {
            "filing_office": "Texas Secretary of State",
            "filing_fee": "$15 online; $25 paper",
            "online_available": True,
            "online_url": "https://www.sos.state.tx.us/ucc/",
            "processing_time": "Same day online",
            "search_fee": "$5",
            "notes": ["Texas has unlimited homestead exemption — important for real estate planning"],
        },
        "florida": {
            "filing_office": "Florida Department of State, Division of Corporations",
            "filing_fee": "$25",
            "online_available": True,
            "online_url": "https://efile.sunbiz.org/",
            "processing_time": "1-2 business days",
            "search_fee": "$10",
            "notes": ["Florida has unlimited homestead exemption for primary residence"],
        },
    }

    def prepare_ucc1_financing_statement(
        self,
        debtor: Dict[str, Any],
        secured_party: Dict[str, Any],
        collateral: Dict[str, Any],
    ) -> UCCForm:
        """
        Prepare a UCC-1 Financing Statement.

        Args:
            debtor: Dict with keys: name, address, city, state, zip, type (individual/entity), org_state
            secured_party: Dict with keys: name, address, city, state, zip
            collateral: Dict with keys: description, types (list), special_flags
        """
        from datetime import timedelta
        today = datetime.now()
        expiration = today.replace(year=today.year + 5)
        continuation_deadline = expiration.replace(
            month=expiration.month - 6 if expiration.month > 6 else expiration.month + 6,
            year=expiration.year if expiration.month > 6 else expiration.year - 1
        )

        debtor_name = debtor.get("name", "[DEBTOR NAME]")
        sp_name = secured_party.get("name", "[SECURED PARTY]")
        collateral_desc = collateral.get("description", "[COLLATERAL DESCRIPTION]")
        filing_state = debtor.get("org_state", debtor.get("state", "[STATE]"))

        form_text = f"""
UCC FINANCING STATEMENT — FORM UCC1
Filed with: Secretary of State, State of {filing_state}
Date of Filing: {today.strftime("%B %d, %Y")}
Effective Through: {expiration.strftime("%B %d, %Y")} (5 years)
MUST CONTINUE BY: {continuation_deadline.strftime("%B %d, %Y")}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. DEBTOR'S EXACT FULL LEGAL NAME:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Name:     {debtor_name}
   Address:  {debtor.get('address', '')}
   City:     {debtor.get('city', '')}
   State:    {debtor.get('state', '')}
   Zip:      {debtor.get('zip', '')}
   Type:     {debtor.get('type', 'Organization')}
   Org. ID:  {debtor.get('org_id', 'N/A')}
   Org. State: {debtor.get('org_state', 'N/A')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2. SECURED PARTY'S NAME:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Name:     {sp_name}
   Address:  {secured_party.get('address', '')}
   City:     {secured_party.get('city', '')}
   State:    {secured_party.get('state', '')}
   Zip:      {secured_party.get('zip', '')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
3. COLLATERAL DESCRIPTION:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{collateral_desc}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
4. ADDITIONAL INFORMATION:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Fixture Filing:    {collateral.get('fixture_filing', 'No')}
   Product of Collateral Covered: {collateral.get('products_covered', 'No')}
   Related Real Property: {collateral.get('real_property', 'N/A')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AUTHORIZED BY: {sp_name} (Secured Party)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        filing_instructions = [
            f"1. File this UCC-1 with the Secretary of State of {filing_state}",
            f"2. Filing fee: {self.STATE_FILING_REQUIREMENTS.get(filing_state.lower(), {}).get('filing_fee', 'Check with SOS')}",
            "3. IMPORTANT: Use EXACT legal name of debtor — not a trade name or abbreviation",
            f"4. This filing expires on {expiration.strftime('%B %d, %Y')}",
            f"5. File a UCC-3 Continuation NO EARLIER THAN {continuation_deadline.strftime('%B %d, %Y')} to extend",
            "6. Conduct a UCC search before filing to identify any prior security interests",
            "7. After filing, verify the filing was recorded correctly by obtaining a certified copy",
            "8. Provide a copy of the filed UCC-1 to the debtor as required",
        ]

        state_reqs = self.STATE_FILING_REQUIREMENTS.get(filing_state.lower(), {})
        fee = state_reqs.get("filing_fee", "$25 (estimate — verify with SOS)")

        return UCCForm(
            form_type="UCC-1",
            debtor_name=debtor_name,
            debtor_address=f"{debtor.get('address', '')}, {debtor.get('city', '')}, {debtor.get('state', '')} {debtor.get('zip', '')}",
            secured_party_name=sp_name,
            secured_party_address=f"{secured_party.get('address', '')}, {secured_party.get('city', '')}, {secured_party.get('state', '')}",
            collateral_description=collateral_desc,
            filing_state=filing_state,
            effective_date=today.strftime("%B %d, %Y"),
            expiration_date=expiration.strftime("%B %d, %Y"),
            continuation_deadline=continuation_deadline.strftime("%B %d, %Y"),
            form_text=form_text,
            filing_instructions=filing_instructions,
            estimated_fee=fee,
        )

    def prepare_ucc3_amendment(
        self,
        original_filing_number: str,
        amendment_type: str,
        changes: Dict[str, Any],
    ) -> UCCForm:
        """
        Prepare a UCC-3 Amendment form.

        Args:
            original_filing_number: Filing number of the original UCC-1
            amendment_type: "continuation", "termination", "amendment", "assignment"
            changes: Dict describing the changes (for amendment/assignment)
        """
        today = datetime.now()
        type_descriptions = {
            "continuation": "CONTINUATION — This filing extends the effectiveness of the original financing statement for an additional 5 years from the lapse date",
            "termination": "TERMINATION — This filing terminates the effectiveness of the financing statement. The secured party certifies that it no longer claims a security interest under the financing statement",
            "amendment": "AMENDMENT — This filing amends the original financing statement as described in the changes section below",
            "assignment": "ASSIGNMENT — The secured party assigns its rights under the financing statement to the assignee identified below",
        }

        changes_text = ""
        if amendment_type == "amendment":
            if changes.get("new_debtor_name"):
                changes_text += f"\nNew Debtor Name: {changes['new_debtor_name']}"
            if changes.get("new_collateral_description"):
                changes_text += f"\nNew/Additional Collateral:\n{changes['new_collateral_description']}"
            if changes.get("delete_collateral"):
                changes_text += f"\nCollateral to Delete:\n{changes['delete_collateral']}"
        elif amendment_type == "assignment":
            changes_text = f"\nAssignee Name: {changes.get('assignee_name', '[ASSIGNEE]')}\nAssignee Address: {changes.get('assignee_address', '[ADDRESS]')}"

        form_text = f"""
UCC FINANCING STATEMENT AMENDMENT — FORM UCC3
Original Filing Number: {original_filing_number}
Date of this Amendment: {today.strftime("%B %d, %Y")}
Amendment Type: {amendment_type.upper()}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AMENDMENT INFORMATION:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{type_descriptions.get(amendment_type.lower(), 'Amendment type not specified')}
{changes_text}

FILER INFORMATION:
Name: {changes.get('filer_name', '[AUTHORIZED FILER]')}
Role: {changes.get('filer_role', 'Secured Party')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IMPORTANT NOTICES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• For CONTINUATION: Must be filed within the SIX-MONTH WINDOW before lapse date
• For TERMINATION: Must be authorized by the secured party
• For AMENDMENT to add collateral: Relates back only to the date of the amendment (not original filing) for new collateral
• For ASSIGNMENT: Both old and new secured party information required
"""
        return UCCForm(
            form_type="UCC-3",
            debtor_name=changes.get("debtor_name", "[Original Debtor]"),
            debtor_address=changes.get("debtor_address", "[Original Address]"),
            secured_party_name=changes.get("secured_party_name", "[Original Secured Party]"),
            secured_party_address=changes.get("secured_party_address", ""),
            collateral_description=changes.get("new_collateral_description", "[See original filing]"),
            filing_state=changes.get("filing_state", "[Filing State]"),
            effective_date=today.strftime("%B %d, %Y"),
            expiration_date="[See original filing or continuation]",
            continuation_deadline="[Varies — see original filing]",
            form_text=form_text,
            filing_instructions=[
                f"File UCC-3 with same office where original UCC-1 (#{original_filing_number}) was filed",
                "Include original filing number on the UCC-3 form",
                "For continuation: file only within the 6-month window before lapse",
                "Obtain confirmation of filing and verify recording",
            ],
            estimated_fee="$10–$50 (varies by state; typically same as UCC-1 fee)",
        )

    def analyze_collateral_description(self, description: str) -> CollateralAnalysis:
        """Analyze a collateral description for adequacy and completeness."""
        desc_lower = description.lower()
        issues = []
        improvements = []
        collateral_types = []
        score = 100.0

        # Check for collateral types mentioned
        type_keywords = {
            "Equipment": ["equipment", "machinery", "tools", "fixtures"],
            "Inventory": ["inventory", "goods", "merchandise", "stock"],
            "Accounts Receivable": ["accounts", "receivable", "accounts receivable"],
            "General Intangibles": ["general intangibles", "intellectual property", "patents", "trademarks", "software"],
            "Deposit Accounts": ["deposit account", "bank account", "checking", "savings"],
            "Investment Property": ["investment property", "securities", "stocks", "bonds", "brokerage"],
            "Real Property (Fixture Filing)": ["fixture", "real property", "real estate"],
            "Chattel Paper": ["chattel paper", "lease", "installment sale"],
            "Instruments": ["instruments", "promissory note", "check", "draft"],
            "Proceeds": ["proceeds", "cash proceeds", "non-cash proceeds"],
        }

        for collateral_type, keywords in type_keywords.items():
            if any(kw in desc_lower for kw in keywords):
                collateral_types.append(collateral_type)

        # Super-generic check
        super_generic = False
        if "all assets" in desc_lower or "all personal property" in desc_lower:
            super_generic = True
            improvements.append("Consider supplementing 'all assets' with specific descriptions for key collateral")

        # Missing proceeds clause
        if "proceeds" not in desc_lower:
            issues.append("Missing proceeds language — add 'together with all proceeds thereof'")
            improvements.append("Add: 'together with all proceeds, products, replacements, additions, and accessions thereto'")
            score -= 10

        # Missing after-acquired property
        if "after-acquired" not in desc_lower and "hereafter acquired" not in desc_lower:
            issues.append("No after-acquired property clause")
            improvements.append("Add: 'whether now owned or hereafter acquired' to cover future collateral")
            score -= 10

        # Vague description
        if len(description) < 30 and not super_generic:
            issues.append("Description may be too vague — §9-108 requires reasonable identification")
            score -= 20

        # No type identification
        if not collateral_types and not super_generic:
            issues.append("Cannot identify collateral type — may be insufficient under §9-108")
            score -= 30

        # Build revised description
        base = description.strip()
        additions = []
        if "proceeds" not in desc_lower:
            additions.append("together with all proceeds, products, and accessions thereof")
        if "after-acquired" not in desc_lower and "hereafter" not in desc_lower:
            additions.append("whether now owned or hereafter acquired by Debtor")

        revised = base
        if additions:
            revised = base + ", " + "; ".join(additions)

        ucc_refs = ["§9-102 (Definitions)", "§9-108 (Sufficiency of description)", "§9-504 (Collateral description in financing statement)"]

        return CollateralAnalysis(
            original_description=description,
            adequacy_score=max(0.0, score),
            issues_found=issues,
            improvements=improvements,
            collateral_types_identified=collateral_types,
            super_generic_warning=super_generic,
            revised_description=revised,
            ucc_article_references=ucc_refs,
        )

    def check_priority_rules(
        self,
        secured_party1: Dict[str, Any],
        secured_party2: Dict[str, Any],
        filing_dates: Dict[str, Any],
    ) -> PriorityAnalysis:
        """
        Determine priority between two secured parties.

        Args:
            secured_party1, secured_party2: Dicts with: name, filed_date, perfected_date,
                                             is_pmsi (bool), collateral_type
            filing_dates: Dict with additional timing information
        """
        sp1_name = secured_party1.get("name", "Secured Party 1")
        sp2_name = secured_party2.get("name", "Secured Party 2")
        sp1_pmsi = secured_party1.get("is_pmsi", False)
        sp2_pmsi = secured_party2.get("is_pmsi", False)
        sp1_filed = secured_party1.get("filed_date")
        sp2_filed = secured_party2.get("filed_date")
        sp1_perfected = secured_party1.get("perfected_date", sp1_filed)
        sp2_perfected = secured_party2.get("perfected_date", sp2_filed)

        # PMSI trumps everything (with proper steps)
        if sp1_pmsi and not sp2_pmsi:
            collateral = secured_party1.get("collateral_type", "goods")
            days_window = 20
            return PriorityAnalysis(
                secured_party_1=sp1_name,
                secured_party_2=sp2_name,
                winner=sp1_name,
                reasoning=f"{sp1_name} holds a PMSI, which has super-priority under §9-324 if perfected within {days_window} days of debtor taking possession (or before, for inventory).",
                applicable_rule="UCC §9-324 — Purchase Money Security Interest Super-Priority",
                exceptions=[
                    "PMSI holder must have complied with timing requirements",
                    "For inventory PMSI: prior filing AND authenticated notice required",
                    "Must be a true PMSI — value must have enabled debtor to acquire the specific goods",
                ],
                risk_factors=[
                    "Verify PMSI status — dual-status rule may limit scope",
                    "Ensure perfection occurred within 20-day window",
                    "Inventory PMSI requires notification to prior lenders",
                ],
            )

        if sp2_pmsi and not sp1_pmsi:
            return PriorityAnalysis(
                secured_party_1=sp1_name,
                secured_party_2=sp2_name,
                winner=sp2_name,
                reasoning=f"{sp2_name} holds a PMSI with super-priority under §9-324.",
                applicable_rule="UCC §9-324 — PMSI Super-Priority",
                exceptions=["PMSI timing requirements must be satisfied"],
                risk_factors=["Verify PMSI compliance — inventory requires notice to existing lenders"],
            )

        # Both non-PMSI: first to file or perfect
        if sp1_filed and sp2_filed:
            try:
                # If dates are strings, parse them
                if isinstance(sp1_filed, str):
                    winner_date = sp1_filed
                    loser_date = sp2_filed
                    winner = sp1_name if sp1_filed <= sp2_filed else sp2_name
                    loser = sp2_name if winner == sp1_name else sp1_name
                else:
                    winner = sp1_name if sp1_filed <= sp2_filed else sp2_name
                    loser = sp2_name if winner == sp1_name else sp1_name
            except Exception:
                winner = sp1_name
                loser = sp2_name

            return PriorityAnalysis(
                secured_party_1=sp1_name,
                secured_party_2=sp2_name,
                winner=winner,
                reasoning=f"{winner} filed or perfected first. Under §9-322(a)(1), the first secured party to file a financing statement or perfect its security interest wins priority.",
                applicable_rule="UCC §9-322(a)(1) — First to File or Perfect Rule",
                exceptions=[
                    "PMSI super-priority can override first-to-file",
                    "Buyer in ordinary course of business takes free of SI created by seller",
                    "Holder in due course takes free of unperfected SI",
                    "Future advances priority is based on date of original filing",
                ],
                risk_factors=[
                    f"Ensure {winner}'s filing is in correct state for debtor's location",
                    "Verify exact debtor name — seriously misleading errors can invalidate",
                    "Check for any intervening lien creditors or buyers",
                ],
            )

        return PriorityAnalysis(
            secured_party_1=sp1_name,
            secured_party_2=sp2_name,
            winner="Indeterminate — insufficient information",
            reasoning="Unable to determine priority without filing/perfection dates and PMSI status.",
            applicable_rule="UCC §9-322 — Priority Rules",
            exceptions=[],
            risk_factors=["Obtain exact filing dates and perfection methods for both parties"],
        )

    def get_filing_requirements(self, state: str) -> FilingRequirements:
        """Get UCC filing requirements for a specific state."""
        state_key = state.lower().replace(" ", "_")
        state_data = self.STATE_FILING_REQUIREMENTS.get(state_key, {})

        return FilingRequirements(
            state=state,
            filing_office=state_data.get("filing_office", f"{state} Secretary of State — UCC Division"),
            filing_fee=state_data.get("filing_fee", "$20–$50 (verify current fee schedule)"),
            online_filing_available=state_data.get("online_available", True),
            online_filing_url=state_data.get("online_url", f"https://www.sos.{state_key}.gov/"),
            paper_form_required=state_data.get("paper_required", False),
            standard_processing_time=state_data.get("processing_time", "1-5 business days"),
            expedited_available=True,
            expedited_fee=state_data.get("expedited_fee", "Varies — check SOS website"),
            search_fee=state_data.get("search_fee", "$10–$25"),
            duration="5 years from filing date (UCC §9-515)",
            continuation_window="Must file UCC-3 Continuation in the 6-MONTH WINDOW before lapse date — not before",
            indexing_method="Debtor name — must be exact (§9-503, §9-519)",
            notes=state_data.get("notes", [
                f"Filing location: State where debtor is located (§9-301)",
                "Registered organization (corp/LLC): File in state of organization",
                "Individual: File in state of principal residence",
                "Exact debtor name critical — use name exactly as it appears on public records",
            ]),
        )
