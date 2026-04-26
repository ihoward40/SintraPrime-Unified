"""
Legal Research Platform Connectors for SintraPrime-Unified.

Supports:
  - Westlaw Edge (REST API)
  - LexisNexis (REST API)
  - Fastcase (free for bar members — REST API)
  - Google Scholar Legal (scraper-based)
  - CourtListener (REST API — extended with citator)

Provides a unified search interface across all sources simultaneously.
"""

from __future__ import annotations

import abc
import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote_plus, urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30


def _build_session(retries: int = 3) -> requests.Session:
    session = requests.Session()
    retry = Retry(total=retries, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class LegalCitation:
    """A parsed legal citation."""

    raw: str
    volume: Optional[str] = None
    reporter: Optional[str] = None
    page: Optional[str] = None
    year: Optional[str] = None
    court: Optional[str] = None
    case_name: Optional[str] = None

    @property
    def is_valid(self) -> bool:
        return bool(self.reporter and self.page)


@dataclass
class ResearchResult:
    """A single result from a legal research search."""

    source: str
    result_id: str
    title: str
    citation: Optional[str] = None
    court: Optional[str] = None
    date: Optional[str] = None
    snippet: Optional[str] = None
    url: Optional[str] = None
    score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CitatorResult:
    """Citator result — who cites a given case."""

    source_citation: str
    citing_cases: List[ResearchResult] = field(default_factory=list)
    treatment: Optional[str] = None  # "positive", "negative", "neutral"
    depth: int = 0  # citation depth


@dataclass
class UnifiedSearchResult:
    """Aggregated search results from all sources."""

    query: str
    total_found: int = 0
    results: List[ResearchResult] = field(default_factory=list)
    errors: Dict[str, str] = field(default_factory=dict)  # source → error message


# ---------------------------------------------------------------------------
# Citation validator
# ---------------------------------------------------------------------------

# Common reporter abbreviations
REPORTERS = {
    "U.S.", "S.Ct.", "L.Ed.", "F.3d", "F.2d", "F.4th", "F.Supp.", "F.Supp.2d",
    "F.Supp.3d", "B.R.", "A.2d", "A.3d", "Cal.", "Cal.2d", "Cal.3d", "Cal.4th",
    "N.Y.", "N.Y.2d", "N.Y.3d", "Tex.", "Ill.", "Ohio", "N.W.2d", "S.W.2d",
    "S.W.3d", "P.2d", "P.3d", "So.2d", "So.3d", "N.E.2d", "N.E.3d",
}

_CITATION_PATTERN = re.compile(
    r"(?P<volume>\d+)\s+"
    r"(?P<reporter>[A-Z][A-Za-z.]+(?:\s*\d?[a-z]{1,2}\.?)*)\s+"
    r"(?P<page>\d+)"
    r"(?:\s+\((?P<court_year>[^)]+)\))?"
)


def parse_citation(raw: str) -> LegalCitation:
    """Attempt to parse a raw citation string into a LegalCitation."""
    raw = raw.strip()
    m = _CITATION_PATTERN.search(raw)
    if not m:
        return LegalCitation(raw=raw)
    court_year = m.group("court_year") or ""
    year_match = re.search(r"\b(\d{4})\b", court_year)
    court = re.sub(r"\b\d{4}\b", "", court_year).strip().strip(",").strip() or None
    return LegalCitation(
        raw=raw,
        volume=m.group("volume"),
        reporter=m.group("reporter").strip(),
        page=m.group("page"),
        year=year_match.group(1) if year_match else None,
        court=court or None,
    )


def validate_citation(raw: str) -> Tuple[bool, LegalCitation]:
    """Return (is_valid, parsed_citation)."""
    citation = parse_citation(raw)
    return citation.is_valid, citation


# ---------------------------------------------------------------------------
# Abstract base class
# ---------------------------------------------------------------------------


class LegalResearchConnector(abc.ABC):
    """Abstract base for all legal research connectors."""

    name: str = "base"

    def __init__(self) -> None:
        self._session = _build_session()

    @abc.abstractmethod
    def authenticate(self) -> None:
        """Set up auth headers."""

    @abc.abstractmethod
    def search(self, query: str, jurisdiction: Optional[str] = None, limit: int = 20) -> List[ResearchResult]:
        """Search cases/statutes matching *query*."""

    @abc.abstractmethod
    def get_document(self, doc_id: str) -> Dict[str, Any]:
        """Retrieve full text / metadata for a document."""

    def cite(self, citation: str) -> CitatorResult:
        """Return citator data (override in connectors that support it)."""
        return CitatorResult(source_citation=citation)

    def _get(self, url: str, **kwargs: Any) -> requests.Response:
        resp = self._session.get(url, timeout=DEFAULT_TIMEOUT, **kwargs)
        resp.raise_for_status()
        return resp

    def _post(self, url: str, **kwargs: Any) -> requests.Response:
        resp = self._session.post(url, timeout=DEFAULT_TIMEOUT, **kwargs)
        resp.raise_for_status()
        return resp


# ---------------------------------------------------------------------------
# Westlaw Edge
# ---------------------------------------------------------------------------


class WestlawEdgeConnector(LegalResearchConnector):
    """
    Westlaw Edge REST API connector.

    Env vars:
        WESTLAW_CLIENT_ID
        WESTLAW_CLIENT_SECRET
        WESTLAW_BASE_URL  (default https://api.thomsonreuters.com/westlaw)
    """

    name = "westlaw"
    _TOKEN_URL = "https://api.thomsonreuters.com/oauth2/token"

    def __init__(self) -> None:
        super().__init__()
        self._client_id = os.environ["WESTLAW_CLIENT_ID"]
        self._client_secret = os.environ["WESTLAW_CLIENT_SECRET"]
        self._base_url = os.getenv("WESTLAW_BASE_URL", "https://api.thomsonreuters.com/westlaw")
        self._access_token: Optional[str] = None

    def authenticate(self) -> None:
        resp = self._session.post(
            self._TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "scope": "research",
            },
            timeout=DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        self._access_token = resp.json()["access_token"]
        self._session.headers.update({"Authorization": f"Bearer {self._access_token}"})
        logger.info("Westlaw Edge: authenticated")

    def search(self, query: str, jurisdiction: Optional[str] = None, limit: int = 20) -> List[ResearchResult]:
        url = f"{self._base_url}/v1/search"
        params: Dict[str, Any] = {"q": query, "count": limit, "database": "ALLCASES"}
        if jurisdiction:
            params["jurisdiction"] = jurisdiction
        resp = self._get(url, params=params)
        results = []
        for item in resp.json().get("Results", []):
            results.append(
                ResearchResult(
                    source=self.name,
                    result_id=item.get("ID", ""),
                    title=item.get("Title", ""),
                    citation=item.get("Citation"),
                    court=item.get("Court"),
                    date=item.get("Date"),
                    snippet=item.get("Snippet"),
                    url=item.get("URL"),
                    score=float(item.get("Relevance", 0)),
                    metadata=item,
                )
            )
        return results

    def get_document(self, doc_id: str) -> Dict[str, Any]:
        url = f"{self._base_url}/v1/document/{doc_id}"
        resp = self._get(url)
        return resp.json()

    def cite(self, citation: str) -> CitatorResult:
        url = f"{self._base_url}/v1/keycite"
        resp = self._get(url, params={"citation": citation})
        data = resp.json()
        citing = [
            ResearchResult(
                source=self.name,
                result_id=c.get("ID", ""),
                title=c.get("Title", ""),
                citation=c.get("Citation"),
                metadata=c,
            )
            for c in data.get("CitingReferences", [])
        ]
        return CitatorResult(
            source_citation=citation,
            citing_cases=citing,
            treatment=data.get("TreatmentFlag", "neutral").lower(),
            depth=len(citing),
        )


# ---------------------------------------------------------------------------
# LexisNexis
# ---------------------------------------------------------------------------


class LexisNexisConnector(LegalResearchConnector):
    """
    LexisNexis API connector.

    Env vars:
        LEXISNEXIS_CLIENT_ID
        LEXISNEXIS_CLIENT_SECRET
        LEXISNEXIS_BASE_URL  (default https://api.lexisnexis.com)
    """

    name = "lexisnexis"
    _TOKEN_URL = "https://auth.lexisnexis.com/oauth/token"

    def __init__(self) -> None:
        super().__init__()
        self._client_id = os.environ["LEXISNEXIS_CLIENT_ID"]
        self._client_secret = os.environ["LEXISNEXIS_CLIENT_SECRET"]
        self._base_url = os.getenv("LEXISNEXIS_BASE_URL", "https://api.lexisnexis.com")
        self._access_token: Optional[str] = None

    def authenticate(self) -> None:
        resp = self._session.post(
            self._TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "scope": "openid",
            },
            timeout=DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        self._access_token = resp.json()["access_token"]
        self._session.headers.update({"Authorization": f"Bearer {self._access_token}"})
        logger.info("LexisNexis: authenticated")

    def search(self, query: str, jurisdiction: Optional[str] = None, limit: int = 20) -> List[ResearchResult]:
        url = f"{self._base_url}/v1/cases/search"
        params: Dict[str, Any] = {"q": query, "page-size": limit}
        if jurisdiction:
            params["jurisdiction"] = jurisdiction
        resp = self._get(url, params=params)
        results = []
        for item in resp.json().get("value", []):
            results.append(
                ResearchResult(
                    source=self.name,
                    result_id=item.get("id", ""),
                    title=item.get("name", ""),
                    citation=item.get("citation"),
                    court=item.get("court"),
                    date=item.get("decisionDate"),
                    snippet=item.get("excerpt"),
                    url=item.get("contentType"),
                    metadata=item,
                )
            )
        return results

    def get_document(self, doc_id: str) -> Dict[str, Any]:
        url = f"{self._base_url}/v1/cases/{doc_id}"
        resp = self._get(url)
        return resp.json()

    def cite(self, citation: str) -> CitatorResult:
        url = f"{self._base_url}/v1/citator"
        resp = self._get(url, params={"citation": citation})
        data = resp.json()
        return CitatorResult(
            source_citation=citation,
            citing_cases=[
                ResearchResult(
                    source=self.name,
                    result_id=c.get("id", ""),
                    title=c.get("name", ""),
                    citation=c.get("citation"),
                    metadata=c,
                )
                for c in data.get("citingDocuments", [])
            ],
            treatment=data.get("treatment", "neutral").lower(),
        )


# ---------------------------------------------------------------------------
# Fastcase
# ---------------------------------------------------------------------------


class FastcaseConnector(LegalResearchConnector):
    """
    Fastcase API connector (free for bar members).

    Env vars:
        FASTCASE_API_KEY
        FASTCASE_BASE_URL  (default https://api.fastcase.com)
    """

    name = "fastcase"

    def __init__(self) -> None:
        super().__init__()
        self._api_key = os.environ["FASTCASE_API_KEY"]
        self._base_url = os.getenv("FASTCASE_BASE_URL", "https://api.fastcase.com")

    def authenticate(self) -> None:
        self._session.headers.update(
            {"Authorization": f"Bearer {self._api_key}", "Accept": "application/json"}
        )
        logger.info("Fastcase: API key configured")

    def search(self, query: str, jurisdiction: Optional[str] = None, limit: int = 20) -> List[ResearchResult]:
        url = f"{self._base_url}/search/cases"
        params: Dict[str, Any] = {"query": query, "pageSize": limit}
        if jurisdiction:
            params["jurisdiction"] = jurisdiction
        resp = self._get(url, params=params)
        results = []
        for item in resp.json().get("cases", []):
            results.append(
                ResearchResult(
                    source=self.name,
                    result_id=item.get("caseId", ""),
                    title=item.get("caseName", ""),
                    citation=item.get("citation"),
                    court=item.get("court"),
                    date=item.get("decisionDate"),
                    snippet=item.get("snippet"),
                    url=item.get("url"),
                    score=float(item.get("relevanceScore", 0)),
                    metadata=item,
                )
            )
        return results

    def get_document(self, doc_id: str) -> Dict[str, Any]:
        url = f"{self._base_url}/cases/{doc_id}"
        resp = self._get(url)
        return resp.json()


# ---------------------------------------------------------------------------
# Google Scholar Legal (scraper)
# ---------------------------------------------------------------------------


class GoogleScholarLegalConnector(LegalResearchConnector):
    """
    Google Scholar Legal — scraper-based connector.

    No API key needed, but rate limiting is strict.
    Respects robots.txt / ToS by adding delays.
    """

    name = "google_scholar"
    _BASE_URL = "https://scholar.google.com"
    _SEARCH_URL = "https://scholar.google.com/scholar"

    def __init__(self, request_delay: float = 2.0) -> None:
        super().__init__()
        self._request_delay = request_delay
        self._session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (compatible; SintraPrime-Research/1.0; "
                    "+https://sintra.prime/research-bot)"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
        )

    def authenticate(self) -> None:
        logger.info("Google Scholar Legal: no auth required (scraper)")

    def search(self, query: str, jurisdiction: Optional[str] = None, limit: int = 20) -> List[ResearchResult]:
        """Scrape Google Scholar for legal cases matching *query*."""
        try:
            from bs4 import BeautifulSoup  # type: ignore
        except ImportError:
            logger.warning("beautifulsoup4 not installed — returning empty results from Google Scholar")
            return []

        params: Dict[str, Any] = {"q": query, "as_sdt": "2006", "num": min(limit, 10)}
        if jurisdiction:
            params["q"] = f"{query} {jurisdiction}"

        time.sleep(self._request_delay)
        resp = self._session.get(self._SEARCH_URL, params=params, timeout=DEFAULT_TIMEOUT)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        results: List[ResearchResult] = []

        for div in soup.select(".gs_r.gs_or.gs_scl")[:limit]:
            title_tag = div.select_one(".gs_rt a")
            title = title_tag.get_text(strip=True) if title_tag else ""
            url = title_tag["href"] if title_tag else None
            snippet_tag = div.select_one(".gs_rs")
            snippet = snippet_tag.get_text(strip=True) if snippet_tag else None
            meta_tag = div.select_one(".gs_a")
            meta_text = meta_tag.get_text(strip=True) if meta_tag else ""
            doc_id = url.split("/")[-1] if url else f"gs_{len(results)}"
            results.append(
                ResearchResult(
                    source=self.name,
                    result_id=doc_id,
                    title=title,
                    snippet=snippet,
                    url=url,
                    metadata={"meta": meta_text},
                )
            )

        return results

    def get_document(self, doc_id: str) -> Dict[str, Any]:
        url = f"{self._BASE_URL}/scholar_case?case={doc_id}"
        time.sleep(self._request_delay)
        resp = self._get(url)
        return {"url": url, "content_length": len(resp.content), "text": resp.text[:5000]}


# ---------------------------------------------------------------------------
# CourtListener (extended with citator)
# ---------------------------------------------------------------------------


class CourtListenerConnector(LegalResearchConnector):
    """
    CourtListener REST API — extended with citator functionality.

    Env vars:
        COURTLISTENER_API_TOKEN
        COURTLISTENER_BASE_URL  (default https://www.courtlistener.com/api/rest/v3)
    """

    name = "courtlistener"

    def __init__(self) -> None:
        super().__init__()
        self._api_token = os.environ["COURTLISTENER_API_TOKEN"]
        self._base_url = os.getenv("COURTLISTENER_BASE_URL", "https://www.courtlistener.com/api/rest/v3")

    def authenticate(self) -> None:
        self._session.headers.update(
            {"Authorization": f"Token {self._api_token}", "Accept": "application/json"}
        )
        logger.info("CourtListener: authenticated")

    def search(self, query: str, jurisdiction: Optional[str] = None, limit: int = 20) -> List[ResearchResult]:
        url = f"{self._base_url}/search/"
        params: Dict[str, Any] = {"q": query, "type": "o", "format": "json", "page_size": limit}
        if jurisdiction:
            params["court"] = jurisdiction
        resp = self._get(url, params=params)
        results = []
        for item in resp.json().get("results", []):
            results.append(
                ResearchResult(
                    source=self.name,
                    result_id=str(item.get("id", "")),
                    title=item.get("caseName", ""),
                    citation=", ".join(item.get("citation", [])),
                    court=item.get("court_id"),
                    date=item.get("dateFiled"),
                    snippet=item.get("snippet"),
                    url=f"https://www.courtlistener.com{item.get('absolute_url', '')}",
                    score=float(item.get("score", 0)),
                    metadata=item,
                )
            )
        return results

    def get_document(self, doc_id: str) -> Dict[str, Any]:
        url = f"{self._base_url}/opinions/{doc_id}/"
        resp = self._get(url)
        return resp.json()

    def cite(self, citation: str) -> CitatorResult:
        """Find cases that cite *citation* using CourtListener's citation graph."""
        # First resolve citation to an opinion ID
        search_url = f"{self._base_url}/search/"
        resp = self._get(search_url, params={"q": f'"{citation}"', "type": "o", "format": "json", "page_size": 1})
        data = resp.json()
        results = data.get("results", [])
        if not results:
            return CitatorResult(source_citation=citation)

        opinion_id = results[0].get("id")
        # Get citing opinions
        citing_url = f"{self._base_url}/opinions/"
        citing_resp = self._get(citing_url, params={"cited_by": opinion_id, "format": "json", "page_size": 50})
        citing_data = citing_resp.json()

        citing_cases = [
            ResearchResult(
                source=self.name,
                result_id=str(c.get("id", "")),
                title=c.get("case_name", ""),
                citation=", ".join(c.get("citations", [])),
                metadata=c,
            )
            for c in citing_data.get("results", [])
        ]
        return CitatorResult(
            source_citation=citation,
            citing_cases=citing_cases,
            depth=len(citing_cases),
        )


# ---------------------------------------------------------------------------
# Unified Search Interface
# ---------------------------------------------------------------------------


class UnifiedLegalSearch:
    """
    Search all available legal research sources simultaneously.

    Connectors are called in parallel via ThreadPoolExecutor.
    Errors from individual sources are captured but do not fail the whole query.
    """

    def __init__(self, connectors: Optional[List[LegalResearchConnector]] = None) -> None:
        self._connectors: List[LegalResearchConnector] = connectors or []

    def add_connector(self, connector: LegalResearchConnector) -> None:
        self._connectors.append(connector)

    def search(
        self,
        query: str,
        jurisdiction: Optional[str] = None,
        limit_per_source: int = 10,
        max_workers: int = 5,
    ) -> UnifiedSearchResult:
        """Search all connectors in parallel."""
        combined = UnifiedSearchResult(query=query)
        if not self._connectors:
            return combined

        def _search_one(connector: LegalResearchConnector) -> Tuple[str, List[ResearchResult], Optional[str]]:
            try:
                results = connector.search(query, jurisdiction=jurisdiction, limit=limit_per_source)
                return connector.name, results, None
            except Exception as exc:  # noqa: BLE001
                logger.warning("Connector %s failed: %s", connector.name, exc)
                return connector.name, [], str(exc)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_search_one, c): c for c in self._connectors}
            for future in as_completed(futures):
                source, results, error = future.result()
                if error:
                    combined.errors[source] = error
                else:
                    combined.results.extend(results)
                    combined.total_found += len(results)

        # Sort by score descending
        combined.results.sort(key=lambda r: r.score, reverse=True)
        return combined

    def cite_all(self, citation: str) -> Dict[str, CitatorResult]:
        """Run citator across all connectors that support it."""
        results: Dict[str, CitatorResult] = {}
        for connector in self._connectors:
            try:
                results[connector.name] = connector.cite(citation)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Citator %s failed for '%s': %s", connector.name, citation, exc)
        return results


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------

_RESEARCH_REGISTRY: Dict[str, type] = {
    "westlaw": WestlawEdgeConnector,
    "lexisnexis": LexisNexisConnector,
    "fastcase": FastcaseConnector,
    "google_scholar": GoogleScholarLegalConnector,
    "courtlistener": CourtListenerConnector,
}


def get_research_connector(source: str) -> LegalResearchConnector:
    """Return an authenticated connector for *source*."""
    cls = _RESEARCH_REGISTRY.get(source.lower())
    if cls is None:
        raise ValueError(f"Unknown source: {source!r}. Choices: {list(_RESEARCH_REGISTRY)}")
    connector: LegalResearchConnector = cls()
    connector.authenticate()
    return connector


def build_unified_search(sources: Optional[List[str]] = None) -> UnifiedLegalSearch:
    """Build a UnifiedLegalSearch pre-loaded with authenticated connectors."""
    sources = sources or list(_RESEARCH_REGISTRY.keys())
    unified = UnifiedLegalSearch()
    for source in sources:
        try:
            connector = get_research_connector(source)
            unified.add_connector(connector)
        except (KeyError, ValueError) as exc:
            logger.warning("Skipping research source '%s': %s", source, exc)
    return unified
