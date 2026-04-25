"""
CourtListener REST API Client
==============================
Interfaces with https://www.courtlistener.com/api/rest/v4/

Free tier: 5,000 requests/day, no API key required for basic queries.
Authenticated requests get higher rate limits.

Features:
- Full-text opinion search with boolean operators
- Filter by court, date range, judge, party name
- Fetch complete opinion text
- Citation network traversal
- PDF download support
- Rate limiting with exponential backoff
- In-memory + Redis response caching
- Fully async (aiohttp)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, date
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple
from urllib.parse import urlencode, urljoin

import aiohttp

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class CourtListenerError(Exception):
    """Base exception for CourtListener client errors."""


class RateLimitError(CourtListenerError):
    """Raised when the API rate limit is exceeded."""


class NotFoundError(CourtListenerError):
    """Raised when a resource is not found (404)."""


class APIError(CourtListenerError):
    """Raised for unexpected API errors."""


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class Court:
    """Represents a court in CourtListener."""

    id: str
    name: str
    full_name: str
    jurisdiction: str
    url: Optional[str] = None
    in_use: bool = True
    has_opinion_scraper: bool = False
    has_oral_argument_scraper: bool = False


@dataclass
class Opinion:
    """Represents a single court opinion."""

    id: int
    cluster_id: int
    author_str: str
    per_curiam: bool
    type: str
    date_created: Optional[str]
    plain_text: Optional[str]
    html: Optional[str]
    html_lawbox: Optional[str]
    html_columbia: Optional[str]
    html_anon_2020: Optional[str]
    xml_harvard: Optional[str]
    download_url: Optional[str]
    absolute_url: Optional[str]


@dataclass
class OpinionCluster:
    """A case cluster grouping related opinions."""

    id: int
    case_name: str
    case_name_full: str
    date_filed: Optional[str]
    docket_id: Optional[int]
    court_id: str
    judges: str
    nature_of_suit: str
    precedential_status: str
    citation_count: int
    slug: str
    absolute_url: str
    citations: List[str] = field(default_factory=list)
    sub_opinions: List[int] = field(default_factory=list)  # opinion IDs


@dataclass
class Docket:
    """Federal court docket."""

    id: int
    court_id: str
    case_name: str
    docket_number: str
    date_filed: Optional[str]
    date_terminated: Optional[str]
    nature_of_suit: str
    cause: str
    jury_demand: str
    jurisdiction_type: str
    assigned_to_str: str
    referred_to_str: str
    absolute_url: str
    pacer_case_id: Optional[str] = None


@dataclass
class SearchResult:
    """A single result from opinion search."""

    cluster_id: int
    case_name: str
    court: str
    date_filed: Optional[str]
    status: str
    snippet: str
    citation: str
    url: str
    score: float = 0.0


@dataclass
class CitationRelationship:
    """Represents a citation from one opinion to another."""

    citing_opinion_id: int
    cited_opinion_id: int
    citing_cluster_id: int
    cited_cluster_id: int
    depth: int = 1  # number of hops in the citation graph


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------


class RateLimiter:
    """Token bucket rate limiter for API calls."""

    def __init__(self, calls_per_second: float = 2.0) -> None:
        self.calls_per_second = calls_per_second
        self._tokens: float = calls_per_second
        self._last_refill: float = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(
                self.calls_per_second,
                self._tokens + elapsed * self.calls_per_second,
            )
            self._last_refill = now
            if self._tokens < 1.0:
                wait_time = (1.0 - self._tokens) / self.calls_per_second
                await asyncio.sleep(wait_time)
                self._tokens = 0.0
            else:
                self._tokens -= 1.0


# ---------------------------------------------------------------------------
# In-memory cache
# ---------------------------------------------------------------------------


class InMemoryCache:
    """Simple TTL-based in-memory cache."""

    def __init__(self, ttl_seconds: int = 3600) -> None:
        self._store: Dict[str, Tuple[Any, float]] = {}
        self._ttl = ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        if key in self._store:
            value, expires_at = self._store[key]
            if time.monotonic() < expires_at:
                return value
            del self._store[key]
        return None

    def set(self, key: str, value: Any) -> None:
        self._store[key] = (value, time.monotonic() + self._ttl)

    def invalidate(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()

    def _cache_key(self, url: str, params: Optional[Dict] = None) -> str:
        raw = url + json.dumps(params or {}, sort_keys=True)
        return hashlib.md5(raw.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Main client
# ---------------------------------------------------------------------------


class CourtListenerClient:
    """
    Async client for the CourtListener REST API v4.

    Args:
        api_token: Optional API token for higher rate limits.
        base_url: Override the base API URL.
        cache_ttl: Cache TTL in seconds (default 1 hour).
        calls_per_second: Max API calls per second (default 2).
        max_retries: Number of retries on transient failures.
    """

    BASE_URL = "https://www.courtlistener.com/api/rest/v4/"
    SITE_URL = "https://www.courtlistener.com"

    def __init__(
        self,
        api_token: Optional[str] = None,
        base_url: str = BASE_URL,
        cache_ttl: int = 3600,
        calls_per_second: float = 2.0,
        max_retries: int = 3,
    ) -> None:
        self._api_token = api_token or os.getenv("COURTLISTENER_API_TOKEN")
        self._base_url = base_url
        self._cache = InMemoryCache(ttl_seconds=cache_ttl)
        self._rate_limiter = RateLimiter(calls_per_second=calls_per_second)
        self._max_retries = max_retries
        self._session: Optional[aiohttp.ClientSession] = None

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "CourtListenerClient":
        self._session = aiohttp.ClientSession(
            headers=self._default_headers(),
            timeout=aiohttp.ClientTimeout(total=30),
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._session:
            await self._session.close()
            self._session = None

    def _default_headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json", "User-Agent": "SintraPrime/1.0"}
        if self._api_token:
            headers["Authorization"] = f"Token {self._api_token}"
        return headers

    # ------------------------------------------------------------------
    # Core HTTP helper
    # ------------------------------------------------------------------

    async def _get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """Perform a GET request with caching, rate limiting, and retries."""
        url = urljoin(self._base_url, endpoint.lstrip("/"))
        cache_key = self._cache._cache_key(url, params)

        if use_cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                logger.debug("Cache hit: %s", url)
                return cached

        for attempt in range(self._max_retries + 1):
            await self._rate_limiter.acquire()
            try:
                session = self._ensure_session()
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if use_cache:
                            self._cache.set(cache_key, data)
                        return data
                    elif resp.status == 429:
                        retry_after = int(resp.headers.get("Retry-After", 60))
                        logger.warning("Rate limited; sleeping %ds", retry_after)
                        await asyncio.sleep(retry_after)
                        raise RateLimitError(f"Rate limited by CourtListener (attempt {attempt+1})")
                    elif resp.status == 404:
                        raise NotFoundError(f"Resource not found: {url}")
                    else:
                        text = await resp.text()
                        raise APIError(f"HTTP {resp.status} from {url}: {text[:200]}")
            except (RateLimitError, aiohttp.ClientError) as exc:
                if attempt >= self._max_retries:
                    raise
                wait = 2 ** attempt
                logger.warning("Retrying in %ds after error: %s", wait, exc)
                await asyncio.sleep(wait)

        raise APIError("Exceeded max retries")

    def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            self._session = aiohttp.ClientSession(
                headers=self._default_headers(),
                timeout=aiohttp.ClientTimeout(total=30),
            )
        return self._session

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    async def search_opinions(
        self,
        query: str,
        court: Optional[str] = None,
        date_filed_min: Optional[str] = None,
        date_filed_max: Optional[str] = None,
        judge: Optional[str] = None,
        party_name: Optional[str] = None,
        status: Optional[str] = None,
        order_by: str = "score desc",
        page_size: int = 20,
        page: int = 1,
    ) -> Dict[str, Any]:
        """
        Full-text search of court opinions.

        Args:
            query: Boolean-capable search string (e.g. "Fourth Amendment AND warrant").
            court: CourtListener court ID (e.g. "scotus", "ca9").
            date_filed_min: ISO date string "YYYY-MM-DD".
            date_filed_max: ISO date string "YYYY-MM-DD".
            judge: Partial judge name.
            party_name: Partial party name.
            status: "Published", "Unpublished", etc.
            order_by: Sort field (score desc, dateFiled desc, citeCount desc).
            page_size: Results per page (max 100).
            page: Page number.

        Returns:
            Dict with 'count', 'results', 'next', 'previous'.
        """
        params: Dict[str, Any] = {
            "q": query,
            "type": "o",  # opinions
            "order_by": order_by,
            "stat_Published": True,
            "page_size": page_size,
            "page": page,
        }
        if court:
            params["court"] = court
        if date_filed_min:
            params["filed_after"] = date_filed_min
        if date_filed_max:
            params["filed_before"] = date_filed_max
        if judge:
            params["judge"] = judge
        if party_name:
            params["case_name"] = party_name
        if status:
            params["stat_" + status] = True

        logger.info("Searching opinions: %s", query)
        return await self._get("search/", params=params)

    async def search_opinions_paginated(
        self, query: str, max_results: int = 100, **kwargs: Any
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Async generator that paginates through all search results.

        Yields individual result dicts up to max_results.
        """
        fetched = 0
        page = 1
        while fetched < max_results:
            page_size = min(20, max_results - fetched)
            data = await self.search_opinions(query, page_size=page_size, page=page, **kwargs)
            results = data.get("results", [])
            if not results:
                break
            for r in results:
                if fetched >= max_results:
                    return
                yield r
                fetched += 1
            if not data.get("next"):
                break
            page += 1

    # ------------------------------------------------------------------
    # Opinion clusters
    # ------------------------------------------------------------------

    async def get_cluster(self, cluster_id: int) -> Dict[str, Any]:
        """
        Retrieve full opinion cluster (case) by ID.

        Args:
            cluster_id: CourtListener cluster ID.

        Returns:
            Cluster data dict.
        """
        return await self._get(f"clusters/{cluster_id}/")

    async def list_clusters(
        self,
        court: Optional[str] = None,
        date_filed_min: Optional[str] = None,
        date_filed_max: Optional[str] = None,
        precedential_status: Optional[str] = None,
        page_size: int = 20,
        page: int = 1,
    ) -> Dict[str, Any]:
        """List clusters with optional filtering."""
        params: Dict[str, Any] = {"page_size": page_size, "page": page}
        if court:
            params["court"] = court
        if date_filed_min:
            params["date_filed__gte"] = date_filed_min
        if date_filed_max:
            params["date_filed__lte"] = date_filed_max
        if precedential_status:
            params["precedential_status"] = precedential_status
        return await self._get("clusters/", params=params)

    # ------------------------------------------------------------------
    # Individual opinions
    # ------------------------------------------------------------------

    async def get_opinion(self, opinion_id: int) -> Dict[str, Any]:
        """Retrieve a single opinion by ID."""
        return await self._get(f"opinions/{opinion_id}/")

    async def get_opinion_text(self, opinion_id: int) -> str:
        """
        Get full plain text of an opinion.

        Tries plain_text, then strips HTML if necessary.
        """
        opinion = await self.get_opinion(opinion_id)
        text = opinion.get("plain_text", "")
        if text:
            return text
        # Fall back to HTML content
        for field in ["html", "html_lawbox", "html_columbia", "html_anon_2020"]:
            html = opinion.get(field, "")
            if html:
                # Very basic HTML stripping
                import re
                return re.sub(r"<[^>]+>", " ", html).strip()
        return ""

    # ------------------------------------------------------------------
    # Dockets
    # ------------------------------------------------------------------

    async def get_docket(self, docket_id: int) -> Dict[str, Any]:
        """Retrieve a docket by ID."""
        return await self._get(f"dockets/{docket_id}/")

    async def search_dockets(
        self,
        query: str,
        court: Optional[str] = None,
        party_name: Optional[str] = None,
        nature_of_suit: Optional[str] = None,
        page_size: int = 20,
        page: int = 1,
    ) -> Dict[str, Any]:
        """Search dockets by keyword and filters."""
        params: Dict[str, Any] = {"q": query, "page_size": page_size, "page": page}
        if court:
            params["court"] = court
        if party_name:
            params["case_name"] = party_name
        if nature_of_suit:
            params["nature_of_suit"] = nature_of_suit
        return await self._get("dockets/", params=params)

    async def get_docket_entries(
        self, docket_id: int, page_size: int = 50
    ) -> Dict[str, Any]:
        """Get all docket entries (filings) for a docket."""
        return await self._get("docket-entries/", params={"docket": docket_id, "page_size": page_size})

    # ------------------------------------------------------------------
    # Courts
    # ------------------------------------------------------------------

    async def list_courts(
        self, jurisdiction: Optional[str] = None, in_use: bool = True
    ) -> Dict[str, Any]:
        """
        List all courts.

        Args:
            jurisdiction: Filter by jurisdiction code (F=federal, S=state, etc.)
            in_use: Only return active courts.
        """
        params: Dict[str, Any] = {"in_use": in_use}
        if jurisdiction:
            params["jurisdiction"] = jurisdiction
        return await self._get("courts/", params=params)

    async def get_court(self, court_id: str) -> Dict[str, Any]:
        """Get metadata for a specific court."""
        return await self._get(f"courts/{court_id}/")

    # ------------------------------------------------------------------
    # Judges / people
    # ------------------------------------------------------------------

    async def search_judges(
        self,
        name: Optional[str] = None,
        court: Optional[str] = None,
        appointing_president: Optional[str] = None,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """Search for judges and attorneys."""
        params: Dict[str, Any] = {"page_size": page_size}
        if name:
            params["name_last"] = name
        if court:
            params["court"] = court
        if appointing_president:
            params["appointing_president"] = appointing_president
        return await self._get("people/", params=params)

    # ------------------------------------------------------------------
    # Citation network
    # ------------------------------------------------------------------

    async def get_opinion_citations(self, opinion_id: int) -> Dict[str, List[int]]:
        """
        Get the citation relationships for an opinion.

        Returns:
            Dict with:
            - 'cites': list of opinion IDs this opinion cites
            - 'cited_by': list of opinion IDs that cite this opinion
        """
        data = await self._get(f"opinions/{opinion_id}/")
        opinions_cited = data.get("opinions_cited", [])
        # cited_by requires a separate query
        cited_by_data = await self._get(
            "opinions/", params={"opinions_cited": opinion_id, "page_size": 100}
        )
        cited_by_ids = [r["id"] for r in cited_by_data.get("results", [])]
        return {
            "cites": [o["id"] if isinstance(o, dict) else o for o in opinions_cited],
            "cited_by": cited_by_ids,
        }

    async def get_cluster_citations(self, cluster_id: int) -> Dict[str, Any]:
        """Get all citation data for a cluster."""
        cluster = await self.get_cluster(cluster_id)
        return {
            "cluster_id": cluster_id,
            "case_name": cluster.get("case_name"),
            "citation_count": cluster.get("citation_count", 0),
            "sub_opinions": cluster.get("sub_opinions", []),
        }

    # ------------------------------------------------------------------
    # PDF download
    # ------------------------------------------------------------------

    async def download_opinion_pdf(self, opinion_id: int, output_path: str) -> str:
        """
        Download an opinion as PDF.

        Args:
            opinion_id: The opinion ID.
            output_path: Local file path to save the PDF.

        Returns:
            The output_path if successful.
        """
        opinion = await self.get_opinion(opinion_id)
        download_url = opinion.get("download_url")
        if not download_url:
            raise NotFoundError(f"No PDF download URL for opinion {opinion_id}")

        session = self._ensure_session()
        async with session.get(download_url) as resp:
            if resp.status != 200:
                raise APIError(f"Failed to download PDF: HTTP {resp.status}")
            content = await resp.read()

        with open(output_path, "wb") as f:
            f.write(content)

        logger.info("Downloaded opinion %d PDF to %s", opinion_id, output_path)
        return output_path

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    async def find_cases_by_party(
        self, party_name: str, court: Optional[str] = None, max_results: int = 20
    ) -> List[Dict[str, Any]]:
        """Find cases involving a specific party."""
        results = []
        async for item in self.search_opinions_paginated(
            query=f'"{party_name}"',
            court=court,
            max_results=max_results,
        ):
            results.append(item)
        return results

    async def get_supreme_court_cases(
        self,
        query: str,
        date_filed_min: Optional[str] = None,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """Convenience method to search only Supreme Court opinions."""
        return await self.search_opinions(
            query=query,
            court="scotus",
            date_filed_min=date_filed_min,
            page_size=page_size,
        )

    async def get_circuit_cases(
        self, query: str, circuit: int, page_size: int = 20
    ) -> Dict[str, Any]:
        """
        Search cases in a specific circuit court.

        Args:
            query: Search query.
            circuit: Circuit number (1-11) or use 'dc' for DC Circuit.
        """
        court_id = f"ca{circuit}" if isinstance(circuit, int) else f"ca{circuit}"
        return await self.search_opinions(query=query, court=court_id, page_size=page_size)

    async def close(self) -> None:
        """Close the underlying HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None
