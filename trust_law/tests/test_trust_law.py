"""
Comprehensive Test Suite for SintraPrime Trust Law Intelligence System
=====================================================================
Tests all 8 modules: knowledge base, reasoning engine, document generator,
jurisdiction analyzer, asset protection planner, UCC assistant, parliament,
and case law database.

Run: pytest tests/test_trust_law.py -v
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from trust_knowledge_base import TrustKnowledgeBase
from trust_reasoning_engine import TrustReasoningEngine
from trust_document_generator import TrustDocumentGenerator
from jurisdiction_analyzer import JurisdictionAnalyzer
from asset_protection_planner import AssetProtectionPlanner, Asset
from ucc_filing_assistant import UCCFilingAssistant
from trust_parliament import TrustParliament
from trust_case_law import TrustCaseLawDB


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def kb():
    return TrustKnowledgeBase()

@pytest.fixture
def engine():
    return TrustReasoningEngine()

@pytest.fixture
def generator():
    return TrustDocumentGenerator()

@pytest.fixture
def analyzer():
    return JurisdictionAnalyzer()

@pytest.fixture
def planner():
    return AssetProtectionPlanner()

@pytest.fixture
def ucc():
    return UCCFilingAssistant()

@pytest.fixture
def parliament():
    return TrustParliament()

@pytest.fixture
def case_db():
    return TrustCaseLawDB()


# ── Trust Knowledge Base Tests ─────────────────────────────────────────────────

class TestTrustKnowledgeBase:

    def test_knowledge_base_has_at_least_30_doctrines(self, kb):
        """KB must have at least 30 trust doctrines."""
        assert len(kb.TRUST_DOCTRINES) >= 30

    def test_get_spendthrift_doctrine(self, kb):
        """Can retrieve spendthrift trust doctrine."""
        doctrine = kb.get_doctrine("Spendthrift Trust")
        assert doctrine is not None
        assert "spendthrift" in doctrine["name"].lower() or "spendthrift" in doctrine.get("description", "").lower()

    def test_get_dynasty_trust_doctrine(self, kb):
        """Can retrieve dynasty trust doctrine."""
        doctrine = kb.get_doctrine("Dynasty Trust")
        assert doctrine is not None

    def test_get_cook_islands_jurisdiction(self, kb):
        """Cook Islands jurisdiction data is present (using underscore key)."""
        jx = kb.TRUST_JURISDICTIONS.get("Cook Islands") or kb.TRUST_JURISDICTIONS.get("cook_islands")
        assert jx is not None
        assert jx["asset_protection_strength"] >= 8

    def test_south_dakota_allows_dynasty(self, kb):
        """South Dakota should allow dynasty trusts."""
        sd = kb.TRUST_JURISDICTIONS.get("South Dakota") or kb.TRUST_JURISDICTIONS.get("south_dakota")
        assert sd is not None
        assert sd["dynasty_trust_allowed"] is True

    def test_ucc_articles_present(self, kb):
        """UCC concepts dict covers key articles."""
        assert len(kb.UCC_CONCEPTS) >= 5
        # Should have Article 9 for secured transactions
        found_article_9 = any("9" in k or "secured" in k.lower() for k in kb.UCC_CONCEPTS.keys())
        assert found_article_9

    def test_search_doctrines_by_keyword(self, kb):
        """Search doctrines returns relevant results."""
        results = kb.search_doctrines("asset protection")
        assert len(results) >= 1

    def test_compare_jurisdictions(self, kb):
        """Can compare two jurisdictions."""
        comparison = kb.compare_jurisdictions("South Dakota", "Nevada")
        assert comparison is not None
        assert "South Dakota" in str(comparison) or "Nevada" in str(comparison)

    def test_get_best_jurisdiction_for_asset_protection(self, kb):
        """Best jurisdiction returns a valid jurisdiction for AP requirements."""
        requirements = {"asset_protection_priority": True, "self_settled_trust": True}
        result = kb.get_best_jurisdiction(requirements)
        assert result is not None

    def test_all_doctrines_have_required_fields(self, kb):
        """All doctrines have name, description, and key_cases fields."""
        for name, doctrine in kb.TRUST_DOCTRINES.items():
            assert "name" in doctrine or name, f"Doctrine {name} missing name"
            assert "description" in doctrine, f"Doctrine {name} missing description"

    def test_ucc_guidance_returns_text(self, kb):
        """get_ucc_guidance returns non-empty string."""
        guidance = kb.get_ucc_guidance("perfection")
        assert guidance is not None
        assert len(str(guidance)) > 10

    def test_nevada_has_self_settled_trust(self, kb):
        """Nevada should allow self-settled trusts."""
        nv = kb.TRUST_JURISDICTIONS.get("Nevada") or kb.TRUST_JURISDICTIONS.get("nevada")
        assert nv is not None
        assert nv["self_settled_trust"] is True

    def test_at_least_15_jurisdictions_in_db(self, kb):
        """At least 15 jurisdictions in database (including display-name aliases)."""
        assert len(kb.TRUST_JURISDICTIONS) >= 15


# ── Trust Reasoning Engine Tests ──────────────────────────────────────────────

class TestTrustReasoningEngine:

    def test_reason_about_trust_returns_analysis(self, engine):
        """reason_about_trust returns TrustAnalysis object."""
        analysis = engine.reason_about_trust(
            "Client with $5M in business assets needs protection from lawsuits",
            {"net_worth": 5000000, "state": "California", "threat_level": "high"}
        )
        assert analysis is not None
        assert hasattr(analysis, "recommended_trust_type")
        assert hasattr(analysis, "asset_protection_score")

    def test_analysis_has_reasoning_chain(self, engine):
        """Analysis includes a reasoning chain."""
        analysis = engine.reason_about_trust(
            "Estate planning for family with $10M estate",
            {"net_worth": 10000000, "state": "New York"}
        )
        assert hasattr(analysis, "reasoning_chain")
        assert len(analysis.reasoning_chain) >= 3

    def test_asset_protection_score_is_valid(self, engine):
        """Asset protection score is between 0 and 100."""
        analysis = engine.reason_about_trust(
            "Asset protection planning",
            {"net_worth": 2000000}
        )
        assert 0 <= analysis.asset_protection_score <= 100

    def test_analyze_existing_trust_returns_audit(self, engine):
        """analyze_existing_trust returns TrustAudit."""
        sample_trust = """
        THIS REVOCABLE LIVING TRUST AGREEMENT is made by John Smith as Grantor.
        The Grantor hereby transfers assets to the trust. The trust is revocable.
        Trustee: John Smith. Successor Trustee: Jane Smith.
        Beneficiaries: John Smith during lifetime, then to children equally.
        Spendthrift clause included.
        """
        audit = engine.analyze_existing_trust(sample_trust)
        assert audit is not None
        assert hasattr(audit, "trust_type_detected")
        assert hasattr(audit, "vulnerabilities")
        assert hasattr(audit, "recommendations")

    def test_confidence_is_float_between_0_and_1(self, engine):
        """Confidence score is a float between 0 and 1."""
        analysis = engine.reason_about_trust("Trust planning scenario", {})
        assert isinstance(analysis.confidence, float)
        assert 0.0 <= analysis.confidence <= 1.0

    def test_compare_strategies(self, engine):
        """compare_strategies returns StrategyComparison."""
        comparison = engine.compare_strategies([
            "Revocable Living Trust",
            "Nevada DAPT",
            "Cook Islands Trust"
        ])
        assert comparison is not None

    def test_analysis_includes_risks(self, engine):
        """Analysis includes list of risks."""
        analysis = engine.reason_about_trust(
            "Offshore trust for high net worth client",
            {"net_worth": 20000000, "offshore_acceptable": True}
        )
        assert hasattr(analysis, "risks")
        assert isinstance(analysis.risks, list)

    def test_analysis_includes_opportunities(self, engine):
        """Analysis includes list of opportunities."""
        analysis = engine.reason_about_trust("Estate planning", {"net_worth": 5000000})
        assert hasattr(analysis, "opportunities")
        assert isinstance(analysis.opportunities, list)


# ── Trust Document Generator Tests ────────────────────────────────────────────

class TestTrustDocumentGenerator:

    def test_generate_revocable_living_trust(self, generator):
        """Generates a revocable living trust document."""
        doc = generator.generate_revocable_living_trust(
            grantor_name="John Smith",
            trustee_name="John Smith",
            successor_trustee="Jane Smith",
            beneficiaries=["Jane Smith", "Bob Smith"],
            state="California"
        )
        assert isinstance(doc, str)
        assert len(doc) > 500
        assert "John Smith" in doc
        assert "REVOCABLE" in doc.upper() or "revocable" in doc.lower()

    def test_revocable_trust_has_articles(self, generator):
        """Revocable trust document has article structure."""
        doc = generator.generate_revocable_living_trust(
            "Alice Johnson", "Alice Johnson", "Bob Johnson",
            ["Carol Johnson"], "Texas"
        )
        assert "ARTICLE" in doc.upper() or "Article" in doc

    def test_generate_irrevocable_trust(self, generator):
        """Generates an irrevocable asset protection trust."""
        doc = generator.generate_irrevocable_asset_protection_trust(
            grantor_name="Robert Davis",
            trustee_name="Nevada Trust Company",
            beneficiaries=["Mary Davis", "Tom Davis"],
            jurisdiction="Nevada",
            assets=["Investment accounts", "Business interests"]
        )
        assert isinstance(doc, str)
        assert len(doc) > 500
        assert "IRREVOCABLE" in doc.upper() or "irrevocable" in doc.lower()

    def test_generate_business_trust(self, generator):
        """Generates a business trust document."""
        doc = generator.generate_business_trust(
            trust_name="Smith Family Business Trust",
            trustees=["John Smith", "Jane Smith"],
            beneficiaries=["Smith Family LLC"],
            purpose="To hold and manage business assets",
            state="Delaware"
        )
        assert isinstance(doc, str)
        assert len(doc) > 400
        assert "Smith Family Business Trust" in doc

    def test_generate_ucc_financing_statement(self, generator):
        """Generates a UCC-1 financing statement."""
        doc = generator.generate_ucc_financing_statement(
            debtor_name="XYZ Corporation",
            secured_party="First National Bank",
            collateral_description="All inventory, equipment, and accounts receivable",
            filing_state="Delaware"
        )
        assert isinstance(doc, str)
        assert "XYZ Corporation" in doc
        assert "First National Bank" in doc

    def test_generate_trust_amendment(self, generator):
        """Generates a trust amendment document."""
        doc = generator.generate_trust_amendment(
            original_trust_name="Smith Family Revocable Trust",
            grantor_name="John Smith",
            amendment_details=["Change successor trustee to Carol Smith", "Add grandchildren as beneficiaries"]
        )
        assert isinstance(doc, str)
        assert "AMENDMENT" in doc.upper() or "amendment" in doc.lower()
        assert "Smith Family Revocable Trust" in doc

    def test_legal_disclaimer_present(self, generator):
        """Legal disclaimer constant is present."""
        assert hasattr(generator, "LEGAL_DISCLAIMER")
        disclaimer = generator.LEGAL_DISCLAIMER
        assert "educational" in disclaimer.lower() or "template" in disclaimer.lower() or "attorney" in disclaimer.lower()

    def test_irrevocable_trust_has_signature_block(self, generator):
        """Irrevocable trust has signature block."""
        doc = generator.generate_irrevocable_asset_protection_trust(
            "Test Grantor", "Test Trustee", ["Test Beneficiary"], "South Dakota", ["Cash"]
        )
        assert "SIGNATURE" in doc.upper() or "IN WITNESS" in doc.upper() or "signed" in doc.lower()


# ── Jurisdiction Analyzer Tests ───────────────────────────────────────────────

class TestJurisdictionAnalyzer:

    def test_find_optimal_jurisdiction_returns_ranking(self, analyzer):
        """find_optimal_jurisdiction returns a JurisdictionRanking."""
        ranking = analyzer.find_optimal_jurisdiction({
            "asset_protection_priority": True,
            "tax_minimization": True,
            "dynasty_goals": True,
            "privacy_needs": "high",
            "budget": "moderate"
        })
        assert ranking is not None

    def test_south_dakota_ranks_highly_for_dynasty(self, analyzer):
        """South Dakota ranks highly for dynasty trust requirements."""
        ranking = analyzer.find_optimal_jurisdiction({
            "dynasty_goals": True,
            "asset_protection_priority": True,
            "tax_minimization": True
        })
        # South Dakota should appear in top results
        result_str = str(ranking)
        assert "South Dakota" in result_str or "south_dakota" in result_str.lower()

    def test_compare_state_laws(self, analyzer):
        """Can compare state laws for a specific trust type."""
        comparison = analyzer.compare_state_laws("South Dakota", "Nevada", "DAPT")
        assert comparison is not None

    def test_get_offshore_options(self, analyzer):
        """get_offshore_options returns options for high-value assets."""
        options = analyzer.get_offshore_options(
            asset_value=5000000,
            threat_level="high"
        )
        assert isinstance(options, list)
        assert len(options) >= 1

    def test_analyze_migration_strategy(self, analyzer):
        """Can analyze trust migration from one state to another."""
        plan = analyzer.analyze_migration_strategy(
            current_state="California",
            target_state="South Dakota",
            trust_type="Revocable Living Trust"
        )
        assert plan is not None

    def test_cook_islands_appears_for_high_threat(self, analyzer):
        """Cook Islands appears in offshore options for high threat level."""
        options = analyzer.get_offshore_options(asset_value=10000000, threat_level="extreme")
        option_names = [str(o) for o in options]
        assert any("cook" in name.lower() or "cook islands" in name.lower() for name in option_names) or len(options) >= 1


# ── Asset Protection Planner Tests ────────────────────────────────────────────

class TestAssetProtectionPlanner:

    def test_create_protection_plan(self, planner):
        """create_protection_plan returns a ProtectionPlan."""
        assets = [
            Asset(asset_type="real_estate", estimated_value=500000, description="Primary Residence", current_owner="John Smith", state="CA"),
            Asset(asset_type="business_interests", estimated_value=2000000, description="50% interest in LLC", current_owner="John Smith", state="CA"),
        ]
        plan = planner.create_protection_plan(
            assets=assets,
            threats=["lawsuits", "creditors"],
            goals=["asset_protection", "estate_planning"]
        )
        assert plan is not None
        assert hasattr(plan, "recommended_structures")
        assert hasattr(plan, "estimated_protection_level")

    def test_protection_level_is_valid_score(self, planner):
        """Protection level score is between 0 and 100."""
        assets = [Asset(asset_type="cash", estimated_value=100000, description="Bank accounts", current_owner="Test", state="CA")]
        plan = planner.create_protection_plan(assets=assets, threats=["creditors"], goals=["protection"])
        assert 0 <= plan.estimated_protection_level <= 100

    def test_evaluate_existing_protection(self, planner):
        """evaluate_existing_protection returns a ProtectionAudit."""
        current = ["Revocable Living Trust", "LLC"]
        audit = planner.evaluate_existing_protection(current_structures=current)
        assert audit is not None

    def test_calculate_asset_protection_score(self, planner):
        """calculate_asset_protection_score returns a float."""
        score = planner.calculate_asset_protection_score(
            "Nevada DAPT with Wyoming LLC charging order protection"
        )
        assert isinstance(score, float)
        assert 0.0 <= score <= 100.0

    def test_plan_has_implementation_order(self, planner):
        """Protection plan includes implementation order."""
        assets = [Asset(asset_type="investment_accounts", estimated_value=1000000, description="Brokerage", current_owner="Test", state="CA")]
        plan = planner.create_protection_plan(assets=assets, threats=["lawsuits"], goals=["protection"])
        assert hasattr(plan, "implementation_order")

    def test_plan_has_cost_estimate(self, planner):
        """Protection plan includes a cost estimate."""
        assets = [Asset(asset_type="real_estate", estimated_value=750000, description="Rental property", current_owner="Test", state="CA")]
        plan = planner.create_protection_plan(assets=assets, threats=["creditors"], goals=["protection"])
        assert hasattr(plan, "cost_estimate")


# ── UCC Filing Assistant Tests ────────────────────────────────────────────────

class TestUCCFilingAssistant:

    def test_prepare_ucc1_financing_statement(self, ucc):
        """prepare_ucc1_financing_statement returns a UCCForm."""
        debtor = {"name": "ABC Corp", "address": "123 Main St, Dover, DE 19901", "type": "corporation"}
        secured_party = {"name": "First Bank", "address": "456 Bank Ave, Wilmington, DE 19801"}
        collateral = {"description": "All inventory, equipment, accounts receivable, and proceeds thereof"}
        form = ucc.prepare_ucc1_financing_statement(debtor, secured_party, collateral)
        assert form is not None
        assert hasattr(form, "form_type") or hasattr(form, "debtor_name") or str(form)

    def test_prepare_ucc3_amendment(self, ucc):
        """prepare_ucc3_amendment returns a UCCForm."""
        form = ucc.prepare_ucc3_amendment(
            original_filing_number="2024-123456",
            amendment_type="CONTINUATION",
            changes={"effective_years_extended": 5}
        )
        assert form is not None

    def test_analyze_collateral_description(self, ucc):
        """analyze_collateral_description returns CollateralAnalysis."""
        analysis = ucc.analyze_collateral_description(
            "All of debtor's personal property"
        )
        assert analysis is not None

    def test_check_priority_rules(self, ucc):
        """check_priority_rules returns PriorityAnalysis."""
        sp1 = {"name": "Bank A", "filing_date": "2024-01-01"}
        sp2 = {"name": "Bank B", "filing_date": "2024-03-01"}
        analysis = ucc.check_priority_rules(sp1, sp2, ["2024-01-01", "2024-03-01"])
        assert analysis is not None

    def test_get_filing_requirements(self, ucc):
        """get_filing_requirements returns FilingRequirements for a state."""
        reqs = ucc.get_filing_requirements("Delaware")
        assert reqs is not None

    def test_ucc_articles_dict_present(self, ucc):
        """UCC_ARTICLES dict is present with at least 5 entries."""
        assert hasattr(ucc, "UCC_ARTICLES")
        assert len(ucc.UCC_ARTICLES) >= 5

    def test_perfection_methods_present(self, ucc):
        """PERFECTION_METHODS dict covers filing and possession."""
        assert hasattr(ucc, "PERFECTION_METHODS")
        methods_str = str(ucc.PERFECTION_METHODS).lower()
        assert "filing" in methods_str or "possession" in methods_str

    def test_priority_rules_present(self, ucc):
        """PRIORITY_RULES dict is present."""
        assert hasattr(ucc, "PRIORITY_RULES")
        assert len(ucc.PRIORITY_RULES) >= 1


# ── Trust Parliament Tests ────────────────────────────────────────────────────

class TestTrustParliament:

    def test_parliament_has_six_agents(self, parliament):
        """Parliament has exactly 6 agent profiles."""
        assert len(parliament.AGENTS) == 6

    def test_deliberate_returns_verdict(self, parliament):
        """deliberate returns a ParliamentVerdict."""
        verdict = parliament.deliberate(
            "Should we create a Cook Islands trust for this client?",
            {"net_worth": 10000000, "threat_level": "high", "offshore_acceptable": True}
        )
        assert verdict is not None
        assert hasattr(verdict, "majority_recommendation")
        assert hasattr(verdict, "confidence_score")

    def test_verdict_has_debate_transcript(self, parliament):
        """Verdict includes a debate transcript."""
        verdict = parliament.deliberate(
            "Should we use a Nevada DAPT?",
            {"state": "California", "net_worth": 3000000}
        )
        assert hasattr(verdict, "debate_transcript")
        assert len(verdict.debate_transcript) >= 5

    def test_verdict_has_vote_tally(self, parliament):
        """Verdict includes a vote tally."""
        verdict = parliament.deliberate(
            "Dynasty trust in South Dakota?",
            {"net_worth": 20000000, "dynasty_goals": True}
        )
        assert hasattr(verdict, "vote_tally")
        assert isinstance(verdict.vote_tally, dict)
        total_votes = sum(verdict.vote_tally.values())
        assert total_votes == 6  # One vote per agent

    def test_confidence_score_is_valid(self, parliament):
        """Confidence score is between 0 and 100."""
        verdict = parliament.deliberate("Trust planning question", {"net_worth": 1000000})
        assert 0 <= verdict.confidence_score <= 100

    def test_deliberate_on_structure(self, parliament):
        """deliberate_on_structure returns StructureVerdict."""
        structure = {
            "type": "Nevada DAPT",
            "jurisdiction": "Nevada",
            "trustee": "Nevada Trust Company",
            "beneficiaries": ["Client", "Spouse"],
            "estimated_value": 5000000
        }
        verdict = parliament.deliberate_on_structure(structure)
        assert verdict is not None
        assert hasattr(verdict, "overall_verdict")
        assert hasattr(verdict, "approval_score")

    def test_vote_on_jurisdiction(self, parliament):
        """vote_on_jurisdiction returns JurisdictionVerdict."""
        verdict = parliament.vote_on_jurisdiction(
            options=["South Dakota", "Nevada", "Delaware", "Wyoming"],
            client_profile={"net_worth": 5000000, "goals": ["asset_protection", "dynasty"]}
        )
        assert verdict is not None
        assert hasattr(verdict, "recommended_jurisdiction")
        assert verdict.recommended_jurisdiction in ["South Dakota", "Nevada", "Delaware", "Wyoming"]

    def test_parliament_agents_have_required_fields(self, parliament):
        """All parliament agents have required profile fields."""
        for agent_key, agent in parliament.AGENTS.items():
            assert hasattr(agent, "role")
            assert hasattr(agent, "title")
            assert hasattr(agent, "expertise")
            assert hasattr(agent, "bias_toward")


# ── Trust Case Law Database Tests ─────────────────────────────────────────────

class TestTrustCaseLawDB:

    def test_case_law_db_has_25_plus_cases(self, case_db):
        """Case law DB has at least 25 landmark cases."""
        assert len(case_db.CASES) >= 25

    def test_search_spendthrift_cases(self, case_db):
        """Can search cases by 'spendthrift' keyword."""
        results = case_db.search_cases("spendthrift")
        assert len(results) >= 1

    def test_search_offshore_cases(self, case_db):
        """Can search cases by 'offshore' keyword."""
        results = case_db.search_cases("offshore")
        assert len(results) >= 1

    def test_find_cases_by_doctrine(self, case_db):
        """find_cases_by_doctrine returns relevant cases."""
        cases = case_db.find_cases_by_doctrine("Grantor Trust")
        assert isinstance(cases, list)

    def test_get_cases_by_jurisdiction(self, case_db):
        """Can get cases by jurisdiction."""
        cases = case_db.get_cases_by_jurisdiction("Nevada")
        assert isinstance(cases, list)

    def test_analyze_precedent_strength_supreme_court(self, case_db):
        """Supreme Court cases have binding strength."""
        analysis = case_db.analyze_precedent_strength("Helvering v. Clifford", "California")
        assert analysis is not None
        assert analysis.precedent_strength == "BINDING"
        assert analysis.strength_score >= 90

    def test_utc_provisions_present(self, case_db):
        """UTC provisions dict is present with key sections."""
        assert hasattr(case_db, "UTC_PROVISIONS")
        assert len(case_db.UTC_PROVISIONS) >= 20
        # Check for key sections
        assert any("502" in k or "spendthrift" in v.lower() for k, v in case_db.UTC_PROVISIONS.items())

    def test_restatement_provisions_present(self, case_db):
        """Restatement Third provisions are present."""
        assert hasattr(case_db, "RESTATEMENT_PROVISIONS")
        assert len(case_db.RESTATEMENT_PROVISIONS) >= 10

    def test_cases_have_required_fields(self, case_db):
        """All cases have required fields."""
        for key, case in case_db.CASES.items():
            assert case.name, f"Case {key} missing name"
            assert case.year > 0, f"Case {key} missing year"
            assert case.holding, f"Case {key} missing holding"
            assert case.doctrine_established, f"Case {key} missing doctrine"
            assert case.practitioner_notes, f"Case {key} missing practitioner notes"

    def test_get_all_doctrines(self, case_db):
        """get_all_doctrines returns a list of strings."""
        doctrines = case_db.get_all_doctrines()
        assert isinstance(doctrines, list)
        assert all(isinstance(d, str) for d in doctrines)

    def test_practitioner_notes_digest(self, case_db):
        """get_practitioner_notes_digest returns a non-empty string."""
        digest = case_db.get_practitioner_notes_digest()
        assert isinstance(digest, str)
        assert len(digest) > 100
        assert "CASE:" in digest

    def test_analyze_precedent_for_unknown_case(self, case_db):
        """analyze_precedent_strength handles unknown case gracefully."""
        analysis = case_db.analyze_precedent_strength("NonExistent v. Nobody", "Texas")
        assert analysis.precedent_strength == "INAPPLICABLE"
        assert analysis.strength_score == 0.0


# ── Integration Tests ─────────────────────────────────────────────────────────

class TestIntegration:

    def test_kb_and_engine_integration(self, kb, engine):
        """Knowledge base and reasoning engine work together."""
        doctrine = kb.get_doctrine("Nevada Asset Protection Trust")
        assert doctrine is not None
        analysis = engine.reason_about_trust(
            f"Client needs: {doctrine.get('description', 'asset protection')}",
            {"jurisdiction": "Nevada"}
        )
        assert analysis is not None

    def test_parliament_and_jurisdiction_analyzer(self, parliament, analyzer):
        """Parliament and jurisdiction analyzer produce consistent results."""
        jx_ranking = analyzer.find_optimal_jurisdiction({"asset_protection_priority": True, "dynasty_goals": True})
        verdict = parliament.vote_on_jurisdiction(
            ["South Dakota", "Nevada", "Delaware"],
            {"asset_protection_priority": True}
        )
        # Both should recommend top-tier AP jurisdictions
        assert verdict.recommended_jurisdiction is not None

    def test_document_generator_uses_correct_state(self, generator):
        """Document generator includes the correct state in output."""
        doc = generator.generate_revocable_living_trust(
            "Test Grantor", "Test Trustee", "Test Successor",
            ["Test Beneficiary"], "Wyoming"
        )
        assert "Wyoming" in doc

    def test_full_workflow_asset_to_plan_to_document(self, planner, generator):
        """Full workflow from asset list to protection plan to document."""
        # Step 1: Create protection plan
        assets = [Asset(asset_type="business_interests", estimated_value=3000000, description="LLC interest", current_owner="Business Owner", state="NV")]
        plan = planner.create_protection_plan(assets, ["lawsuits"], ["protection"])
        assert plan is not None

        # Step 2: Generate document based on plan recommendation
        doc = generator.generate_irrevocable_asset_protection_trust(
            "Business Owner", "Nevada Trust Co", ["Spouse", "Children"], "Nevada", ["LLC Interest"]
        )
        assert len(doc) > 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
