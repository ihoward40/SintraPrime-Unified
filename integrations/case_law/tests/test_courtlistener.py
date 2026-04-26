"""
Tests for CourtListenerClient
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiohttp import ClientSession

from ..courtlistener_client import (
    CourtListenerClient,
    InMemoryCache,
    RateLimiter,
    RateLimitError,
    NotFoundError,
    APIError,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_session():
    """Create a mock aiohttp ClientSession."""
    session = AsyncMock(spec=ClientSession)
    return session


@pytest.fixture
def client(monkeypatch):
    """Create a CourtListenerClient with no API token.
    Clears COURTLISTENER_API_TOKEN env var to prevent test pollution.
    """
    monkeypatch.delenv("COURTLISTENER_API_TOKEN", raising=False)
    return CourtListenerClient(api_token=None, cache_ttl=60, calls_per_second=10)


@pytest.fixture
def client_with_token():
    """Create a CourtListenerClient with an API token."""
    return CourtListenerClient(api_token="test_token_abc123")


# ---------------------------------------------------------------------------
# InMemoryCache tests
# ---------------------------------------------------------------------------


class TestInMemoryCache:
    def test_set_and_get(self):
        cache = InMemoryCache(ttl_seconds=60)
        cache.set("key1", {"data": "value"})
        result = cache.get("key1")
        assert result == {"data": "value"}

    def test_get_missing_key(self):
        cache = InMemoryCache()
        assert cache.get("nonexistent") is None

    def test_ttl_expiry(self):
        import time
        cache = InMemoryCache(ttl_seconds=1)
        cache.set("key", "value")
        assert cache.get("key") == "value"
        # Manually expire
        cache._store["key"] = ("value", time.monotonic() - 10)
        assert cache.get("key") is None

    def test_invalidate(self):
        cache = InMemoryCache()
        cache.set("k", "v")
        cache.invalidate("k")
        assert cache.get("k") is None

    def test_clear(self):
        cache = InMemoryCache()
        cache.set("a", 1)
        cache.set("b", 2)
        cache.clear()
        assert cache.get("a") is None
        assert cache.get("b") is None

    def test_cache_key_deterministic(self):
        cache = InMemoryCache()
        key1 = cache._cache_key("https://example.com/api", {"q": "test", "page": 1})
        key2 = cache._cache_key("https://example.com/api", {"page": 1, "q": "test"})
        assert key1 == key2  # Same keys regardless of dict order

    def test_cache_key_different_urls(self):
        cache = InMemoryCache()
        k1 = cache._cache_key("https://url1.com", {})
        k2 = cache._cache_key("https://url2.com", {})
        assert k1 != k2


# ---------------------------------------------------------------------------
# RateLimiter tests
# ---------------------------------------------------------------------------


class TestRateLimiter:
    @pytest.mark.asyncio
    async def test_acquire_does_not_block_initially(self):
        limiter = RateLimiter(calls_per_second=10)
        # Should complete quickly (no blocking on first few calls)
        await limiter.acquire()
        await limiter.acquire()

    @pytest.mark.asyncio
    async def test_acquire_respects_rate(self):
        import time
        limiter = RateLimiter(calls_per_second=100)
        start = time.monotonic()
        for _ in range(5):
            await limiter.acquire()
        elapsed = time.monotonic() - start
        # Should complete well under 1 second at 100/s
        assert elapsed < 1.0


# ---------------------------------------------------------------------------
# CourtListenerClient tests
# ---------------------------------------------------------------------------


class TestCourtListenerClient:
    @pytest.mark.asyncio
    async def test_search_opinions_success(self, client):
        """Test successful opinion search."""
        mock_response = {
            "count": 2,
            "results": [
                {
                    "id": 1001,
                    "cluster_id": 500,
                    "caseName": "Test v. Case",
                    "court_id": "scotus",
                    "dateFiled": "2023-01-15",
                    "snippet": "This is a test holding",
                    "score": 15.5,
                    "citeCount": 42,
                    "absolute_url": "/opinion/1001/test-v-case/",
                },
                {
                    "id": 1002,
                    "cluster_id": 501,
                    "caseName": "Another v. Case",
                    "court_id": "ca9",
                    "dateFiled": "2022-06-01",
                    "snippet": "Another test snippet",
                    "score": 10.0,
                    "citeCount": 10,
                    "absolute_url": "/opinion/1002/another-v-case/",
                },
            ],
            "next": None,
            "previous": None,
        }

        with patch.object(client, "_get", new=AsyncMock(return_value=mock_response)):
            result = await client.search_opinions("test query", court="scotus")

        assert result["count"] == 2
        assert len(result["results"]) == 2
        assert result["results"][0]["caseName"] == "Test v. Case"

    @pytest.mark.asyncio
    async def test_search_opinions_with_filters(self, client):
        """Test opinion search with multiple filters."""
        mock_response = {"count": 0, "results": [], "next": None, "previous": None}
        with patch.object(client, "_get", new=AsyncMock(return_value=mock_response)) as mock_get:
            await client.search_opinions(
                query="Fourth Amendment",
                court="ca9",
                date_filed_min="2020-01-01",
                date_filed_max="2023-12-31",
                judge="Smith",
                page_size=10,
            )
            call_args = mock_get.call_args
            params = call_args[1].get("params") or call_args[0][1]
            assert params["q"] == "Fourth Amendment"
            assert params["court"] == "ca9"

    @pytest.mark.asyncio
    async def test_get_opinion_success(self, client):
        """Test fetching a single opinion."""
        mock_opinion = {
            "id": 999,
            "cluster_id": 100,
            "plain_text": "This is the full opinion text...",
            "author_str": "ROBERTS, C.J.",
            "per_curiam": False,
            "type": "010combined",
        }
        with patch.object(client, "_get", new=AsyncMock(return_value=mock_opinion)):
            result = await client.get_opinion(999)
        assert result["id"] == 999
        assert result["plain_text"] == "This is the full opinion text..."

    @pytest.mark.asyncio
    async def test_get_opinion_text_plain(self, client):
        """Test getting plain text from an opinion."""
        mock_opinion = {
            "id": 1,
            "plain_text": "The court finds for the plaintiff.",
            "html": "",
        }
        with patch.object(client, "_get", new=AsyncMock(return_value=mock_opinion)):
            text = await client.get_opinion_text(1)
        assert text == "The court finds for the plaintiff."

    @pytest.mark.asyncio
    async def test_get_opinion_text_html_fallback(self, client):
        """Test HTML fallback when no plain text available."""
        mock_opinion = {
            "id": 2,
            "plain_text": "",
            "html": "<p>The <strong>court</strong> finds.</p>",
        }
        with patch.object(client, "_get", new=AsyncMock(return_value=mock_opinion)):
            text = await client.get_opinion_text(2)
        assert "court" in text
        assert "<" not in text  # HTML stripped

    @pytest.mark.asyncio
    async def test_get_cluster(self, client):
        """Test fetching an opinion cluster."""
        mock_cluster = {
            "id": 100,
            "case_name": "Marbury v. Madison",
            "date_filed": "1803-02-24",
            "court_id": "scotus",
            "citation_count": 50000,
        }
        with patch.object(client, "_get", new=AsyncMock(return_value=mock_cluster)):
            result = await client.get_cluster(100)
        assert result["case_name"] == "Marbury v. Madison"

    @pytest.mark.asyncio
    async def test_not_found_raises_error(self, client):
        """Test that 404 raises NotFoundError."""
        with patch.object(client, "_get", new=AsyncMock(side_effect=NotFoundError("Not found"))):
            with pytest.raises(NotFoundError):
                await client.get_opinion(99999)

    @pytest.mark.asyncio
    async def test_rate_limit_error(self, client):
        """Test rate limit error propagation."""
        with patch.object(client, "_get", new=AsyncMock(side_effect=RateLimitError("Rate limited"))):
            with pytest.raises(RateLimitError):
                await client.search_opinions("test")

    @pytest.mark.asyncio
    async def test_search_opinions_paginated(self, client):
        """Test paginated search returns all results."""
        page1 = {
            "count": 3,
            "results": [{"id": 1, "caseName": "A v. B"}, {"id": 2, "caseName": "C v. D"}],
            "next": "page2url",
        }
        page2 = {
            "count": 3,
            "results": [{"id": 3, "caseName": "E v. F"}],
            "next": None,
        }
        call_count = 0

        async def mock_get(endpoint, params=None, use_cache=True):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return page1
            return page2

        with patch.object(client, "_get", new=mock_get):
            results = []
            async for item in client.search_opinions_paginated("test", max_results=3):
                results.append(item)

        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_get_opinion_citations(self, client):
        """Test citation relationship extraction."""
        mock_opinion = {
            "id": 10,
            "opinions_cited": [{"id": 20}, {"id": 30}],
        }
        mock_cited_by = {
            "results": [{"id": 40}, {"id": 50}]
        }

        call_count = 0

        async def mock_get(endpoint, params=None, use_cache=True):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_opinion
            return mock_cited_by

        with patch.object(client, "_get", new=mock_get):
            citations = await client.get_opinion_citations(10)

        assert set(citations["cites"]) == {20, 30}
        assert set(citations["cited_by"]) == {40, 50}

    @pytest.mark.asyncio
    async def test_get_supreme_court_cases(self, client):
        """Test convenience method for SCOTUS search."""
        mock_response = {"count": 1, "results": [], "next": None}
        with patch.object(client, "_get", new=AsyncMock(return_value=mock_response)) as mock_get:
            await client.get_supreme_court_cases("search term")
            call_args = mock_get.call_args
            params = call_args[1].get("params") or call_args[0][1]
            assert params["court"] == "scotus"

    @pytest.mark.asyncio
    async def test_find_cases_by_party(self, client):
        """Test party name search."""
        mock_response = {"count": 1, "results": [{"id": 1, "caseName": "Smith v. Jones"}], "next": None}
        with patch.object(client, "_get", new=AsyncMock(return_value=mock_response)):
            results = await client.find_cases_by_party("Smith", max_results=5)
        assert len(results) == 1

    def test_auth_header(self, client_with_token):
        """Test that API token is included in headers."""
        headers = client_with_token._default_headers()
        assert "Authorization" in headers
        assert "Token test_token_abc123" in headers["Authorization"]

    def test_no_auth_header(self, client):
        """Test that no auth header without token."""
        headers = client._default_headers()
        assert "Authorization" not in headers

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager opens and closes session."""
        async with CourtListenerClient() as cl:
            assert cl._session is not None
        assert cl._session is None

    @pytest.mark.asyncio
    async def test_list_courts(self, client):
        """Test listing courts."""
        mock_response = {
            "results": [
                {"id": "scotus", "full_name": "Supreme Court of the United States"},
                {"id": "ca9", "full_name": "Ninth Circuit"},
            ]
        }
        with patch.object(client, "_get", new=AsyncMock(return_value=mock_response)):
            result = await client.list_courts(jurisdiction="F")
        assert len(result["results"]) == 2

    @pytest.mark.asyncio
    async def test_search_dockets(self, client):
        """Test docket search."""
        mock_response = {"count": 1, "results": [{"id": 999, "case_name": "Test Corp v. Big Co"}]}
        with patch.object(client, "_get", new=AsyncMock(return_value=mock_response)):
            result = await client.search_dockets("Test Corp")
        assert result["count"] == 1
