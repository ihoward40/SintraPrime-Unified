from __future__ import annotations

import pytest

from agent_runtime.collective_intelligence import (
    CollectiveIntelligence,
    CollectiveIntelligenceError,
    CompetencyState,
    EvidenceRef,
    LearningState,
)


def evidence() -> EvidenceRef:
    return EvidenceRef("EV-1", "https://example.test/source", "sha256:abc")


def verified_lesson(ci: CollectiveIntelligence, lesson_id: str = "LESSON-1"):
    lesson = ci.observe(
        lesson_id=lesson_id,
        subject="competitive-intelligence",
        proposition="A verified proposition",
        source_agent_id="agent.scout",
        evidence=[evidence()],
        applicable_agents=["agent.marketing", "agent.strategy"],
    )
    ci.challenge(
        lesson_id,
        challenger_agent_id="agent.redteam",
        finding="source and proposition align",
        passed=True,
        evidence_refs=["EV-1"],
    )
    ci.verify(lesson_id, verifier_agent_id="agent.verifier")
    return ci.mark_distributable(lesson_id)


def test_learning_requires_independent_challenge_and_verification():
    ci = CollectiveIntelligence()
    lesson = ci.observe(
        lesson_id="L1",
        subject="tax",
        proposition="claim",
        source_agent_id="agent.scout",
        evidence=[evidence()],
        applicable_agents=["agent.tax"],
    )
    with pytest.raises(CollectiveIntelligenceError, match="challenge required"):
        ci.verify("L1", verifier_agent_id="agent.verifier")
    with pytest.raises(CollectiveIntelligenceError, match="independent challenger"):
        ci.challenge("L1", challenger_agent_id="agent.scout", finding="self", passed=True)
    ci.challenge("L1", challenger_agent_id="agent.redteam", finding="ok", passed=True)
    with pytest.raises(CollectiveIntelligenceError, match="independent of challengers"):
        ci.verify("L1", verifier_agent_id="agent.redteam")
    ci.verify("L1", verifier_agent_id="agent.verifier")
    assert lesson.state is LearningState.VERIFIED


def test_failed_challenge_blocks_distribution():
    ci = CollectiveIntelligence()
    ci.observe(
        lesson_id="L2",
        subject="law",
        proposition="unsupported",
        source_agent_id="agent.scout",
        evidence=[evidence()],
        applicable_agents=["agent.legal"],
    )
    ci.challenge("L2", challenger_agent_id="agent.redteam", finding="unsupported", passed=False)
    with pytest.raises(CollectiveIntelligenceError, match="failed challenge"):
        ci.verify("L2", verifier_agent_id="agent.verifier")
    assert ci._require("L2").state is LearningState.REJECTED
    with pytest.raises(CollectiveIntelligenceError):
        ci.mark_distributable("L2")


def test_only_relevant_agents_inherit_verified_lessons():
    ci = CollectiveIntelligence()
    lesson = verified_lesson(ci)
    assert ci.inherited_lessons("agent.marketing") == (lesson,)
    assert ci.inherited_lessons("agent.unrelated") == ()


def test_competency_is_measured_and_does_not_grant_authority():
    ci = CollectiveIntelligence()
    verified_lesson(ci)
    receipt = ci.demonstrate_competency(
        agent_id="agent.marketing",
        subject="competitive-intelligence",
        exam_id="EXAM-1",
        score=92,
        threshold=90,
        lesson_ids=["LESSON-1"],
    )
    assert receipt.state is CompetencyState.CERTIFIED
    proposal = ci.propose_value(
        "LESSON-1",
        proposal_type="OFFER_EXPERIMENT",
        description="Test a differentiated offer",
        expected_metric="conversion_rate",
    )
    assert proposal.requires_principal_approval is True


def test_outcomes_require_evidence_and_feed_back_as_records():
    ci = CollectiveIntelligence()
    verified_lesson(ci)
    with pytest.raises(CollectiveIntelligenceError, match="outcome evidence"):
        ci.record_outcome(
            lesson_id="LESSON-1",
            proposal_type="OFFER_EXPERIMENT",
            metric="revenue",
            observed_value=100.0,
            successful=True,
            evidence_refs=[],
        )
    outcome = ci.record_outcome(
        lesson_id="LESSON-1",
        proposal_type="OFFER_EXPERIMENT",
        metric="revenue",
        observed_value=100.0,
        successful=True,
        evidence_refs=["receipt:stripe:1"],
    )
    assert ci.outcomes("LESSON-1") == (outcome,)


def test_supersession_stales_competency_bound_to_old_lesson():
    ci = CollectiveIntelligence()
    verified_lesson(ci, "OLD")
    ci.demonstrate_competency(
        agent_id="agent.strategy",
        subject="competitive-intelligence",
        exam_id="EXAM-OLD",
        score=95,
        threshold=90,
        lesson_ids=["OLD"],
    )
    new = ci.observe(
        lesson_id="NEW",
        subject="competitive-intelligence",
        proposition="updated proposition",
        source_agent_id="agent.scout",
        evidence=[EvidenceRef("EV-2", "https://example.test/new", "sha256:def")],
        applicable_agents=["agent.strategy"],
        supersedes="OLD",
    )
    ci.challenge("NEW", challenger_agent_id="agent.redteam", finding="ok", passed=True)
    ci.verify("NEW", verifier_agent_id="agent.verifier")
    ci.mark_distributable("NEW")
    ci.supersede("OLD", "NEW")
    assert new.state is LearningState.DISTRIBUTABLE
    assert ci._require("OLD").state is LearningState.SUPERSEDED
    assert ci.competency("agent.strategy", "competitive-intelligence").state is CompetencyState.STALE
