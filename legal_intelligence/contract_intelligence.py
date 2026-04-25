"""
Contract Intelligence Module — SintraPrime Legal Intelligence System

World-class contract analysis, drafting, risk identification, and negotiation
strategy. Covers all major commercial and consumer contract types.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class RedFlag:
    """
    Represents a high-risk or problematic contract clause.

    Example:
        >>> flag = RedFlag(
        ...     clause_type="auto_renewal",
        ...     text="This agreement shall automatically renew for successive one-year terms",
        ...     severity="high",
        ...     risk="Client may be locked in for years without notice",
        ...     recommendation="Add mutual written notice requirement (60-90 days) to prevent renewal"
        ... )
    """
    clause_type: str
    text: str
    severity: str  # "critical" | "high" | "medium" | "low"
    risk: str
    recommendation: str
    legal_authority: str = ""


@dataclass
class ContractAnalysis:
    """
    Comprehensive analysis of a contract including risks and recommendations.

    Example:
        >>> analysis = ContractAnalysis(
        ...     risk_score=72.5,
        ...     risk_factors=["One-sided arbitration clause", "No limitation of liability"],
        ...     missing_clauses=["Force majeure", "Governing law"],
        ...     favorable_terms=["Payment terms are standard"],
        ...     unfavorable_terms=["Auto-renewal without notice"],
        ...     recommendations=["Add termination for convenience clause"],
        ...     plain_english_summary="This is a vendor agreement heavily favoring the service provider."
        ... )
    """
    risk_score: float  # 0-100 (100 = highest risk)
    risk_factors: List[str]
    missing_clauses: List[str]
    favorable_terms: List[str]
    unfavorable_terms: List[str]
    recommendations: List[str]
    plain_english_summary: str
    red_flags: List[RedFlag] = field(default_factory=list)
    contract_type: str = "unknown"
    jurisdiction: str = ""
    enforceability_concerns: List[str] = field(default_factory=list)


@dataclass
class ContractSummary:
    """
    Plain-English summary of key contract terms.

    Example:
        >>> summary = ContractSummary(
        ...     parties={"buyer": "ACME Corp", "seller": "Smith LLC"},
        ...     effective_date="2024-01-01",
        ...     term="2 years",
        ...     payment_terms="Net 30",
        ...     key_obligations={"buyer": "Pay invoices", "seller": "Deliver goods"},
        ...     termination_rights="Either party with 30 days notice"
        ... )
    """
    parties: Dict[str, str]
    effective_date: str
    term: str
    payment_terms: str
    key_obligations: Dict[str, str]
    termination_rights: str
    governing_law: str = ""
    dispute_resolution: str = ""
    ip_ownership: str = ""
    confidentiality: str = ""
    limitation_of_liability: str = ""
    indemnification: str = ""
    plain_english: str = ""


@dataclass
class NegotiationStrategy:
    """
    Negotiation strategy and positions for contract terms.

    Example:
        >>> strategy = NegotiationStrategy(
        ...     party_position="buyer",
        ...     priority_issues=["Payment terms", "IP ownership"],
        ...     must_haves=["Mutual termination right", "IP assignment"],
        ...     nice_to_haves=["Extended warranty"],
        ...     concessions_available=["Extended payment schedule"],
        ...     red_lines=["No unilateral modification clause"],
        ...     opening_positions={"payment_terms": "Net 60"},
        ...     fallback_positions={"payment_terms": "Net 45"}
        ... )
    """
    party_position: str
    priority_issues: List[str]
    must_haves: List[str]
    nice_to_haves: List[str]
    concessions_available: List[str]
    red_lines: List[str]
    opening_positions: Dict[str, str]
    fallback_positions: Dict[str, str]
    recommended_approach: str = ""


@dataclass
class EnforceabilityReport:
    """
    Analysis of whether a contract is enforceable in a given jurisdiction.

    Example:
        >>> report = EnforceabilityReport(
        ...     enforceable=True,
        ...     jurisdiction="California",
        ...     issues=[],
        ...     partially_enforceable_clauses=["Non-compete (CA will not enforce)"],
        ...     void_clauses=["Non-compete clause void under Cal. Bus. & Prof. Code § 16600"],
        ...     recommendations=["Remove non-compete; use NDA instead"]
        ... )
    """
    enforceable: bool
    jurisdiction: str
    issues: List[str]
    partially_enforceable_clauses: List[str]
    void_clauses: List[str]
    recommendations: List[str]
    statute_of_frauds_compliant: bool = True
    consideration_present: bool = True
    capacity_issues: str = ""
    unconscionability_risk: float = 0.0  # 0-1.0


# ---------------------------------------------------------------------------
# Red Flag Patterns
# ---------------------------------------------------------------------------

RED_FLAG_PATTERNS: Dict[str, Dict] = {
    "auto_renewal": {
        "patterns": ["automatically renew", "auto-renew", "automatically extend",
                     "evergreen clause", "successive term", "unless cancelled"],
        "severity": "high",
        "risk": "Party may be locked in for additional term(s) without realizing it. "
                "Can result in significant financial obligations.",
        "recommendation": "Add: 'Either party may terminate by providing written notice at least "
                          "[60-90] days prior to renewal date.'",
    },
    "unilateral_modification": {
        "patterns": ["reserves the right to modify", "may change these terms",
                     "sole discretion to amend", "at any time without notice",
                     "unilaterally modify"],
        "severity": "critical",
        "risk": "Other party can change terms without consent — contract becomes illusory.",
        "recommendation": "Replace with mutual written amendment requirement. This clause may render "
                          "the contract illusory and unenforceable.",
    },
    "broad_indemnification": {
        "patterns": ["indemnify and hold harmless", "defend, indemnify",
                     "any and all claims", "including negligence"],
        "severity": "high",
        "risk": "May require indemnifying the other party even for their own negligence or misconduct.",
        "recommendation": "Narrow indemnification to claims arising from your OWN acts/omissions. "
                          "Add mutual indemnification or cap liability.",
    },
    "limitation_of_liability_waiver": {
        "patterns": ["no liability", "not liable for any", "shall not be liable",
                     "waive all claims", "in no event shall"],
        "severity": "high",
        "risk": "May eliminate all remedies even for willful misconduct or gross negligence.",
        "recommendation": "Ensure carve-out for gross negligence, willful misconduct, fraud, "
                          "IP indemnification, and confidentiality breaches.",
    },
    "one_sided_arbitration": {
        "patterns": ["binding arbitration", "waive right to jury trial",
                     "class action waiver", "aaa rules", "jams arbitration"],
        "severity": "medium",
        "risk": "Waives jury trial rights; class action waiver may prevent joining others with same claim. "
                "Arbitration can be expensive for consumers.",
        "recommendation": "Negotiate: mutual jury trial waiver, opt-out right, consumer carve-out, "
                          "fee-splitting, local arbitration venue.",
        "legal_authority": "AT&T Mobility LLC v. Concepcion, 563 U.S. 333 (2011) — class waivers generally enforceable.",
    },
    "ip_assignment_all_inventions": {
        "patterns": ["assign all inventions", "work made for hire", "all intellectual property",
                     "any invention conceived", "moral rights waived"],
        "severity": "high",
        "risk": "May require assigning inventions unrelated to employment, including personal projects.",
        "recommendation": "Narrow to inventions related to employer's business, made during work hours, "
                          "or using employer resources. California, Delaware, Illinois, Minnesota, "
                          "North Carolina, Washington prohibit overbroad assignment.",
    },
    "non_compete": {
        "patterns": ["non-compete", "non compete", "not compete", "covenant not to compete",
                     "restrictive covenant", "shall not engage in"],
        "severity": "high",
        "risk": "May restrict employment or business opportunities for years. California bans most non-competes.",
        "recommendation": "If CA, ban applies (Bus. & Prof. Code § 16600). Elsewhere: negotiate narrow "
                          "scope (geography, time, activities). Prefer NDA over non-compete.",
        "legal_authority": "Cal. Bus. & Prof. Code § 16600; FTC Rule (if in effect).",
    },
    "hidden_fees": {
        "patterns": ["administrative fee", "processing fee", "termination fee",
                     "early termination", "cancellation fee", "convenience fee"],
        "severity": "medium",
        "risk": "Unexpected fees can dramatically increase total cost of contract.",
        "recommendation": "List all fees explicitly. Add: 'No additional fees not expressly stated herein.'",
    },
    "perpetual_license": {
        "patterns": ["perpetual license", "irrevocable license", "royalty-free license",
                     "sublicensable"],
        "severity": "medium",
        "risk": "Granting perpetual irrevocable IP rights means you cannot revoke even if other party "
                "breaches or defaults.",
        "recommendation": "Add: 'License terminates upon material breach not cured within 30 days.'",
    },
    "choice_of_law_unfavorable": {
        "patterns": ["governed by the laws of", "jurisdiction of", "exclusive jurisdiction",
                     "venue shall be"],
        "severity": "medium",
        "risk": "Unfavorable forum may require expensive travel and application of unfamiliar law.",
        "recommendation": "Negotiate for your home state's law or a neutral jurisdiction. "
                          "Add: 'Each party may seek injunctive relief in any court of competent jurisdiction.'",
    },
    "liquidated_damages_excessive": {
        "patterns": ["liquidated damages", "penalty clause", "daily penalty",
                     "per diem penalty", "predetermined damages"],
        "severity": "medium",
        "risk": "Excessive liquidated damages clauses may be unenforceable as penalties.",
        "recommendation": "Ensure LDs are reasonable estimate of actual damages at time of contracting. "
                          "Courts strike penalties disguised as LDs.",
        "legal_authority": "Restatement (Second) of Contracts § 356 — LDs enforceable if reasonable forecast of harm.",
    },
    "warranty_disclaimer": {
        "patterns": ["as is", "as-is", "no warranties", "disclaimer of warranties",
                     "merchantability", "fitness for particular purpose"],
        "severity": "medium",
        "risk": "Eliminates implied warranties of merchantability and fitness for particular purpose.",
        "recommendation": "Request express warranty of: (1) conformance to specifications; "
                          "(2) no infringement; (3) functionality for intended purpose.",
        "legal_authority": "UCC § 2-316 — disclaimer must be conspicuous; 'AS IS' in caps sufficient.",
    },
    "force_majeure_exclusion": {
        "patterns": ["does not include", "pandemic shall not", "force majeure excludes"],
        "severity": "medium",
        "risk": "Contract may not excuse performance during genuine emergencies.",
        "recommendation": "Ensure force majeure clause covers pandemics, government orders, supply chain "
                          "disruptions, and natural disasters. COVID-19 exposed gaps in many clauses.",
    },
    "unilateral_termination": {
        "patterns": ["may terminate at any time", "terminate for any reason", "at will termination",
                     "sole discretion to terminate"],
        "severity": "high",
        "risk": "Other party can exit contract without cause, leaving you without recourse or transition time.",
        "recommendation": "Add: 'Termination for cause requires 30-day cure period. Termination for "
                          "convenience requires [60-90] days notice and payment through notice period.'",
    },
    "no_consequential_damages": {
        "patterns": ["no consequential damages", "not liable for lost profits",
                     "indirect damages excluded", "special or incidental damages"],
        "severity": "high",
        "risk": "If other party breaches, you can only recover direct damages — not lost business profits.",
        "recommendation": "Negotiate carve-outs for: intentional misconduct, gross negligence, IP/data "
                          "breach, confidentiality violations.",
    },
}

# ---------------------------------------------------------------------------
# Contract Templates
# ---------------------------------------------------------------------------

CONTRACT_TEMPLATES: Dict[str, Dict] = {
    "nda": {
        "essential_clauses": [
            "Definition of Confidential Information (broad but specific)",
            "Exclusions from confidentiality (already public, received from third party, independently developed)",
            "Standard of care (at least same care as own confidential info)",
            "Term of confidentiality obligations (post-termination)",
            "Permitted disclosures (legal requirement, need-to-know basis)",
            "Return/destruction of information",
            "No license grant",
            "No warranty of information accuracy",
            "Injunctive relief provision",
            "Governing law and dispute resolution",
        ],
        "typical_terms": {
            "duration": "2-5 years; some information (trade secrets) indefinitely",
            "standard_of_care": "Reasonable care; same as own confidential information",
            "exclusions": "Public domain, prior knowledge, independent development, third-party disclosure",
        },
    },
    "employment": {
        "essential_clauses": [
            "Job title, duties, and reporting structure",
            "Compensation (salary/hourly, bonus, equity)",
            "Benefits",
            "At-will employment statement (where applicable)",
            "Non-disclosure and confidentiality",
            "IP assignment (limited to work-related inventions)",
            "Non-solicitation (employees and customers)",
            "Non-compete (if enforceable in jurisdiction)",
            "Dispute resolution",
            "Governing law",
        ],
        "red_flags": [
            "Overbroad IP assignment (capturing personal inventions)",
            "Non-compete in California (void under § 16600)",
            "No severance provision",
            "No notice of termination requirement",
        ],
    },
    "llc_operating_agreement": {
        "essential_clauses": [
            "Members and membership interests (percentage)",
            "Capital contributions",
            "Allocations and distributions (profits and losses)",
            "Management structure (member-managed vs. manager-managed)",
            "Voting rights and thresholds (majority, supermajority)",
            "Transfer restrictions (right of first refusal, consent requirements)",
            "Admission of new members",
            "Buyout/buy-sell provisions",
            "Dissolution and wind-up",
            "Tax treatment elections",
            "Indemnification of managers",
        ],
        "red_flags": [
            "No buyout mechanism (trapped investors)",
            "Unilateral removal of manager",
            "Failure to address deadlock",
            "No anti-dilution provisions for existing members",
        ],
    },
    "services_agreement": {
        "essential_clauses": [
            "Scope of services (detailed, specific)",
            "Deliverables and acceptance criteria",
            "Timeline and milestones",
            "Payment terms and invoicing",
            "Change order process",
            "IP ownership of deliverables (work for hire or assignment)",
            "Confidentiality",
            "Non-solicitation",
            "Limitation of liability",
            "Indemnification",
            "Termination (for cause and convenience)",
            "Dispute resolution",
        ],
    },
    "real_estate_purchase": {
        "essential_clauses": [
            "Property description (legal description, APN)",
            "Purchase price and payment terms",
            "Earnest money deposit (amount, conditions for return/forfeiture)",
            "Contingencies (financing, inspection, appraisal)",
            "Title insurance and title condition",
            "Closing date and possession",
            "Property condition disclosures",
            "Prorations (taxes, HOA, utilities)",
            "Risk of loss allocation",
            "Default remedies (specific performance vs. liquidated damages)",
        ],
    },
}

# ---------------------------------------------------------------------------
# Jurisdiction-Specific Rules
# ---------------------------------------------------------------------------

JURISDICTION_RULES: Dict[str, Dict] = {
    "California": {
        "non_compete": "VOID — Cal. Bus. & Prof. Code § 16600 (with limited exceptions for sale of business)",
        "ip_assignment": "Cannot assign inventions developed on own time without employer resources or relating to employer's business. Labor Code § 2870.",
        "arbitration": "Unconscionability doctrine applied more aggressively. Armendariz v. Foundation Health (2000).",
        "at_will": "Presumed at-will but public policy exceptions broad (Tameny v. Atlantic Richfield).",
        "consumer_protection": "Strong consumer protection — Unfair Competition Law (Bus. & Prof. Code § 17200).",
    },
    "Delaware": {
        "non_compete": "Generally enforceable if reasonable in scope, duration, geography.",
        "corporate": "Delaware is preferred corporate law jurisdiction. General Corporation Law highly developed.",
        "fiduciary_duty": "Strong fiduciary duty law; entire fairness review for interested transactions.",
    },
    "New York": {
        "non_compete": "Enforceable if reasonable — protects legitimate business interest, reasonable time/geography.",
        "arbitration": "NY enforces arbitration agreements broadly under CPLR § 7501.",
        "statute_of_frauds": "6 years for written contracts; 3 years for UCC sales.",
        "blue_pencil": "Courts may reform (blue pencil) overbroad non-competes.",
    },
    "Texas": {
        "non_compete": "Enforceable if ancillary to otherwise enforceable agreement; reasonable limits. Bus. & Com. Code § 15.50.",
        "at_will": "Strong at-will presumption.",
    },
}


# ---------------------------------------------------------------------------
# Contract Intelligence
# ---------------------------------------------------------------------------

class ContractIntelligence:
    """
    World-class contract analysis, drafting, and negotiation system.

    Analyzes contracts for risks, missing clauses, and enforceability.
    Drafts new contracts with all essential provisions. Provides negotiation
    strategy based on party position.

    Example:
        >>> ci = ContractIntelligence()
        >>> analysis = ci.analyze_contract(
        ...     "This agreement automatically renews unless cancelled. "
        ...     "Company may modify terms at any time without notice."
        ... )
        >>> analysis.risk_score > 50
        True
        >>> len(analysis.red_flags) >= 2
        True
    """

    def __init__(self) -> None:
        self.red_flag_patterns = RED_FLAG_PATTERNS
        self.contract_templates = CONTRACT_TEMPLATES
        self.jurisdiction_rules = JURISDICTION_RULES

    def analyze_contract(self, text: str) -> ContractAnalysis:
        """
        Analyze a contract for risks, missing clauses, and one-sided terms.

        Args:
            text: Full text of the contract to analyze.

        Returns:
            ContractAnalysis with risk score, red flags, and recommendations.

        Example:
            >>> ci = ContractIntelligence()
            >>> analysis = ci.analyze_contract(
            ...     "Contractor shall indemnify Company for any and all claims including negligence."
            ... )
            >>> any("indemnif" in rf.clause_type for rf in analysis.red_flags)
            True
        """
        text_lower = text.lower()
        red_flags = self._find_red_flags(text)
        missing = self._check_missing_clauses(text_lower)
        favorable, unfavorable = self._classify_terms(text_lower)
        risk_score = self._calculate_risk_score(red_flags, missing)

        recommendations = []
        for flag in red_flags:
            recommendations.append(flag.recommendation)

        if missing:
            recommendations.append(
                f"Add missing essential clauses: {', '.join(missing[:5])}"
            )

        contract_type = self._detect_contract_type(text_lower)
        summary = self._generate_plain_english_summary(text, contract_type, red_flags, missing)

        enforceability = []
        if risk_score > 70:
            enforceability.append("High number of one-sided terms may raise unconscionability concerns.")
        if "arbitration" in text_lower and "class action" in text_lower:
            enforceability.append("Class action waiver may be unenforceable in certain states.")

        return ContractAnalysis(
            risk_score=risk_score,
            risk_factors=[rf.risk for rf in red_flags],
            missing_clauses=missing,
            favorable_terms=favorable,
            unfavorable_terms=unfavorable,
            recommendations=recommendations,
            plain_english_summary=summary,
            red_flags=red_flags,
            contract_type=contract_type,
            enforceability_concerns=enforceability,
        )

    def _find_red_flags(self, text: str) -> List[RedFlag]:
        """Scan contract for known red flag patterns."""
        text_lower = text.lower()
        flags = []

        for flag_type, flag_info in self.red_flag_patterns.items():
            patterns = flag_info.get("patterns", [])
            for pattern in patterns:
                if pattern.lower() in text_lower:
                    # Find surrounding context
                    idx = text_lower.find(pattern.lower())
                    start = max(0, idx - 50)
                    end = min(len(text), idx + len(pattern) + 100)
                    context = text[start:end].strip()

                    flags.append(RedFlag(
                        clause_type=flag_type,
                        text=context,
                        severity=flag_info.get("severity", "medium"),
                        risk=flag_info.get("risk", ""),
                        recommendation=flag_info.get("recommendation", ""),
                        legal_authority=flag_info.get("legal_authority", ""),
                    ))
                    break  # Only flag each type once

        return flags

    def _check_missing_clauses(self, text_lower: str) -> List[str]:
        """Check for missing essential clauses."""
        essential_checks = {
            "Governing law": ["governing law", "laws of the state", "governed by"],
            "Dispute resolution": ["arbitration", "mediation", "dispute resolution", "jurisdiction and venue"],
            "Force majeure": ["force majeure", "act of god", "unforeseeable circumstances", "pandemic"],
            "Limitation of liability": ["limitation of liability", "liability shall not exceed", "maximum liability"],
            "Termination clause": ["termination", "terminate", "end this agreement"],
            "Indemnification": ["indemnif"],
            "Confidentiality": ["confidential", "non-disclosure", "proprietary"],
            "Amendment process": ["amended", "modification", "no modification except"],
            "Entire agreement / integration": ["entire agreement", "integration clause", "supersedes"],
            "Severability": ["severab"],
            "Notice provisions": ["notice shall be", "notices to", "written notice"],
            "Warranty provisions": ["warrant", "representation"],
        }

        missing = []
        for clause_name, patterns in essential_checks.items():
            if not any(p in text_lower for p in patterns):
                missing.append(clause_name)

        return missing

    def _classify_terms(self, text_lower: str) -> Tuple[List[str], List[str]]:
        """Classify terms as favorable or unfavorable."""
        favorable = []
        unfavorable = []

        favorable_patterns = [
            ("mutual termination right", ["either party may terminate", "mutual termination"]),
            ("cure period for breach", ["cure period", "30 days to cure", "60 days to cure"]),
            ("capped liability", ["not to exceed", "capped at", "maximum liability"]),
            ("governing law acceptable", ["laws of", "governed by"]),
            ("payment terms specified", ["net 30", "net 45", "net 60", "payment due"]),
        ]

        unfavorable_patterns = [
            ("auto-renewal without notice", ["automatically renew"]),
            ("unilateral modification right", ["reserves the right to modify", "may change these terms"]),
            ("one-sided indemnification", ["indemnify", "hold harmless"]),
            ("broad IP assignment", ["all inventions", "all intellectual property"]),
            ("non-compete clause", ["non-compete", "covenant not to compete"]),
        ]

        for label, patterns in favorable_patterns:
            if any(p in text_lower for p in patterns):
                favorable.append(label)

        for label, patterns in unfavorable_patterns:
            if any(p in text_lower for p in patterns):
                unfavorable.append(label)

        return favorable, unfavorable

    def _calculate_risk_score(self, red_flags: List[RedFlag], missing: List[str]) -> float:
        """Calculate a 0-100 risk score."""
        severity_weights = {"critical": 20, "high": 12, "medium": 7, "low": 3}
        base_score = 0.0

        for flag in red_flags:
            base_score += severity_weights.get(flag.severity, 5)

        # Missing clauses add risk
        base_score += len(missing) * 3

        return min(100.0, round(base_score, 1))

    def _detect_contract_type(self, text_lower: str) -> str:
        """Detect the type of contract from text."""
        type_patterns = {
            "employment": ["employment agreement", "employee", "employer", "salary", "at-will"],
            "nda": ["non-disclosure", "nda", "confidentiality agreement", "confidential information"],
            "services": ["services agreement", "statement of work", "deliverables", "consultant"],
            "real_estate": ["purchase agreement", "real property", "closing", "earnest money"],
            "lease": ["lease", "landlord", "tenant", "rent", "premises"],
            "llc_operating": ["operating agreement", "members", "manager", "llc", "membership interest"],
            "loan": ["promissory note", "loan agreement", "principal", "interest rate", "default"],
            "ip_assignment": ["assignment agreement", "assigns all right", "patent application"],
            "licensing": ["license agreement", "licensor", "licensee", "royalty", "sublicense"],
            "merger_acquisition": ["purchase price", "representations and warranties", "closing conditions", "acquisition"],
            "franchise": ["franchise", "franchisee", "franchisor", "franchise fee", "royalty"],
        }

        for contract_type, patterns in type_patterns.items():
            if sum(1 for p in patterns if p in text_lower) >= 2:
                return contract_type

        return "general_commercial"

    def _generate_plain_english_summary(
        self,
        text: str,
        contract_type: str,
        red_flags: List[RedFlag],
        missing: List[str],
    ) -> str:
        """Generate a plain English summary of the contract."""
        type_descriptions = {
            "employment": "employment agreement",
            "nda": "non-disclosure / confidentiality agreement",
            "services": "services / consulting agreement",
            "real_estate": "real estate purchase agreement",
            "lease": "lease agreement",
            "llc_operating": "LLC operating agreement",
            "loan": "loan / promissory note",
            "ip_assignment": "IP assignment agreement",
            "licensing": "license agreement",
        }

        type_desc = type_descriptions.get(contract_type, "commercial agreement")
        risk_level = "LOW" if len(red_flags) <= 1 else "MODERATE" if len(red_flags) <= 3 else "HIGH"
        critical_flags = [rf for rf in red_flags if rf.severity == "critical"]

        summary = (
            f"This appears to be a {type_desc}. "
            f"Overall risk level: {risk_level}. "
        )

        if red_flags:
            summary += (
                f"Key concerns: {'; '.join(rf.clause_type.replace('_', ' ') for rf in red_flags[:3])}. "
            )

        if critical_flags:
            summary += (
                f"CRITICAL ISSUES requiring immediate attention: "
                f"{'; '.join(rf.clause_type.replace('_', ' ') for rf in critical_flags)}. "
            )

        if missing:
            summary += (
                f"Missing essential clauses: {', '.join(missing[:5])}. "
            )

        summary += "Review with qualified attorney before signing."

        return summary

    def draft_contract(self, contract_type: str, parties: dict, terms: dict) -> "LegalDocument":
        """
        Draft a new contract of the specified type.

        Args:
            contract_type: Type of contract (nda, employment, services, etc.).
            parties: Dict with party names and roles (e.g., {"company": "ACME Corp", "employee": "John Smith"}).
            terms: Dict with specific terms (e.g., {"salary": "$100,000", "start_date": "2024-01-01"}).

        Returns:
            LegalDocument with complete drafted contract.

        Example:
            >>> ci = ContractIntelligence()
            >>> try:
    from legal_intelligence.motion_drafting_engine import LegalDocument
except ImportError:
    from motion_drafting_engine import LegalDocument
            >>> doc = ci.draft_contract(
            ...     "nda",
            ...     {"disclosing_party": "ACME Corp", "receiving_party": "John Smith"},
            ...     {"purpose": "evaluate potential partnership", "term": "2 years"}
            ... )
            >>> "CONFIDENTIAL" in doc.content.upper() or "NON-DISCLOSURE" in doc.content.upper()
            True
        """
        from datetime import datetime
        try:
            from legal_intelligence.motion_drafting_engine import LegalDocument
        except ImportError:
            from motion_drafting_engine import LegalDocument

        templates_map = {
            "nda": self._draft_nda,
            "employment": self._draft_employment,
            "services": self._draft_services_agreement,
        }

        draft_fn = templates_map.get(contract_type, self._draft_generic)
        content = draft_fn(parties, terms)

        return LegalDocument(
            title=f"{contract_type.upper().replace('_', ' ')} AGREEMENT",
            court="N/A",
            case_number="N/A",
            content=content,
            motion_type=f"contract_{contract_type}",
            word_count=len(content.split()),
            jurisdiction=terms.get("governing_law", ""),
        )

    def _draft_nda(self, parties: dict, terms: dict) -> str:
        """Draft a mutual non-disclosure agreement."""
        party_a = parties.get("disclosing_party", parties.get("party_a", "Party A"))
        party_b = parties.get("receiving_party", parties.get("party_b", "Party B"))
        purpose = terms.get("purpose", "evaluating a potential business relationship")
        nda_term = terms.get("term", "two (2) years")
        governing_law = terms.get("governing_law", "[STATE]")
        date = terms.get("date", "[DATE]")

        return f"""MUTUAL NON-DISCLOSURE AGREEMENT

This Mutual Non-Disclosure Agreement ("Agreement") is entered into as of {date}
by and between {party_a} ("Party A") and {party_b} ("Party B")
(each a "Party" and collectively the "Parties").

RECITALS

WHEREAS, the Parties desire to explore {purpose}; and
WHEREAS, in connection therewith, each Party may disclose certain confidential information
to the other Party.

NOW, THEREFORE, in consideration of the mutual covenants herein, the Parties agree as follows:

1. DEFINITION OF CONFIDENTIAL INFORMATION.
"Confidential Information" means any non-public information disclosed by one Party ("Disclosing Party")
to the other Party ("Receiving Party"), either directly or indirectly, in writing, orally, or by
inspection of tangible objects, that is designated as confidential or that reasonably should be
understood to be confidential given the nature of the information and circumstances of disclosure.

2. EXCLUSIONS.
Confidential Information does not include information that: (a) is or becomes publicly available
through no breach of this Agreement; (b) was rightfully known to Receiving Party prior to disclosure;
(c) is rightfully received from a third party without restriction; or (d) is independently developed
by Receiving Party without use of Confidential Information.

3. OBLIGATIONS OF RECEIVING PARTY.
Receiving Party shall: (a) protect Confidential Information with at least the same degree of care
used for its own confidential information, but no less than reasonable care; (b) use Confidential
Information solely for the Purpose; (c) limit disclosure to employees with a need to know who are
bound by confidentiality obligations no less protective than this Agreement.

4. TERM. This Agreement shall remain in effect for {nda_term} from the Effective Date.
Confidentiality obligations survive termination of this Agreement.

5. RETURN OF INFORMATION. Upon request, Receiving Party shall promptly return or certify destruction
of all Confidential Information and copies thereof.

6. NO LICENSE. Nothing herein grants any license under any patent, copyright, trademark, or trade secret.

7. INJUNCTIVE RELIEF. Each Party acknowledges that breach would cause irreparable harm for which
monetary damages would be inadequate. Each Party consents to injunctive relief without bond.

8. GOVERNING LAW. This Agreement is governed by the laws of {governing_law}, without regard to
conflict of laws principles.

9. ENTIRE AGREEMENT. This Agreement constitutes the entire agreement between the Parties concerning
the subject matter hereof and supersedes all prior agreements.

IN WITNESS WHEREOF, the Parties have executed this Agreement as of the date first written above.

{party_a.upper()}                        {party_b.upper()}

By: ___________________________         By: ___________________________
Name:                                   Name:
Title:                                  Title:
Date:                                   Date:
"""

    def _draft_employment(self, parties: dict, terms: dict) -> str:
        """Draft an employment agreement."""
        company = parties.get("company", "Company")
        employee = parties.get("employee", "Employee")
        title = terms.get("title", "[Job Title]")
        salary = terms.get("salary", "[Annual Salary]")
        start_date = terms.get("start_date", "[Start Date]")
        governing_law = terms.get("governing_law", "[STATE]")

        return f"""EMPLOYMENT AGREEMENT

This Employment Agreement ("Agreement") is entered into as of {start_date},
between {company} ("Company") and {employee} ("Employee").

1. POSITION. Company employs Employee as {title}, reporting to [Manager/Title].
   Employee's duties include [specific duties].

2. COMPENSATION. Company shall pay Employee a base salary of {salary} per year,
   payable in accordance with Company's standard payroll schedule.

3. BENEFITS. Employee is eligible for Company's standard benefit programs including
   [health insurance, 401(k), PTO] subject to applicable plan documents.

4. AT-WILL EMPLOYMENT. Employee's employment is at-will. Either party may terminate
   the employment relationship at any time, with or without cause or notice, subject to
   applicable law.

5. CONFIDENTIALITY. Employee agrees to maintain the confidentiality of Company's
   Confidential Information during and after employment. "Confidential Information"
   means non-public technical, business, financial, and customer information.

6. IP ASSIGNMENT. Employee assigns to Company all inventions, works, and developments
   created in the scope of employment, using Company resources, or relating to Company's
   business. This does not apply to inventions developed on Employee's own time without
   Company resources and not relating to Company's business (per applicable state law).

7. NON-SOLICITATION. For one (1) year post-employment, Employee shall not solicit
   Company's employees or customers with whom Employee had material contact.

8. GOVERNING LAW. This Agreement is governed by the laws of {governing_law}.

9. DISPUTE RESOLUTION. Any dispute shall be resolved by binding arbitration under
   AAA Employment Arbitration Rules, except either party may seek injunctive relief.

COMPANY: {company}                      EMPLOYEE: {employee}

By: ___________________________         Signature: ___________________________
Name:                                   Date:
Title:
Date:
"""

    def _draft_services_agreement(self, parties: dict, terms: dict) -> str:
        """Draft a professional services agreement."""
        client = parties.get("client", "Client")
        provider = parties.get("provider", parties.get("contractor", "Service Provider"))
        services = terms.get("services", "[Description of Services]")
        fee = terms.get("fee", "[Fee Amount]")
        payment_terms = terms.get("payment_terms", "Net 30 days from invoice")
        governing_law = terms.get("governing_law", "[STATE]")
        start = terms.get("start_date", "[Start Date]")
        end = terms.get("end_date", "[End Date]")

        return f"""PROFESSIONAL SERVICES AGREEMENT

This Professional Services Agreement is entered into between {client} ("Client")
and {provider} ("Provider"), effective {start}.

1. SERVICES. Provider shall perform: {services}.

2. TERM. From {start} to {end}, unless earlier terminated.

3. COMPENSATION. Client shall pay {fee}. Payment terms: {payment_terms}.
   Late payments accrue interest at 1.5% per month.

4. IP OWNERSHIP. All work product, deliverables, and materials created by Provider
   specifically for Client under this Agreement shall be deemed work-for-hire owned by
   Client upon payment in full. Provider retains all pre-existing IP.

5. CONFIDENTIALITY. Both parties shall maintain confidentiality of the other's
   Confidential Information.

6. INDEPENDENT CONTRACTOR. Provider is an independent contractor. Provider is
   responsible for all taxes on compensation received hereunder.

7. LIMITATION OF LIABILITY. Neither party shall be liable for indirect, incidental,
   special, punitive, or consequential damages. Each party's aggregate liability
   shall not exceed fees paid in the 6 months preceding the claim.

8. INDEMNIFICATION. Each party indemnifies the other for third-party claims arising
   from its own negligence, willful misconduct, or breach of this Agreement.

9. TERMINATION. Either party may terminate for material breach with 30 days written
   notice and opportunity to cure. Client may terminate for convenience with 30 days notice
   and payment for work completed.

10. GOVERNING LAW. {governing_law}.

CLIENT: {client}                        PROVIDER: {provider}
By: _______________                     By: _______________
"""

    def _draft_generic(self, parties: dict, terms: dict) -> str:
        """Draft a generic commercial agreement."""
        party_a = parties.get("party_a", list(parties.values())[0] if parties else "Party A")
        party_b = parties.get("party_b", list(parties.values())[-1] if len(parties) > 1 else "Party B")
        purpose = terms.get("purpose", "the purposes set forth herein")

        return f"""COMMERCIAL AGREEMENT

This Agreement is entered into between {party_a} and {party_b} for {purpose}.

[Terms to be negotiated and added per specific requirements]

Signed:
{party_a}: ___________________________
{party_b}: ___________________________
"""

    def negotiate_terms(self, contract: str, party_position: str) -> NegotiationStrategy:
        """
        Develop a negotiation strategy for a contract based on party position.

        Args:
            contract: Contract text.
            party_position: Role in the contract (e.g., "buyer", "seller", "employee", "employer").

        Returns:
            NegotiationStrategy with must-haves, nice-to-haves, and red lines.

        Example:
            >>> ci = ContractIntelligence()
            >>> strategy = ci.negotiate_terms(
            ...     "Services agreement with auto-renewal and unilateral modification",
            ...     "client"
            ... )
            >>> isinstance(strategy.must_haves, list)
            True
        """
        analysis = self.analyze_contract(contract)
        red_flags = analysis.red_flags

        # Position-specific priorities
        buyer_must_haves = [
            "Right to inspect / due diligence period",
            "Financing contingency",
            "Representations and warranties survive closing",
            "Indemnification for pre-closing liabilities",
            "Mutual termination right",
        ]

        seller_must_haves = [
            "Firm purchase price (no post-closing price adjustments)",
            "Limited representations and warranties",
            "Cap on indemnification liability",
            "Short indemnification survival period",
            "No clawback provisions",
        ]

        employee_must_haves = [
            "Defined severance package",
            "Narrow non-compete (or removal if in California)",
            "IP carve-out for personal inventions",
            "At-will with adequate notice period",
            "Equity vesting acceleration upon termination",
        ]

        employer_must_haves = [
            "Broad IP assignment (work-related)",
            "Non-solicitation of employees and customers",
            "Return of company property",
            "Arbitration clause",
        ]

        position_lower = party_position.lower()
        if "buyer" in position_lower or "client" in position_lower or "customer" in position_lower:
            must_haves = buyer_must_haves
        elif "seller" in position_lower or "vendor" in position_lower or "provider" in position_lower:
            must_haves = seller_must_haves
        elif "employee" in position_lower or "worker" in position_lower:
            must_haves = employee_must_haves
        elif "employer" in position_lower or "company" in position_lower:
            must_haves = employer_must_haves
        else:
            must_haves = [
                "Mutual termination right with notice",
                "Governing law neutral or home state",
                "Mutual limitation of liability",
                "Cure period for breach",
            ]

        # Red lines — non-negotiable
        red_lines = []
        for flag in red_flags:
            if flag.severity == "critical":
                red_lines.append(f"Remove or fundamentally change: {flag.clause_type.replace('_', ' ')}")

        if not red_lines:
            red_lines = ["No unilateral modification right without consent"]

        # Opening vs. fallback positions
        opening_positions = {}
        fallback_positions = {}

        for flag in red_flags:
            if flag.clause_type == "auto_renewal":
                opening_positions["renewal"] = "No auto-renewal; manual renewal only"
                fallback_positions["renewal"] = "90 days written notice required to prevent renewal"
            elif flag.clause_type == "non_compete":
                opening_positions["non_compete"] = "Remove non-compete entirely"
                fallback_positions["non_compete"] = "6-month non-compete, local geography only"
            elif flag.clause_type == "one_sided_arbitration":
                opening_positions["dispute_resolution"] = "State court litigation; jury trial preserved"
                fallback_positions["dispute_resolution"] = "Mutual arbitration; AAA rules; local venue; fee sharing"

        return NegotiationStrategy(
            party_position=party_position,
            priority_issues=[flag.clause_type.replace("_", " ") for flag in red_flags[:5]],
            must_haves=must_haves,
            nice_to_haves=[
                "Most-favored-nation clause",
                "Audit rights",
                "Step-in rights for critical services",
            ],
            concessions_available=[
                "Extended payment schedule",
                "Extended term with fixed pricing",
                "Right of first refusal on future work",
            ],
            red_lines=red_lines,
            opening_positions=opening_positions,
            fallback_positions=fallback_positions,
            recommended_approach=(
                f"As the {party_position}, prioritize: {', '.join(must_haves[:3])}. "
                f"{'High risk contract — consider not signing without significant revisions.' if analysis.risk_score > 60 else 'Moderate risk — negotiate key terms before signing.'}"
            ),
        )

    def identify_red_flags(self, contract: str) -> List[RedFlag]:
        """
        Identify all red flag clauses in a contract.

        Args:
            contract: Contract text.

        Returns:
            List of RedFlag objects for each problematic clause found.

        Example:
            >>> ci = ContractIntelligence()
            >>> flags = ci.identify_red_flags("This agreement automatically renews annually.")
            >>> any(f.clause_type == "auto_renewal" for f in flags)
            True
        """
        return self._find_red_flags(contract)

    def extract_key_terms(self, contract: str) -> ContractSummary:
        """
        Extract and summarize key terms in plain English.

        Args:
            contract: Contract text.

        Returns:
            ContractSummary with all key terms extracted.

        Example:
            >>> ci = ContractIntelligence()
            >>> summary = ci.extract_key_terms("Net 30 payment terms. Governed by California law.")
            >>> "30" in summary.payment_terms or "Net" in summary.payment_terms
            True
        """
        text_lower = contract.lower()

        # Extract payment terms
        payment_terms = "Not specified"
        for term in ["net 30", "net 45", "net 60", "due on receipt", "30 days", "45 days"]:
            if term in text_lower:
                payment_terms = f"Payment due {term}"
                break

        # Extract governing law
        governing_law = "Not specified"
        gov_match = re.search(r"laws?\s+of\s+(?:the\s+state\s+of\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", contract)
        if gov_match:
            governing_law = gov_match.group(1)

        # Extract dispute resolution
        dispute_resolution = "Not specified"
        if "arbitration" in text_lower:
            dispute_resolution = "Binding arbitration"
        elif "mediation" in text_lower:
            dispute_resolution = "Mediation (then litigation)"
        elif "jurisdiction" in text_lower:
            dispute_resolution = "Court litigation"

        # Extract term
        contract_term = "Not specified"
        term_match = re.search(
            r"(?:term|period)\s+(?:of|shall be|is)\s+(\w+(?:\s+\w+)?(?:\s+year[s]?|\s+month[s]?))",
            text_lower
        )
        if term_match:
            contract_term = term_match.group(1)

        return ContractSummary(
            parties={},  # Would need entity extraction
            effective_date="See contract",
            term=contract_term,
            payment_terms=payment_terms,
            key_obligations={"review_required": "Manual review needed for complete obligation extraction"},
            termination_rights="See termination clause" if "terminat" in text_lower else "Not specified",
            governing_law=governing_law,
            dispute_resolution=dispute_resolution,
            ip_ownership="Work for hire" if "work for hire" in text_lower else "See IP clause",
            confidentiality="Yes" if "confidential" in text_lower else "Not specified",
            limitation_of_liability="Present" if "limitation of liability" in text_lower else "Not specified",
            indemnification="Present" if "indemnif" in text_lower else "Not specified",
            plain_english=self._generate_plain_english_summary(
                contract, self._detect_contract_type(text_lower), [], []
            ),
        )

    def check_enforceability(self, contract: str, jurisdiction: str) -> EnforceabilityReport:
        """
        Analyze whether a contract is enforceable in a given jurisdiction.

        Args:
            contract: Contract text.
            jurisdiction: State or jurisdiction name.

        Returns:
            EnforceabilityReport with enforceability assessment.

        Example:
            >>> ci = ContractIntelligence()
            >>> report = ci.check_enforceability(
            ...     "Employee shall not compete for 5 years nationwide.",
            ...     "California"
            ... )
            >>> len(report.void_clauses) >= 1
            True
        """
        text_lower = contract.lower()
        issues = []
        partially_enforceable = []
        void_clauses = []
        recommendations = []

        # Check jurisdiction-specific rules
        jur_rules = self.jurisdiction_rules.get(jurisdiction, {})

        if "non_compete" in jur_rules:
            if "non-compete" in text_lower or "covenant not to compete" in text_lower:
                if jurisdiction == "California":
                    void_clauses.append(
                        f"Non-compete clause — VOID in California. Cal. Bus. & Prof. Code § 16600."
                    )
                    recommendations.append("Remove non-compete; replace with narrowly tailored NDA.")
                else:
                    partially_enforceable.append(
                        f"Non-compete clause — may be enforceable in {jurisdiction} if reasonable."
                    )

        # Check statute of frauds
        statute_of_frauds = True
        sof_items = ["real estate", "marriage", "goods over $500", "suretyship", "year-long contract"]
        requires_writing = any(item in text_lower for item in ["real property", "real estate", "purchase"])
        if requires_writing and len(contract) < 100:
            statute_of_frauds = False
            issues.append("Contract may not satisfy statute of frauds — must be in writing.")

        # Check consideration
        consideration = True
        if "no consideration" in text_lower:
            consideration = False
            issues.append("Apparent lack of consideration — contract may be unenforceable.")

        # Unconscionability check
        analysis = self.analyze_contract(contract)
        unconscionability_risk = min(1.0, analysis.risk_score / 100)
        if unconscionability_risk > 0.7:
            issues.append(
                "High concentration of one-sided terms raises unconscionability risk. "
                "Courts may refuse to enforce or may reform the agreement."
            )

        enforceable = len(void_clauses) == 0 and len([i for i in issues if "void" in i.lower()]) == 0

        return EnforceabilityReport(
            enforceable=enforceable,
            jurisdiction=jurisdiction,
            issues=issues,
            partially_enforceable_clauses=partially_enforceable,
            void_clauses=void_clauses,
            recommendations=recommendations,
            statute_of_frauds_compliant=statute_of_frauds,
            consideration_present=consideration,
            unconscionability_risk=unconscionability_risk,
        )
