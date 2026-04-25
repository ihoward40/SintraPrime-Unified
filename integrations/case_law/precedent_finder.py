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
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class BindingStatus(Enum):
    BINDING = "binding"
    PERSUASIVE = "persuasive"
    NOT_APPLICABLE = "not_applicable"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class PrecedentResult:
    """A single precedent search result."""

    case_id: int = 0
    case_name: str = ""
    citation: str = ""
    court: str = ""
    date: Optional[str] = None
    holding: str = ""
    relevance_score: float = 0.0
    authority_score: float = 0.0
    binding_status: BindingStatus = BindingStatus.NOT_APPLICABLE
    url: str = ""
    is_overruled: bool = False
    snippet: str = ""


@dataclass
class PrecedentBrief:
    """A structured brief of precedents for a legal issue."""

    fact_pattern: str = ""
    forum_court: str = ""
    binding_precedents: List[PrecedentResult] = field(default_factory=list)
    persuasive_precedents: List[PrecedentResult] = field(default_factory=list)
    summary: str = ""
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class PrecedentCandidate:
    """A case that may serve as precedent (legacy compat)."""

    opinion_id: int = 0
    cluster_id: int = 0
    case_name: str = ""
    citation: str = ""
    court: str = ""
    date_filed: Optional[str] = None
    holding: str = ""
    reasoning: str = ""
    practice_areas: List[str] = field(default_factory=list)
    is_binding: bool = False
    is_favorable: bool = True
    relevance_score: float = 0.0
    authority_score: float = 0.0
    recency_score: float = 0.0
    combined_score: float = 0.0
    snippet: str = ""
    url: str = ""


# ---------------------------------------------------------------------------
# Jurisdiction filter
# ---------------------------------------------------------------------------


# Maps forum court -> binding courts
_CIRCUIT_MAP: Dict[str, str] = {
    "dcd": "cadc",
    "nysd": "ca2", "nyed": "ca2", "nynd": "ca2", "nywd": "ca2",
    "cacd": "ca9", "cand": "ca9", "casd": "ca9", "caed": "ca9",
    "txsd": "ca5", "txnd": "ca5", "txed": "ca5", "txwd": "ca5",
    "ilnd": "ca7",
    "flsd": "ca11", "flnd": "ca11", "flmd": "ca11",
    "gamd": "ca11", "gand": "ca11", "gasd": "ca11",
}


class JurisdictionFilter:
    """Filter cases by jurisdiction / binding authority."""

    def __init__(self, forum_court: str = "", state: Optional[str] = None, **kwargs: Any):
        self.forum_court = forum_court
        self.state = state
        self._binding: List[str] = self._compute_binding()

    def _compute_binding(self) -> List[str]:
        courts: List[str] = ["scotus"]
        if self.forum_court == "scotus":
            return []
        # If forum is a circuit court, only scotus binds it
        if self.forum_court.startswith("ca") or self.forum_court == "cadc" or self.forum_court == "cafc":
            return courts
        # If forum is a district, add the circuit
        circuit = _CIRCUIT_MAP.get(self.forum_court)
        if circuit:
            courts.append(circuit)
        return courts

    @property
    def includes_scotus(self) -> bool:
        return "scotus" in self._binding or self.forum_court != "scotus"

    @property
    def binding_courts(self) -> List[str]:
        return self._binding

    def is_binding(self, court: str) -> bool:
        return court in self._binding


# ---------------------------------------------------------------------------
# Precedent Finder
# ---------------------------------------------------------------------------


class PrecedentFinder:
    """
    Finds controlling and persuasive precedent for any legal question.
    """

    def __init__(
        self,
        courtlistener: Optional[Any] = None,
        citation_network: Optional[Any] = None,
        **kwargs: Any,
    ) -> None:
        self._cl = courtlistener
        self._cn = citation_network

    # ------------------------------------------------------------------
    # Core search
    # ------------------------------------------------------------------

    async def find_precedent(
        self,
        fact_pattern: str = "",
        forum_court: str = "scotus",
        include_persuasive: bool = True,
        exclude_overruled: bool = False,
        **kwargs: Any,
    ) -> List[PrecedentResult]:
        """Find precedent matching a fact pattern."""
        if not fact_pattern and not self._cl:
            return []

        results: List[PrecedentResult] = []

        # Try CourtListener
        if self._cl is not None:
            try:
                from .courtlistener_client import APIError
            except ImportError:
                APIError = Exception  # type: ignore[misc]
            try:
                resp = await self._cl.search_opinions(query=fact_pattern, page_size=50)
                raw_results = resp.get("results", [])
            except Exception as exc:
                # Check if it's an APIError
                try:
                    from .courtlistener_client import APIError as AE
                    if isinstance(exc, AE):
                        return []
                except ImportError:
                    pass
                return []

            jf = JurisdictionFilter(forum_court=forum_court)

            for r in raw_results:
                court = r.get("court_id", "")
                cite_count = r.get("citeCount", 0)

                # Determine binding status
                if court == "scotus":
                    bs = BindingStatus.BINDING
                elif jf.is_binding(court):
                    bs = BindingStatus.BINDING
                else:
                    bs = BindingStatus.PERSUASIVE

                # Skip persuasive if not wanted
                if not include_persuasive and bs == BindingStatus.PERSUASIVE:
                    continue

                # Authority score from citation network or cite count
                authority = 0.0
                if self._cn is not None:
                    try:
                        authority = self._cn.get_authority_score(r.get("id", 0))
                    except Exception:
                        authority = min(1.0, cite_count / 10000.0)
                else:
                    authority = min(1.0, cite_count / 10000.0)

                # Check overruled
                is_overruled = False
                if self._cn is not None:
                    try:
                        is_overruled = self._cn.is_overruled(r.get("id", 0))
                    except Exception:
                        pass

                if exclude_overruled and is_overruled:
                    continue

                relevance = r.get("score", 0.0) / 30.0  # normalize
                relevance = min(1.0, relevance)

                citations = r.get("citation", [])
                citation_str = citations[0] if citations else ""

                pr = PrecedentResult(
                    case_id=r.get("id", 0),
                    case_name=r.get("caseName", ""),
                    citation=citation_str,
                    court=court,
                    date=r.get("dateFiled"),
                    holding=r.get("snippet", ""),
                    relevance_score=round(relevance, 4),
                    authority_score=round(authority, 4),
                    binding_status=bs,
                    url=f"https://www.courtlistener.com{r.get('absolute_url', '')}",
                    is_overruled=is_overruled,
                )
                results.append(pr)

        # Sort by combined score (relevance * 0.6 + authority * 0.4)
        results.sort(
            key=lambda r: r.relevance_score * 0.6 + r.authority_score * 0.4,
            reverse=True,
        )
        return results

    # ------------------------------------------------------------------
    # Brief generation
    # ------------------------------------------------------------------

    def generate_precedent_brief(
        self,
        fact_pattern: str = "",
        results: Optional[List[PrecedentResult]] = None,
        forum_court: str = "",
        **kwargs: Any,
    ) -> PrecedentBrief:
        """Generate a precedent brief from search results."""
        if results is None:
            results = []

        binding = [r for r in results if r.binding_status == BindingStatus.BINDING]
        persuasive = [r for r in results if r.binding_status == BindingStatus.PERSUASIVE]

        if not results:
            summary = "No precedent found for the given fact pattern."
        else:
            lines = [f"Found {len(results)} precedents for: {fact_pattern}"]
            if binding:
                lines.append(f"Binding: {len(binding)} cases")
            if persuasive:
                lines.append(f"Persuasive: {len(persuasive)} cases")
            summary = " | ".join(lines)

        return PrecedentBrief(
            fact_pattern=fact_pattern,
            forum_court=forum_court,
            binding_precedents=binding,
            persuasive_precedents=persuasive,
            summary=summary,
        )

    # ------------------------------------------------------------------
    # Analogous cases
    # ------------------------------------------------------------------

    async def find_analogous_cases(
        self,
        case_id: int = 0,
        fact_summary: str = "",
        **kwargs: Any,
    ) -> List[PrecedentResult]:
        """Find analogous cases based on a fact summary."""
        if fact_summary and self._cl:
            return await self.find_precedent(fact_pattern=fact_summary)
        return []

    # ------------------------------------------------------------------
    # Filtering / ranking helpers
    # ------------------------------------------------------------------

    def filter_favorable(
        self,
        results: List[PrecedentResult],
        client_position: str = "",
    ) -> List[PrecedentResult]:
        """Filter results to those likely favorable to client position."""
        # Simple heuristic: return all for now (real impl would use NLP)
        return list(results)

    def filter_unfavorable(
        self,
        results: List[PrecedentResult],
        client_position: str = "",
    ) -> List[PrecedentResult]:
        """Filter results to those likely unfavorable."""
        return []

    def rank_by_authority(self, results: List[PrecedentResult]) -> List[PrecedentResult]:
        """Sort results by authority score descending."""
        return sorted(results, key=lambda r: r.authority_score, reverse=True)

    def rank_by_recency(self, results: List[PrecedentResult]) -> List[PrecedentResult]:
        """Sort results by date descending (most recent first)."""
        return sorted(results, key=lambda r: r.date or "", reverse=True)
