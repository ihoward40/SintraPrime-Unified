"""
Practice Areas Module — SintraPrime Legal Intelligence System

Defines all practice areas, legal matter classification, strategy templates,
and applicable legal standards for the SintraPrime AI law firm platform.

Philosophy: One for All and All for One — replace the entire firm.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class PracticeArea(Enum):
    """All major legal practice areas handled by SintraPrime."""

    CONTRACT_LAW = "contract_law"
    CRIMINAL_DEFENSE = "criminal_defense"
    FAMILY_LAW = "family_law"
    IMMIGRATION = "immigration"
    BANKRUPTCY = "bankruptcy"
    INTELLECTUAL_PROPERTY = "intellectual_property"
    REAL_ESTATE = "real_estate"
    EMPLOYMENT_LAW = "employment_law"
    CIVIL_RIGHTS = "civil_rights"
    PERSONAL_INJURY = "personal_injury"
    CORPORATE_LAW = "corporate_law"
    TAX_LAW = "tax_law"
    ENVIRONMENTAL_LAW = "environmental_law"
    CONSTITUTIONAL_LAW = "constitutional_law"
    INTERNATIONAL_LAW = "international_law"
    ADMINISTRATIVE_LAW = "administrative_law"
    PROBATE_ESTATES = "probate_estates"
    SECURITIES_LAW = "securities_law"
    HEALTHCARE_LAW = "healthcare_law"
    CYBERSECURITY_LAW = "cybersecurity_law"


class StandardOfProof(Enum):
    """Legal standards of proof across practice areas."""

    BEYOND_REASONABLE_DOUBT = "beyond_reasonable_doubt"
    CLEAR_AND_CONVINCING = "clear_and_convincing"
    PREPONDERANCE_OF_EVIDENCE = "preponderance_of_evidence"
    PROBABLE_CAUSE = "probable_cause"
    REASONABLE_SUSPICION = "reasonable_suspicion"
    SUBSTANTIAL_EVIDENCE = "substantial_evidence"


class CasePriority(Enum):
    """Priority levels for legal matters."""

    CRITICAL = "critical"   # Immediate liberty/safety at stake
    HIGH = "high"           # Significant rights/assets at risk
    MEDIUM = "medium"       # Important but not immediate
    LOW = "low"             # Routine matters


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class LegalMatter:
    """
    Represents a classified legal matter with all relevant metadata.

    Example:
        >>> matter = LegalMatter(
        ...     description="My employer fired me because of my race",
        ...     practice_area=PracticeArea.EMPLOYMENT_LAW,
        ...     confidence=0.92,
        ...     keywords_matched=["fired", "race", "employer"],
        ...     priority=CasePriority.HIGH,
        ...     federal_jurisdiction=True,
        ...     state_jurisdiction=True
        ... )
    """

    description: str
    practice_area: PracticeArea
    confidence: float  # 0.0 – 1.0
    keywords_matched: List[str] = field(default_factory=list)
    secondary_areas: List[PracticeArea] = field(default_factory=list)
    priority: CasePriority = CasePriority.MEDIUM
    federal_jurisdiction: bool = False
    state_jurisdiction: bool = True
    estimated_complexity: str = "moderate"  # simple | moderate | complex | very_complex
    notes: str = ""


@dataclass
class StrategyTemplate:
    """
    High-level litigation/matter strategy for a practice area.

    Example:
        >>> template = StrategyTemplate(
        ...     practice_area=PracticeArea.CONTRACT_LAW,
        ...     initial_steps=["Obtain all contracts", "Identify breach"],
        ...     key_legal_theories=["Breach of contract", "Anticipatory repudiation"],
        ...     common_defenses=["Statute of frauds", "Waiver"],
        ...     discovery_priorities=["Contract documents", "Communications"],
        ...     typical_timeline_months=(6, 18),
        ...     settlement_likelihood=0.75
        ... )
    """

    practice_area: PracticeArea
    initial_steps: List[str]
    key_legal_theories: List[str]
    common_defenses: List[str]
    discovery_priorities: List[str]
    typical_timeline_months: Tuple[int, int]
    settlement_likelihood: float  # 0.0 – 1.0
    key_statutes: List[str] = field(default_factory=list)
    key_cases: List[str] = field(default_factory=list)
    tips: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Legal Standards
# ---------------------------------------------------------------------------

LEGAL_STANDARDS: Dict[PracticeArea, Dict[str, str]] = {
    PracticeArea.CRIMINAL_DEFENSE: {
        "standard_of_proof": StandardOfProof.BEYOND_REASONABLE_DOUBT.value,
        "description": "Prosecution must prove every element beyond a reasonable doubt. "
                       "This is the highest standard in the law.",
        "jury_instruction": "A reasonable doubt is a doubt based upon reason and common sense.",
        "constitutional_basis": "Due Process Clause, 5th and 14th Amendments; In re Winship, 397 U.S. 358 (1970)",
    },
    PracticeArea.CIVIL_RIGHTS: {
        "standard_of_proof": StandardOfProof.PREPONDERANCE_OF_EVIDENCE.value,
        "description": "Plaintiff must show it is more likely than not (>50%) that the violation occurred.",
        "heightened_standard": "Clear and convincing for punitive damages in some circuits.",
        "constitutional_basis": "42 U.S.C. § 1983; 42 U.S.C. § 1988",
    },
    PracticeArea.CONTRACT_LAW: {
        "standard_of_proof": StandardOfProof.PREPONDERANCE_OF_EVIDENCE.value,
        "description": "Elements of breach must be shown by preponderance.",
        "reformation_standard": "Clear and convincing evidence required to reform a written contract.",
        "fraud_standard": "Clear and convincing in many jurisdictions.",
    },
    PracticeArea.FAMILY_LAW: {
        "standard_of_proof": StandardOfProof.PREPONDERANCE_OF_EVIDENCE.value,
        "termination_of_parental_rights": StandardOfProof.CLEAR_AND_CONVINCING.value,
        "description": "General family matters use preponderance; TPR requires clear and convincing (Santosky v. Kramer).",
        "key_case": "Santosky v. Kramer, 455 U.S. 745 (1982)",
    },
    PracticeArea.IMMIGRATION: {
        "standard_of_proof": StandardOfProof.CLEAR_AND_CONVINCING.value,
        "removal_standard": "Government must prove alienage; alien must prove relief by clear and convincing or preponderance.",
        "asylum_standard": "Well-founded fear = 10% chance of persecution (INS v. Cardoza-Fonseca).",
        "key_case": "INS v. Cardoza-Fonseca, 480 U.S. 421 (1987)",
    },
    PracticeArea.BANKRUPTCY: {
        "standard_of_proof": StandardOfProof.PREPONDERANCE_OF_EVIDENCE.value,
        "fraud_exception": StandardOfProof.CLEAR_AND_CONVINCING.value,
        "description": "Dischargeability disputes use preponderance; fraud-based non-dischargeability may require clear and convincing.",
    },
    PracticeArea.INTELLECTUAL_PROPERTY: {
        "standard_of_proof": StandardOfProof.PREPONDERANCE_OF_EVIDENCE.value,
        "patent_invalidity": "Clear and convincing evidence to invalidate an issued patent (Microsoft v. i4i, 2011).",
        "key_case": "Microsoft Corp. v. i4i Ltd. Partnership, 564 U.S. 91 (2011)",
    },
    PracticeArea.REAL_ESTATE: {
        "standard_of_proof": StandardOfProof.PREPONDERANCE_OF_EVIDENCE.value,
        "adverse_possession": "Clear and convincing in many states.",
        "description": "General real estate disputes use preponderance.",
    },
    PracticeArea.EMPLOYMENT_LAW: {
        "standard_of_proof": StandardOfProof.PREPONDERANCE_OF_EVIDENCE.value,
        "description": "McDonnell Douglas burden-shifting framework for discrimination claims.",
        "key_case": "McDonnell Douglas Corp. v. Green, 411 U.S. 792 (1973)",
    },
    PracticeArea.PERSONAL_INJURY: {
        "standard_of_proof": StandardOfProof.PREPONDERANCE_OF_EVIDENCE.value,
        "description": "Plaintiff must prove duty, breach, causation, damages by preponderance.",
    },
    PracticeArea.CORPORATE_LAW: {
        "standard_of_proof": StandardOfProof.PREPONDERANCE_OF_EVIDENCE.value,
        "fiduciary_duty": "Business judgment rule presumption; entire fairness standard for interested transactions.",
        "description": "Delaware courts apply entire fairness or business judgment rule depending on transaction type.",
    },
    PracticeArea.TAX_LAW: {
        "standard_of_proof": StandardOfProof.PREPONDERANCE_OF_EVIDENCE.value,
        "description": "Taxpayer generally bears burden of proof; shifts to IRS in some cases under IRC § 7491.",
        "fraud_standard": "Clear and convincing evidence for civil tax fraud.",
    },
    PracticeArea.ENVIRONMENTAL_LAW: {
        "standard_of_proof": StandardOfProof.PREPONDERANCE_OF_EVIDENCE.value,
        "description": "CERCLA liability is strict; causation must be shown by preponderance.",
    },
    PracticeArea.CONSTITUTIONAL_LAW: {
        "standard_of_proof": StandardOfProof.PREPONDERANCE_OF_EVIDENCE.value,
        "heightened_scrutiny": "Strict scrutiny (compelling interest + narrow tailoring) for fundamental rights.",
        "description": "Standard varies by right; strict, intermediate, or rational basis scrutiny.",
    },
    PracticeArea.INTERNATIONAL_LAW: {
        "standard_of_proof": StandardOfProof.PREPONDERANCE_OF_EVIDENCE.value,
        "description": "ICC: beyond reasonable doubt; ICJ: balance of probabilities; ICSID: preponderance.",
    },
    PracticeArea.ADMINISTRATIVE_LAW: {
        "standard_of_proof": StandardOfProof.SUBSTANTIAL_EVIDENCE.value,
        "description": "Agency decisions reviewed under substantial evidence standard (5 U.S.C. § 706).",
        "arbitrary_capricious": "Courts may set aside arbitrary, capricious agency action.",
    },
    PracticeArea.PROBATE_ESTATES: {
        "standard_of_proof": StandardOfProof.CLEAR_AND_CONVINCING.value,
        "description": "Contesting a will typically requires clear and convincing evidence of undue influence or lack of capacity.",
    },
    PracticeArea.SECURITIES_LAW: {
        "standard_of_proof": StandardOfProof.PREPONDERANCE_OF_EVIDENCE.value,
        "scienter": "Fraudulent intent (scienter) must be pled with particularity under PSLRA.",
        "key_statute": "15 U.S.C. § 78u-4 (PSLRA)",
    },
    PracticeArea.HEALTHCARE_LAW: {
        "standard_of_proof": StandardOfProof.PREPONDERANCE_OF_EVIDENCE.value,
        "description": "Medical malpractice requires expert testimony; False Claims Act uses preponderance.",
    },
    PracticeArea.CYBERSECURITY_LAW: {
        "standard_of_proof": StandardOfProof.PREPONDERANCE_OF_EVIDENCE.value,
        "description": "Data breach liability typically uses preponderance; criminal computer fraud uses beyond reasonable doubt.",
        "key_statute": "Computer Fraud and Abuse Act, 18 U.S.C. § 1030",
    },
}

# ---------------------------------------------------------------------------
# Statutes of Limitations
# ---------------------------------------------------------------------------

STATUTES_OF_LIMITATIONS: Dict[PracticeArea, Dict[str, str]] = {
    PracticeArea.CONTRACT_LAW: {
        "federal_written": "No specific federal SOL; most contracts governed by state law.",
        "state_written_range": "3-10 years (UCC Art 2 sales: 4 years; CA: 4 yr written, 2 yr oral)",
        "ucc_article_2": "4 years (UCC § 2-725)",
        "note": "SOL begins at time of breach.",
    },
    PracticeArea.CRIMINAL_DEFENSE: {
        "federal_general": "5 years (18 U.S.C. § 3282)",
        "federal_capital": "No statute of limitations",
        "federal_terrorism": "No SOL for certain terrorism offenses",
        "state_felony_range": "Varies: 3-7 years; murder typically no SOL",
        "state_misdemeanor_range": "1-3 years",
    },
    PracticeArea.CIVIL_RIGHTS: {
        "section_1983": "Borrowed from state personal injury SOL (typically 2-3 years)",
        "title_vii": "180 days to file EEOC charge (300 days in deferral states)",
        "ada": "180/300 days for EEOC charge; 90 days after right-to-sue to file",
        "equal_pay_act": "2 years; 3 years for willful violations",
        "section_1981": "4 years (28 U.S.C. § 1658) for post-Civil Rights Act claims",
    },
    PracticeArea.PERSONAL_INJURY: {
        "federal_ftca": "2 years to file administrative claim; 6 months after denial to sue",
        "state_range": "1-6 years (most states: 2-3 years)",
        "discovery_rule": "SOL may toll until plaintiff discovers injury",
        "medical_malpractice": "1-3 years depending on state; discovery rule often applies",
    },
    PracticeArea.EMPLOYMENT_LAW: {
        "flsa_wage": "2 years; 3 years for willful violations",
        "title_vii_eeoc": "180/300 days to file EEOC charge; 90 days after right-to-sue",
        "nlra_unfair_labor": "6 months (29 U.S.C. § 160(b))",
        "adea": "180/300 days for EEOC charge",
        "fmla": "2 years; 3 years willful",
    },
    PracticeArea.INTELLECTUAL_PROPERTY: {
        "copyright": "3 years from discovery of infringement (17 U.S.C. § 507(b))",
        "patent": "6 years for damages; no SOL on injunction (35 U.S.C. § 286)",
        "trademark": "Laches doctrine applies; no statutory SOL under Lanham Act",
        "trade_secret_dtsa": "3 years from discovery (18 U.S.C. § 1836(d))",
    },
    PracticeArea.REAL_ESTATE: {
        "federal_claims": "Varies by specific claim",
        "adverse_possession_range": "5-21 years depending on state",
        "quiet_title": "Varies; often no SOL if in possession",
        "breach_of_deed_covenants": "Varies by covenant type and state",
    },
    PracticeArea.SECURITIES_LAW: {
        "section_10b_rule_10b5": "2 years from discovery; 5 years from violation (28 U.S.C. § 1658(b))",
        "section_11_12": "1 year from discovery; 3 years from offering (15 U.S.C. § 77m)",
        "sec_enforcement": "5 years for civil penalties (28 U.S.C. § 2462)",
    },
    PracticeArea.TAX_LAW: {
        "irs_assessment": "3 years from filing (IRC § 6501(a))",
        "irs_substantial_omission": "6 years if >25% income omitted",
        "irs_fraud": "No SOL for fraudulent returns",
        "refund_claim": "Earlier of 3 years from filing or 2 years from payment (IRC § 6511)",
        "criminal_tax": "6 years (26 U.S.C. § 6531)",
    },
    PracticeArea.ENVIRONMENTAL_LAW: {
        "cercla_cost_recovery": "3 years for removal; 6 years for remedial action",
        "clean_water_act": "5 years (28 U.S.C. § 2462)",
        "rcra_citizen_suit": "No specific SOL",
        "state_range": "Varies; discovery rule often tolls SOL",
    },
    PracticeArea.IMMIGRATION: {
        "removal_proceedings": "No SOL; deportable aliens may be removed at any time",
        "naturalization": "N/A (eligibility-based not SOL-based)",
        "visa_overstay": "Accrual begins day after authorized stay expires",
    },
    PracticeArea.BANKRUPTCY: {
        "preference_action": "2 years from order for relief (11 U.S.C. § 546(a))",
        "fraudulent_transfer": "2 years from order for relief",
        "discharge_complaint": "60 days after first date set for creditors meeting (FRBP 4007)",
    },
    PracticeArea.FAMILY_LAW: {
        "divorce": "No SOL; can file at any time",
        "child_support_arrears": "10-20 years depending on state",
        "paternity": "Varies; often until child reaches majority + several years",
    },
    PracticeArea.ADMINISTRATIVE_LAW: {
        "apa_review": "6 years (28 U.S.C. § 2401(a)) unless otherwise specified",
        "merit_systems_protection": "30 days from effective date of action",
        "foia": "No SOL to file request; 6 years to sue under APA",
    },
    PracticeArea.PROBATE_ESTATES: {
        "will_contest": "Varies: 30 days to several years after probate opened",
        "creditor_claims": "Typically 3-6 months after notice to creditors published",
        "state_range": "Highly state-specific",
    },
    PracticeArea.HEALTHCARE_LAW: {
        "medical_malpractice": "1-3 years depending on state; discovery rule",
        "false_claims_act": "6 years from violation; 3 years from government knowledge (max 10 years)",
        "hipaa_complaint": "180 days from discovery of violation",
    },
    PracticeArea.CYBERSECURITY_LAW: {
        "cfaa_civil": "2 years from discovery (18 U.S.C. § 1030(g))",
        "cfaa_criminal": "5 years for most offenses; 10 years repeat",
        "state_data_breach": "Varies; most states 2-3 years",
    },
    PracticeArea.CORPORATE_LAW: {
        "breach_fiduciary": "Varies by state; Delaware: 3 years laches analysis",
        "derivative_suit": "State specific; demand futility must be pled",
        "securities_fraud": "See securities law SOL",
    },
    PracticeArea.CONSTITUTIONAL_LAW: {
        "section_1983": "State personal injury SOL applies",
        "habeas_corpus": "1 year from final judgment under AEDPA (28 U.S.C. § 2244(d))",
        "bivens": "Borrowed from state personal injury SOL",
    },
    PracticeArea.INTERNATIONAL_LAW: {
        "icsid_arbitration": "Per treaty/arbitration agreement",
        "alien_tort_statute": "10 years (28 U.S.C. § 1350 note)",
        "fsia": "Varies by exception; general rule 6 years",
    },
}

# Module-level alias for backward compatibility
statutes_of_limitations = STATUTES_OF_LIMITATIONS

# ---------------------------------------------------------------------------
# Keyword Maps for Classification
# ---------------------------------------------------------------------------

KEYWORD_SCORES: Dict[PracticeArea, List[str]] = {
    PracticeArea.CONTRACT_LAW: [
        "contract", "breach", "agreement", "terms", "clause", "nda", "non-disclosure",
        "vendor", "service agreement", "warranty", "indemnification", "arbitration clause",
        "confidentiality", "liquidated damages", "force majeure", "consideration",
        "offer", "acceptance", "promissory", "unenforceable", "void", "voidable",
        "implied warranty", "express warranty", "material breach", "anticipatory",
    ],
    PracticeArea.CRIMINAL_DEFENSE: [
        "arrested", "charged", "indicted", "felony", "misdemeanor", "prison", "jail",
        "probation", "parole", "sentence", "plea", "guilty", "criminal", "defendant",
        "prosecution", "grand jury", "bail", "arraignment", "suppression", "miranda",
        "fourth amendment search", "drug charge", "dui", "assault", "battery",
        "theft", "robbery", "fraud", "murder", "manslaughter", "conspiracy",
    ],
    PracticeArea.FAMILY_LAW: [
        "divorce", "custody", "child support", "alimony", "spousal support",
        "marriage", "separation", "prenuptial", "postnuptial", "domestic violence",
        "restraining order", "visitation", "adoption", "guardianship", "paternity",
        "parental rights", "termination of parental rights", "family court",
    ],
    PracticeArea.IMMIGRATION: [
        "visa", "green card", "immigration", "deportation", "removal", "asylum",
        "citizenship", "naturalization", "undocumented", "daca", "uscis", "i-130",
        "i-485", "work authorization", "ead", "h1b", "h-1b", "l-1", "o-1",
        "refugee", "tps", "withholding of removal", "immigration court",
    ],
    PracticeArea.BANKRUPTCY: [
        "bankruptcy", "chapter 7", "chapter 11", "chapter 13", "discharge",
        "debt relief", "creditor", "automatic stay", "trustee", "liquidation",
        "reorganization", "means test", "exemption", "reaffirmation", "insolvency",
        "preferential transfer", "fraudulent conveyance",
    ],
    PracticeArea.INTELLECTUAL_PROPERTY: [
        "patent", "trademark", "copyright", "trade secret", "infringement",
        "intellectual property", "ip", "license", "royalty", "fair use",
        "dmca", "takedown", "invention", "trade dress", "brand", "logo",
        "software license", "open source", "prior art", "patent pending",
    ],
    PracticeArea.REAL_ESTATE: [
        "real estate", "property", "landlord", "tenant", "lease", "eviction",
        "mortgage", "foreclosure", "deed", "title", "zoning", "easement",
        "adverse possession", "quiet title", "closing", "purchase agreement",
        "hoa", "homeowners association", "commercial property", "land use",
    ],
    PracticeArea.EMPLOYMENT_LAW: [
        "fired", "terminated", "wrongful termination", "workplace", "discrimination",
        "harassment", "hostile work environment", "wage", "overtime", "flsa",
        "unemployment", "workers compensation", "retaliation", "whistleblower",
        "non-compete", "employment contract", "title vii", "adea", "fmla",
        "unpaid wages", "tip credit", "misclassification", "independent contractor",
    ],
    PracticeArea.CIVIL_RIGHTS: [
        "civil rights", "section 1983", "constitutional violation", "police brutality",
        "excessive force", "discrimination by government", "equal protection",
        "due process", "first amendment", "free speech", "religion", "assembly",
        "qualified immunity", "color of law", "ada", "disability discrimination",
    ],
    PracticeArea.PERSONAL_INJURY: [
        "injured", "accident", "negligence", "car accident", "slip and fall",
        "medical malpractice", "product liability", "defective product", "wrongful death",
        "damages", "pain and suffering", "liability", "tort", "personal injury",
        "insurance claim", "settlement", "premises liability", "dog bite",
    ],
    PracticeArea.CORPORATE_LAW: [
        "corporation", "llc", "partnership", "merger", "acquisition", "shareholder",
        "board of directors", "fiduciary duty", "derivative suit", "bylaws",
        "articles of incorporation", "operating agreement", "due diligence",
        "corporate governance", "private equity", "venture capital", "startup",
    ],
    PracticeArea.TAX_LAW: [
        "tax", "irs", "audit", "income tax", "estate tax", "gift tax",
        "tax evasion", "tax fraud", "deduction", "tax lien", "levy",
        "collection", "offer in compromise", "installment agreement", "back taxes",
        "penalty", "interest", "tax return", "w-2", "1099",
    ],
    PracticeArea.ENVIRONMENTAL_LAW: [
        "environmental", "epa", "pollution", "toxic", "hazardous waste", "cercla",
        "superfund", "clean water act", "clean air act", "contamination",
        "spill", "permit", "environmental impact", "endangered species",
        "wetlands", "brownfield",
    ],
    PracticeArea.CONSTITUTIONAL_LAW: [
        "constitutional", "first amendment", "second amendment", "fourth amendment",
        "fifth amendment", "fourteenth amendment", "equal protection", "due process",
        "habeas corpus", "bill of rights", "supreme court", "unconstitutional",
        "judicial review", "separation of powers",
    ],
    PracticeArea.INTERNATIONAL_LAW: [
        "international", "treaty", "foreign", "icc", "icj", "wto", "icsid",
        "extradition", "diplomatic immunity", "international arbitration",
        "sanctions", "export control", "foreign corrupt practices", "fcpa",
        "jurisdictional", "sovereign immunity",
    ],
    PracticeArea.ADMINISTRATIVE_LAW: [
        "administrative", "agency", "regulation", "rulemaking", "adjudication",
        "foia", "freedom of information", "hearing", "administrative law judge",
        "alj", "apa", "notice and comment", "deference", "chevron",
        "license revocation", "permit denial", "benefits denial",
    ],
    PracticeArea.PROBATE_ESTATES: [
        "will", "estate", "probate", "trust", "inheritance", "beneficiary",
        "executor", "administrator", "intestate", "power of attorney",
        "living trust", "revocable trust", "irrevocable trust", "heir",
        "testate", "decedent", "guardianship estate",
    ],
    PracticeArea.SECURITIES_LAW: [
        "securities", "stock", "sec", "investor", "fraud securities", "insider trading",
        "material misrepresentation", "prospectus", "ipo", "offering",
        "broker-dealer", "investment adviser", "hedge fund", "10-b5",
        "pslra", "ponzi scheme",
    ],
    PracticeArea.HEALTHCARE_LAW: [
        "healthcare", "hipaa", "medical", "hospital", "physician", "patient rights",
        "medicare", "medicaid", "false claims", "stark law", "anti-kickback",
        "credentialing", "malpractice", "informed consent", "mental health",
    ],
    PracticeArea.CYBERSECURITY_LAW: [
        "cybersecurity", "data breach", "hacking", "computer fraud", "cfaa",
        "ransomware", "phishing", "privacy", "gdpr", "ccpa", "data protection",
        "cyber attack", "network intrusion", "identity theft", "electronic surveillance",
    ],
}


# ---------------------------------------------------------------------------
# Practice Area Router
# ---------------------------------------------------------------------------

class PracticeAreaRouter:
    """
    Classifies legal matters to the correct practice area using keyword scoring.

    The router uses a weighted keyword matching algorithm that:
    1. Tokenizes the description
    2. Scores each practice area based on keyword hits
    3. Returns the top-scoring area with confidence

    Example:
        >>> router = PracticeAreaRouter()
        >>> matter = router.classify_matter("My employer discriminated against me because of my race")
        >>> matter.practice_area
        <PracticeArea.EMPLOYMENT_LAW: 'employment_law'>
        >>> matter.confidence > 0.5
        True
    """

    def __init__(self) -> None:
        self.keyword_scores = KEYWORD_SCORES
        self.legal_standards = LEGAL_STANDARDS
        self.statutes_of_limitations = STATUTES_OF_LIMITATIONS

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize and normalize text for keyword matching."""
        text_lower = text.lower()
        # Remove punctuation except hyphens (for compound terms)
        text_clean = re.sub(r"[^\w\s\-]", " ", text_lower)
        tokens = text_clean.split()
        return tokens

    def _score_area(self, tokens: List[str], area: PracticeArea) -> Tuple[float, List[str]]:
        """
        Score a practice area against tokenized text.

        Returns:
            Tuple of (score, matched_keywords)
        """
        keywords = self.keyword_scores.get(area, [])
        matched = []
        score = 0.0
        text_joined = " ".join(tokens)

        for kw in keywords:
            if kw in text_joined:
                matched.append(kw)
                # Longer keywords get higher weight (more specific)
                score += 1.0 + len(kw.split()) * 0.5

        return score, matched

    def classify_matter(self, description: str) -> LegalMatter:
        """
        Classify a legal matter based on natural language description.

        Args:
            description: Plain-English description of the legal issue.

        Returns:
            LegalMatter with practice area, confidence, and metadata.

        Example:
            >>> router = PracticeAreaRouter()
            >>> matter = router.classify_matter(
            ...     "I was arrested for drug possession and need a defense attorney"
            ... )
            >>> matter.practice_area == PracticeArea.CRIMINAL_DEFENSE
            True
        """
        if not description or not description.strip():
            return LegalMatter(
                description=description,
                practice_area=PracticeArea.CONTRACT_LAW,
                confidence=0.0,
                notes="No description provided; defaulted to contract law.",
            )

        tokens = self._tokenize(description)
        area_scores: Dict[PracticeArea, Tuple[float, List[str]]] = {}

        for area in PracticeArea:
            score, matched = self._score_area(tokens, area)
            area_scores[area] = (score, matched)

        # Sort by score descending
        sorted_areas = sorted(area_scores.items(), key=lambda x: x[1][0], reverse=True)

        if not sorted_areas or sorted_areas[0][1][0] == 0:
            # No keywords matched; return low-confidence generic matter
            return LegalMatter(
                description=description,
                practice_area=PracticeArea.CONTRACT_LAW,
                confidence=0.1,
                notes="No clear practice area identified; manual review recommended.",
            )

        top_area, (top_score, top_matched) = sorted_areas[0]
        total_score = sum(s for s, _ in area_scores.values())

        confidence = round(top_score / total_score, 4) if total_score > 0 else 0.0

        # Secondary areas: any area with score > 30% of top score
        secondary = [
            area for area, (score, _) in sorted_areas[1:]
            if score > top_score * 0.3 and score > 0
        ]

        # Determine priority
        priority = self._assess_priority(description, top_area)

        # Federal or state?
        federal = self._has_federal_nexus(description, top_area)

        # Complexity
        complexity = self._assess_complexity(description, top_score)

        return LegalMatter(
            description=description,
            practice_area=top_area,
            confidence=confidence,
            keywords_matched=top_matched,
            secondary_areas=secondary[:3],
            priority=priority,
            federal_jurisdiction=federal,
            state_jurisdiction=True,
            estimated_complexity=complexity,
        )

    def _assess_priority(self, description: str, area: PracticeArea) -> CasePriority:
        """Assess urgency/priority of a legal matter."""
        desc_lower = description.lower()
        critical_terms = [
            "arrested", "detained", "jail", "prison", "deportation", "removal",
            "eviction notice", "foreclosure", "emergency", "immediate", "urgent",
            "restraining order", "domestic violence", "custody emergency",
        ]
        high_terms = [
            "fired", "terminated", "lawsuit", "sued", "court date", "hearing",
            "deadline", "discrimination", "harassment", "breach", "damage",
        ]

        if any(t in desc_lower for t in critical_terms) or area == PracticeArea.CRIMINAL_DEFENSE:
            return CasePriority.CRITICAL
        if any(t in desc_lower for t in high_terms):
            return CasePriority.HIGH
        if area in (PracticeArea.IMMIGRATION, PracticeArea.FAMILY_LAW, PracticeArea.CIVIL_RIGHTS):
            return CasePriority.HIGH
        return CasePriority.MEDIUM

    def _has_federal_nexus(self, description: str, area: PracticeArea) -> bool:
        """Determine if matter likely involves federal jurisdiction."""
        federal_areas = {
            PracticeArea.IMMIGRATION,
            PracticeArea.CRIMINAL_DEFENSE,
            PracticeArea.CIVIL_RIGHTS,
            PracticeArea.SECURITIES_LAW,
            PracticeArea.ENVIRONMENTAL_LAW,
            PracticeArea.CONSTITUTIONAL_LAW,
            PracticeArea.INTERNATIONAL_LAW,
            PracticeArea.ADMINISTRATIVE_LAW,
            PracticeArea.BANKRUPTCY,
            PracticeArea.TAX_LAW,
            PracticeArea.INTELLECTUAL_PROPERTY,
        }
        desc_lower = description.lower()
        federal_terms = ["federal", "irs", "fbi", "doj", "uscis", "sec", "epa", "dol",
                         "federal court", "us district", "circuit court"]
        return area in federal_areas or any(t in desc_lower for t in federal_terms)

    def _assess_complexity(self, description: str, score: float) -> str:
        """Estimate case complexity."""
        if score > 20:
            return "very_complex"
        if score > 12:
            return "complex"
        if score > 6:
            return "moderate"
        return "simple"

    def get_strategy_template(self, matter: LegalMatter) -> dict:
        """
        Return a complete strategy template for a legal matter.

        Args:
            matter: A classified LegalMatter.

        Returns:
            dict with strategy details, initial steps, key theories, and timelines.

        Example:
            >>> router = PracticeAreaRouter()
            >>> matter = router.classify_matter("Patent infringement on my software")
            >>> strategy = router.get_strategy_template(matter)
            >>> "initial_steps" in strategy
            True
        """
        templates: Dict[PracticeArea, dict] = {
            PracticeArea.CONTRACT_LAW: {
                "initial_steps": [
                    "Obtain and review all contracts and related correspondence",
                    "Identify specific clauses at issue",
                    "Assess breach elements: existence of contract, performance/breach, causation, damages",
                    "Calculate actual damages",
                    "Evaluate statute of limitations",
                ],
                "key_legal_theories": [
                    "Breach of express contract",
                    "Breach of implied contract",
                    "Anticipatory repudiation",
                    "Promissory estoppel",
                    "Unjust enrichment / quasi-contract",
                ],
                "common_defenses": [
                    "Statute of frauds (must be in writing)",
                    "Lack of consideration",
                    "Mutual mistake or fraud",
                    "Waiver or modification",
                    "Impossibility / frustration of purpose",
                    "Unclean hands",
                ],
                "discovery_priorities": [
                    "All contracts, amendments, and addenda",
                    "Communications about the contract",
                    "Performance records",
                    "Damage documentation (invoices, payments, losses)",
                ],
                "typical_timeline_months": (6, 24),
                "settlement_likelihood": 0.80,
                "key_statutes": ["UCC Article 2 (sales of goods)", "Restatement (Second) of Contracts"],
                "key_cases": [
                    "Hadley v. Baxendale (1854) — foreseeability of damages",
                    "Lucy v. Zehmer (1954) — objective theory of contracts",
                    "Jacob & Youngs v. Kent (1921) — substantial performance",
                ],
                "tips": [
                    "Always document all breach-related communications",
                    "Mitigate damages immediately",
                    "Consider UCC vs. common law applicability (goods vs. services)",
                ],
            },
            PracticeArea.CRIMINAL_DEFENSE: {
                "initial_steps": [
                    "Obtain arrest record, police reports, and charging documents",
                    "Request all discovery under Brady/Giglio",
                    "Evaluate Fourth Amendment search and seizure issues",
                    "Review Miranda warnings and custodial interrogation compliance",
                    "Assess speedy trial deadlines",
                    "Interview client and potential witnesses",
                ],
                "key_legal_theories": [
                    "Motion to suppress illegally obtained evidence",
                    "Constitutional defenses (4th, 5th, 6th Amendment)",
                    "Affirmative defenses (self-defense, entrapment, necessity)",
                    "Challenging element of each charge",
                    "Attacking witness credibility",
                ],
                "common_defenses": [
                    "Lack of probable cause for arrest/search",
                    "Miranda violation — suppress statements",
                    "Self-defense / defense of others",
                    "Entrapment",
                    "Alibi",
                    "Mistaken identity",
                    "Insufficient evidence (reasonable doubt)",
                    "Brady violation — government withheld exculpatory evidence",
                ],
                "discovery_priorities": [
                    "Police reports and body camera footage",
                    "Search warrant applications and affidavits",
                    "Lab results and expert reports",
                    "Witness statements",
                    "Brady material (exculpatory evidence)",
                    "Giglio material (witness impeachment info)",
                ],
                "typical_timeline_months": (6, 36),
                "settlement_likelihood": 0.90,  # plea deals
                "key_statutes": [
                    "4th Amendment — search and seizure",
                    "5th Amendment — self-incrimination",
                    "6th Amendment — right to counsel, speedy trial",
                    "Brady v. Maryland (disclosure obligations)",
                ],
                "key_cases": [
                    "Miranda v. Arizona, 384 U.S. 436 (1966)",
                    "Mapp v. Ohio, 367 U.S. 643 (1961) — exclusionary rule",
                    "Brady v. Maryland, 373 U.S. 83 (1963)",
                    "Gideon v. Wainwright, 372 U.S. 335 (1963)",
                    "Terry v. Ohio, 392 U.S. 1 (1968)",
                ],
                "tips": [
                    "Client must NOT speak to police or prosecutors without counsel",
                    "Preserve all potential evidence immediately",
                    "File suppression motions early to understand prosecution's case",
                    "Evaluate federal vs. state charges — often can negotiate one over the other",
                ],
            },
            PracticeArea.EMPLOYMENT_LAW: {
                "initial_steps": [
                    "Document all discriminatory/retaliatory actions with dates",
                    "File EEOC charge within 300 days (deferral state) or 180 days",
                    "Preserve all employment records, emails, performance reviews",
                    "Identify comparators (similarly situated employees treated differently)",
                    "Calculate damages: back pay, front pay, emotional distress",
                ],
                "key_legal_theories": [
                    "Disparate treatment discrimination (Title VII, ADEA, ADA)",
                    "Hostile work environment",
                    "Retaliation for protected activity",
                    "Failure to accommodate (ADA/FMLA)",
                    "FLSA wage and hour violations",
                ],
                "common_defenses": [
                    "Legitimate non-discriminatory reason for termination",
                    "Business necessity",
                    "At-will employment",
                    "Failure to exhaust administrative remedies",
                    "After-acquired evidence doctrine",
                ],
                "discovery_priorities": [
                    "Personnel file and performance reviews",
                    "Emails and communications about plaintiff",
                    "Comparator employee files",
                    "Company policies and handbooks",
                    "Payroll records",
                ],
                "typical_timeline_months": (12, 36),
                "settlement_likelihood": 0.72,
                "key_statutes": [
                    "Title VII of Civil Rights Act, 42 U.S.C. § 2000e",
                    "ADEA, 29 U.S.C. § 621",
                    "ADA, 42 U.S.C. § 12101",
                    "FLSA, 29 U.S.C. § 201",
                    "FMLA, 29 U.S.C. § 2601",
                ],
                "key_cases": [
                    "McDonnell Douglas Corp. v. Green, 411 U.S. 792 (1973)",
                    "Burlington Northern v. White, 548 U.S. 53 (2006) — retaliation",
                    "Oncale v. Sundowner, 523 U.S. 75 (1998) — same-sex harassment",
                ],
                "tips": [
                    "EEOC charge is mandatory prerequisite — do not miss deadline",
                    "Document the 'but-for' causation clearly",
                    "Demand letter before EEOC is often effective",
                ],
            },
            PracticeArea.IMMIGRATION: {
                "initial_steps": [
                    "Determine immigration status and history",
                    "Identify all prior immigration applications and decisions",
                    "Assess criminal history (any conviction is potentially deportable)",
                    "Determine applicable visa categories",
                    "Identify any bars to relief",
                ],
                "key_legal_theories": [
                    "Family-based adjustment of status",
                    "Employment-based visa petition",
                    "Asylum and withholding of removal",
                    "Cancellation of removal",
                    "U visa (crime victims)",
                    "DACA",
                ],
                "common_defenses": [
                    "Asylum — persecution on protected ground",
                    "Withholding of removal",
                    "Convention Against Torture (CAT)",
                    "Cancellation of removal (10 years + exceptional hardship)",
                    "Voluntary departure",
                    "Motion to reopen / reconsider",
                ],
                "discovery_priorities": [
                    "All immigration documents (I-94, visas, prior applications)",
                    "Criminal records (certified copies)",
                    "Country conditions evidence for asylum",
                    "Family relationships (marriage certificates, birth certificates)",
                ],
                "typical_timeline_months": (12, 60),
                "settlement_likelihood": 0.40,
                "key_statutes": [
                    "Immigration and Nationality Act (INA), 8 U.S.C. § 1101 et seq.",
                    "REAL ID Act",
                    "IIRIRA",
                ],
                "key_cases": [
                    "INS v. Cardoza-Fonseca, 480 U.S. 421 (1987) — asylum standard",
                    "Chevron USA v. NRDC (agency deference)",
                    "Pereira v. Sessions (NTA jurisdiction)",
                ],
                "tips": [
                    "Never advise a client to admit anything without reviewing all facts",
                    "Criminal convictions can trigger mandatory bars — always check",
                    "Consular processing vs. adjustment of status — strategic choice",
                ],
            },
        }

        # Default template for areas without specific template
        default_template = {
            "initial_steps": [
                "Gather all relevant documents and facts",
                "Assess applicable statutes and regulations",
                "Identify all parties and their interests",
                "Evaluate statute of limitations",
                "Consult relevant case law",
            ],
            "key_legal_theories": [
                f"Primary claims under {matter.practice_area.value} law",
                "Supporting equitable theories",
            ],
            "common_defenses": [
                "Statute of limitations",
                "Failure to state a claim",
                "Lack of standing",
            ],
            "discovery_priorities": [
                "Key documents",
                "Witness list",
                "Electronic communications",
            ],
            "typical_timeline_months": (6, 24),
            "settlement_likelihood": 0.65,
            "tips": [
                "Document everything contemporaneously",
                "Preserve all potential evidence",
                "Assess settlement value early",
            ],
        }

        template = templates.get(matter.practice_area, default_template)
        template["practice_area"] = matter.practice_area.value
        template["standard_of_proof"] = (
            self.legal_standards.get(matter.practice_area, {}).get("standard_of_proof", "preponderance_of_evidence")
        )
        template["statutes_of_limitations"] = self.statutes_of_limitations.get(matter.practice_area, {})

        return template

    def get_all_areas(self) -> List[PracticeArea]:
        """Return all available practice areas."""
        return list(PracticeArea)

    def get_standard_of_proof(self, area: PracticeArea) -> str:
        """Return the applicable standard of proof for a practice area."""
        info = self.legal_standards.get(area, {})
        return info.get("standard_of_proof", StandardOfProof.PREPONDERANCE_OF_EVIDENCE.value)

    def get_statute_of_limitations(self, area: PracticeArea) -> Dict[str, str]:
        """Return statute of limitations information for a practice area."""
        return self.statutes_of_limitations.get(area, {})
