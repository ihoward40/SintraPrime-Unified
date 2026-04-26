"""
Legal Research Skill

Searches case law, statutes, and regulations by keyword and jurisdiction.
In production, this would integrate with CourtListener, Westlaw, or LexisNexis APIs.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..skill_types import SkillCategory, SkillTemplate


# ---------------------------------------------------------------------------
# Simulated legal database (illustrative – replace with real API in production)
# ---------------------------------------------------------------------------

SAMPLE_CASES = [
    {
        "citation": "Brown v. Board of Education, 347 U.S. 483 (1954)",
        "court": "U.S. Supreme Court",
        "year": 1954,
        "jurisdiction": "federal",
        "keywords": ["segregation", "equal protection", "education", "civil rights"],
        "summary": "Held that racial segregation in public schools violated the Equal Protection Clause.",
    },
    {
        "citation": "Miranda v. Arizona, 384 U.S. 436 (1966)",
        "court": "U.S. Supreme Court",
        "year": 1966,
        "jurisdiction": "federal",
        "keywords": ["miranda rights", "self-incrimination", "custodial interrogation", "criminal procedure"],
        "summary": "Established that suspects must be informed of their constitutional rights before interrogation.",
    },
    {
        "citation": "Roe v. Wade, 410 U.S. 113 (1973)",
        "court": "U.S. Supreme Court",
        "year": 1973,
        "jurisdiction": "federal",
        "keywords": ["abortion", "privacy", "due process", "reproductive rights"],
        "summary": "Recognized constitutional right to abortion under the right to privacy.",
    },
    {
        "citation": "Marbury v. Madison, 5 U.S. 137 (1803)",
        "court": "U.S. Supreme Court",
        "year": 1803,
        "jurisdiction": "federal",
        "keywords": ["judicial review", "constitution", "supreme court", "separation of powers"],
        "summary": "Established the principle of judicial review in the United States.",
    },
    {
        "citation": "Griggs v. Duke Power Co., 401 U.S. 424 (1971)",
        "court": "U.S. Supreme Court",
        "year": 1971,
        "jurisdiction": "federal",
        "keywords": ["employment discrimination", "disparate impact", "title vii", "civil rights"],
        "summary": "Established the disparate impact theory of employment discrimination.",
    },
]

SAMPLE_STATUTES = [
    {
        "citation": "42 U.S.C. § 1983",
        "title": "Civil Action for Deprivation of Rights",
        "jurisdiction": "federal",
        "keywords": ["civil rights", "section 1983", "constitutional violation", "state action"],
        "summary": "Provides a private right of action for constitutional violations by state actors.",
    },
    {
        "citation": "29 U.S.C. § 201 et seq. (FLSA)",
        "title": "Fair Labor Standards Act",
        "jurisdiction": "federal",
        "keywords": ["minimum wage", "overtime", "employment", "labor"],
        "summary": "Establishes minimum wage, overtime pay, and child labor standards.",
    },
    {
        "citation": "11 U.S.C. § 362",
        "title": "Automatic Stay in Bankruptcy",
        "jurisdiction": "federal",
        "keywords": ["bankruptcy", "automatic stay", "creditor", "debt"],
        "summary": "Imposes automatic stay of collection actions upon bankruptcy filing.",
    },
]


class LegalResearchSkill(SkillTemplate):
    """Searches case law, statutes, and regulations."""

    @property
    def skill_id(self) -> str:
        return "builtin_legal_research"

    @property
    def name(self) -> str:
        return "legal_research"

    @property
    def description(self) -> str:
        return "Searches case law, statutes, and regulations by keyword and jurisdiction."

    @property
    def category(self) -> SkillCategory:
        return SkillCategory.LEGAL

    @property
    def parameter_schema(self) -> Dict[str, Any]:
        return {
            "query": {"type": "str", "required": True, "description": "Search keywords"},
            "jurisdiction": {"type": "str", "required": False, "default": "federal", "description": "Jurisdiction filter"},
            "search_type": {"type": "str", "required": False, "default": "all", "description": "all|cases|statutes"},
            "limit": {"type": "int", "required": False, "default": 5, "description": "Max results"},
        }

    def execute(self, **kwargs) -> Dict[str, Any]:
        """Search legal resources for the given query."""
        query = kwargs.get("query", "")
        jurisdiction = kwargs.get("jurisdiction", "federal").lower()
        search_type = kwargs.get("search_type", "all").lower()
        limit = int(kwargs.get("limit", 5))

        if not query:
            return {"error": "Query is required", "results": [], "success": False}

        query_terms = re.sub(r"[^a-zA-Z0-9 ]", "", query.lower()).split()
        results: List[Dict[str, Any]] = []

        if search_type in ("all", "cases"):
            results.extend(self._search_cases(query_terms, jurisdiction))

        if search_type in ("all", "statutes"):
            results.extend(self._search_statutes(query_terms, jurisdiction))

        # Sort by relevance (hit count)
        results.sort(key=lambda x: x.get("_hits", 0), reverse=True)
        for r in results:
            r.pop("_hits", None)

        return {
            "query": query,
            "jurisdiction": jurisdiction,
            "results": results[:limit],
            "total_found": len(results),
            "searched_at": datetime.utcnow().isoformat(),
            "success": True,
        }

    def summarize(self, **kwargs) -> Dict[str, Any]:
        """Produce a structured summary of a legal case from text."""
        case_text = kwargs.get("case_text", "")
        if not case_text:
            return {"error": "case_text is required", "success": False}

        words = case_text.split()
        sentences = [s.strip() for s in re.split(r"[.!?]", case_text) if s.strip()]

        # Extract key info via simple patterns
        parties = re.findall(r"([A-Z][a-z]+(?: [A-Z][a-z]+)*) v\. ([A-Z][a-z]+(?: [A-Z][a-z]+)*)", case_text)
        citations = re.findall(r"\d+ [A-Z]\.[A-Z]\.\d*\.? [§\d]+", case_text)

        return {
            "summary": " ".join(sentences[:3]) if sentences else "Unable to extract summary.",
            "word_count": len(words),
            "sentence_count": len(sentences),
            "parties_identified": [f"{p[0]} v. {p[1]}" for p in parties[:3]],
            "citations_found": citations[:5],
            "success": True,
        }

    def _search_cases(self, terms: List[str], jurisdiction: str) -> List[Dict]:
        results = []
        for case in SAMPLE_CASES:
            if jurisdiction != "all" and case["jurisdiction"] != jurisdiction and jurisdiction != "federal":
                continue
            hits = sum(1 for t in terms if any(t in kw.lower() for kw in case["keywords"]))
            hits += sum(2 for t in terms if t in case["summary"].lower())
            if hits > 0:
                r = dict(case, type="case", _hits=hits)
                results.append(r)
        return results

    def _search_statutes(self, terms: List[str], jurisdiction: str) -> List[Dict]:
        results = []
        for statute in SAMPLE_STATUTES:
            if jurisdiction != "all" and statute["jurisdiction"] != jurisdiction:
                continue
            hits = sum(1 for t in terms if any(t in kw.lower() for kw in statute["keywords"]))
            hits += sum(2 for t in terms if t in statute["summary"].lower())
            if hits > 0:
                r = dict(statute, type="statute", _hits=hits)
                results.append(r)
        return results
