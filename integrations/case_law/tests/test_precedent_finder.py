"""
Tests for PrecedentFinder
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from ..precedent_finder import (
    PrecedentFinder,
    PrecedentResult,
    PrecedentBrief,
    BindingStatus,
    JurisdictionFilter,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_courtlistener():
    """Mock CourtListenerClient."""
    client = AsyncMock()
    client.search_opinions = AsyncMock(return_value={
        "count": 3,
        "results": [
            {
                "id": 101,
                "cluster_id": 201,
                "caseName": "Riley v. California",
                "court_id": "scotus",
                "dateFiled": "2014-06-25",
                "snippet": "Police must generally obtain a warrant before searching a cell phone",
                "score": 20.0,
                "citeCount": 5000,
                "absolute_url": "/opinion/101/riley-v-california/",
                "citation": ["573 U.S. 373"],
            },
            {
                "id": 102,
                "cluster_id": 202,
                "caseName": "United States v. Jones",
                "court_id": "scotus",
                "dateFiled": "2012-01-23",
                "snippet": "GPS tracking device attachment is a Fourth Amendment search",
                "score": 15.0,
                "citeCount": 3000,
                "absolute_url": "/opinion/102/us-v-jones/",
                "citation": ["565 U.S. 400"],
            },
            {
                "id": 103,
                "cluster_id": 203,
                "caseName": "State v. Johnson",
                "court_id": "ca9",
                "dateFiled": "2020-03-10",
                "snippet": "Warrantless search of laptop contents was unconstitutional",
                "score": 8.0,
                "citeCount": 150,
                "absolute_url": "/opinion/103/state-v-johnson/",
                "citation": ["987 F.3d 654"],
            },
        ],
        "next": None,
    })
    return client


@pytest.fixture
def mock_citation_network():
    """Mock CitationNetwork."""
    net = MagicMock()
    net.get_authority_score = MagicMock(return_value=0.8)
    net.is_overruled = MagicMock(return_value=False)
    return net


@pytest.fixture
def finder(mock_courtlistener, mock_citation_network):
    """Create a PrecedentFinder with mocked dependencies."""
    return PrecedentFinder(
        courtlistener=mock_courtlistener,
        citation_network=mock_citation_network,
    )


# ---------------------------------------------------------------------------
# PrecedentResult tests
# ---------------------------------------------------------------------------


class TestPrecedentResult:
    def test_create_precedent_result(self):
        result = PrecedentResult(
            case_id=101,
            case_name="Riley v. California",
            citation="573 U.S. 373",
            court="scotus",
            date="2014-06-25",
            holding="Warrant required to search cell phone",
            relevance_score=0.95,
            authority_score=0.9,
            binding_status=BindingStatus.BINDING,
            url="https://www.courtlistener.com/opinion/101/",
        )
        assert result.case_id == 101
        assert result.binding_status == BindingStatus.BINDING
        assert result.relevance_score == 0.95

    def test_binding_status_values(self):
        assert BindingStatus.BINDING.value == "binding"
        assert BindingStatus.PERSUASIVE.value == "persuasive"
        assert BindingStatus.NOT_APPLICABLE.value == "not_applicable"


# ---------------------------------------------------------------------------
# JurisdictionFilter tests
# ---------------------------------------------------------------------------


class TestJurisdictionFilter:
    def test_create_filter(self):
        jf = JurisdictionFilter(forum_court="ca9", state="CA")
        assert jf.forum_court == "ca9"
        assert jf.state == "CA"

    def test_include_scotus(self):
        jf = JurisdictionFilter(forum_court="ca9")
        assert jf.includes_scotus is True

    def test_binding_courts_include_scotus(self):
        jf = JurisdictionFilter(forum_court="ca9")
        assert "scotus" in jf.binding_courts

    def test_binding_courts_include_circuit(self):
        jf = JurisdictionFilter(forum_court="txnd")
        assert "ca5" in jf.binding_courts


# ---------------------------------------------------------------------------
# PrecedentFinder tests
# ---------------------------------------------------------------------------


class TestPrecedentFinder:
    @pytest.mark.asyncio
    async def test_find_precedent_returns_results(self, finder):
        """Test that find_precedent returns a list of results."""
        results = await finder.find_precedent(
            fact_pattern="Police searched suspect's cell phone without a warrant",
            forum_court="ca9",
        )
        assert isinstance(results, list)
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_find_precedent_scotus_ranked_higher(self, finder):
        """Test that SCOTUS cases rank higher than circuit cases."""
        results = await finder.find_precedent(
            fact_pattern="warrant search cell phone digital privacy",
            forum_court="ca9",
        )
        if len(results) >= 2:
            scotus_results = [r for r in results if r.court == "scotus"]
            ca9_results = [r for r in results if r.court == "ca9"]
            if scotus_results and ca9_results:
                assert scotus_results[0].authority_score >= ca9_results[0].authority_score

    @pytest.mark.asyncio
    async def test_find_precedent_binding_status_scotus(self, finder):
        """Test that SCOTUS opinions are marked as binding."""
        results = await finder.find_precedent(
            fact_pattern="Fourth Amendment warrant requirement digital search",
            forum_court="ca9",
        )
        scotus_results = [r for r in results if r.court == "scotus"]
        for r in scotus_results:
            assert r.binding_status == BindingStatus.BINDING

    @pytest.mark.asyncio
    async def test_find_precedent_with_jurisdiction_filter(self, finder):
        """Test jurisdiction filtering limits results."""
        results = await finder.find_precedent(
            fact_pattern="cell phone search",
            forum_court="scotus",
            include_persuasive=False,
        )
        # When forum is scotus and persuasive excluded, should return empty or only scotus
        for r in results:
            assert r.court == "scotus"

    @pytest.mark.asyncio
    async def test_find_precedent_excludes_overruled(self, finder, mock_citation_network):
        """Test that overruled cases are excluded or flagged."""
        mock_citation_network.is_overruled = MagicMock(return_value=True)
        results = await finder.find_precedent(
            fact_pattern="test pattern",
            forum_court="ca9",
            exclude_overruled=True,
        )
        for r in results:
            assert not r.is_overruled

    @pytest.mark.asyncio
    async def test_generate_precedent_brief(self, finder):
        """Test generating a complete precedent brief."""
        results = await finder.find_precedent(
            fact_pattern="warrant required for cell phone search",
            forum_court="ca9",
        )
        if results:
            brief = finder.generate_precedent_brief(
                fact_pattern="warrant required for cell phone search",
                results=results,
                forum_court="ca9",
            )
            assert isinstance(brief, PrecedentBrief)
            assert brief.fact_pattern
            assert isinstance(brief.binding_precedents, list)
            assert isinstance(brief.persuasive_precedents, list)

    @pytest.mark.asyncio
    async def test_find_analogous_cases(self, finder):
        """Test finding analogous cases across practice areas."""
        results = await finder.find_analogous_cases(
            case_id=101,
            fact_summary="Digital privacy, warrant required for cell phone",
        )
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_distinguish_favorable_unfavorable(self, finder):
        """Test distinguishing favorable from unfavorable precedent."""
        all_results = await finder.find_precedent(
            fact_pattern="search without warrant",
            forum_court="ca9",
        )
        if all_results:
            favorable = finder.filter_favorable(
                results=all_results,
                client_position="defendant seeking suppression",
            )
            unfavorable = finder.filter_unfavorable(
                results=all_results,
                client_position="defendant seeking suppression",
            )
            assert isinstance(favorable, list)
            assert isinstance(unfavorable, list)

    @pytest.mark.asyncio
    async def test_rank_by_authority_score(self, finder):
        """Test that results can be ranked by authority score."""
        results = await finder.find_precedent("test pattern", forum_court="ca1")
        if len(results) >= 2:
            ranked = finder.rank_by_authority(results)
            scores = [r.authority_score for r in ranked]
            assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_rank_by_recency(self, finder):
        """Test that results can be ranked by recency."""
        results = await finder.find_precedent("test pattern", forum_court="ca1")
        if len(results) >= 2:
            ranked = finder.rank_by_recency(results)
            dates = [r.date for r in ranked if r.date]
            assert dates == sorted(dates, reverse=True)

    @pytest.mark.asyncio
    async def test_find_precedent_empty_query(self, finder, mock_courtlistener):
        """Test handling of empty or very short query."""
        mock_courtlistener.search_opinions = AsyncMock(return_value={"count": 0, "results": [], "next": None})
        results = await finder.find_precedent("", forum_court="ca9")
        assert results == []

    @pytest.mark.asyncio
    async def test_find_precedent_api_error(self, finder, mock_courtlistener):
        """Test graceful handling of API errors."""
        from ..courtlistener_client import APIError
        mock_courtlistener.search_opinions = AsyncMock(side_effect=APIError("API error"))
        results = await finder.find_precedent("test pattern", forum_court="ca9")
        assert results == []

    def test_generate_brief_empty_results(self, finder):
        """Test generating brief with no results."""
        brief = finder.generate_precedent_brief(
            fact_pattern="unsearchable topic",
            results=[],
            forum_court="ca9",
        )
        assert brief.fact_pattern == "unsearchable topic"
        assert brief.binding_precedents == []
        assert brief.persuasive_precedents == []
        assert "no precedent" in brief.summary.lower()

    @pytest.mark.asyncio
    async def test_combined_relevance_authority_score(self, finder):
        """Test that final ranking combines relevance and authority."""
        results = await finder.find_precedent(
            fact_pattern="Fourth Amendment digital privacy",
            forum_court="ca9",
        )
        # Results should be sorted by combined score
        if len(results) >= 2:
            final_scores = [r.relevance_score * 0.6 + r.authority_score * 0.4 for r in results]
            # Should be roughly descending (some tolerance for tie-breaking)
            assert final_scores[0] >= final_scores[-1]
