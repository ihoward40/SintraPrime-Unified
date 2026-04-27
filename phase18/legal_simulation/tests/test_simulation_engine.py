"""
Phase 18D — Multi-Agent Legal Case Simulation Tests
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from phase18.legal_simulation.simulation_engine import (
    AgentRole,
    CaseSimulation,
    CaseStatus,
    CaseType,
    LegalCase,
    LegalSimulationEngine,
    LegalSimulationReward,
    MotionType,
    NovaExecutionAgent,
    SigmaStrategyAgent,
    Verdict,
    ZeroResearchAgent,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def engine():
    return LegalSimulationEngine()


@pytest.fixture
def contract_case(engine):
    return engine.create_case(
        title="Acme v. Beta Corp",
        case_type=CaseType.CONTRACT_DISPUTE,
        description="Defendant failed to deliver software per contract terms",
        client_name="Acme Inc.",
        opposing_party="Beta Corp",
    )


@pytest.fixture
def employment_case(engine):
    return engine.create_case(
        title="Smith v. MegaCorp",
        case_type=CaseType.EMPLOYMENT,
        description="Wrongful termination based on protected class status",
        client_name="Jane Smith",
        opposing_party="MegaCorp LLC",
    )


@pytest.fixture
def ip_case(engine):
    return engine.create_case(
        title="TechCo v. CopyCat Inc.",
        case_type=CaseType.INTELLECTUAL_PROPERTY,
        description="Patent infringement on core algorithm",
        client_name="TechCo",
        opposing_party="CopyCat Inc.",
    )


@pytest.fixture
def zero_agent():
    return ZeroResearchAgent()


@pytest.fixture
def sigma_agent():
    return SigmaStrategyAgent()


@pytest.fixture
def nova_agent():
    return NovaExecutionAgent()


# ---------------------------------------------------------------------------
# LegalCase tests
# ---------------------------------------------------------------------------

class TestLegalCase:
    def test_case_creation(self, engine, contract_case):
        assert contract_case.id is not None
        assert contract_case.case_type == CaseType.CONTRACT_DISPUTE
        assert contract_case.status == CaseStatus.INTAKE
        assert contract_case.verdict == Verdict.PENDING

    def test_case_has_unique_id(self, engine):
        c1 = engine.create_case("A", CaseType.EMPLOYMENT, "desc", "client", "opp")
        c2 = engine.create_case("B", CaseType.EMPLOYMENT, "desc", "client", "opp")
        assert c1.id != c2.id

    def test_case_default_jurisdiction(self, engine, contract_case):
        assert contract_case.jurisdiction == "federal"

    def test_case_custom_jurisdiction(self, engine):
        c = engine.create_case("X", CaseType.REAL_ESTATE, "desc", "client", "opp", jurisdiction="california")
        assert c.jurisdiction == "california"


# ---------------------------------------------------------------------------
# ZeroResearchAgent tests
# ---------------------------------------------------------------------------

class TestZeroResearchAgent:
    def test_research_returns_evidence(self, zero_agent, contract_case):
        evidence, meta = zero_agent.research_case(contract_case)
        assert len(evidence) > 0

    def test_evidence_has_correct_case_id(self, zero_agent, contract_case):
        evidence, _ = zero_agent.research_case(contract_case)
        for e in evidence:
            assert e.case_id == contract_case.id

    def test_evidence_collected_by_zero(self, zero_agent, contract_case):
        evidence, _ = zero_agent.research_case(contract_case)
        for e in evidence:
            assert e.collected_by == AgentRole.ZERO

    def test_evidence_strength_in_range(self, zero_agent, contract_case):
        evidence, _ = zero_agent.research_case(contract_case)
        for e in evidence:
            assert 0.0 <= e.strength <= 1.0

    def test_research_metadata_has_precedents(self, zero_agent, contract_case):
        _, meta = zero_agent.research_case(contract_case)
        assert "precedents" in meta
        assert len(meta["precedents"]) > 0

    def test_research_metadata_has_statutes(self, zero_agent, contract_case):
        _, meta = zero_agent.research_case(contract_case)
        assert "statutes" in meta

    def test_research_metadata_avg_strength(self, zero_agent, contract_case):
        evidence, meta = zero_agent.research_case(contract_case)
        expected = sum(e.strength for e in evidence) / len(evidence)
        assert meta["avg_strength"] == pytest.approx(expected, abs=0.001)

    def test_employment_case_has_hr_evidence(self, zero_agent, employment_case):
        evidence, _ = zero_agent.research_case(employment_case)
        descriptions = [e.description for e in evidence]
        assert any("HR" in d or "Employment" in d for d in descriptions)

    def test_ip_case_has_patent_evidence(self, zero_agent, ip_case):
        evidence, _ = zero_agent.research_case(ip_case)
        descriptions = [e.description for e in evidence]
        assert any("Patent" in d or "patent" in d or "trademark" in d.lower() for d in descriptions)

    def test_total_evidence_counter_increments(self, zero_agent, contract_case, employment_case):
        _, _ = zero_agent.research_case(contract_case)
        count1 = zero_agent.total_evidence_collected
        _, _ = zero_agent.research_case(employment_case)
        assert zero_agent.total_evidence_collected > count1

    def test_llm_fn_called_if_provided(self, contract_case):
        calls = []
        def mock_llm(prompt):
            calls.append(prompt)
            return "LLM summary"
        agent = ZeroResearchAgent(llm_fn=mock_llm)
        _, meta = agent.research_case(contract_case)
        assert len(calls) == 1
        assert "llm_summary" in meta


# ---------------------------------------------------------------------------
# SigmaStrategyAgent tests
# ---------------------------------------------------------------------------

class TestSigmaStrategyAgent:
    def test_develop_strategy_returns_arguments(self, zero_agent, sigma_agent, contract_case):
        evidence, meta = zero_agent.research_case(contract_case)
        arguments, _ = sigma_agent.develop_strategy(contract_case, evidence, meta)
        assert len(arguments) >= 2

    def test_arguments_have_correct_case_id(self, zero_agent, sigma_agent, contract_case):
        evidence, meta = zero_agent.research_case(contract_case)
        arguments, _ = sigma_agent.develop_strategy(contract_case, evidence, meta)
        for a in arguments:
            assert a.case_id == contract_case.id

    def test_arguments_developed_by_sigma(self, zero_agent, sigma_agent, contract_case):
        evidence, meta = zero_agent.research_case(contract_case)
        arguments, _ = sigma_agent.develop_strategy(contract_case, evidence, meta)
        for a in arguments:
            assert a.developed_by == AgentRole.SIGMA

    def test_argument_strength_in_range(self, zero_agent, sigma_agent, contract_case):
        evidence, meta = zero_agent.research_case(contract_case)
        arguments, _ = sigma_agent.develop_strategy(contract_case, evidence, meta)
        for a in arguments:
            assert 0.0 <= a.strength <= 1.0

    def test_strategy_metadata_has_approach(self, zero_agent, sigma_agent, contract_case):
        evidence, meta = zero_agent.research_case(contract_case)
        _, strategy_meta = sigma_agent.develop_strategy(contract_case, evidence, meta)
        assert "approach" in strategy_meta

    def test_strategy_metadata_has_risk_level(self, zero_agent, sigma_agent, contract_case):
        evidence, meta = zero_agent.research_case(contract_case)
        _, strategy_meta = sigma_agent.develop_strategy(contract_case, evidence, meta)
        assert strategy_meta["risk_level"] in ("low", "medium", "high")

    def test_strategy_metadata_has_duration(self, zero_agent, sigma_agent, contract_case):
        evidence, meta = zero_agent.research_case(contract_case)
        _, strategy_meta = sigma_agent.develop_strategy(contract_case, evidence, meta)
        assert strategy_meta["estimated_duration_days"] > 0

    def test_strategy_recommends_motions(self, zero_agent, sigma_agent, contract_case):
        evidence, meta = zero_agent.research_case(contract_case)
        _, strategy_meta = sigma_agent.develop_strategy(contract_case, evidence, meta)
        assert len(strategy_meta["recommended_motions"]) > 0

    def test_primary_argument_contains_case_type_info(self, zero_agent, sigma_agent, contract_case):
        evidence, meta = zero_agent.research_case(contract_case)
        arguments, _ = sigma_agent.develop_strategy(contract_case, evidence, meta)
        assert "breach" in arguments[0].argument.lower() or "contract" in arguments[0].argument.lower()

    def test_precedent_argument_included(self, zero_agent, sigma_agent, contract_case):
        evidence, meta = zero_agent.research_case(contract_case)
        arguments, _ = sigma_agent.develop_strategy(contract_case, evidence, meta)
        precedent_args = [a for a in arguments if "Precedent" in a.argument]
        assert len(precedent_args) >= 1

    def test_total_arguments_counter(self, zero_agent, sigma_agent, contract_case, employment_case):
        ev1, m1 = zero_agent.research_case(contract_case)
        sigma_agent.develop_strategy(contract_case, ev1, m1)
        count1 = sigma_agent.total_arguments_developed
        ev2, m2 = zero_agent.research_case(employment_case)
        sigma_agent.develop_strategy(employment_case, ev2, m2)
        assert sigma_agent.total_arguments_developed > count1

    def test_llm_fn_called_if_provided(self, zero_agent, contract_case):
        calls = []
        def mock_llm(prompt):
            calls.append(prompt)
            return "LLM strategy"
        agent = SigmaStrategyAgent(llm_fn=mock_llm)
        evidence, meta = zero_agent.research_case(contract_case)
        _, strategy_meta = agent.develop_strategy(contract_case, evidence, meta)
        assert len(calls) == 1
        assert "llm_strategy" in strategy_meta


# ---------------------------------------------------------------------------
# NovaExecutionAgent tests
# ---------------------------------------------------------------------------

class TestNovaExecutionAgent:
    def test_execute_strategy_returns_motions(self, zero_agent, sigma_agent, nova_agent, contract_case):
        evidence, meta = zero_agent.research_case(contract_case)
        arguments, strategy_meta = sigma_agent.develop_strategy(contract_case, evidence, meta)
        motions, _ = nova_agent.execute_strategy(contract_case, arguments, strategy_meta)
        assert len(motions) > 0

    def test_motions_have_correct_case_id(self, zero_agent, sigma_agent, nova_agent, contract_case):
        evidence, meta = zero_agent.research_case(contract_case)
        arguments, strategy_meta = sigma_agent.develop_strategy(contract_case, evidence, meta)
        motions, _ = nova_agent.execute_strategy(contract_case, arguments, strategy_meta)
        for m in motions:
            assert m.case_id == contract_case.id

    def test_motions_filed_by_nova(self, zero_agent, sigma_agent, nova_agent, contract_case):
        evidence, meta = zero_agent.research_case(contract_case)
        arguments, strategy_meta = sigma_agent.develop_strategy(contract_case, evidence, meta)
        motions, _ = nova_agent.execute_strategy(contract_case, arguments, strategy_meta)
        for m in motions:
            assert m.filed_by == AgentRole.NOVA

    def test_motion_body_not_empty(self, zero_agent, sigma_agent, nova_agent, contract_case):
        evidence, meta = zero_agent.research_case(contract_case)
        arguments, strategy_meta = sigma_agent.develop_strategy(contract_case, evidence, meta)
        motions, _ = nova_agent.execute_strategy(contract_case, arguments, strategy_meta)
        for m in motions:
            assert len(m.body) > 50

    def test_execution_metadata_has_motions_count(self, zero_agent, sigma_agent, nova_agent, contract_case):
        evidence, meta = zero_agent.research_case(contract_case)
        arguments, strategy_meta = sigma_agent.develop_strategy(contract_case, evidence, meta)
        _, exec_meta = nova_agent.execute_strategy(contract_case, arguments, strategy_meta)
        assert "motions_filed" in exec_meta

    def test_execution_metadata_has_outcome(self, zero_agent, sigma_agent, nova_agent, contract_case):
        evidence, meta = zero_agent.research_case(contract_case)
        arguments, strategy_meta = sigma_agent.develop_strategy(contract_case, evidence, meta)
        _, exec_meta = nova_agent.execute_strategy(contract_case, arguments, strategy_meta)
        assert exec_meta["estimated_outcome"] in ("favorable", "likely_settlement", "uncertain")

    def test_close_case_returns_verdict(self, zero_agent, sigma_agent, nova_agent, contract_case):
        sim = CaseSimulation(id="sim1", case=contract_case)
        verdict = nova_agent.close_case(contract_case, sim)
        assert isinstance(verdict, Verdict)

    def test_total_motions_counter(self, zero_agent, sigma_agent, nova_agent, contract_case, employment_case):
        ev1, m1 = zero_agent.research_case(contract_case)
        args1, sm1 = sigma_agent.develop_strategy(contract_case, ev1, m1)
        nova_agent.execute_strategy(contract_case, args1, sm1)
        count1 = nova_agent.total_motions_filed
        ev2, m2 = zero_agent.research_case(employment_case)
        args2, sm2 = sigma_agent.develop_strategy(employment_case, ev2, m2)
        nova_agent.execute_strategy(employment_case, args2, sm2)
        assert nova_agent.total_motions_filed > count1

    def test_llm_fn_called_if_provided(self, zero_agent, sigma_agent, contract_case):
        calls = []
        def mock_llm(prompt):
            calls.append(prompt)
            return "MOTION TO DISMISS\n\nARGUMENT: test\n\nWHEREFORE, dismissed."
        agent = NovaExecutionAgent(llm_fn=mock_llm)
        evidence, meta = zero_agent.research_case(contract_case)
        arguments, strategy_meta = sigma_agent.develop_strategy(contract_case, evidence, meta)
        motions, _ = agent.execute_strategy(contract_case, arguments, strategy_meta)
        assert len(calls) == len(motions)


# ---------------------------------------------------------------------------
# LegalSimulationReward tests
# ---------------------------------------------------------------------------

class TestLegalSimulationReward:
    def test_reward_all_agents_complete(self, engine, contract_case):
        sim = engine.run_simulation(contract_case)
        reward_fn = LegalSimulationReward(lambda1=0.3, lambda2=0.1)
        reward = reward_fn.compute(sim)
        assert reward["r_parallel"] == pytest.approx(1.0, abs=0.01)
        assert reward["r_finish"] == 1.0

    def test_reward_total_in_range(self, engine, contract_case):
        sim = engine.run_simulation(contract_case)
        reward_fn = LegalSimulationReward()
        reward = reward_fn.compute(sim)
        assert 0.0 <= reward["total"] <= 2.0

    def test_reward_keys_present(self, engine, contract_case):
        sim = engine.run_simulation(contract_case)
        reward_fn = LegalSimulationReward()
        reward = reward_fn.compute(sim)
        assert all(k in reward for k in ("total", "r_parallel", "r_finish", "r_perf", "lambda1", "lambda2"))

    def test_incomplete_sim_zero_r_finish(self, contract_case):
        sim = CaseSimulation(id="s1", case=contract_case)
        reward_fn = LegalSimulationReward()
        reward = reward_fn.compute(sim)
        assert reward["r_finish"] == 0.0


# ---------------------------------------------------------------------------
# LegalSimulationEngine tests
# ---------------------------------------------------------------------------

class TestLegalSimulationEngine:
    def test_run_simulation_completes(self, engine, contract_case):
        sim = engine.run_simulation(contract_case)
        assert sim.is_complete

    def test_run_simulation_has_three_steps(self, engine, contract_case):
        sim = engine.run_simulation(contract_case)
        assert sim.total_steps == 3

    def test_run_simulation_all_agents_used(self, engine, contract_case):
        sim = engine.run_simulation(contract_case)
        agents = {s.agent for s in sim.steps}
        assert AgentRole.ZERO in agents
        assert AgentRole.SIGMA in agents
        assert AgentRole.NOVA in agents

    def test_run_simulation_evidence_collected(self, engine, contract_case):
        sim = engine.run_simulation(contract_case)
        assert len(sim.evidence_collected) > 0

    def test_run_simulation_arguments_developed(self, engine, contract_case):
        sim = engine.run_simulation(contract_case)
        assert len(sim.arguments_developed) > 0

    def test_run_simulation_motions_filed(self, engine, contract_case):
        sim = engine.run_simulation(contract_case)
        assert len(sim.motions_filed) > 0

    def test_run_simulation_verdict_set(self, engine, contract_case):
        sim = engine.run_simulation(contract_case)
        assert contract_case.verdict != Verdict.PENDING

    def test_run_simulation_case_status_closed(self, engine, contract_case):
        engine.run_simulation(contract_case)
        assert contract_case.status == CaseStatus.CLOSED

    def test_run_simulation_parl_reward_positive(self, engine, contract_case):
        sim = engine.run_simulation(contract_case)
        assert sim.total_parl_reward > 0.0

    def test_run_simulation_completed_at_set(self, engine, contract_case):
        sim = engine.run_simulation(contract_case)
        assert sim.completed_at is not None

    def test_win_probability_in_range(self, engine, contract_case):
        sim = engine.run_simulation(contract_case)
        assert 0.0 <= sim.win_probability <= 1.0

    def test_evidence_strength_in_range(self, engine, contract_case):
        sim = engine.run_simulation(contract_case)
        assert 0.0 <= sim.evidence_strength <= 1.0

    def test_get_simulation_by_id(self, engine, contract_case):
        sim = engine.run_simulation(contract_case)
        retrieved = engine.get_simulation(sim.id)
        assert retrieved is sim

    def test_get_simulation_unknown_id(self, engine):
        assert engine.get_simulation("nonexistent") is None

    def test_total_simulations_counter(self, engine, contract_case, employment_case):
        engine.run_simulation(contract_case)
        engine.run_simulation(employment_case)
        assert engine.total_simulations == 2

    def test_simulation_report_structure(self, engine, contract_case):
        sim = engine.run_simulation(contract_case)
        report = engine.simulation_report(sim)
        assert "simulation_id" in report
        assert "verdict" in report
        assert "win_probability" in report
        assert "parl_reward" in report
        assert "agents_used" in report

    def test_simulation_report_agents_used(self, engine, contract_case):
        sim = engine.run_simulation(contract_case)
        report = engine.simulation_report(sim)
        assert "zero" in report["agents_used"]
        assert "sigma" in report["agents_used"]
        assert "nova" in report["agents_used"]

    def test_batch_simulate(self, engine, contract_case, employment_case, ip_case):
        cases = [contract_case, employment_case, ip_case]
        simulations = engine.batch_simulate(cases)
        assert len(simulations) == 3
        assert all(s.is_complete for s in simulations)

    def test_aggregate_stats(self, engine, contract_case, employment_case, ip_case):
        cases = [contract_case, employment_case, ip_case]
        simulations = engine.batch_simulate(cases)
        stats = engine.aggregate_stats(simulations)
        assert stats["total_cases"] == 3
        assert 0.0 <= stats["win_rate"] <= 1.0
        assert 0.0 <= stats["avg_parl_reward"] <= 2.0

    def test_aggregate_stats_empty(self, engine):
        stats = engine.aggregate_stats([])
        assert stats == {}

    def test_employment_case_simulation(self, engine, employment_case):
        sim = engine.run_simulation(employment_case)
        assert sim.is_complete
        assert len(sim.evidence_collected) > 0

    def test_ip_case_simulation(self, engine, ip_case):
        sim = engine.run_simulation(ip_case)
        assert sim.is_complete
        assert len(sim.motions_filed) > 0

    def test_simulation_with_llm(self, engine):
        calls = []
        def mock_llm(prompt):
            calls.append(prompt)
            return f"LLM response for: {prompt[:30]}"

        llm_engine = LegalSimulationEngine(
            zero_llm=mock_llm,
            sigma_llm=mock_llm,
            nova_llm=mock_llm,
        )
        case = llm_engine.create_case(
            "LLM Test Case", CaseType.CONTRACT_DISPUTE, "desc", "client", "opp"
        )
        sim = llm_engine.run_simulation(case)
        assert sim.is_complete
        assert len(calls) >= 2  # zero + sigma at minimum

    def test_step_durations_recorded(self, engine, contract_case):
        sim = engine.run_simulation(contract_case)
        for step in sim.steps:
            assert step.duration_ms >= 0.0

    def test_step_parl_rewards_distributed(self, engine, contract_case):
        sim = engine.run_simulation(contract_case)
        total_step_reward = sum(s.parl_reward for s in sim.steps)
        assert total_step_reward == pytest.approx(sim.total_parl_reward, abs=0.001)

    def test_simulation_duration_positive(self, engine, contract_case):
        sim = engine.run_simulation(contract_case)
        assert sim.duration_s >= 0.0
