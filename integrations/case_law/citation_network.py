"""
Citation Network Builder
========================
Builds and analyzes directed citation graphs for court opinions.

Uses networkx for graph operations and provides:
- PageRank-style authority scoring
- Landmark/foundational case identification
- Citation chain visualization
- Overruled/distinguished case detection
- JSON export for d3.js visualization
- Citation reports
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class CitationNetworkError(Exception):
    """Base citation network exception."""


class GraphNotBuiltError(CitationNetworkError):
    """The citation graph has not been built yet."""


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class CaseNode:
    """A node in the citation graph."""

    case_id: int
    case_name: str
    court: str
    year: int
    citation: str

    # Optional / computed
    authority_score: float = 0.0
    is_overruled: bool = False
    overruled_by: Optional[int] = None
    practice_areas: List[str] = field(default_factory=list)
    citation_count: int = 0
    pagerank_score: float = 0.0
    in_degree: int = 0
    out_degree: int = 0
    hub_score: float = 0.0


@dataclass
class CitationEdge:
    """A directed edge: citing_id -> cited_id."""

    citing_id: int
    cited_id: int
    treatment: str = "cited"
    weight: float = 1.0


@dataclass
class CitationReport:
    """Citation analysis report for a case."""

    case_id: int
    case_name: str = ""
    citation: str = ""
    total_citing_cases: int = 0
    total_cited_cases: int = 0
    authority_score: float = 0.0
    authority_rank: int = 0
    is_overruled: bool = False
    overruled_by: Optional[int] = None


# ---------------------------------------------------------------------------
# Citation Network
# ---------------------------------------------------------------------------


class CitationNetwork:
    """
    Builds and analyzes a directed citation graph for court opinions.
    """

    def __init__(self) -> None:
        self._cases: Dict[int, CaseNode] = {}
        self._edges: List[CitationEdge] = []
        self._authority_computed = False

    def add_case(
        self,
        case_id: int = 0,
        case_name: str = "",
        court: str = "",
        year: int = 0,
        citation: str = "",
        **kwargs: Any,
    ) -> CaseNode:
        if case_id in self._cases:
            return self._cases[case_id]
        node = CaseNode(
            case_id=case_id,
            case_name=case_name,
            court=court,
            year=year,
            citation=citation,
        )
        self._cases[case_id] = node
        self._authority_computed = False
        return node

    def add_citation(
        self,
        citing_id: int = 0,
        cited_id: int = 0,
        treatment: str = "cited",
        weight: float = 1.0,
        **kwargs: Any,
    ) -> CitationEdge:
        if citing_id not in self._cases or cited_id not in self._cases:
            raise ValueError(
                f"Both citing_id={citing_id} and cited_id={cited_id} must exist in the network"
            )
        edge = CitationEdge(
            citing_id=citing_id,
            cited_id=cited_id,
            treatment=treatment,
            weight=weight,
        )
        self._edges.append(edge)
        self._authority_computed = False
        return edge

    # ------------------------------------------------------------------
    # Traversal helpers
    # ------------------------------------------------------------------

    def get_cases_citing(self, case_id: int) -> List[CaseNode]:
        """Get all cases that directly cite the given case."""
        citing_ids = {e.citing_id for e in self._edges if e.cited_id == case_id}
        return [self._cases[cid] for cid in citing_ids if cid in self._cases]

    def get_cases_cited_by(self, case_id: int) -> List[CaseNode]:
        """Get all cases directly cited by the given case."""
        cited_ids = {e.cited_id for e in self._edges if e.citing_id == case_id}
        return [self._cases[cid] for cid in cited_ids if cid in self._cases]

    def get_citation_count(self, case_id: int) -> int:
        """Return number of cases that cite the given case."""
        return len([e for e in self._edges if e.cited_id == case_id])

    # ------------------------------------------------------------------
    # Authority scoring
    # ------------------------------------------------------------------

    def compute_authority_scores(self) -> None:
        """Compute authority scores for all cases using simple citation counting + court weight."""
        court_weights = {"scotus": 3.0, "cadc": 1.5}
        for cid, node in self._cases.items():
            cite_count = self.get_citation_count(cid)
            court_w = court_weights.get(node.court, 1.0)
            node.authority_score = cite_count * court_w
            node.citation_count = cite_count
        self._authority_computed = True

    # ------------------------------------------------------------------
    # Citation chain / depth
    # ------------------------------------------------------------------

    def find_citation_chain(
        self, source_id: int, target_id: int, max_depth: int = 10
    ) -> Optional[List[int]]:
        """BFS from source following citing->cited edges to find target."""
        if source_id not in self._cases or target_id not in self._cases:
            return None
        if source_id == target_id:
            return [source_id]

        # Build adjacency: citing -> [cited]
        adj: Dict[int, List[int]] = defaultdict(list)
        for e in self._edges:
            adj[e.citing_id].append(e.cited_id)

        visited: Set[int] = {source_id}
        queue: deque = deque([(source_id, [source_id])])
        while queue:
            current, path = queue.popleft()
            if len(path) > max_depth:
                continue
            for nxt in adj.get(current, []):
                if nxt == target_id:
                    return path + [nxt]
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append((nxt, path + [nxt]))
        return None

    def get_citation_depth(
        self, starting_id: int, max_depth: int = 3
    ) -> Dict[int, int]:
        """BFS from starting_id following citing->cited edges, returning {case_id: depth}."""
        adj: Dict[int, List[int]] = defaultdict(list)
        for e in self._edges:
            adj[e.citing_id].append(e.cited_id)

        result: Dict[int, int] = {}
        visited: Set[int] = {starting_id}
        queue: deque = deque([(starting_id, 0)])
        while queue:
            current, depth = queue.popleft()
            if depth >= max_depth:
                continue
            for nxt in adj.get(current, []):
                if nxt not in visited:
                    visited.add(nxt)
                    result[nxt] = depth + 1
                    queue.append((nxt, depth + 1))
        return result

    # ------------------------------------------------------------------
    # Overruling
    # ------------------------------------------------------------------

    def mark_overruled(self, case_id: int, overruled_by_id: int) -> None:
        node = self._cases.get(case_id)
        if node:
            node.is_overruled = True
            node.overruled_by = overruled_by_id

    def is_overruled(self, case_id: int) -> bool:
        node = self._cases.get(case_id)
        return node.is_overruled if node else False

    # ------------------------------------------------------------------
    # Landmark / most-cited
    # ------------------------------------------------------------------

    def get_landmark_cases(self, top_n: int = 10) -> List[CaseNode]:
        if not self._authority_computed:
            self.compute_authority_scores()
        return sorted(
            self._cases.values(), key=lambda n: n.authority_score, reverse=True
        )[:top_n]

    def get_most_cited_in_court(self, court: str, top_n: int = 10) -> List[CaseNode]:
        if not self._authority_computed:
            self.compute_authority_scores()
        court_cases = [n for n in self._cases.values() if n.court == court]
        return sorted(court_cases, key=lambda n: n.authority_score, reverse=True)[
            :top_n
        ]

    # ------------------------------------------------------------------
    # Export / report
    # ------------------------------------------------------------------

    def export_json_graph(self) -> str:
        nodes = [
            {
                "id": n.case_id,
                "name": n.case_name,
                "court": n.court,
                "year": n.year,
                "citation": n.citation,
                "authority_score": n.authority_score,
            }
            for n in self._cases.values()
        ]
        links = [
            {
                "source": e.citing_id,
                "target": e.cited_id,
                "treatment": e.treatment,
            }
            for e in self._edges
        ]
        return json.dumps({"nodes": nodes, "links": links})

    def generate_citation_report(self, case_id: int) -> CitationReport:
        node = self._cases.get(case_id)
        if not node:
            raise CitationNetworkError(f"Case {case_id} not in network")
        citing = self.get_cases_citing(case_id)
        cited = self.get_cases_cited_by(case_id)
        return CitationReport(
            case_id=case_id,
            case_name=node.case_name,
            citation=node.citation,
            total_citing_cases=len(citing),
            total_cited_cases=len(cited),
            authority_score=node.authority_score,
            is_overruled=node.is_overruled,
            overruled_by=node.overruled_by,
        )

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_cases": len(self._cases),
            "total_citations": len(self._edges),
        }


# Keep old name as alias for backward compatibility
CitationNetworkBuilder = CitationNetwork
