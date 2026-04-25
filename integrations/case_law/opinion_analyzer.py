"""
Opinion Analyzer
================
Extracts structured data from court opinions.

Features:
- Extract: court, judge, date, parties, docket number
- Identify: holding, dicta, reasoning sections
- Extract cited statutes and regulations
- Identify key legal tests and standards
- Summarize in plain English
- Tag with practice area(s)
- Score: complexity, importance, recency
- Flag: overruling, distinguishing, limiting prior cases
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class OpinionMetadata:
    """Extracted metadata from a court opinion."""

    court: str
    court_full_name: str
    judge: str
    date: Optional[str]
    parties: Tuple[str, str]        # (plaintiff/appellant, defendant/appellee)
    docket_number: str
    citation: str
    case_name: str
    is_per_curiam: bool
    panel_judges: List[str]
    dissenting_judges: List[str]
    concurring_judges: List[str]


@dataclass
class LegalHolding:
    """The legal holding extracted from an opinion."""

    text: str
    rule_of_law: str
    applies_to: str
    is_narrow: bool
    is_dicta: bool
    confidence: float


@dataclass
class StatuteCitation:
    """A statute or regulation cited in the opinion."""

    citation: str
    citation_type: str      # "usc", "cfr", "state", "other"
    title: Optional[int]
    section: Optional[str]
    context: str            # surrounding text


@dataclass
class LegalTest:
    """A multi-factor legal test identified in the opinion."""

    test_name: str
    factors: List[str]
    source_case: Optional[str]
    how_applied: str


@dataclass
class OpinionTreatment:
    """How this opinion treats cited precedents."""

    cited_case: str
    treatment: str          # "follows", "distinguishes", "overrules", "criticizes", "limits"
    explanation: str


@dataclass
class AnalyzedOpinion:
    """Complete analysis of a court opinion."""

    opinion_id: int
    metadata: OpinionMetadata
    holdings: List[LegalHolding]
    reasoning_summary: str
    statute_citations: List[StatuteCitation]
    case_citations: List[str]
    legal_tests: List[LegalTest]
    treatments: List[OpinionTreatment]
    practice_areas: List[str]
    plain_english_summary: str
    complexity_score: float      # 0-1 (1 = most complex)
    importance_score: float      # 0-1 (1 = most important)
    recency_score: float         # 0-1 (1 = most recent)
    flags: List[str]             # "overruling", "en banc", "landmark", etc.


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Case citation patterns
_CASE_CITATION_PATTERNS = [
    r'\b\d+\s+U\.S\.\s+\d+',                          # 410 U.S. 113
    r'\b\d+\s+S\.\s*Ct\.\s+\d+',                      # 142 S. Ct. 2111
    r'\b\d+\s+F\.\d+[d]?\s+\d+',                      # 996 F.3d 1
    r'\b\d+\s+F\.\s*App\'?x\s+\d+',                   # 123 F. App'x 456
    r'\b\d+\s+[A-Z][a-z]+\.\s+\d+',                   # 123 Cal. 456
]

# USC citation patterns
_USC_PATTERNS = [
    r'\d+\s+U\.S\.C\.?\s+§?\s*\w+(?:\([^)]+\))*',    # 42 U.S.C. § 1983
    r'\d+\s+U\.S\.C\.\s+\d+\w*',                       # 18 U.S.C. 2252
]

# CFR citation patterns
_CFR_PATTERNS = [
    r'\d+\s+C\.F\.R\.?\s+§?\s*[\d.]+',               # 40 C.F.R. § 60.1
    r'\d+\s+CFR\s+\d+',                                # 40 CFR 60
]

# State code patterns (common)
_STATE_CODE_PATTERNS = [
    r'[A-Z][a-z]+\s+(?:Rev\.\s+)?(?:Code|Stat\.?)\s+(?:Ann\.?\s+)?§?\s*[\d.-]+',
    r'[A-Z]{2}\s+Code\s+§?\s*[\d.-]+',
]

# Holding indicators
_HOLDING_PHRASES = [
    "we hold", "we conclude", "we find", "we affirm", "we reverse",
    "we vacate", "we remand", "the court holds", "it is held",
    "we therefore hold", "accordingly, we hold", "we agree",
    "we disagree", "we decline",
]

# Treatment phrases
_TREATMENT_MAP = {
    "overrule": "overrules",
    "overruling": "overrules",
    "distinguish": "distinguishes",
    "distinguished": "distinguishes",
    "limiting": "limits",
    "limit": "limits",
    "criticize": "criticizes",
    "criticized": "criticizes",
    "follow": "follows",
    "followed": "follows",
    "extend": "extends",
}

# Practice area keywords
_PRACTICE_AREA_KEYWORDS: Dict[str, List[str]] = {
    "constitutional law": ["constitution", "amendment", "due process", "equal protection", "bill of rights"],
    "criminal law": ["criminal", "indictment", "conviction", "sentence", "guilty", "defendant", "prosecution"],
    "civil rights": ["civil rights", "section 1983", "discrimination", "title vii", "ada"],
    "intellectual property": ["patent", "copyright", "trademark", "trade secret", "infringement"],
    "securities law": ["securities", "sec", "fraud", "insider trading", "exchange act"],
    "antitrust": ["antitrust", "sherman act", "clayton act", "monopoly", "competition"],
    "environmental law": ["environmental", "epa", "clean air", "clean water", "superfund"],
    "bankruptcy": ["bankruptcy", "chapter 11", "chapter 7", "debtor", "creditor", "discharge"],
    "immigration": ["immigration", "deportation", "asylum", "visa", "alien", "uscis"],
    "tax law": ["tax", "internal revenue", "irs", "deduction", "taxpayer"],
    "employment law": ["employment", "labor", "nlra", "flsa", "title vii", "discrimination"],
    "administrative law": ["administrative", "agency", "chevron", "apa", "rulemaking", "arbitrary"],
    "contract law": ["contract", "breach", "consideration", "offer", "acceptance"],
    "tort law": ["negligence", "liability", "damages", "duty of care", "proximate cause"],
    "family law": ["custody", "divorce", "marriage", "child support", "alimony"],
    "property law": ["property", "title", "deed", "easement", "takings", "eminent domain"],
}


# ---------------------------------------------------------------------------
# Opinion Analyzer
# ---------------------------------------------------------------------------


class OpinionAnalyzer:
    """
    Analyzes court opinions to extract structured legal information.

    Can operate standalone with raw text, or integrate with
    CourtListenerClient for fetching opinions.

    Usage:
        analyzer = OpinionAnalyzer()
        analysis = analyzer.analyze(
            opinion_id=12345,
            text=opinion_text,
            case_name="Riley v. California",
            court="scotus",
            date_filed="2014-06-25",
            citation="573 U.S. 373",
        )
    """

    def analyze(
        self,
        opinion_id: int,
        text: str,
        case_name: str = "",
        court: str = "",
        date_filed: Optional[str] = None,
        citation: str = "",
        docket_number: str = "",
        judge: str = "",
    ) -> AnalyzedOpinion:
        """
        Analyze a court opinion and extract structured data.

        Args:
            opinion_id: CourtListener opinion ID.
            text: Full opinion text.
            case_name: Case name (e.g., "Riley v. California").
            court: Court ID.
            date_filed: Date the opinion was filed.
            citation: Official citation.
            docket_number: Case docket number.
            judge: Author judge.

        Returns:
            AnalyzedOpinion with all extracted fields.
        """
        text_lower = text.lower()

        # Extract metadata
        metadata = self._extract_metadata(
            text, case_name, court, date_filed, citation, docket_number, judge
        )

        # Extract legal content
        holdings = self._extract_holdings(text)
        statutes = self._extract_statute_citations(text)
        case_citations = self._extract_case_citations(text)
        legal_tests = self._extract_legal_tests(text)
        treatments = self._extract_treatments(text)
        practice_areas = self._classify_practice_areas(text_lower)
        flags = self._extract_flags(text_lower)

        # Scoring
        complexity_score = self._score_complexity(text, holdings, statutes, legal_tests)
        importance_score = self._score_importance(court, flags, len(case_citations))
        recency_score = self._score_recency(date_filed)

        # Summaries
        reasoning_summary = self._summarize_reasoning(text, holdings)
        plain_english = self._generate_plain_english(
            metadata, holdings, practice_areas, treatments
        )

        return AnalyzedOpinion(
            opinion_id=opinion_id,
            metadata=metadata,
            holdings=holdings,
            reasoning_summary=reasoning_summary,
            statute_citations=statutes,
            case_citations=case_citations,
            legal_tests=legal_tests,
            treatments=treatments,
            practice_areas=practice_areas,
            plain_english_summary=plain_english,
            complexity_score=complexity_score,
            importance_score=importance_score,
            recency_score=recency_score,
            flags=flags,
        )

    def _extract_metadata(
        self,
        text: str,
        case_name: str,
        court: str,
        date_filed: Optional[str],
        citation: str,
        docket_number: str,
        judge: str,
    ) -> OpinionMetadata:
        """Extract and parse opinion metadata."""
        # Parse parties from case name
        parties = self._parse_parties(case_name)

        # Try to extract docket number from text if not provided
        if not docket_number:
            match = re.search(r'(?:No\.?|Docket(?:\s+No\.?)?)\s+(\d[\d-]+\w*)', text[:2000])
            if match:
                docket_number = match.group(1)

        # Extract panel judges from text
        panel_judges = self._extract_judges(text, judge)
        dissenting = self._extract_dissenting_judges(text)
        concurring = self._extract_concurring_judges(text)

        # Detect per curiam
        is_per_curiam = "per curiam" in text[:500].lower()

        return OpinionMetadata(
            court=court,
            court_full_name=self._get_court_full_name(court),
            judge=judge,
            date=date_filed,
            parties=parties,
            docket_number=docket_number,
            citation=citation,
            case_name=case_name,
            is_per_curiam=is_per_curiam,
            panel_judges=panel_judges,
            dissenting_judges=dissenting,
            concurring_judges=concurring,
        )

    def _parse_parties(self, case_name: str) -> Tuple[str, str]:
        """Parse parties from case name."""
        separators = [" v. ", " vs. ", " v ", " V. "]
        for sep in separators:
            if sep in case_name:
                parts = case_name.split(sep, 1)
                return (parts[0].strip(), parts[1].strip())
        return (case_name, "")

    def _get_court_full_name(self, court_id: str) -> str:
        """Map court ID to full name."""
        COURT_NAMES = {
            "scotus": "Supreme Court of the United States",
            "ca1": "U.S. Court of Appeals for the First Circuit",
            "ca2": "U.S. Court of Appeals for the Second Circuit",
            "ca3": "U.S. Court of Appeals for the Third Circuit",
            "ca4": "U.S. Court of Appeals for the Fourth Circuit",
            "ca5": "U.S. Court of Appeals for the Fifth Circuit",
            "ca6": "U.S. Court of Appeals for the Sixth Circuit",
            "ca7": "U.S. Court of Appeals for the Seventh Circuit",
            "ca8": "U.S. Court of Appeals for the Eighth Circuit",
            "ca9": "U.S. Court of Appeals for the Ninth Circuit",
            "ca10": "U.S. Court of Appeals for the Tenth Circuit",
            "ca11": "U.S. Court of Appeals for the Eleventh Circuit",
            "cadc": "U.S. Court of Appeals for the D.C. Circuit",
            "cafc": "U.S. Court of Appeals for the Federal Circuit",
        }
        return COURT_NAMES.get(court_id, court_id.upper())

    def _extract_judges(self, text: str, primary_judge: str) -> List[str]:
        """Extract all judges mentioned in the opinion header."""
        judges = [primary_judge] if primary_judge else []
        # Common header pattern: "JUDGE_NAME, Circuit Judge"
        pattern = r'\b([A-Z][A-Z\s]+(?:,\s+(?:Circuit|District|Senior|Chief)\s+Judge)?)'
        matches = re.findall(pattern, text[:1000])
        for m in matches[:10]:
            name = m.strip()
            if len(name.split()) <= 4 and name not in judges:
                judges.append(name)
        return judges[:7]  # limit to reasonable panel size

    def _extract_dissenting_judges(self, text: str) -> List[str]:
        """Extract dissenting judge names."""
        pattern = r'([A-Z][A-Za-z]+(?:,\s*J\.)?),?\s+dissenting'
        return re.findall(pattern, text)

    def _extract_concurring_judges(self, text: str) -> List[str]:
        """Extract concurring judge names."""
        pattern = r'([A-Z][A-Za-z]+(?:,\s*J\.)?),?\s+concurring'
        return re.findall(pattern, text)

    def _extract_holdings(self, text: str) -> List[LegalHolding]:
        """Extract legal holdings from opinion text."""
        holdings = []
        sentences = re.split(r'(?<=[.!?])\s+', text)

        for sent in sentences:
            sent_lower = sent.lower().strip()
            is_holding = any(phrase in sent_lower for phrase in _HOLDING_PHRASES)
            if is_holding and 10 < len(sent) < 500:
                holdings.append(
                    LegalHolding(
                        text=sent.strip(),
                        rule_of_law=self._extract_rule(sent),
                        applies_to=self._extract_applies_to(sent),
                        is_narrow="only" in sent_lower or "narrow" in sent_lower,
                        is_dicta="dicta" in sent_lower or "dictum" in sent_lower,
                        confidence=0.8 if any(
                            p in sent_lower for p in ["we hold", "it is held", "the court holds"]
                        ) else 0.5,
                    )
                )

        return holdings[:10]  # top 10 holdings

    def _extract_rule(self, sentence: str) -> str:
        """Extract the rule of law from a holding sentence."""
        # Simple: take first 100 chars after holding phrase
        for phrase in _HOLDING_PHRASES:
            idx = sentence.lower().find(phrase)
            if idx >= 0:
                return sentence[idx + len(phrase):idx + len(phrase) + 150].strip()
        return sentence[:150]

    def _extract_applies_to(self, sentence: str) -> str:
        """Extract what the holding applies to."""
        if "defendant" in sentence.lower():
            return "defendant"
        if "plaintiff" in sentence.lower():
            return "plaintiff"
        if "government" in sentence.lower():
            return "government"
        return "parties"

    def _extract_statute_citations(self, text: str) -> List[StatuteCitation]:
        """Extract all statute and regulation citations from the opinion."""
        citations = []
        seen = set()

        for pattern in _USC_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                cite = match.group(0).strip()
                if cite not in seen:
                    seen.add(cite)
                    # Extract title number
                    title_match = re.match(r'(\d+)', cite)
                    title = int(title_match.group(1)) if title_match else None
                    # Get context (surrounding text)
                    start = max(0, match.start() - 50)
                    end = min(len(text), match.end() + 50)
                    citations.append(
                        StatuteCitation(
                            citation=cite,
                            citation_type="usc",
                            title=title,
                            section=None,
                            context=text[start:end].replace(cite, f"[{cite}]"),
                        )
                    )

        for pattern in _CFR_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                cite = match.group(0).strip()
                if cite not in seen:
                    seen.add(cite)
                    citations.append(
                        StatuteCitation(
                            citation=cite,
                            citation_type="cfr",
                            title=None,
                            section=None,
                            context="",
                        )
                    )

        return citations[:50]

    def _extract_case_citations(self, text: str) -> List[str]:
        """Extract all case citations from the opinion."""
        citations = set()
        for pattern in _CASE_CITATION_PATTERNS:
            for match in re.finditer(pattern, text):
                citations.add(match.group(0).strip())
        return sorted(citations)[:100]

    def _extract_legal_tests(self, text: str) -> List[LegalTest]:
        """Identify multi-factor legal tests applied in the opinion."""
        tests = []
        text_lower = text.lower()

        known_tests = {
            "Chevron": ["step one", "step two", "ambiguous", "agency interpretation"],
            "Lemon": ["secular purpose", "primary effect", "excessive entanglement"],
            "Strickland": ["deficient performance", "prejudice"],
            "Brandenburg": ["imminent lawless action", "directed to", "likely to produce"],
            "Mathews": ["private interest", "risk of erroneous deprivation", "government interest"],
            "Penn Central": ["economic impact", "investment-backed expectations", "character of government action"],
            "Tinker": ["substantial disruption", "material interference"],
            "Miller": ["prurient interest", "patently offensive", "serious value"],
        }

        for test_name, factors in known_tests.items():
            if test_name.lower() in text_lower:
                present_factors = [f for f in factors if f.lower() in text_lower]
                if present_factors:
                    tests.append(
                        LegalTest(
                            test_name=f"{test_name} Test",
                            factors=present_factors,
                            source_case=None,
                            how_applied=f"Applied {test_name} test with {len(present_factors)} factors",
                        )
                    )

        return tests

    def _extract_treatments(self, text: str) -> List[OpinionTreatment]:
        """Extract how this opinion treats prior cases."""
        treatments = []
        for phrase, treatment in _TREATMENT_MAP.items():
            pattern = rf'(?:we\s+|the\s+court\s+)?{re.escape(phrase)}\s+([A-Z][^.]+?(?:\d+\s+[A-Z][a-z]+\.?\s+\d+)?)'
            for match in re.finditer(pattern, text, re.IGNORECASE):
                context = text[max(0, match.start()-100):match.end()+100]
                treatments.append(
                    OpinionTreatment(
                        cited_case=match.group(1).strip()[:100],
                        treatment=treatment,
                        explanation=context.strip()[:200],
                    )
                )
        return treatments[:20]

    def _classify_practice_areas(self, text_lower: str) -> List[str]:
        """Classify the opinion into practice areas based on keyword frequency."""
        scores: Dict[str, int] = {}
        for area, keywords in _PRACTICE_AREA_KEYWORDS.items():
            score = sum(text_lower.count(kw.lower()) for kw in keywords)
            if score > 0:
                scores[area] = score

        # Return top areas
        sorted_areas = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [area for area, _ in sorted_areas[:5]]

    def _extract_flags(self, text_lower: str) -> List[str]:
        """Extract special flags for the opinion."""
        flags = []
        if "en banc" in text_lower:
            flags.append("en banc")
        if "overrul" in text_lower:
            flags.append("overruling")
        if "per curiam" in text_lower:
            flags.append("per curiam")
        if "affirm" in text_lower and "reverse" in text_lower:
            flags.append("mixed result")
        if "dissent" in text_lower:
            flags.append("has dissent")
        if "concurr" in text_lower:
            flags.append("has concurrence")
        if "vacate" in text_lower:
            flags.append("vacated")
        if "remand" in text_lower:
            flags.append("remanded")
        return flags

    def _score_complexity(
        self,
        text: str,
        holdings: List[LegalHolding],
        statutes: List[StatuteCitation],
        tests: List[LegalTest],
    ) -> float:
        """Score opinion complexity (0-1)."""
        word_count = len(text.split())
        length_score = min(1.0, word_count / 15000)
        citation_score = min(1.0, len(statutes) / 30)
        test_score = min(1.0, len(tests) / 5)
        holding_score = min(1.0, len(holdings) / 10)
        return round((length_score * 0.4 + citation_score * 0.3 + test_score * 0.2 + holding_score * 0.1), 3)

    def _score_importance(self, court: str, flags: List[str], citation_count: int) -> float:
        """Score opinion importance (0-1)."""
        court_weights = {"scotus": 1.0, "cadc": 0.8, "ca2": 0.7, "ca9": 0.7}
        court_score = court_weights.get(court, 0.4)
        flag_score = min(1.0, len(flags) * 0.15)
        cite_score = min(1.0, citation_count / 100)
        overruling_bonus = 0.3 if "overruling" in flags else 0.0
        en_banc_bonus = 0.2 if "en banc" in flags else 0.0
        return round(min(1.0, court_score * 0.5 + flag_score * 0.2 + cite_score * 0.15 + overruling_bonus + en_banc_bonus), 3)

    def _score_recency(self, date_filed: Optional[str]) -> float:
        """Score opinion recency (0-1). Recent = 1."""
        if not date_filed:
            return 0.3
        try:
            year = int(date_filed[:4])
            age = max(0, datetime.utcnow().year - year)
            return round(max(0.0, 1.0 - age / 50.0), 3)
        except (ValueError, IndexError):
            return 0.3

    def _summarize_reasoning(self, text: str, holdings: List[LegalHolding]) -> str:
        """Generate a summary of the opinion's reasoning."""
        if not holdings:
            # Extract first substantive paragraph
            paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 100]
            return paragraphs[0][:500] if paragraphs else text[:500]
        # Use first holding as core of summary
        return holdings[0].text[:500] if holdings else text[:500]

    def _generate_plain_english(
        self,
        metadata: OpinionMetadata,
        holdings: List[LegalHolding],
        practice_areas: List[str],
        treatments: List[OpinionTreatment],
    ) -> str:
        """Generate a plain-English summary of the opinion."""
        lines = []
        plaintiff, defendant = metadata.parties
        lines.append(f"Case: {metadata.case_name}")
        lines.append(f"Court: {metadata.court_full_name}")
        if metadata.date:
            lines.append(f"Decided: {metadata.date}")
        if practice_areas:
            lines.append(f"Areas of Law: {', '.join(practice_areas[:3])}")
        lines.append("")

        if metadata.is_per_curiam:
            lines.append("This is a per curiam opinion (unsigned, from the full court).")

        if holdings:
            lines.append("Key Holdings:")
            for i, h in enumerate(holdings[:3], 1):
                lines.append(f"  {i}. {h.text[:200]}")
        else:
            lines.append("No clear holdings extracted (check full opinion text).")

        if treatments:
            overrulings = [t for t in treatments if t.treatment == "overrules"]
            if overrulings:
                lines.append("")
                lines.append("IMPORTANT: This opinion overrules prior cases:")
                for t in overrulings[:3]:
                    lines.append(f"  - {t.cited_case}")

        return "\n".join(lines)
