"""
Precedent Finder
================
Finds controlling legal precedent for any fact pattern or legal question.

Features:
- Semantic similarity search against case database
- Jurisdiction filtering (binding vs. persuasive)
- Favorable vs. unfavorable precedent classification
- Precedent brief generation
- Authority-weighted ranking
- Cross-practice area analogous case finding
"""

from __future__ import annotations

import asyncio
import logging
import math
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class PrecedentCandidate:
    """A case that may serve as precedent."""

    opinion_id: int
    cluster_id: int
    case_name: str
    citation: str
    court: str
    date_filed: Optional[str]
    holding: str
    reasoning: str
    practice_areas: List[str]
    is_binding: bool
    is_favorable: bool
    relevance_score: float
    authority_score: float
    recency_score: float
    combined_score: float
    snippet: str = ""
    url: str = ""


@dataclass
class PrecedentBrief:
    """A structured brief of precedents for a legal issue."""

    query: str
    jurisdiction: str
    binding_precedents: List[PrecedentCandidate]
    persuasive_precedents: List[PrecedentCandidate]
    unfavorable_precedents: List[PrecedentCandidate]
    landmark_cases: List[PrecedentCandidate]
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    summary: str = ""


@dataclass
class JurisdictionHierarchy:
    """Binding authority hierarchy for a given forum court."""

    forum_court: str
    binding_courts: List[str]
    persuasive_courts: List[str]


# ---------------------------------------------------------------------------
# Jurisdiction authority mapping
# ---------------------------------------------------------------------------

# Maps forum court → courts whose opinions are binding
_BINDING_AUTHORITY: Dict[str, List[str]] = {
    # SCOTUS binds everyone
    "scotus": [],  # nothing binds SCOTUS

    # Federal circuits bind their districts
    "ca1": ["scotus"],
    "ca2": ["scotus"],
    "ca3": ["scotus"],
    "ca4": ["scotus"],
    "ca5": ["scotus"],
    "ca6": ["scotus"],
    "ca7": ["scotus"],
    "ca8": ["scotus"],
    "ca9": ["scotus"],
    "ca10": ["scotus"],
    "ca11": ["scotus"],
    "cadc": ["scotus"],
    "cafc": ["scotus"],

    # District courts bound by circuit + SCOTUS
    "dcd": ["scotus", "cadc"],
    "nysd": ["scotus", "ca2"],
    "nyed": ["scotus", "ca2"],
    "nynd": ["scotus", "ca2"],
    "nywd": ["scotus", "ca2"],
    "cacd": ["scotus", "ca9"],
    "cand": ["scotus", "ca9"],
    "casd": ["scotus", "ca9"],
    "caed": ["scotus", "ca9"],
    "txsd": ["scotus", "ca5"],
    "txnd": ["scotus", "ca5"],
    "txed": ["scotus", "ca5"],
    "txwd": ["scotus", "ca5"],
    "ilnd": ["scotus", "ca7"],
    "flsd": ["scotus", "ca11"],
    "flnd": ["scotus", "ca11"],
    "flmd": ["scotus", "ca11"],
    "gamd": ["scotus", "ca11"],
    "gand": ["scotus", "ca11"],
    "gasd": ["scotus", "ca11"],

    # State supreme courts - bound only by SCOTUS on federal questions
    "scotus_state": ["scotus"],
}


def get_binding_courts(forum_court: str) -> List[str]:
    """Get list of courts whose opinions bind the forum court."""
    return _BINDING_AUTHORITY.get(forum_court, ["scotus"])


# ---------------------------------------------------------------------------
# Simple TF-IDF relevance scorer (no external ML dependencies)
# ---------------------------------------------------------------------------


def _tokenize(text: str) -> List[str]:
    """Simple tokenizer: lowercase, strip punctuation, split on whitespace."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return [t for t in text.split() if len(t) > 2]


def _compute_tf(tokens: List[str]) -> Dict[str, float]:
    tf: Dict[str, float] = {}
    n = len(tokens) or 1
    for tok in tokens:
        tf[tok] = tf.get(tok, 0) + 1.0 / n
    return tf


def _cosine_similarity(vec_a: Dict[str, float], vec_b: Dict[str, float]) -> float:
    """Cosine similarity between two TF dicts."""
    common = set(vec_a.keys()) & set(vec_b.keys())
    if not common:
        return 0.0
    dot = sum(vec_a[k] * vec_b[k] for k in common)
    mag_a = math.sqrt(sum(v ** 2 for v in vec_a.values()))
    mag_b = math.sqrt(sum(v ** 2 for v in vec_b.values()))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def _text_similarity(query: str, text: str) -> float:
    """Compute TF-based cosine similarity between query and text."""
    q_tokens = _tokenize(query)
    t_tokens = _tokenize(text)
    if not q_tokens or not t_tokens:
        return 0.0
    q_tf = _compute_tf(q_tokens)
    t_tf = _compute_tf(t_tokens)
    return _cosine_similarity(q_tf, t_tf)


def _recency_score(date_filed: Optional[str]) -> float:
    """Score 0-1 based on how recent the case is (1 = current year)."""
    if not date_filed:
        return 0.3
    try:
        year = int(date_filed[:4])
        current_year = datetime.utcnow().year
        age = max(0, current_year - year)
        return max(0.0, 1.0 - (age / 100.0))
    except (ValueError, IndexError):
        return 0.3


# ---------------------------------------------------------------------------
# Precedent Finder
# ---------------------------------------------------------------------------


class PrecedentFinder:
    """
    Finds controlling and persuasive precedent for any legal question.

    Integrates with CourtListenerClient and CitationNetworkBuilder for
    comprehensive precedent research.

    Usage:
        finder = PrecedentFinder(courtlistener_client=cl_client,
                                  citation_network=cn_builder)
        brief = await finder.find(
            query="warrantless search of cell phone",
            forum_court="ca9",
            favorable_keywords=["Fourth Amendment protection"],
            unfavorable_keywords=["exception", "exigent circumstances"]
        )
    """

    def __init__(
        self,
        courtlistener_client: Optional[Any] = None,
        citation_network: Optional[Any] = None,
        relevance_weight: float = 0.5,
        authority_weight: float = 0.3,
        recency_weight: float = 0.2,
    ) -> None:
        self._cl = courtlistener_client
        self._cn = citation_network
        self.w_relevance = relevance_weight
        self.w_authority = authority_weight
        self.w_recency = recency_weight
        self._case_db: List[Dict[str, Any]] = []  # local cached cases

    def load_cases(self, cases: List[Dict[str, Any]]) -> None:
        """
        Load cases into the local search index.

        Args:
            cases: List of case dicts with keys: opinion_id, case_name,
                   citation, court, date_filed, text, holding, practice_areas.
        """
        self._case_db.extend(cases)
        logger.info("Loaded %d cases into precedent finder index", len(cases))

    def _score_case(
        self,
        query: str,
        case: Dict[str, Any],
        forum_court: str,
        favorable_keywords: Optional[List[str]] = None,
        unfavorable_keywords: Optional[List[str]] = None,
    ) -> Optional[PrecedentCandidate]:
        """Score a single case against the query."""
        text = " ".join([
            case.get("case_name", ""),
            case.get("holding", ""),
            case.get("text", "")[:2000],  # first 2000 chars
        ])

        relevance = _text_similarity(query, text)
        if relevance < 0.01:
            return None  # skip irrelevant cases

        authority_score = case.get("pagerank_score", 0.0)
        # Normalize authority score (0-1)
        authority_normalized = min(1.0, authority_score * 100)

        recency = _recency_score(case.get("date_filed"))

        combined = (
            self.w_relevance * relevance
            + self.w_authority * authority_normalized
            + self.w_recency * recency
        )

        court = case.get("court", "")
        binding_courts = get_binding_courts(forum_court)
        is_binding = court in binding_courts or court == "scotus"

        # Determine favorability
        is_favorable = True
        if favorable_keywords:
            fav_text = " ".join(favorable_keywords).lower()
            is_favorable = _text_similarity(fav_text, text) > 0.05
        if unfavorable_keywords:
            unfav_text = " ".join(unfavorable_keywords).lower()
            if _text_similarity(unfav_text, text) > 0.05:
                is_favorable = False

        return PrecedentCandidate(
            opinion_id=case.get("opinion_id", 0),
            cluster_id=case.get("cluster_id", 0),
            case_name=case.get("case_name", ""),
            citation=case.get("citation", ""),
            court=court,
            date_filed=case.get("date_filed"),
            holding=case.get("holding", ""),
            reasoning=case.get("reasoning", ""),
            practice_areas=case.get("practice_areas", []),
            is_binding=is_binding,
            is_favorable=is_favorable,
            relevance_score=round(relevance, 4),
            authority_score=round(authority_normalized, 4),
            recency_score=round(recency, 4),
            combined_score=round(combined, 4),
            snippet=text[:300],
            url=case.get("url", ""),
        )

    async def find(
        self,
        query: str,
        forum_court: str = "scotus",
        favorable_keywords: Optional[List[str]] = None,
        unfavorable_keywords: Optional[List[str]] = None,
        practice_areas: Optional[List[str]] = None,
        date_min: Optional[str] = None,
        date_max: Optional[str] = None,
        max_results: int = 50,
        include_persuasive: bool = True,
    ) -> PrecedentBrief:
        """
        Find relevant precedent for a legal question.

        Args:
            query: Legal question or fact pattern.
            forum_court: CourtListener ID of the forum court.
            favorable_keywords: Terms that make a case favorable.
            unfavorable_keywords: Terms that make a case unfavorable.
            practice_areas: Filter to specific practice areas.
            date_min: Only include cases after this date.
            date_max: Only include cases before this date.
            max_results: Maximum results to return.
            include_persuasive: Include non-binding persuasive authority.

        Returns:
            PrecedentBrief with organized precedents.
        """
        # If connected to CourtListener, fetch live results
        if self._cl is not None:
            await self._fetch_from_courtlistener(query, max_results)

        # Score all cases in local DB
        candidates: List[PrecedentCandidate] = []
        for case in self._case_db:
            # Date filtering
            if date_min and case.get("date_filed", "0") < date_min:
                continue
            if date_max and case.get("date_filed", "9") > date_max:
                continue
            # Practice area filtering
            if practice_areas:
                case_areas = case.get("practice_areas", [])
                if not any(pa.lower() in [a.lower() for a in case_areas] for pa in practice_areas):
                    continue

            candidate = self._score_case(
                query, case, forum_court,
                favorable_keywords, unfavorable_keywords
            )
            if candidate:
                candidates.append(candidate)

        # Sort by combined score
        candidates.sort(key=lambda c: c.combined_score, reverse=True)
        candidates = candidates[:max_results]

        # Categorize
        binding_favorable = [c for c in candidates if c.is_binding and c.is_favorable]
        binding_unfavorable = [c for c in candidates if c.is_binding and not c.is_favorable]
        persuasive = [c for c in candidates if not c.is_binding] if include_persuasive else []
        landmarks = [c for c in candidates if c.authority_score > 0.5]

        brief = PrecedentBrief(
            query=query,
            jurisdiction=forum_court,
            binding_precedents=binding_favorable,
            persuasive_precedents=persuasive,
            unfavorable_precedents=binding_unfavorable,
            landmark_cases=landmarks,
        )
        brief.summary = self._generate_summary(brief)
        return brief

    async def _fetch_from_courtlistener(self, query: str, max_results: int) -> None:
        """Fetch cases from CourtListener and add to local cache."""
        try:
            result = await self._cl.search_opinions(query=query, page_size=min(max_results, 50))
            for r in result.get("results", []):
                case = {
                    "opinion_id": r.get("id", 0),
                    "cluster_id": r.get("cluster_id", 0),
                    "case_name": r.get("caseName", ""),
                    "citation": r.get("citation", [""])[0] if r.get("citation") else "",
                    "court": r.get("court_id", ""),
                    "date_filed": r.get("dateFiled"),
                    "holding": r.get("snippet", ""),
                    "text": r.get("text", ""),
                    "practice_areas": [r.get("suitNature", "")],
                    "pagerank_score": r.get("citeCount", 0) / 10000.0,
                    "url": f"https://www.courtlistener.com{r.get('absolute_url', '')}",
                }
                if not any(c.get("opinion_id") == case["opinion_id"] for c in self._case_db):
                    self._case_db.append(case)
        except Exception as exc:
            logger.error("Failed to fetch from CourtListener: %s", exc)

    def _generate_summary(self, brief: PrecedentBrief) -> str:
        """Generate a plain-English summary of the precedent brief."""
        lines = [f"Precedent Research: {brief.query}", ""]
        lines.append(f"Forum: {brief.jurisdiction}")
        lines.append(f"Binding favorable precedents: {len(brief.binding_precedents)}")
        lines.append(f"Binding unfavorable precedents: {len(brief.unfavorable_precedents)}")
        lines.append(f"Persuasive authority: {len(brief.persuasive_precedents)}")
        lines.append(f"Landmark cases: {len(brief.landmark_cases)}")

        if brief.binding_precedents:
            lines.append("\nTop binding favorable precedents:")
            for p in brief.binding_precedents[:3]:
                lines.append(f"  - {p.case_name} ({p.citation}) [score: {p.combined_score:.3f}]")

        if brief.unfavorable_precedents:
            lines.append("\nBinding unfavorable precedents to distinguish:")
            for p in brief.unfavorable_precedents[:3]:
                lines.append(f"  - {p.case_name} ({p.citation}) [score: {p.combined_score:.3f}]")

        return "\n".join(lines)

    async def find_analogous_cases(
        self,
        query: str,
        source_practice_area: str,
        target_practice_area: str,
        max_results: int = 10,
    ) -> List[PrecedentCandidate]:
        """
        Find analogous cases across different practice areas.

        Args:
            query: Legal principle or fact pattern.
            source_practice_area: Primary practice area (e.g., "criminal law").
            target_practice_area: Analogous area (e.g., "administrative law").
            max_results: Max results.

        Returns:
            List of analogous PrecedentCandidate objects.
        """
        brief = await self.find(
            query=query,
            practice_areas=[source_practice_area, target_practice_area],
            max_results=max_results * 2,
        )
        all_candidates = (
            brief.binding_precedents
            + brief.persuasive_precedents
            + brief.unfavorable_precedents
        )
        return sorted(all_candidates, key=lambda c: c.combined_score, reverse=True)[:max_results]
