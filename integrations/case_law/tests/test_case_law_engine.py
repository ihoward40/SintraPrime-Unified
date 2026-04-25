"""
Tests for CaseLawSearchEngine
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from ..case_law_search_engine import (
    CaseLawSearchEngine,
    QueryParser,
    SearchQuery,
    SearchResultItem,
    SearchResults,
    SavedSearch,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def make_result(rid, source, rtype, title, date=None, court="scotus", score=0.8):
    return SearchResultItem(
        result_id=rid,
        source=source,
        result_type=rtype,
        title=title,
        url=f"https://example.com/{rid}",
        date=date,
        court_or_agency=court,
        snippet=f"Snippet for {title}",
        relevance_score=score,
        authority_score=0.5,
    )


@pytest.fixture
def mock_courtlistener():
    client = AsyncMock()
    client.search_opinions = AsyncMock(return_value={
        "count": 2,
        "results": [
            {
                "id": 1,
                "caseName": "Riley v. California",
                "court_id": "scotus",
                "dateFiled": "2014-06-25",
                "snippet": "Cell phone warrant required",
                "score": 20.0,
                "citeCount": 5000,
                "absolute_url": "/opinion/1/riley-v-california/",
            },
            {
                "id": 2,
                "caseName": "US v. Jones",
                "court_id": "scotus",
                "dateFiled": "2012-01-23",
                "snippet": "GPS tracking is a search",
                "score": 15.0,
                "citeCount": 3000,
                "absolute_url": "/opinion/2/us-v-jones/",
            },
        ],
        "next": None,
    })
    client.search_dockets = AsyncMock(return_value={
        "count": 1,
        "results": [{
            "docket_id": 99,
            "caseName": "Some Corp v. Other Corp",
            "court_id": "nysd",
            "date_filed": "2023-01-10",
            "snippet": "Complex commercial dispute",
            "score": 5.0,
            "absolute_url": "/docket/99/some-corp/",
        }],
    })
    return client


@pytest.fixture
def mock_congress():
    client = AsyncMock()
    client.search_bills = AsyncMock(return_value={
        "bills": [
            {
                "congress": 118,
                "type": "HR",
                "number": 1234,
                "title": "Digital Privacy Protection Act",
                "url": "https://api.congress.gov/v3/bill/118/hr/1234",
                "latestAction": {"actionDate": "2023-09-15", "text": "Passed committee"},
            }
        ]
    })
    return client


@pytest.fixture
def engine(mock_courtlistener, mock_congress):
    return CaseLawSearchEngine(
        courtlistener=mock_courtlistener,
        congress=mock_congress,
    )


@pytest.fixture
def engine_no_sources():
    return CaseLawSearchEngine()


# ---------------------------------------------------------------------------
# QueryParser tests
# ---------------------------------------------------------------------------


class TestQueryParser:
    def test_parse_basic_query(self):
        parser = QueryParser()
        q = parser.parse("Fourth Amendment warrant cell phone")
        assert "Fourth" in " ".join(q.terms) or len(q.terms) > 0

    def test_parse_with_phrase(self):
        parser = QueryParser()
        q = parser.parse('"reasonable expectation of privacy" Fourth Amendment')
        assert q.phrase == "reasonable expectation of privacy"

    def test_detect_court_scotus(self):
        parser = QueryParser()
        q = parser.parse("Supreme Court Fourth Amendment ruling")
        assert q.court_filter == "scotus"

    def test_detect_court_ninth_circuit(self):
        parser = QueryParser()
        q = parser.parse("Ninth Circuit immigration decision")
        assert q.court_filter == "ca9"

    def test_detect_practice_area_antitrust(self):
        parser = QueryParser()
        q = parser.parse("antitrust monopoly Sherman Act violation")
        assert q.practice_area == "antitrust"

    def test_detect_practice_area_patent(self):
        parser = QueryParser()
        q = parser.parse("patent infringement software claims")
        assert q.practice_area == "intellectual property"

    def test_no_court_detected(self):
        parser = QueryParser()
        q = parser.parse("general contract dispute breach")
        assert q.court_filter is None

    def test_override_court_with_kwarg(self):
        parser = QueryParser()
        q = parser.parse("Supreme Court case", court_filter="ca2")
        assert q.court_filter == "ca2"

    def test_date_range_passed_through(self):
        parser = QueryParser()
        q = parser.parse("contract law", date_min="2020-01-01", date_max="2023-12-31")
        assert q.date_min == "2020-01-01"
        assert q.date_max == "2023-12-31"

    def test_page_and_size_defaults(self):
        parser = QueryParser()
        q = parser.parse("test")
        assert q.page == 1
        assert q.page_size == 20

    def test_source_filters_default(self):
        parser = QueryParser()
        q = parser.parse("test")
        assert "opinions" in q.source_filters
        assert "bills" in q.source_filters


# ---------------------------------------------------------------------------
# CaseLawSearchEngine tests
# ---------------------------------------------------------------------------


class TestCaseLawSearchEngine:
    @pytest.mark.asyncio
    async def test_search_returns_results(self, engine):
        """Test basic search returns results."""
        results = await engine.search("Fourth Amendment cell phone warrant")
        assert isinstance(results, SearchResults)
        assert results.total_results >= 0

    @pytest.mark.asyncio
    async def test_search_includes_opinions(self, engine):
        """Test that opinions are included in results."""
        results = await engine.search(
            "cell phone warrant",
            sources=["opinions"],
        )
        opinion_results = [r for r in results.results if r.result_type == "opinion"]
        assert len(opinion_results) >= 1

    @pytest.mark.asyncio
    async def test_search_includes_bills(self, engine):
        """Test that bills are included when querying Congress."""
        results = await engine.search(
            "digital privacy legislation",
            sources=["bills"],
        )
        bill_results = [r for r in results.results if r.result_type == "bill"]
        assert len(bill_results) >= 1

    @pytest.mark.asyncio
    async def test_search_no_sources_returns_empty(self, engine_no_sources):
        """Test that engine with no sources returns empty results."""
        results = await engine_no_sources.search("any query")
        assert results.total_results == 0
        assert results.results == []

    @pytest.mark.asyncio
    async def test_search_pagination(self, engine):
        """Test that pagination works correctly."""
        results_p1 = await engine.search("privacy", page=1, page_size=2)
        assert results_p1.page == 1
        assert len(results_p1.results) <= 2

    @pytest.mark.asyncio
    async def test_search_has_next_page(self, engine, mock_courtlistener):
        """Test has_next_page is True when more results exist."""
        # Make search return many results
        mock_courtlistener.search_opinions = AsyncMock(return_value={
            "count": 10,
            "results": [
                {"id": i, "caseName": f"Case {i}", "court_id": "ca9",
                 "dateFiled": "2023-01-01", "snippet": "", "score": float(10-i),
                 "citeCount": 100, "absolute_url": f"/opinion/{i}/"}
                for i in range(10)
            ],
            "next": None,
        })
        results = await engine.search("test", sources=["opinions"], page=1, page_size=2)
        assert results.has_next_page is True

    @pytest.mark.asyncio
    async def test_search_order_by_date(self, engine):
        """Test sorting results by date."""
        results = await engine.search("privacy", order_by="date")
        if len(results.results) >= 2:
            dates = [r.date for r in results.results if r.date]
            if dates:
                assert dates == sorted(dates, reverse=True)

    @pytest.mark.asyncio
    async def test_search_order_by_authority(self, engine):
        """Test sorting results by authority score."""
        results = await engine.search("privacy", order_by="authority")
        if len(results.results) >= 2:
            scores = [r.authority_score for r in results.results]
            assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_search_builds_facets(self, engine):
        """Test that search results include facets."""
        results = await engine.search("Fourth Amendment", sources=["opinions", "bills"])
        assert "source" in results.facets
        assert "result_type" in results.facets

    @pytest.mark.asyncio
    async def test_search_deduplicates_results(self, engine, mock_courtlistener):
        """Test that duplicate results are removed."""
        # Return same result twice
        same_result = {
            "id": 1,
            "caseName": "Riley v. California",
            "court_id": "scotus",
            "dateFiled": "2014-06-25",
            "snippet": "Cell phone",
            "score": 20.0,
            "citeCount": 5000,
            "absolute_url": "/opinion/1/riley/",
        }
        mock_courtlistener.search_opinions = AsyncMock(return_value={
            "count": 2,
            "results": [same_result, same_result],
            "next": None,
        })
        results = await engine.search("test", sources=["opinions"])
        ids = [r.result_id for r in results.results]
        assert len(ids) == len(set(ids))  # No duplicates

    @pytest.mark.asyncio
    async def test_search_records_history(self, engine):
        """Test that searches are recorded in history."""
        await engine.search("test query one")
        await engine.search("test query two")
        history = engine.get_search_history()
        assert len(history) >= 2
        queries = [h["query"] for h in history]
        assert "test query one" in queries
        assert "test query two" in queries

    def test_save_search(self, engine):
        """Test saving a search configuration."""
        parser = QueryParser()
        q = parser.parse("Fourth Amendment digital privacy")
        search_id = engine.save_search("Fourth Amendment Cases", q)
        assert search_id is not None
        listing = engine.list_saved_searches()
        assert any(s["search_id"] == search_id for s in listing)

    @pytest.mark.asyncio
    async def test_run_saved_search(self, engine):
        """Test running a previously saved search."""
        parser = QueryParser()
        q = parser.parse("Fourth Amendment")
        search_id = engine.save_search("Test Save", q)
        results = await engine.run_saved_search(search_id)
        assert results is not None

    @pytest.mark.asyncio
    async def test_run_missing_saved_search(self, engine):
        """Test running a missing saved search returns None."""
        result = await engine.run_saved_search("nonexistent_id")
        assert result is None

    def test_export_json(self, engine):
        """Test exporting results as JSON."""
        item = make_result("cl_opinion_1", "courtlistener", "opinion", "Riley v. California", "2014-06-25")
        results = SearchResults(
            query="test",
            total_results=1,
            results=[item],
            facets={"source": {"courtlistener": 1}},
            sources_queried=["courtlistener"],
            search_time_ms=42.0,
            page=1,
            page_size=20,
            has_next_page=False,
        )
        json_str = engine.export_json(results)
        data = json.loads(json_str)
        assert data["total"] == 1
        assert len(data["results"]) == 1

    def test_export_csv(self, engine):
        """Test exporting results as CSV."""
        item = make_result("cl_opinion_1", "courtlistener", "opinion", "Test v. Case", "2020-01-01")
        results = SearchResults(
            query="test",
            total_results=1,
            results=[item],
            facets={},
            sources_queried=["courtlistener"],
            search_time_ms=10.0,
            page=1,
            page_size=20,
            has_next_page=False,
        )
        csv_str = engine.export_csv(results)
        assert "Test v. Case" in csv_str
        assert "courtlistener" in csv_str

    @pytest.mark.asyncio
    async def test_search_handles_source_error_gracefully(self, engine, mock_courtlistener):
        """Test that one source error doesn't break the whole search."""
        mock_courtlistener.search_opinions = AsyncMock(side_effect=Exception("Network error"))
        # Should not raise, just skip failing source
        results = await engine.search("test", sources=["opinions", "bills"])
        assert isinstance(results, SearchResults)

    def test_list_saved_searches_empty(self, engine):
        """Test listing saved searches when none exist."""
        listing = engine.list_saved_searches()
        assert listing == []

    def test_get_search_history_limit(self, engine):
        """Test that history limit is respected."""
        for i in range(10):
            engine._search_history.append({
                "query": f"query {i}",
                "timestamp": f"2024-01-{i+1:02d}T00:00:00",
                "total_results": i,
                "search_time_ms": 100.0,
            })
        history = engine.get_search_history(limit=5)
        assert len(history) == 5

    @pytest.mark.asyncio
    async def test_search_time_recorded(self, engine):
        """Test that search time is recorded in results."""
        results = await engine.search("test")
        assert results.search_time_ms >= 0.0
