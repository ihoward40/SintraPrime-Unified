"""
Tests for the Blackstone Reference Architecture (BRA) engines.
"""
from __future__ import annotations

import pytest

from blackstone.engines import BlackstoneOrchestrator
from blackstone.engines.authority_engine import AuthorityEngine
from blackstone.engines.evidence_engine import EvidenceEngine
from blackstone.engines.provenance_engine import ProvenanceEngine
from blackstone.engines.reasoning_engine import ReasoningEngine
from blackstone.engines.risk_engine import RiskEngine
from blackstone.models import (
    Claim,
    ClaimStatus,
    Confidence,
    EvidenceItem,
    Jurisdiction,
    Recommendation,
    Risk,
    Source,
    SourceClassification,
)


@pytest.fixture
def federal_us():
    return Jurisdiction(name="United States", level="federal")


@pytest.fixture
def irs_pub_source(federal_us):
    return Source(
        id="SRC-IRS-PUB-1",
        citation="IRS Publication 594, The IRS Collection Process",
        classification=SourceClassification.PRIMARY_LEGAL,
        jurisdiction=federal_us,
        publisher="Internal Revenue Service",
    )


@pytest.fixture
def private_blog_source():
    return Source(
        id="SRC-PVT-BLOG-1",
        citation="Unverified tax blog post",
        classification=SourceClassification.PRIVATE_PUBLISHED,
        publisher="Private blogger",
    )


def test_evidence_engine_scores_primary_legal_high(federal_us, irs_pub_source):
    engine = EvidenceEngine()
    claim = Claim(id="CLAIM-1", text="IRS can file a Notice of Federal Tax Lien.", subject="tax_collection", jurisdiction=federal_us)
    evidence = EvidenceItem(
        id="EV-1",
        source=irs_pub_source,
        claim_text="IRC § 6321 creates a lien upon failure to pay tax.",
        confidence=Confidence.HIGH,
    )
    claim.evidence.append(evidence)
    engine.add_claim(claim)
    engine.evaluate_claim(claim)

    assert claim.status == ClaimStatus.CONTROLLING
    assert claim.confidence in (Confidence.HIGH, Confidence.MODERATE)


def test_evidence_engine_private_source_is_emerging(federal_us, private_blog_source):
    engine = EvidenceEngine()
    claim = Claim(id="CLAIM-2", text="You can discharge tax debt in bankruptcy.", subject="bankruptcy_tax", jurisdiction=federal_us)
    evidence = EvidenceItem(
        id="EV-2",
        source=private_blog_source,
        claim_text="Some tax debts are dischargeable.",
        confidence=Confidence.MODERATE,
    )
    claim.evidence.append(evidence)
    engine.add_claim(claim)
    engine.evaluate_claim(claim)

    assert claim.status == ClaimStatus.EMERGING
    assert claim.confidence in (Confidence.LIMITED, Confidence.PRELIMINARY, Confidence.INSUFFICIENT)


def test_authority_engine_finds_controlling(federal_us, irs_pub_source):
    engine = AuthorityEngine(default_jurisdiction=federal_us)
    claim = Claim(id="CLAIM-3", text="IRS may levy.", subject="tax_collection", jurisdiction=federal_us)
    claim.evidence.append(
        EvidenceItem(
            id="EV-3",
            source=irs_pub_source,
            claim_text="IRC § 6331 authorizes levy.",
            confidence=Confidence.HIGH,
        )
    )
    controlling = engine.controlling_authority(claim)
    assert controlling is not None
    assert controlling.id == irs_pub_source.id


def test_authority_engine_conflict_detection(federal_us):
    engine = AuthorityEngine(default_jurisdiction=federal_us)
    claim = Claim(id="CLAIM-4", text="X is prohibited.", subject="conflict_demo", jurisdiction=federal_us)
    claim.evidence.append(
        EvidenceItem(
            id="EV-4A",
            source=Source(
                id="SRC-A",
                citation="Statute A",
                classification=SourceClassification.PRIMARY_LEGAL,
                jurisdiction=federal_us,
            ),
            claim_text="X is prohibited.",
            confidence=Confidence.HIGH,
        )
    )
    claim.evidence.append(
        EvidenceItem(
            id="EV-4B",
            source=Source(
                id="SRC-B",
                citation="Statute B",
                classification=SourceClassification.PRIMARY_LEGAL,
                jurisdiction=federal_us,
            ),
            claim_text="X is allowed.",
            confidence=Confidence.HIGH,
        )
    )
    conflicts = engine.find_conflicts(claim)
    assert len(conflicts) == 1
    assert conflicts[0]["reason"] == "conflicting primary authority"


def test_reasoning_engine_produces_recommendation(federal_us, irs_pub_source):
    evidence_engine = EvidenceEngine()
    authority_engine = AuthorityEngine(default_jurisdiction=federal_us)
    reasoning_engine = ReasoningEngine(evidence_engine, authority_engine, agents=["AGENT-HERMES-2-0"])

    claim = Claim(id="CLAIM-5", text="IRS can file a lien.", subject="tax_collection", jurisdiction=federal_us)
    claim.evidence.append(
        EvidenceItem(
            id="EV-5",
            source=irs_pub_source,
            claim_text="IRC § 6321 creates a lien.",
            confidence=Confidence.HIGH,
        )
    )
    evidence_engine.add_claim(claim)

    rec = reasoning_engine.recommend(question="Can the IRS file a lien?", claim=claim)
    assert isinstance(rec, Recommendation)
    assert rec.recommendation.startswith("Adopt")
    assert "AGENT-HERMES-2-0" in rec.agents


def test_provenance_engine_verifies_chain():
    engine = ProvenanceEngine()
    engine.record("OBJ-1", "evidence", "created", "user", payload={"x": 1})
    engine.record("OBJ-1", "evidence", "reviewed", "reviewer", payload={"x": 2})
    result = engine.verify("OBJ-1")
    assert result["valid"] is True
    assert result["breaks"] == []


def test_risk_engine_scores_risk():
    engine = RiskEngine()
    risk = Risk(
        id="RISK-1",
        category="litigation",
        description="Statute of limitations may have expired.",
        likelihood=Confidence.MODERATE,
        impact=Confidence.HIGH,
    )
    engine.add_risk(risk)
    assert engine.score(risk) == 0.7 * 1.0


def test_orchestrator_evaluates_claim(federal_us, irs_pub_source):
    orch = BlackstoneOrchestrator(agents=["AGENT-HERMES-2-0"])
    orch.register_jurisdiction(federal_us)
    orch.register_source(irs_pub_source)

    claim = Claim(id="CLAIM-6", text="IRS can file a lien.", subject="tax_collection", jurisdiction=federal_us)
    evidence = EvidenceItem(
        id="EV-6",
        source=irs_pub_source,
        claim_text="IRC § 6321 creates a lien.",
        confidence=Confidence.HIGH,
    )
    orch.add_evidence(evidence, actor="AGENT-HERMES-2-0")
    orch.add_claim(claim)
    claim.evidence.append(evidence)

    result = orch.evaluate("CLAIM-6", question="Can the IRS file a lien?")
    assert result["claim"]["status"] == "controlling"
    assert result["provenance"]["verified"] is True
    assert result["recommendation"]["recommendation"].startswith("Adopt")


def test_orchestrator_private_source_is_not_adopted(federal_us, private_blog_source):
    orch = BlackstoneOrchestrator()
    orch.register_jurisdiction(federal_us)
    orch.register_source(private_blog_source)

    claim = Claim(id="CLAIM-7", text="Discharge tax debt in bankruptcy.", subject="bankruptcy_tax", jurisdiction=federal_us)
    evidence = EvidenceItem(
        id="EV-7",
        source=private_blog_source,
        claim_text="Tax debt may be dischargeable.",
        confidence=Confidence.MODERATE,
    )
    orch.add_evidence(evidence)
    orch.add_claim(claim)
    claim.evidence.append(evidence)

    result = orch.evaluate("CLAIM-7", question="Should we tell the user to file bankruptcy to discharge tax debt?")
    assert result["claim"]["status"] == "emerging"
    assert result["recommendation"]["recommendation"].startswith("Track")
    assert result["recommendation"]["confidence"] != "high"
