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
    logger.warning("networkx not installed. Citation graph features limited.")

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

    opinion_id: int
    cluster_id: int
    case_name: str
    court: str
    date_filed: Optional[str]
    citation: str
    precedential_status: str
    citation_count: int = 0

    # Computed graph metrics
    pagerank_score: float = 0.0
    in_degree: int = 0
    out_degree: int = 0
    authority_score: float = 0.0
    hub_score: float = 0.0


@dataclass
class CitationEdge:
    """A directed edge: citing_id → cited_id."""

    citing_opinion_id: int
    cited_opinion_id: int
    citing_case: str
    cited_case: str
    year_cited: Optional[int]
    treatment: str = "cited"  # cited, distinguished, criticized, overruled, followed


@dataclass
class CitationReport:
    """Full citation analysis report for a case."""

    opinion_id: int
    case_name: str
    citation: str
    total_citations_received: int
    total_citations_given: int
    pagerank_score: float
    authority_rank: int
    cites: List[Dict[str, Any]]
    cited_by: List[Dict[str, Any]]
    landmark_cases_in_ancestry: List[str]
    is_overruled: bool
    overruling_case: Optional[str]
    treatment_summary: Dict[str, int]


# ---------------------------------------------------------------------------
# Citation Network Builder
# ---------------------------------------------------------------------------


class CitationNetworkBuilder:
    """
    Builds and analyzes a directed citation graph for court opinions.

    The graph is directed: an edge A → B means "A cites B".

    Usage:
        builder = CitationNetworkBuilder()
        builder.add_case(opinion_id=1, cluster_id=1, case_name="Marbury v. Madison",
                         court="scotus", date_filed="1803-02-24", citation="5 U.S. 137")
        builder.add_citation(citing_id=2, cited_id=1)
        report = builder.get_citation_report(1)
    """

    def __init__(self) -> None:
        if HAS_NETWORKX:
            self._graph: nx.DiGraph = nx.DiGraph()
        else:
            self._graph = None
        self._nodes: Dict[int, CaseNode] = {}
        self._edges: List[CitationEdge] = []
        self._pagerank_computed = False

    # ------------------------------------------------------------------
    # Building the graph
    # ------------------------------------------------------------------

    def add_case(
        self,
        opinion_id: int,
        cluster_id: int,
        case_name: str,
        court: str,
        date_filed: Optional[str],
        citation: str,
        precedential_status: str = "Published",
        citation_count: int = 0,
    ) -> CaseNode:
        """
        Add a case (opinion) node to the citation graph.

        Args:
            opinion_id: CourtListener opinion ID.
            cluster_id: CourtListener cluster ID.
            case_name: Case name (e.g., "Roe v. Wade").
            court: Court identifier (e.g., "scotus").
            date_filed: ISO date string.
            citation: Official citation (e.g., "410 U.S. 113").
            precedential_status: "Published" or "Unpublished".
            citation_count: Number of times cited (pre-computed).

        Returns:
            The CaseNode that was added.
        """
        node = CaseNode(
            opinion_id=opinion_id,
            cluster_id=cluster_id,
            case_name=case_name,
            court=court,
            date_filed=date_filed,
            citation=citation,
            precedential_status=precedential_status,
            citation_count=citation_count,
        )
        self._nodes[opinion_id] = node
        if self._graph is not None:
            self._graph.add_node(opinion_id, **{k: v for k, v in asdict(node).items()})
        self._pagerank_computed = False
        return node

    def add_citation(
        self,
        citing_id: int,
        cited_id: int,
        treatment: str = "cited",
        year_cited: Optional[int] = None,
    ) -> None:
        """
        Add a directed citation edge: citing_id → cited_id.

        Args:
            citing_id: Opinion ID of the citing case.
            cited_id: Opinion ID of the cited case.
            treatment: How the citing case treats the cited case.
            year_cited: Year the citation was made.
        """
        citing_node = self._nodes.get(citing_id)
        cited_node = self._nodes.get(cited_id)

        edge = CitationEdge(
            citing_opinion_id=citing_id,
            cited_opinion_id=cited_id,
            citing_case=citing_node.case_name if citing_node else f"Opinion {citing_id}",
            cited_case=cited_node.case_name if cited_node else f"Opinion {cited_id}",
            year_cited=year_cited,
            treatment=treatment,
        )
        self._edges.append(edge)

        if self._graph is not None:
            self._graph.add_edge(citing_id, cited_id, treatment=treatment, year=year_cited)
        self._pagerank_computed = False

    def add_citations_bulk(self, citation_pairs: List[Tuple[int, int]]) -> None:
        """Add multiple citation relationships at once."""
        for citing_id, cited_id in citation_pairs:
            self.add_citation(citing_id, cited_id)

    # ------------------------------------------------------------------
    # Graph analytics
    # ------------------------------------------------------------------

    def compute_authority_scores(self) -> None:
        """
        Compute PageRank and HITS authority/hub scores for all nodes.
        Updates node objects in place.
        """
        if not HAS_NETWORKX or self._graph is None or len(self._graph) == 0:
            logger.warning("Cannot compute authority scores: networkx unavailable or empty graph")
            return

        # PageRank: nodes with many citations from authoritative nodes rank higher
        try:
            pagerank = nx.pagerank(self._graph.reverse(), alpha=0.85, max_iter=100)
        except Exception as exc:
            logger.error("PageRank computation failed: %s", exc)
            pagerank = {}

        # HITS algorithm
        try:
            hits_hubs, hits_auth = nx.hits(self._graph.reverse(), max_iter=100, normalized=True)
        except Exception:
            hits_hubs, hits_auth = {}, {}

        # Update node objects
        for opinion_id, node in self._nodes.items():
            node.pagerank_score = pagerank.get(opinion_id, 0.0)
            node.in_degree = self._graph.in_degree(opinion_id) if opinion_id in self._graph else 0
            node.out_degree = self._graph.out_degree(opinion_id) if opinion_id in self._graph else 0
            node.authority_score = hits_auth.get(opinion_id, 0.0)
            node.hub_score = hits_hubs.get(opinion_id, 0.0)

        self._pagerank_computed = True
        logger.info("Authority scores computed for %d nodes", len(self._nodes))

    def get_top_cases_by_authority(self, n: int = 20) -> List[CaseNode]:
        """
        Get the N most authoritative cases by PageRank score.

        Args:
            n: Number of top cases to return.

        Returns:
            List of CaseNode sorted by authority (descending).
        """
        if not self._pagerank_computed:
            self.compute_authority_scores()
        return sorted(self._nodes.values(), key=lambda c: c.pagerank_score, reverse=True)[:n]

    def get_landmark_cases(self, threshold_percentile: float = 0.95) -> List[CaseNode]:
        """
        Identify landmark cases (top percentile by citation count + authority).

        Args:
            threshold_percentile: Cases above this percentile are "landmark".

        Returns:
            List of landmark CaseNode objects.
        """
        if not self._pagerank_computed:
            self.compute_authority_scores()

        if not self._nodes:
            return []

        scores = sorted(n.pagerank_score for n in self._nodes.values())
        if not scores:
            return []

        threshold_idx = int(len(scores) * threshold_percentile)
        threshold_score = scores[min(threshold_idx, len(scores) - 1)]

        return [
            n for n in self._nodes.values()
            if n.pagerank_score >= threshold_score
        ]

    # ------------------------------------------------------------------
    # Citation traversal
    # ------------------------------------------------------------------

    def get_cases_citing(self, opinion_id: int) -> List[CaseNode]:
        """Get all cases that directly cite the given opinion."""
        if self._graph is None:
            # Fallback: linear scan
            citing_ids = {e.citing_opinion_id for e in self._edges if e.cited_opinion_id == opinion_id}
        else:
            citing_ids = set(self._graph.predecessors(opinion_id))
        return [self._nodes[oid] for oid in citing_ids if oid in self._nodes]

    def get_cases_cited_by(self, opinion_id: int) -> List[CaseNode]:
        """Get all cases directly cited by the given opinion."""
        if self._graph is None:
            cited_ids = {e.cited_opinion_id for e in self._edges if e.citing_opinion_id == opinion_id}
        else:
            cited_ids = set(self._graph.successors(opinion_id))
        return [self._nodes[oid] for oid in cited_ids if oid in self._nodes]

    def get_citation_chain(
        self,
        from_id: int,
        to_id: int,
        max_depth: int = 5,
    ) -> Optional[List[CaseNode]]:
        """
        Find the shortest citation chain from one case to another.

        Args:
            from_id: Starting opinion ID.
            to_id: Target opinion ID.
            max_depth: Maximum chain length to search.

        Returns:
            List of CaseNode forming the chain, or None if no path exists.
        """
        if self._graph is not None:
            try:
                path = nx.shortest_path(self._graph, from_id, to_id)
                return [self._nodes[n] for n in path if n in self._nodes]
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                return None
        else:
            # BFS fallback
            queue: deque = deque([(from_id, [from_id])])
            visited: Set[int] = {from_id}
            while queue:
                current, path = queue.popleft()
                if len(path) > max_depth:
                    continue
                for edge in self._edges:
                    if edge.citing_opinion_id == current:
                        nxt = edge.cited_opinion_id
                        if nxt == to_id:
                            return [self._nodes[n] for n in path + [nxt] if n in self._nodes]
                        if nxt not in visited:
                            visited.add(nxt)
                            queue.append((nxt, path + [nxt]))
            return None

    def get_all_ancestors(self, opinion_id: int, max_depth: int = 3) -> Set[int]:
        """
        Get all cases in the citation ancestry (cases this case traces back to).

        Args:
            opinion_id: Root opinion.
            max_depth: Maximum hops back in history.

        Returns:
            Set of opinion IDs.
        """
        ancestors: Set[int] = set()
        queue: deque = deque([(opinion_id, 0)])
        while queue:
            current, depth = queue.popleft()
            if depth >= max_depth:
                continue
            for edge in self._edges:
                if edge.citing_opinion_id == current and edge.cited_opinion_id not in ancestors:
                    ancestors.add(edge.cited_opinion_id)
                    queue.append((edge.cited_opinion_id, depth + 1))
        return ancestors

    def get_all_descendants(self, opinion_id: int, max_depth: int = 3) -> Set[int]:
        """Get all cases that cite back to this opinion (transitively)."""
        descendants: Set[int] = set()
        queue: deque = deque([(opinion_id, 0)])
        while queue:
            current, depth = queue.popleft()
            if depth >= max_depth:
                continue
            for edge in self._edges:
                if edge.cited_opinion_id == current and edge.citing_opinion_id not in descendants:
                    descendants.add(edge.citing_opinion_id)
                    queue.append((edge.citing_opinion_id, depth + 1))
        return descendants

    # ------------------------------------------------------------------
    # Overruling detection
    # ------------------------------------------------------------------

    def is_overruled(self, opinion_id: int) -> Tuple[bool, Optional[str]]:
        """
        Check if an opinion has been overruled.

        Args:
            opinion_id: The opinion to check.

        Returns:
            Tuple of (is_overruled: bool, overruling_case: Optional case name).
        """
        for edge in self._edges:
            if edge.cited_opinion_id == opinion_id and edge.treatment == "overruled":
                overruling = self._nodes.get(edge.citing_opinion_id)
                return True, overruling.case_name if overruling else f"Opinion {edge.citing_opinion_id}"
        return False, None

    def get_treatment_history(self, opinion_id: int) -> Dict[str, List[str]]:
        """
        Get full treatment history for an opinion.

        Returns:
            Dict mapping treatment type → list of citing case names.
        """
        treatments: Dict[str, List[str]] = defaultdict(list)
        for edge in self._edges:
            if edge.cited_opinion_id == opinion_id:
                node = self._nodes.get(edge.citing_opinion_id)
                case_name = node.case_name if node else f"Opinion {edge.citing_opinion_id}"
                treatments[edge.treatment].append(case_name)
        return dict(treatments)

    # ------------------------------------------------------------------
    # Reports
    # ------------------------------------------------------------------

    def get_citation_report(self, opinion_id: int) -> CitationReport:
        """
        Generate a comprehensive citation report for an opinion.

        Args:
            opinion_id: The opinion to analyze.

        Returns:
            CitationReport with full citation analysis.
        """
        if not self._pagerank_computed:
            self.compute_authority_scores()

        node = self._nodes.get(opinion_id)
        if not node:
            raise CitationNetworkError(f"Opinion {opinion_id} not in graph")

        cites = self.get_cases_cited_by(opinion_id)
        cited_by = self.get_cases_citing(opinion_id)
        is_overruled, overruling_case = self.is_overruled(opinion_id)
        treatments = self.get_treatment_history(opinion_id)
        ancestors = self.get_all_ancestors(opinion_id, max_depth=2)
        landmark_ancestors = [
            self._nodes[aid].case_name
            for aid in ancestors
            if aid in self._nodes and self._nodes[aid].pagerank_score > 0.01
        ]

        # Rank by authority
        sorted_nodes = sorted(self._nodes.values(), key=lambda n: n.pagerank_score, reverse=True)
        authority_rank = next(
            (i + 1 for i, n in enumerate(sorted_nodes) if n.opinion_id == opinion_id), -1
        )

        return CitationReport(
            opinion_id=opinion_id,
            case_name=node.case_name,
            citation=node.citation,
            total_citations_received=len(cited_by),
            total_citations_given=len(cites),
            pagerank_score=node.pagerank_score,
            authority_rank=authority_rank,
            cites=[{"id": n.opinion_id, "case": n.case_name, "citation": n.citation} for n in cites],
            cited_by=[{"id": n.opinion_id, "case": n.case_name, "citation": n.citation} for n in cited_by],
            landmark_cases_in_ancestry=landmark_ancestors[:10],
            is_overruled=is_overruled,
            overruling_case=overruling_case,
            treatment_summary={t: len(cases) for t, cases in treatments.items()},
        )

    # ------------------------------------------------------------------
    # Visualization export
    # ------------------------------------------------------------------

    def export_to_json(
        self,
        max_nodes: int = 500,
        min_authority_score: float = 0.0,
    ) -> str:
        """
        Export the citation graph as a JSON string for d3.js visualization.

        Format:
        {
            "nodes": [{"id": int, "name": str, "court": str, "score": float, ...}],
            "links": [{"source": int, "target": int, "treatment": str}]
        }

        Args:
            max_nodes: Maximum nodes to include (top by authority).
            min_authority_score: Filter nodes below this score.

        Returns:
            JSON string.
        """
        if not self._pagerank_computed:
            self.compute_authority_scores()

        # Select top nodes
        sorted_nodes = sorted(
            self._nodes.values(),
            key=lambda n: n.pagerank_score,
            reverse=True,
        )
        selected = [
            n for n in sorted_nodes
            if n.pagerank_score >= min_authority_score
        ][:max_nodes]
        selected_ids = {n.opinion_id for n in selected}

        nodes_json = [
            {
                "id": n.opinion_id,
                "name": n.case_name,
                "citation": n.citation,
                "court": n.court,
                "date": n.date_filed,
                "score": round(n.pagerank_score, 6),
                "authority": round(n.authority_score, 6),
                "in_degree": n.in_degree,
                "out_degree": n.out_degree,
            }
            for n in selected
        ]

        links_json = [
            {
                "source": e.citing_opinion_id,
                "target": e.cited_opinion_id,
                "treatment": e.treatment,
            }
            for e in self._edges
            if e.citing_opinion_id in selected_ids and e.cited_opinion_id in selected_ids
        ]

        return json.dumps({"nodes": nodes_json, "links": links_json}, indent=2)

    def export_to_gexf(self, output_path: str) -> str:
        """Export graph to GEXF format (for Gephi visualization)."""
        if not HAS_NETWORKX or self._graph is None:
            raise CitationNetworkError("networkx required for GEXF export")
        nx.write_gexf(self._graph, output_path)
        return output_path

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_statistics(self) -> Dict[str, Any]:
        """Get summary statistics for the citation network."""
        if not self._pagerank_computed:
            self.compute_authority_scores()

        overruled_count = sum(
            1 for oid in self._nodes if self.is_overruled(oid)[0]
        )

        return {
            "total_cases": len(self._nodes),
            "total_citations": len(self._edges),
            "average_citations_per_case": (
                len(self._edges) / len(self._nodes) if self._nodes else 0
            ),
            "most_cited": (
                max(self._nodes.values(), key=lambda n: n.in_degree).case_name
                if self._nodes else None
            ),
            "most_citing": (
                max(self._nodes.values(), key=lambda n: n.out_degree).case_name
                if self._nodes else None
            ),
            "overruled_cases": overruled_count,
            "treatment_breakdown": self._get_treatment_breakdown(),
        }

    def _get_treatment_breakdown(self) -> Dict[str, int]:
        breakdown: Dict[str, int] = defaultdict(int)
        for edge in self._edges:
            breakdown[edge.treatment] += 1
        return dict(breakdown)
