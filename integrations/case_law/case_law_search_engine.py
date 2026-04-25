"""
Case Law Search Engine
======================
Unified federated search across CourtListener, PACER, Congress.gov,
and regulatory sources via a single query interface.

Features:
- Natural language query understanding
- Multi-source federated search
- Relevance ranking
- Faceted filtering (court, date, practice area, jurisdiction)
- Saved searches
- Export to CSV/JSON/PDF
- Integration with PrecedentFinder
"""

from __future__ import annotations

import asyncio
import csv
import io
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class SearchQuery:
    """A parsed and structured search query."""

    raw_query: str
    terms: List[str]
    phrase: Optional[str]
    court_filter: Optional[str]
    date_min: Optional[str]
    date_max: Optional[str]
    practice_area: Optional[str]
    jurisdiction: Optional[str]
    source_filters: List[str]          # "opinions", "dockets", "bills", "regulations"
    order_by: str = "relevance"
    page: int = 1
    page_size: int = 20


@dataclass
class SearchResultItem:
    """A single result from the unified search engine."""

    result_id: str
    source: str                  # "courtlistener", "pacer", "congress", "federal_register"
    result_type: str             # "opinion", "docket", "bill", "regulation"
    title: str
    url: str
    date: Optional[str]
    court_or_agency: str
    snippet: str
    relevance_score: float
    authority_score: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResults:
    """Complete results from a unified search."""

    query: str
    total_results: int
    results: List[SearchResultItem]
    facets: Dict[str, Dict[str, int]]   # facet_name → {value: count}
    sources_queried: List[str]
    search_time_ms: float
    page: int
    page_size: int
    has_next_page: bool


@dataclass
class SavedSearch:
    """A saved search configuration."""

    search_id: str
    name: str
    query: SearchQuery
    created_at: str
    last_run: Optional[str] = None
    run_count: int = 0
    alert_enabled: bool = False


# ---------------------------------------------------------------------------
# Query parser
# ---------------------------------------------------------------------------


class QueryParser:
    """Parses natural language legal queries into structured SearchQuery."""

    COURT_KEYWORDS = {
        "supreme court": "scotus",
        "scotus": "scotus",
        "ninth circuit": "ca9",
        "second circuit": "ca2",
        "first circuit": "ca1",
        "third circuit": "ca3",
        "fourth circuit": "ca4",
        "fifth circuit": "ca5",
        "sixth circuit": "ca6",
        "seventh circuit": "ca7",
        "eighth circuit": "ca8",
        "tenth circuit": "ca10",
        "eleventh circuit": "ca11",
        "dc circuit": "cadc",
        "federal circuit": "cafc",
    }

    PRACTICE_AREA_KEYWORDS = {
        "fourth amendment": "constitutional law",
        "first amendment": "constitutional law",
        "civil rights": "civil rights",
        "securities": "securities law",
        "antitrust": "antitrust",
        "patent": "intellectual property",
        "copyright": "intellectual property",
        "bankruptcy": "bankruptcy",
        "immigration": "immigration",
        "tax": "tax law",
        "employment": "employment law",
        "environmental": "environmental law",
        "criminal": "criminal law",
        "contract": "contract law",
        "tort": "tort law",
    }

    def parse(self, raw_query: str, **kwargs: Any) -> SearchQuery:
        """
        Parse a natural language query into a SearchQuery.

        Args:
            raw_query: The raw search string.
            **kwargs: Override specific query fields.

        Returns:
            Structured SearchQuery.
        """
        q_lower = raw_query.lower()

        # Extract quoted phrases
        import re
        phrases = re.findall(r'"([^"]+)"', raw_query)
        phrase = phrases[0] if phrases else None

        # Remove quotes from terms
        clean = re.sub(r'"[^"]*"', "", raw_query).strip()
        terms = [t for t in clean.split() if len(t) > 1]

        # Detect court filter
        court_filter = kwargs.get("court")
        if not court_filter:
            for keyword, court_id in self.COURT_KEYWORDS.items():
                if keyword in q_lower:
                    court_filter = court_id
                    break

        # Detect practice area
        practice_area = kwargs.get("practice_area")
        if not practice_area:
            for keyword, area in self.PRACTICE_AREA_KEYWORDS.items():
                if keyword in q_lower:
                    practice_area = area
                    break

        return SearchQuery(
            raw_query=raw_query,
            terms=terms,
            phrase=phrase,
            court_filter=court_filter or kwargs.get("court_filter"),
            date_min=kwargs.get("date_min"),
            date_max=kwargs.get("date_max"),
            practice_area=practice_area,
            jurisdiction=kwargs.get("jurisdiction"),
            source_filters=kwargs.get("source_filters", ["opinions", "dockets", "bills", "regulations"]),
            order_by=kwargs.get("order_by", "relevance"),
            page=kwargs.get("page", 1),
            page_size=kwargs.get("page_size", 20),
        )


# ---------------------------------------------------------------------------
# Unified Search Engine
# ---------------------------------------------------------------------------


class CaseLawSearchEngine:
    """
    Federated search across all SintraPrime legal data sources.

    Usage:
        engine = CaseLawSearchEngine(
            courtlistener=cl_client,
            congress=congress_client,
            regulatory=reg_monitor,
        )
        results = await engine.search("Fourth Amendment cell phone warrant")
        brief_csv = engine.export_csv(results)
    """

    def __init__(
        self,
        courtlistener: Optional[Any] = None,
        congress: Optional[Any] = None,
        regulatory: Optional[Any] = None,
        precedent_finder: Optional[Any] = None,
    ) -> None:
        self._cl = courtlistener
        self._congress = congress
        self._regulatory = regulatory
        self._precedent_finder = precedent_finder
        self._query_parser = QueryParser()
        self._saved_searches: Dict[str, SavedSearch] = {}
        self._search_history: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Main search
    # ------------------------------------------------------------------

    async def search(
        self,
        query: str,
        sources: Optional[List[str]] = None,
        court: Optional[str] = None,
        date_min: Optional[str] = None,
        date_max: Optional[str] = None,
        practice_area: Optional[str] = None,
        jurisdiction: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        order_by: str = "relevance",
    ) -> SearchResults:
        """
        Execute a federated search across all configured sources.

        Args:
            query: Natural language or boolean search query.
            sources: List of sources to search (default all configured).
            court: Filter by specific court ID.
            date_min: ISO date lower bound.
            date_max: ISO date upper bound.
            practice_area: Filter by practice area.
            jurisdiction: State or federal jurisdiction.
            page: Page number.
            page_size: Results per page.
            order_by: Sort order ("relevance", "date", "authority").

        Returns:
            SearchResults with ranked, faceted results.
        """
        start_time = datetime.utcnow()

        parsed_query = self._query_parser.parse(
            query,
            court_filter=court,
            date_min=date_min,
            date_max=date_max,
            practice_area=practice_area,
            jurisdiction=jurisdiction,
            page=page,
            page_size=page_size,
            order_by=order_by,
            source_filters=sources or ["opinions", "dockets", "bills", "regulations"],
        )

        # Fan out searches concurrently
        search_tasks = []
        sources_queried = []

        if "opinions" in parsed_query.source_filters and self._cl:
            search_tasks.append(self._search_opinions(parsed_query))
            sources_queried.append("courtlistener")

        if "dockets" in parsed_query.source_filters and self._cl:
            search_tasks.append(self._search_dockets(parsed_query))
            sources_queried.append("pacer")

        if "bills" in parsed_query.source_filters and self._congress:
            search_tasks.append(self._search_bills(parsed_query))
            sources_queried.append("congress")

        if "regulations" in parsed_query.source_filters and self._regulatory:
            search_tasks.append(self._search_regulations(parsed_query))
            sources_queried.append("federal_register")

        if not search_tasks:
            logger.warning("No search sources configured")
            return SearchResults(
                query=query,
                total_results=0,
                results=[],
                facets={},
                sources_queried=[],
                search_time_ms=0.0,
                page=page,
                page_size=page_size,
                has_next_page=False,
            )

        task_results = await asyncio.gather(*search_tasks, return_exceptions=True)
        all_items: List[SearchResultItem] = []

        for result in task_results:
            if isinstance(result, Exception):
                logger.error("Search source error: %s", result)
            else:
                all_items.extend(result)

        # Rank and deduplicate
        ranked = self._rank_results(all_items, parsed_query)

        # Build facets
        facets = self._build_facets(ranked)

        # Paginate
        start = (page - 1) * page_size
        page_items = ranked[start : start + page_size]

        elapsed = (datetime.utcnow() - start_time).total_seconds() * 1000

        results = SearchResults(
            query=query,
            total_results=len(ranked),
            results=page_items,
            facets=facets,
            sources_queried=sources_queried,
            search_time_ms=round(elapsed, 1),
            page=page,
            page_size=page_size,
            has_next_page=(start + page_size) < len(ranked),
        )

        # Log to history
        self._search_history.append({
            "query": query,
            "timestamp": datetime.utcnow().isoformat(),
            "total_results": results.total_results,
            "search_time_ms": results.search_time_ms,
        })

        return results

    async def _search_opinions(self, q: SearchQuery) -> List[SearchResultItem]:
        """Search CourtListener opinions."""
        try:
            data = await self._cl.search_opinions(
                query=q.raw_query,
                court=q.court_filter,
                date_filed_min=q.date_min,
                date_filed_max=q.date_max,
                page_size=q.page_size * 2,
            )
            items = []
            for r in data.get("results", []):
                items.append(
                    SearchResultItem(
                        result_id=f"cl_opinion_{r.get('id', '')}",
                        source="courtlistener",
                        result_type="opinion",
                        title=r.get("caseName", "Unknown Case"),
                        url=f"https://www.courtlistener.com{r.get('absolute_url', '')}",
                        date=r.get("dateFiled"),
                        court_or_agency=r.get("court_id", ""),
                        snippet=r.get("snippet", "")[:400],
                        relevance_score=float(r.get("score", 0)),
                        authority_score=float(r.get("citeCount", 0)) / 1000.0,
                        metadata={
                            "citation": r.get("citation", []),
                            "status": r.get("status", ""),
                            "cluster_id": r.get("cluster_id"),
                        },
                    )
                )
            return items
        except Exception as exc:
            logger.error("Opinion search failed: %s", exc)
            return []

    async def _search_dockets(self, q: SearchQuery) -> List[SearchResultItem]:
        """Search PACER dockets via CourtListener."""
        try:
            data = await self._cl.search_dockets(
                query=q.raw_query,
                court=q.court_filter,
                page_size=q.page_size,
            )
            items = []
            for r in data.get("results", []):
                items.append(
                    SearchResultItem(
                        result_id=f"pacer_docket_{r.get('docket_id', '')}",
                        source="pacer",
                        result_type="docket",
                        title=r.get("caseName", "Unknown Docket"),
                        url=f"https://www.courtlistener.com{r.get('absolute_url', '')}",
                        date=r.get("date_filed"),
                        court_or_agency=r.get("court_id", ""),
                        snippet=r.get("snippet", "")[:400],
                        relevance_score=float(r.get("score", 0)),
                        authority_score=0.0,
                        metadata={"docket_number": r.get("docketNumber", "")},
                    )
                )
            return items
        except Exception as exc:
            logger.error("Docket search failed: %s", exc)
            return []

    async def _search_bills(self, q: SearchQuery) -> List[SearchResultItem]:
        """Search Congress.gov bills."""
        try:
            data = await self._congress.search_bills(query=q.raw_query, limit=q.page_size)
            items = []
            for b in data.get("bills", []):
                items.append(
                    SearchResultItem(
                        result_id=f"congress_bill_{b.get('congress')}_{b.get('type')}_{b.get('number')}",
                        source="congress",
                        result_type="bill",
                        title=b.get("title", "Unknown Bill"),
                        url=b.get("url", ""),
                        date=b.get("latestAction", {}).get("actionDate"),
                        court_or_agency=f"Congress {b.get('congress')}",
                        snippet=b.get("latestAction", {}).get("text", "")[:400],
                        relevance_score=0.5,
                        authority_score=0.0,
                        metadata={
                            "bill_type": b.get("type"),
                            "bill_number": b.get("number"),
                            "congress": b.get("congress"),
                        },
                    )
                )
            return items
        except Exception as exc:
            logger.error("Bill search failed: %s", exc)
            return []

    async def _search_regulations(self, q: SearchQuery) -> List[SearchResultItem]:
        """Search Federal Register regulations."""
        try:
            actions = await self._regulatory.search_federal_register(
                keywords=q.terms[:5],
                per_page=q.page_size,
                publication_date_gte=q.date_min,
                publication_date_lte=q.date_max,
            )
            items = []
            for a in actions:
                items.append(
                    SearchResultItem(
                        result_id=f"fr_{a.document_number}",
                        source="federal_register",
                        result_type="regulation",
                        title=a.title,
                        url=a.url,
                        date=a.publication_date,
                        court_or_agency=a.agency,
                        snippet=a.abstract[:400],
                        relevance_score=0.4,
                        authority_score=0.0,
                        metadata={
                            "action_type": a.action_type,
                            "cfr_references": a.cfr_references,
                            "comment_deadline": a.comment_deadline,
                        },
                    )
                )
            return items
        except Exception as exc:
            logger.error("Regulation search failed: %s", exc)
            return []

    # ------------------------------------------------------------------
    # Ranking and faceting
    # ------------------------------------------------------------------

    def _rank_results(
        self, items: List[SearchResultItem], query: SearchQuery
    ) -> List[SearchResultItem]:
        """Rank and deduplicate search results."""
        # Deduplicate by result_id
        seen = set()
        unique_items = []
        for item in items:
            if item.result_id not in seen:
                seen.add(item.result_id)
                unique_items.append(item)

        # Sort by specified order
        if query.order_by == "date":
            unique_items.sort(key=lambda i: i.date or "0", reverse=True)
        elif query.order_by == "authority":
            unique_items.sort(key=lambda i: i.authority_score, reverse=True)
        else:  # relevance (default)
            unique_items.sort(
                key=lambda i: (i.relevance_score + i.authority_score * 0.3),
                reverse=True,
            )

        return unique_items

    def _build_facets(self, items: List[SearchResultItem]) -> Dict[str, Dict[str, int]]:
        """Build facet counts from result set."""
        facets: Dict[str, Dict[str, int]] = {
            "source": {},
            "result_type": {},
            "court_or_agency": {},
            "year": {},
        }
        for item in items:
            facets["source"][item.source] = facets["source"].get(item.source, 0) + 1
            facets["result_type"][item.result_type] = facets["result_type"].get(item.result_type, 0) + 1
            facets["court_or_agency"][item.court_or_agency] = (
                facets["court_or_agency"].get(item.court_or_agency, 0) + 1
            )
            if item.date:
                year = item.date[:4]
                facets["year"][year] = facets["year"].get(year, 0) + 1
        return facets

    # ------------------------------------------------------------------
    # Saved searches
    # ------------------------------------------------------------------

    def save_search(self, name: str, query: SearchQuery) -> str:
        """Save a search for later reuse."""
        import hashlib
        search_id = hashlib.md5(f"{name}:{datetime.utcnow().isoformat()}".encode()).hexdigest()[:12]
        saved = SavedSearch(
            search_id=search_id,
            name=name,
            query=query,
            created_at=datetime.utcnow().isoformat(),
        )
        self._saved_searches[search_id] = saved
        return search_id

    async def run_saved_search(self, search_id: str) -> Optional[SearchResults]:
        """Run a previously saved search."""
        saved = self._saved_searches.get(search_id)
        if not saved:
            return None
        saved.last_run = datetime.utcnow().isoformat()
        saved.run_count += 1
        q = saved.query
        return await self.search(
            query=q.raw_query,
            court=q.court_filter,
            date_min=q.date_min,
            date_max=q.date_max,
            page=q.page,
            page_size=q.page_size,
            order_by=q.order_by,
        )

    def list_saved_searches(self) -> List[Dict[str, Any]]:
        """List all saved searches."""
        return [
            {
                "search_id": s.search_id,
                "name": s.name,
                "query": s.query.raw_query,
                "created_at": s.created_at,
                "last_run": s.last_run,
                "run_count": s.run_count,
            }
            for s in self._saved_searches.values()
        ]

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_json(self, results: SearchResults) -> str:
        """Export search results as JSON string."""
        return json.dumps(
            {
                "query": results.query,
                "total": results.total_results,
                "page": results.page,
                "results": [asdict(r) for r in results.results],
                "facets": results.facets,
            },
            indent=2,
            default=str,
        )

    def export_csv(self, results: SearchResults) -> str:
        """Export search results as CSV string."""
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=["title", "source", "result_type", "court_or_agency", "date", "url", "snippet", "relevance_score"],
        )
        writer.writeheader()
        for r in results.results:
            writer.writerow({
                "title": r.title,
                "source": r.source,
                "result_type": r.result_type,
                "court_or_agency": r.court_or_agency,
                "date": r.date or "",
                "url": r.url,
                "snippet": r.snippet[:200],
                "relevance_score": r.relevance_score,
            })
        return output.getvalue()

    def get_search_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent search history."""
        return sorted(
            self._search_history, key=lambda h: h["timestamp"], reverse=True
        )[:limit]
