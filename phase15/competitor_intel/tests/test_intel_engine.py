"""Tests for Phase 15E — Competitor Intel Engine."""
import sys, os

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from phase15.competitor_intel.intel_engine import (
    CompetitorCategory, PricingModel, ThreatLevel, ChangeType,
    PricingTier, Competitor, CompetitorChange, FeatureGap, IntelReport,
    WebScraper, ChangeDetector, FeatureGapAnalyzer, StrategyEngine,
    CompetitorIntelEngine, SINTRA_FEATURES,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def clio_v1():
    return Competitor(
        competitor_id="clio",
        name="Clio",
        website="https://www.clio.com",
        category=CompetitorCategory.LEGAL_TECH,
        description="Practice management",
        pricing_model=PricingModel.SUBSCRIPTION,
        pricing_tiers=[PricingTier("Starter", price_monthly=49.0)],
        features=["Case management", "Billing"],
        integrations=["QuickBooks"],
        threat_level=ThreatLevel.HIGH,
    )


@pytest.fixture
def clio_v2():
    return Competitor(
        competitor_id="clio",
        name="Clio",
        website="https://www.clio.com",
        category=CompetitorCategory.LEGAL_TECH,
        description="Practice management",
        pricing_model=PricingModel.SUBSCRIPTION,
        pricing_tiers=[PricingTier("Starter", price_monthly=59.0)],  # Price increase
        features=["Case management", "Billing", "AI drafting"],  # New feature
        integrations=["QuickBooks", "Slack"],  # New integration
        threat_level=ThreatLevel.HIGH,
        funding_total=50_000_000,  # New funding
    )


@pytest.fixture
def harvey():
    return Competitor(
        competitor_id="harvey",
        name="Harvey AI",
        website="https://www.harvey.ai",
        category=CompetitorCategory.LEGAL_AI,
        description="AI for legal research",
        pricing_model=PricingModel.ENTERPRISE,
        features=["AI legal Q&A", "Document drafting", "Contract analysis"],
        threat_level=ThreatLevel.CRITICAL,
        funding_total=100_000_000,
    )


@pytest.fixture
def engine():
    # Use a fresh engine without default competitors for isolated tests
    eng = CompetitorIntelEngine.__new__(CompetitorIntelEngine)
    eng._scraper = WebScraper()
    eng._change_detector = ChangeDetector()
    eng._gap_analyzer = FeatureGapAnalyzer()
    eng._strategy_engine = StrategyEngine()
    eng._on_change_detected = None
    eng._on_report_generated = None
    eng._competitors = {}
    eng._snapshots = {}
    eng._changes = []
    eng._reports = []
    return eng


@pytest.fixture
def engine_with_defaults():
    return CompetitorIntelEngine()


# ---------------------------------------------------------------------------
# Competitor model tests
# ---------------------------------------------------------------------------

class TestCompetitor:
    def test_get_min_price_with_tiers(self, clio_v1):
        assert clio_v1.get_min_price() == 49.0

    def test_get_min_price_no_tiers(self, harvey):
        assert harvey.get_min_price() is None

    def test_get_min_price_multiple_tiers(self):
        comp = Competitor("C1", "Test", "https://test.com", CompetitorCategory.LEGAL_AI, "")
        comp.pricing_tiers = [
            PricingTier("Basic", price_monthly=99.0),
            PricingTier("Pro", price_monthly=199.0),
            PricingTier("Enterprise", price_monthly=499.0),
        ]
        assert comp.get_min_price() == 99.0

    def test_has_feature_exact_match(self, clio_v1):
        assert clio_v1.has_feature("Case management") is True

    def test_has_feature_case_insensitive(self, clio_v1):
        assert clio_v1.has_feature("case management") is True

    def test_has_feature_partial_match(self, clio_v1):
        assert clio_v1.has_feature("billing") is True

    def test_has_feature_not_present(self, clio_v1):
        assert clio_v1.has_feature("AI drafting") is False

    def test_domain_extraction(self, clio_v1):
        assert clio_v1.domain() == "www.clio.com"


# ---------------------------------------------------------------------------
# WebScraper tests
# ---------------------------------------------------------------------------

class TestWebScraper:
    def test_fetch_without_client_returns_none(self):
        scraper = WebScraper()
        result = scraper.fetch("https://example.com")
        assert result is None

    def test_fetch_with_mock_client_200(self):
        mock_http = MagicMock()
        mock_http.get.return_value = MagicMock(status_code=200, text="<html>Hello</html>")
        scraper = WebScraper(http_client=mock_http, rate_limit_seconds=0)
        result = scraper.fetch("https://example.com")
        assert result == "<html>Hello</html>"

    def test_fetch_with_mock_client_404(self):
        mock_http = MagicMock()
        mock_http.get.return_value = MagicMock(status_code=404)
        scraper = WebScraper(http_client=mock_http, rate_limit_seconds=0)
        result = scraper.fetch("https://example.com")
        assert result is None

    def test_fetch_exception_returns_none(self):
        mock_http = MagicMock()
        mock_http.get.side_effect = Exception("Connection refused")
        scraper = WebScraper(http_client=mock_http, rate_limit_seconds=0)
        result = scraper.fetch("https://example.com")
        assert result is None

    def test_extract_text_strips_html(self):
        scraper = WebScraper()
        html = "<h1>Hello</h1><p>World</p>"
        text = scraper.extract_text(html)
        assert "Hello" in text
        assert "World" in text
        assert "<h1>" not in text

    def test_extract_price_finds_dollar_amount(self):
        scraper = WebScraper()
        assert scraper.extract_price("Starting at $49.99/month") == 49.99
        assert scraper.extract_price("Free plan available") is None

    def test_extract_rating_finds_score(self):
        scraper = WebScraper()
        assert scraper.extract_rating("Rated 4.5/5 by users") == 4.5
        assert scraper.extract_rating("4.8 out of 5 stars") == 4.8
        assert scraper.extract_rating("No rating") is None


# ---------------------------------------------------------------------------
# ChangeDetector tests
# ---------------------------------------------------------------------------

class TestChangeDetector:
    def test_detects_new_feature(self, clio_v1, clio_v2):
        detector = ChangeDetector()
        changes = detector.detect_changes(clio_v1, clio_v2)
        feature_changes = [c for c in changes if c.change_type == ChangeType.NEW_FEATURE]
        assert len(feature_changes) == 1
        assert "AI drafting" in feature_changes[0].description

    def test_detects_price_increase(self, clio_v1, clio_v2):
        detector = ChangeDetector()
        changes = detector.detect_changes(clio_v1, clio_v2)
        price_changes = [c for c in changes if c.change_type == ChangeType.PRICE_CHANGE]
        assert len(price_changes) == 1
        assert "increased" in price_changes[0].description

    def test_detects_price_decrease(self, clio_v1):
        clio_cheaper = Competitor(
            competitor_id="clio", name="Clio", website="https://clio.com",
            category=CompetitorCategory.LEGAL_TECH, description="",
            pricing_tiers=[PricingTier("Starter", price_monthly=39.0)],
        )
        detector = ChangeDetector()
        changes = detector.detect_changes(clio_v1, clio_cheaper)
        price_changes = [c for c in changes if c.change_type == ChangeType.PRICE_CHANGE]
        assert len(price_changes) == 1
        assert "decreased" in price_changes[0].description

    def test_detects_new_integration(self, clio_v1, clio_v2):
        detector = ChangeDetector()
        changes = detector.detect_changes(clio_v1, clio_v2)
        integration_changes = [c for c in changes if c.change_type == ChangeType.NEW_INTEGRATION]
        assert len(integration_changes) == 1
        assert "Slack" in integration_changes[0].description

    def test_detects_funding_increase(self, clio_v1, clio_v2):
        detector = ChangeDetector()
        changes = detector.detect_changes(clio_v1, clio_v2)
        funding_changes = [c for c in changes if c.change_type == ChangeType.FUNDING]
        assert len(funding_changes) == 1

    def test_no_changes_when_identical(self, clio_v1):
        detector = ChangeDetector()
        changes = detector.detect_changes(clio_v1, clio_v1)
        assert len(changes) == 0

    def test_change_has_competitor_id(self, clio_v1, clio_v2):
        detector = ChangeDetector()
        changes = detector.detect_changes(clio_v1, clio_v2)
        for change in changes:
            assert change.competitor_id == "clio"


# ---------------------------------------------------------------------------
# FeatureGapAnalyzer tests
# ---------------------------------------------------------------------------

class TestFeatureGapAnalyzer:
    def test_identifies_gaps(self, clio_v1, harvey):
        analyzer = FeatureGapAnalyzer()
        gaps = analyzer.analyze([clio_v1, harvey])
        gap_features = {g.feature for g in gaps}
        assert "AI legal Q&A" in gap_features  # Harvey has it, Sintra has it too
        assert "Case management" in gap_features

    def test_sintra_has_feature_correctly_set(self, harvey):
        analyzer = FeatureGapAnalyzer()
        gaps = analyzer.analyze([harvey])
        qa_gap = next((g for g in gaps if g.feature == "AI legal Q&A"), None)
        assert qa_gap is not None
        assert qa_gap.sintra_has is True  # Sintra has AI legal Q&A

    def test_missing_feature_flagged(self):
        comp = Competitor(
            "C1", "Exotic Tool", "https://exotic.com",
            CompetitorCategory.LEGAL_AI, "",
            features=["Blockchain contracts", "NFT deeds"],
        )
        analyzer = FeatureGapAnalyzer()
        gaps = analyzer.analyze([comp])
        nft_gap = next((g for g in gaps if g.feature == "NFT deeds"), None)
        assert nft_gap is not None
        assert nft_gap.sintra_has is False

    def test_gaps_sorted_by_priority(self, clio_v1, harvey):
        analyzer = FeatureGapAnalyzer()
        gaps = analyzer.analyze([clio_v1, harvey])
        priorities = [g.priority for g in gaps]
        assert priorities == sorted(priorities, reverse=True)

    def test_recommendation_for_missing_feature(self):
        comp = Competitor(
            "C1", "Test", "https://test.com",
            CompetitorCategory.LEGAL_AI, "",
            features=["Holographic interface"],
        )
        analyzer = FeatureGapAnalyzer()
        gaps = analyzer.analyze([comp])
        gap = next((g for g in gaps if g.feature == "Holographic interface"), None)
        assert gap is not None
        assert "Consider adding" in gap.recommendation


# ---------------------------------------------------------------------------
# StrategyEngine tests
# ---------------------------------------------------------------------------

class TestStrategyEngine:
    def test_generates_pricing_recommendation(self, clio_v1):
        engine = StrategyEngine()
        recs = engine.generate_recommendations([clio_v1], [], [])
        assert any("price" in r.lower() or "Price" in r for r in recs)

    def test_generates_critical_gap_recommendation(self):
        engine = StrategyEngine()
        gap = FeatureGap(
            feature="Blockchain contracts",
            sintra_has=False,
            competitors_with_feature=["Comp1", "Comp2", "Comp3"],
            priority=5,
        )
        recs = engine.generate_recommendations([], [gap], [])
        assert any("Blockchain contracts" in r for r in recs)

    def test_generates_funding_threat_recommendation(self):
        engine = StrategyEngine()
        change = CompetitorChange(
            change_id="C1", competitor_id="Harvey",
            change_type=ChangeType.FUNDING,
            description="Received $100M",
            significance=5,
        )
        recs = engine.generate_recommendations([], [], [change])
        assert any("Harvey" in r or "funding" in r.lower() for r in recs)

    def test_default_recommendation_when_no_threats(self):
        engine = StrategyEngine()
        recs = engine.generate_recommendations([], [], [])
        assert len(recs) >= 1
        assert any("monitoring" in r.lower() for r in recs)


# ---------------------------------------------------------------------------
# CompetitorIntelEngine tests
# ---------------------------------------------------------------------------

class TestCompetitorIntelEngine:
    def test_add_and_get_competitor(self, engine, clio_v1):
        engine.add_competitor(clio_v1)
        assert engine.get_competitor("clio") is clio_v1

    def test_list_competitors_all(self, engine, clio_v1, harvey):
        engine.add_competitor(clio_v1)
        engine.add_competitor(harvey)
        assert len(engine.list_competitors()) == 2

    def test_list_competitors_by_category(self, engine, clio_v1, harvey):
        engine.add_competitor(clio_v1)
        engine.add_competitor(harvey)
        legal_ai = engine.list_competitors(category=CompetitorCategory.LEGAL_AI)
        assert len(legal_ai) == 1
        assert legal_ai[0].competitor_id == "harvey"

    def test_list_competitors_by_threat(self, engine, clio_v1, harvey):
        engine.add_competitor(clio_v1)
        engine.add_competitor(harvey)
        critical = engine.list_competitors(threat_level=ThreatLevel.CRITICAL)
        assert len(critical) == 1
        assert critical[0].competitor_id == "harvey"

    def test_update_competitor_detects_changes(self, engine, clio_v1, clio_v2):
        engine.add_competitor(clio_v1)
        # Set snapshot
        engine._snapshots["clio"] = clio_v1
        changes = engine.update_competitor(clio_v2)
        assert len(changes) > 0

    def test_update_competitor_no_snapshot_no_changes(self, engine, clio_v1):
        engine.add_competitor(clio_v1)
        changes = engine.update_competitor(clio_v1)
        assert len(changes) == 0

    def test_on_change_detected_callback(self, engine, clio_v1, clio_v2):
        callback = MagicMock()
        engine._on_change_detected = callback
        engine.add_competitor(clio_v1)
        engine._snapshots["clio"] = clio_v1
        engine.update_competitor(clio_v2)
        assert callback.call_count > 0

    def test_generate_report_structure(self, engine, clio_v1, harvey):
        engine.add_competitor(clio_v1)
        engine.add_competitor(harvey)
        report = engine.generate_report()
        assert report.competitors_analyzed == 2
        assert report.generated_at is not None
        assert len(report.strategic_recommendations) > 0
        assert len(report.pricing_comparison) == 2

    def test_generate_report_threat_summary(self, engine, clio_v1, harvey):
        engine.add_competitor(clio_v1)
        engine.add_competitor(harvey)
        report = engine.generate_report()
        assert ThreatLevel.HIGH.value in report.threat_summary
        assert ThreatLevel.CRITICAL.value in report.threat_summary

    def test_on_report_generated_callback(self, engine, clio_v1):
        callback = MagicMock()
        engine._on_report_generated = callback
        engine.add_competitor(clio_v1)
        engine.generate_report()
        callback.assert_called_once()

    def test_get_latest_report(self, engine, clio_v1):
        engine.add_competitor(clio_v1)
        assert engine.get_latest_report() is None
        report = engine.generate_report()
        assert engine.get_latest_report() is report

    def test_report_to_markdown(self, engine, clio_v1, harvey):
        engine.add_competitor(clio_v1)
        engine.add_competitor(harvey)
        report = engine.generate_report()
        md = report.to_markdown()
        assert "# SintraPrime Competitor Intelligence Report" in md
        assert "Clio" in md or "Harvey" in md
        assert "## Strategic Recommendations" in md

    def test_get_stats(self, engine, clio_v1, harvey):
        engine.add_competitor(clio_v1)
        engine.add_competitor(harvey)
        stats = engine.get_stats()
        assert stats["total_competitors"] == 2
        assert stats["critical_threat_count"] == 1
        assert stats["high_threat_count"] == 1

    def test_default_competitors_loaded(self, engine_with_defaults):
        comps = engine_with_defaults.list_competitors()
        assert len(comps) >= 4
        names = {c.name for c in comps}
        assert "Clio" in names
        assert "Harvey AI" in names

    def test_get_all_changes_empty(self, engine):
        assert engine.get_all_changes() == []

    def test_get_all_changes_after_update(self, engine, clio_v1, clio_v2):
        engine.add_competitor(clio_v1)
        engine._snapshots["clio"] = clio_v1
        engine.update_competitor(clio_v2)
        changes = engine.get_all_changes()
        assert len(changes) > 0

    def test_report_includes_recent_changes_only(self, engine, clio_v1, clio_v2):
        engine.add_competitor(clio_v1)
        engine._snapshots["clio"] = clio_v1
        engine.update_competitor(clio_v2)
        # Backdate one change to 10 days ago
        if engine._changes:
            engine._changes[0].detected_at = datetime.utcnow() - timedelta(days=10)
        report = engine.generate_report()
        # Only changes within 7 days should appear
        for change in report.changes_detected:
            assert (datetime.utcnow() - change.detected_at).days <= 7
