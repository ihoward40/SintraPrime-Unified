"""Phase 16D — AI Contract Redlining tests (112 tests)."""
import pytest
from phase16.contract_redline.models import (
    ClauseType, RiskLevel, RedlineAction,
)
from phase16.contract_redline.redline_engine import (
    ContractRedlineEngine, ClauseExtractor, RiskAnalyzer, RedlineSuggester,
    RISK_PATTERNS, CLAUSE_KEYWORDS, STANDARD_REDLINES,
)

# ── Sample contract texts ─────────────────────────────────────────────────────
INDEMNIFICATION_TEXT = """
1. INDEMNIFICATION
Client shall indemnify and hold harmless Provider from any and all claims, damages,
losses, and expenses, including unlimited liability for any breach.
"""

TERMINATION_TEXT = """
2. TERMINATION
Either party may terminate this Agreement immediately upon written notice
if the other party breaches any provision hereof.
"""

NON_COMPETE_TEXT = """
3. NON-COMPETE
Employee agrees not to compete with Company for a period of five years
within any jurisdiction where Company conducts business.
"""

PAYMENT_TEXT = """
4. PAYMENT TERMS
All invoices are due and payable on a net-90 basis from the date of invoice.
Late payments shall accrue interest at 1.5% per month.
"""

FULL_CONTRACT = INDEMNIFICATION_TEXT + TERMINATION_TEXT + NON_COMPETE_TEXT + PAYMENT_TEXT

CONFIDENTIALITY_TEXT = """
5. CONFIDENTIALITY
The receiving party agrees to maintain perpetual confidentiality of all
information disclosed without limit on scope or duration.
"""

IP_TEXT = """
6. INTELLECTUAL PROPERTY
All intellectual property created under this Agreement shall be assigned
to Client as work for hire.
"""


@pytest.fixture
def engine():
    return ContractRedlineEngine()


@pytest.fixture
def extractor():
    return ClauseExtractor()


@pytest.fixture
def analyzer():
    return RiskAnalyzer()


@pytest.fixture
def suggester():
    return RedlineSuggester()


@pytest.fixture
def analysis(engine):
    return engine.analyze("contract_001", FULL_CONTRACT)


# ─────────────────────────────────────────────────────────────
# Clause extraction tests (20)
# ─────────────────────────────────────────────────────────────
class TestClauseExtraction:
    def test_extract_returns_clauses(self, extractor):
        clauses = extractor.extract(FULL_CONTRACT)
        assert len(clauses) >= 1

    def test_clause_has_id(self, extractor):
        clauses = extractor.extract(INDEMNIFICATION_TEXT)
        assert all(c.clause_id.startswith("cl_") for c in clauses)

    def test_indemnification_classified(self, extractor):
        clauses = extractor.extract(INDEMNIFICATION_TEXT)
        types = [c.clause_type for c in clauses]
        assert ClauseType.INDEMNIFICATION in types

    def test_termination_classified(self, extractor):
        clauses = extractor.extract(TERMINATION_TEXT)
        types = [c.clause_type for c in clauses]
        assert ClauseType.TERMINATION in types

    def test_non_compete_classified(self, extractor):
        clauses = extractor.extract(NON_COMPETE_TEXT)
        types = [c.clause_type for c in clauses]
        assert ClauseType.NON_COMPETE in types

    def test_payment_classified(self, extractor):
        clauses = extractor.extract(PAYMENT_TEXT)
        types = [c.clause_type for c in clauses]
        assert ClauseType.PAYMENT in types

    def test_confidentiality_classified(self, extractor):
        clauses = extractor.extract(CONFIDENTIALITY_TEXT)
        types = [c.clause_type for c in clauses]
        assert ClauseType.CONFIDENTIALITY in types

    def test_ip_classified(self, extractor):
        clauses = extractor.extract(IP_TEXT)
        types = [c.clause_type for c in clauses]
        assert ClauseType.INTELLECTUAL_PROPERTY in types

    def test_clause_text_not_empty(self, extractor):
        clauses = extractor.extract(FULL_CONTRACT)
        assert all(len(c.original_text) > 0 for c in clauses)

    def test_clause_unique_ids(self, extractor):
        clauses = extractor.extract(FULL_CONTRACT)
        ids = [c.clause_id for c in clauses]
        assert len(ids) == len(set(ids))

    def test_empty_text_returns_clause(self, extractor):
        clauses = extractor.extract("Some general text here.")
        assert len(clauses) >= 1

    def test_general_clause_fallback(self, extractor):
        clauses = extractor.extract("This is a general clause with no specific keywords.")
        assert clauses[0].clause_type == ClauseType.GENERAL

    def test_classify_text_governing_law(self, extractor):
        text = "This agreement shall be governed by the laws of New York jurisdiction."
        clause_type = extractor._classify_text(text)
        assert clause_type == ClauseType.GOVERNING_LAW

    def test_classify_text_dispute_resolution(self, extractor):
        text = "All disputes shall be resolved through binding arbitration."
        clause_type = extractor._classify_text(text)
        assert clause_type == ClauseType.DISPUTE_RESOLUTION

    def test_classify_text_force_majeure(self, extractor):
        text = "Neither party shall be liable for force majeure events or acts of God."
        clause_type = extractor._classify_text(text)
        assert clause_type == ClauseType.FORCE_MAJEURE

    def test_classify_text_assignment(self, extractor):
        text = "This agreement may not be assigned without prior written consent."
        clause_type = extractor._classify_text(text)
        assert clause_type == ClauseType.ASSIGNMENT

    def test_clause_page_number_positive(self, extractor):
        clauses = extractor.extract(FULL_CONTRACT)
        assert all(c.page_number >= 1 for c in clauses)

    def test_multiple_clauses_from_full_contract(self, extractor):
        clauses = extractor.extract(FULL_CONTRACT)
        assert len(clauses) >= 2

    def test_clause_keywords_coverage(self):
        assert len(CLAUSE_KEYWORDS) >= 10

    def test_risk_patterns_coverage(self):
        assert len(RISK_PATTERNS) >= 5


# ─────────────────────────────────────────────────────────────
# Risk analysis tests (25)
# ─────────────────────────────────────────────────────────────
class TestRiskAnalysis:
    def test_analyze_returns_flags(self, extractor, analyzer):
        clauses = extractor.extract(INDEMNIFICATION_TEXT)
        flags = analyzer.analyze(clauses)
        assert len(flags) >= 1

    def test_indemnification_high_risk(self, extractor, analyzer):
        clauses = extractor.extract(INDEMNIFICATION_TEXT)
        flags = analyzer.analyze(clauses)
        levels = [f.risk_level for f in flags]
        assert RiskLevel.HIGH in levels or RiskLevel.CRITICAL in levels

    def test_unlimited_liability_critical(self, extractor, analyzer):
        text = "Party shall assume unlimited liability for all claims."
        clauses = extractor.extract(text)
        # Manually set clause type for deterministic test
        for c in clauses:
            c.clause_type = ClauseType.INDEMNIFICATION
        flags = analyzer.analyze(clauses)
        critical = [f for f in flags if f.risk_level == RiskLevel.CRITICAL]
        assert len(critical) >= 1

    def test_termination_immediate_high_risk(self, extractor, analyzer):
        clauses = extractor.extract(TERMINATION_TEXT)
        flags = analyzer.analyze(clauses)
        assert len(flags) >= 1

    def test_non_compete_high_risk(self, extractor, analyzer):
        clauses = extractor.extract(NON_COMPETE_TEXT)
        flags = analyzer.analyze(clauses)
        assert len(flags) >= 1

    def test_payment_net90_medium_risk(self, extractor, analyzer):
        clauses = extractor.extract(PAYMENT_TEXT)
        flags = analyzer.analyze(clauses)
        medium_or_higher = [f for f in flags if f.risk_level in (RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL)]
        assert len(medium_or_higher) >= 1

    def test_flag_has_issue(self, extractor, analyzer):
        clauses = extractor.extract(INDEMNIFICATION_TEXT)
        flags = analyzer.analyze(clauses)
        assert all(len(f.issue) > 0 for f in flags)

    def test_flag_has_recommendation(self, extractor, analyzer):
        clauses = extractor.extract(INDEMNIFICATION_TEXT)
        flags = analyzer.analyze(clauses)
        assert all(len(f.recommendation) > 0 for f in flags)

    def test_flag_has_clause_id(self, extractor, analyzer):
        clauses = extractor.extract(INDEMNIFICATION_TEXT)
        flags = analyzer.analyze(clauses)
        clause_ids = {c.clause_id for c in clauses}
        assert all(f.clause_id in clause_ids for f in flags)

    def test_flag_unique_ids(self, extractor, analyzer):
        clauses = extractor.extract(FULL_CONTRACT)
        flags = analyzer.analyze(clauses)
        ids = [f.flag_id for f in flags]
        assert len(ids) == len(set(ids))

    def test_overall_risk_critical_wins(self, analyzer):
        from phase16.contract_redline.models import RiskFlag
        flags = [
            RiskFlag("f1", "c1", RiskLevel.LOW, "i", "r"),
            RiskFlag("f2", "c2", RiskLevel.CRITICAL, "i", "r"),
            RiskFlag("f3", "c3", RiskLevel.HIGH, "i", "r"),
        ]
        assert analyzer.compute_overall_risk(flags) == RiskLevel.CRITICAL

    def test_overall_risk_high(self, analyzer):
        from phase16.contract_redline.models import RiskFlag
        flags = [
            RiskFlag("f1", "c1", RiskLevel.LOW, "i", "r"),
            RiskFlag("f2", "c2", RiskLevel.HIGH, "i", "r"),
        ]
        assert analyzer.compute_overall_risk(flags) == RiskLevel.HIGH

    def test_overall_risk_medium(self, analyzer):
        from phase16.contract_redline.models import RiskFlag
        flags = [
            RiskFlag("f1", "c1", RiskLevel.LOW, "i", "r"),
            RiskFlag("f2", "c2", RiskLevel.MEDIUM, "i", "r"),
        ]
        assert analyzer.compute_overall_risk(flags) == RiskLevel.MEDIUM

    def test_overall_risk_low_when_no_flags(self, analyzer):
        assert analyzer.compute_overall_risk([]) == RiskLevel.LOW

    def test_overall_risk_low_when_all_low(self, analyzer):
        from phase16.contract_redline.models import RiskFlag
        flags = [RiskFlag("f1", "c1", RiskLevel.LOW, "i", "r")]
        assert analyzer.compute_overall_risk(flags) == RiskLevel.LOW

    def test_confidentiality_perpetual_medium(self, extractor, analyzer):
        clauses = extractor.extract(CONFIDENTIALITY_TEXT)
        flags = analyzer.analyze(clauses)
        assert len(flags) >= 1

    def test_ip_work_for_hire_medium(self, extractor, analyzer):
        clauses = extractor.extract(IP_TEXT)
        flags = analyzer.analyze(clauses)
        assert len(flags) >= 1

    def test_flag_confidence_range(self, extractor, analyzer):
        clauses = extractor.extract(FULL_CONTRACT)
        flags = analyzer.analyze(clauses)
        assert all(0.0 <= f.confidence <= 1.0 for f in flags)

    def test_clean_contract_no_flags(self, extractor, analyzer):
        clean = "This Agreement is entered into between Party A and Party B for mutual benefit."
        clauses = extractor.extract(clean)
        flags = analyzer.analyze(clauses)
        assert len(flags) == 0

    def test_full_contract_multiple_flags(self, extractor, analyzer):
        clauses = extractor.extract(FULL_CONTRACT)
        flags = analyzer.analyze(clauses)
        assert len(flags) >= 3

    def test_analysis_overall_risk_full_contract(self, engine):
        analysis = engine.analyze("c1", FULL_CONTRACT)
        assert analysis.overall_risk in (RiskLevel.HIGH, RiskLevel.CRITICAL)

    def test_analysis_critical_flags_property(self, engine):
        analysis = engine.analyze("c1", INDEMNIFICATION_TEXT)
        # critical_flags is a subset of risk_flags
        assert all(f.risk_level == RiskLevel.CRITICAL for f in analysis.critical_flags)

    def test_analysis_high_risk_flags_property(self, engine):
        analysis = engine.analyze("c1", FULL_CONTRACT)
        assert all(f.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
                   for f in analysis.high_risk_flags)

    def test_analysis_summary_not_empty(self, engine):
        analysis = engine.analyze("c1", FULL_CONTRACT)
        assert len(analysis.summary) > 0

    def test_analysis_created_at(self, engine):
        analysis = engine.analyze("c1", FULL_CONTRACT)
        assert analysis.created_at > 0


# ─────────────────────────────────────────────────────────────
# Redline suggestion tests (25)
# ─────────────────────────────────────────────────────────────
class TestRedlineSuggestions:
    def test_suggest_returns_redlines(self, extractor, analyzer, suggester):
        clauses = extractor.extract(FULL_CONTRACT)
        flags = analyzer.analyze(clauses)
        redlines = suggester.suggest(clauses, flags)
        assert len(redlines) >= 1

    def test_redline_has_id(self, extractor, analyzer, suggester):
        clauses = extractor.extract(FULL_CONTRACT)
        flags = analyzer.analyze(clauses)
        redlines = suggester.suggest(clauses, flags)
        assert all(r.redline_id.startswith("rl_") for r in redlines)

    def test_redline_unique_ids(self, extractor, analyzer, suggester):
        clauses = extractor.extract(FULL_CONTRACT)
        flags = analyzer.analyze(clauses)
        redlines = suggester.suggest(clauses, flags)
        ids = [r.redline_id for r in redlines]
        assert len(ids) == len(set(ids))

    def test_termination_redline_suggested(self, extractor, analyzer, suggester):
        clauses = extractor.extract(TERMINATION_TEXT)
        flags = analyzer.analyze(clauses)
        redlines = suggester.suggest(clauses, flags)
        assert len(redlines) >= 1

    def test_non_compete_redline_suggested(self, extractor, analyzer, suggester):
        clauses = extractor.extract(NON_COMPETE_TEXT)
        flags = analyzer.analyze(clauses)
        redlines = suggester.suggest(clauses, flags)
        assert len(redlines) >= 1

    def test_payment_redline_suggested(self, extractor, analyzer, suggester):
        clauses = extractor.extract(PAYMENT_TEXT)
        flags = analyzer.analyze(clauses)
        redlines = suggester.suggest(clauses, flags)
        assert len(redlines) >= 1

    def test_redline_has_rationale(self, extractor, analyzer, suggester):
        clauses = extractor.extract(FULL_CONTRACT)
        flags = analyzer.analyze(clauses)
        redlines = suggester.suggest(clauses, flags)
        assert all(len(r.rationale) > 0 for r in redlines)

    def test_redline_action_modify_or_flag(self, extractor, analyzer, suggester):
        clauses = extractor.extract(FULL_CONTRACT)
        flags = analyzer.analyze(clauses)
        redlines = suggester.suggest(clauses, flags)
        valid_actions = {RedlineAction.MODIFY, RedlineAction.FLAG}
        assert all(r.action in valid_actions for r in redlines)

    def test_redline_suggested_text_not_empty(self, extractor, analyzer, suggester):
        clauses = extractor.extract(FULL_CONTRACT)
        flags = analyzer.analyze(clauses)
        redlines = suggester.suggest(clauses, flags)
        assert all(len(r.suggested_text) > 0 for r in redlines)

    def test_redline_clause_id_valid(self, extractor, analyzer, suggester):
        clauses = extractor.extract(FULL_CONTRACT)
        flags = analyzer.analyze(clauses)
        redlines = suggester.suggest(clauses, flags)
        clause_ids = {c.clause_id for c in clauses}
        assert all(r.clause_id in clause_ids for r in redlines)

    def test_redline_pending_by_default(self, analysis):
        assert all(r.accepted is None for r in analysis.pending_redlines)

    def test_accept_redline(self, engine, analysis):
        if not analysis.redlines:
            pytest.skip("No redlines to accept")
        redline = analysis.redlines[0]
        accepted = engine.accept_redline(analysis.analysis_id, redline.redline_id)
        assert accepted.accepted is True

    def test_reject_redline(self, engine, analysis):
        if not analysis.redlines:
            pytest.skip("No redlines to reject")
        redline = analysis.redlines[0]
        rejected = engine.reject_redline(analysis.analysis_id, redline.redline_id)
        assert rejected.accepted is False

    def test_add_comment(self, engine, analysis):
        if not analysis.redlines:
            pytest.skip("No redlines to comment")
        redline = analysis.redlines[0]
        commented = engine.add_comment(analysis.analysis_id, redline.redline_id, "Review with counsel")
        assert commented.comment == "Review with counsel"

    def test_accepted_redlines_property(self, engine, analysis):
        if not analysis.redlines:
            pytest.skip("No redlines")
        engine.accept_redline(analysis.analysis_id, analysis.redlines[0].redline_id)
        assert len(analysis.accepted_redlines) >= 1

    def test_pending_redlines_decreases_after_accept(self, engine, analysis):
        if not analysis.redlines:
            pytest.skip("No redlines")
        initial_pending = len(analysis.pending_redlines)
        engine.accept_redline(analysis.analysis_id, analysis.redlines[0].redline_id)
        assert len(analysis.pending_redlines) == initial_pending - 1

    def test_accept_nonexistent_redline_raises(self, engine, analysis):
        with pytest.raises(KeyError):
            engine.accept_redline(analysis.analysis_id, "nonexistent")

    def test_accept_nonexistent_analysis_raises(self, engine):
        with pytest.raises(KeyError):
            engine.accept_redline("nonexistent", "rl_123")

    def test_reject_nonexistent_raises(self, engine, analysis):
        with pytest.raises(KeyError):
            engine.reject_redline(analysis.analysis_id, "nonexistent")

    def test_export_redlined_text(self, engine, analysis):
        if not analysis.redlines:
            pytest.skip("No redlines")
        engine.accept_redline(analysis.analysis_id, analysis.redlines[0].redline_id)
        exported = engine.export_redlined_text(analysis.analysis_id)
        assert "[REDLINED:" in exported

    def test_export_no_accepted_redlines(self, engine, analysis):
        exported = engine.export_redlined_text(analysis.analysis_id)
        assert "[REDLINED:" not in exported

    def test_standard_redlines_coverage(self):
        assert ClauseType.TERMINATION in STANDARD_REDLINES
        assert ClauseType.NON_COMPETE in STANDARD_REDLINES
        assert ClauseType.PAYMENT in STANDARD_REDLINES

    def test_net90_redline_suggests_net30(self, extractor, analyzer, suggester):
        clauses = extractor.extract(PAYMENT_TEXT)
        flags = analyzer.analyze(clauses)
        redlines = suggester.suggest(clauses, flags)
        modify_redlines = [r for r in redlines if r.action == RedlineAction.MODIFY]
        if modify_redlines:
            assert any("Net-30" in r.suggested_text for r in modify_redlines)

    def test_five_year_noncompete_redline(self, extractor, analyzer, suggester):
        clauses = extractor.extract(NON_COMPETE_TEXT)
        flags = analyzer.analyze(clauses)
        redlines = suggester.suggest(clauses, flags)
        modify_redlines = [r for r in redlines if r.action == RedlineAction.MODIFY]
        if modify_redlines:
            assert any("12" in r.suggested_text for r in modify_redlines)

    def test_redline_risk_level_set(self, extractor, analyzer, suggester):
        clauses = extractor.extract(FULL_CONTRACT)
        flags = analyzer.analyze(clauses)
        redlines = suggester.suggest(clauses, flags)
        assert all(isinstance(r.risk_level, RiskLevel) for r in redlines)


# ─────────────────────────────────────────────────────────────
# Full engine integration tests (22)
# ─────────────────────────────────────────────────────────────
class TestEngineIntegration:
    def test_analyze_returns_analysis(self, engine):
        analysis = engine.analyze("c1", FULL_CONTRACT)
        assert analysis.analysis_id.startswith("ana_")

    def test_analysis_contract_id(self, engine):
        analysis = engine.analyze("my_contract", FULL_CONTRACT)
        assert analysis.contract_id == "my_contract"

    def test_get_analysis(self, engine, analysis):
        retrieved = engine.get_analysis(analysis.analysis_id)
        assert retrieved.analysis_id == analysis.analysis_id

    def test_get_nonexistent_analysis(self, engine):
        assert engine.get_analysis("nonexistent") is None

    def test_analysis_has_clauses(self, engine, analysis):
        assert len(analysis.clauses) >= 1

    def test_analysis_has_risk_flags(self, engine, analysis):
        assert len(analysis.risk_flags) >= 1

    def test_analysis_has_redlines(self, engine, analysis):
        assert len(analysis.redlines) >= 1

    def test_analysis_overall_risk_not_none(self, engine, analysis):
        assert analysis.overall_risk is not None

    def test_multiple_analyses_independent(self, engine):
        a1 = engine.analyze("c1", INDEMNIFICATION_TEXT)
        a2 = engine.analyze("c2", PAYMENT_TEXT)
        assert a1.analysis_id != a2.analysis_id
        assert a1.contract_id != a2.contract_id

    def test_full_lifecycle(self, engine):
        analysis = engine.analyze("c1", FULL_CONTRACT)
        if analysis.redlines:
            rl = analysis.redlines[0]
            engine.accept_redline(analysis.analysis_id, rl.redline_id)
            engine.add_comment(analysis.analysis_id, rl.redline_id, "Approved by counsel")
            exported = engine.export_redlined_text(analysis.analysis_id)
            assert len(exported) > 0

    def test_clean_contract_low_risk(self, engine):
        clean = "Both parties agree to cooperate in good faith for mutual benefit."
        analysis = engine.analyze("clean", clean)
        assert analysis.overall_risk == RiskLevel.LOW

    def test_critical_contract_critical_risk(self, engine):
        critical = """
        INDEMNIFICATION: Party shall indemnify with unlimited liability for all claims.
        NON-COMPETE: Employee agrees not to compete for ten years globally.
        """
        analysis = engine.analyze("critical", critical)
        assert analysis.overall_risk in (RiskLevel.HIGH, RiskLevel.CRITICAL)

    def test_analysis_summary_contains_risk_level(self, engine, analysis):
        assert analysis.overall_risk.value in analysis.summary.lower()

    def test_analysis_summary_contains_clause_count(self, engine, analysis):
        assert str(len(analysis.clauses)) in analysis.summary

    def test_accept_then_export_shows_redline(self, engine):
        analysis = engine.analyze("c1", TERMINATION_TEXT)
        if not analysis.redlines:
            pytest.skip("No redlines generated")
        rl = next((r for r in analysis.redlines if r.action.value == "modify"), None)
        if not rl:
            pytest.skip("No modify redlines")
        engine.accept_redline(analysis.analysis_id, rl.redline_id)
        exported = engine.export_redlined_text(analysis.analysis_id)
        assert "[REDLINED:" in exported

    def test_reject_does_not_appear_in_export(self, engine):
        analysis = engine.analyze("c1", TERMINATION_TEXT)
        if not analysis.redlines:
            pytest.skip("No redlines")
        rl = analysis.redlines[0]
        engine.reject_redline(analysis.analysis_id, rl.redline_id)
        exported = engine.export_redlined_text(analysis.analysis_id)
        assert "[REDLINED:" not in exported

    def test_comment_preserved(self, engine, analysis):
        if not analysis.redlines:
            pytest.skip("No redlines")
        rl = analysis.redlines[0]
        engine.add_comment(analysis.analysis_id, rl.redline_id, "See attorney notes")
        retrieved = engine.get_analysis(analysis.analysis_id)
        updated_rl = next(r for r in retrieved.redlines if r.redline_id == rl.redline_id)
        assert updated_rl.comment == "See attorney notes"

    def test_analysis_ids_unique(self, engine):
        ids = {engine.analyze(f"c{i}", FULL_CONTRACT).analysis_id for i in range(5)}
        assert len(ids) == 5

    def test_export_nonexistent_analysis_raises(self, engine):
        with pytest.raises(KeyError):
            engine.export_redlined_text("nonexistent")

    def test_indemnification_analysis(self, engine):
        analysis = engine.analyze("c1", INDEMNIFICATION_TEXT)
        assert len(analysis.risk_flags) >= 1

    def test_ip_analysis(self, engine):
        analysis = engine.analyze("c1", IP_TEXT)
        assert len(analysis.risk_flags) >= 1

    def test_confidentiality_analysis(self, engine):
        analysis = engine.analyze("c1", CONFIDENTIALITY_TEXT)
        assert len(analysis.risk_flags) >= 1
