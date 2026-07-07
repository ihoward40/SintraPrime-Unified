"""
Live case script: FDCPA validation demand and counter-strategy against LVNV.

Scenario: the consumer received a collection letter from LVNV Funding LLC.
The letter lacks the validation notice required by 15 U.S.C. § 1692g.
This case evaluates whether to demand validation, dispute the debt, and
preserve claims for FDCPA and state consumer-protection violations.
"""
from __future__ import annotations

from blackstone.engines import BlackstoneOrchestrator
from blackstone.models import (
    Claim,
    Confidence,
    EvidenceItem,
    Jurisdiction,
    Risk,
    Source,
    SourceClassification,
)


def build_case():
    orchestrator = BlackstoneOrchestrator(
        agents=["AGENT-HERMES-2-0", "AGENT-BLACKSTONE-2-0"]
    )
    orchestrator.register_jurisdiction(
        Jurisdiction(name="United States", level="federal")
    )
    orchestrator.register_jurisdiction(
        Jurisdiction(name="New Jersey", level="state", parent="United States")
    )

    sources = [
        Source(
            id="src-fdcpa-1692g",
            citation="15 U.S.C. § 1692g — Validation of debts",
            classification=SourceClassification.PRIMARY_LEGAL,
        ),
        Source(
            id="src-fdcpa-1692k",
            citation="15 U.S.C. § 1692k — Civil liability",
            classification=SourceClassification.PRIMARY_LEGAL,
        ),
        Source(
            id="src-nj-cpa",
            citation="N.J.S.A. 56:8-1 et seq. — New Jersey Consumer Fraud Act",
            classification=SourceClassification.PRIMARY_LEGAL,
        ),
        Source(
            id="src-collection-letter",
            citation="LVNV collection letter dated 2026-06-15",
            classification=SourceClassification.PRIVATE_PUBLISHED,
        ),
    ]
    for s in sources:
        orchestrator.register_source(s)

    evidence = [
        EvidenceItem(
            id="ev-lvnv-1",
            source=sources[0],
            claim_text="FDCPA requires validation notice with amount, creditor, and dispute rights within five days of initial communication.",
            confidence=Confidence.HIGH,
        ),
        EvidenceItem(
            id="ev-lvnv-2",
            source=sources[1],
            claim_text="A debt collector that fails to comply with FDCPA may be liable for actual damages, statutory damages, and costs/fees.",
            confidence=Confidence.HIGH,
        ),
        EvidenceItem(
            id="ev-lvnv-3",
            source=sources[2],
            claim_text="New Jersey Consumer Fraud Act provides additional remedies for unconscionable commercial practices.",
            confidence=Confidence.MODERATE,
        ),
        EvidenceItem(
            id="ev-lvnv-4",
            source=sources[3],
            claim_text="LVNV's letter demands payment but does not include the required validation notice or name the original creditor.",
            confidence=Confidence.HIGH,
        ),
    ]
    for e in evidence:
        orchestrator.add_evidence(e, actor="AGENT-BLACKSTONE-2-0")

    claim = Claim(
        id="claim-lvnv-counter-001",
        text="LVNV's collection letter violates FDCPA § 1692g by omitting the validation notice and original creditor identification, and the consumer should immediately demand validation while preserving claims under § 1692k and the New Jersey Consumer Fraud Act.",
        subject="LVNV validation demand / counter-strategy",
        assumptions=[
            "The letter is the first communication from LVNV on this account.",
            "The consumer disputes the debt and requires verification.",
        ],
        missing_evidence=[
            "Certified mail receipt for collection letter.",
            "Signed debt validation demand letter.",
            "Any prior communications or statements from original creditor.",
            "Consumer's credit report showing the tradeline.",
        ],
        tags=["lvnv", "fdcpa", "validation", "counter-strategy", "new-jersey"],
    )
    for e in evidence:
        claim.evidence.append(e)

    risks = [
        Risk(
            id="risk-lvnv-sol",
            category="litigation",
            description="FDCPA has a one-year statute of limitations from the violation; the clock started when the letter was sent.",
            likelihood=Confidence.MODERATE,
            impact=Confidence.HIGH,
            controls=["confirm letter date", "file suit or preserve claim promptly"],
            owner="AGENT-BLACKSTONE-2-0",
            actor="AGENT-BLACKSTONE-2-0",
            tags=["lvnv", "fdcpa", "sol"],
        ),
        Risk(
            id="risk-lvnv-response",
            category="strategy",
            description="LVNV may provide validation after demand, weakening the FDCPA claim but leaving FCRA/credit-reporting claims intact.",
            likelihood=Confidence.MODERATE,
            impact=Confidence.MODERATE,
            controls=["document pre-validation collection activity", "preserve all correspondence"],
            owner="AGENT-BLACKSTONE-2-0",
            actor="AGENT-BLACKSTONE-2-0",
            tags=["lvnv", "strategy"],
        ),
    ]
    for r in risks:
        orchestrator.add_risk(r)

    orchestrator.add_claim(claim)

    return orchestrator, claim.id


if __name__ == "__main__":
    orchestrator, claim_id = build_case()
    result = orchestrator.evaluate(
        claim_id,
        question="Should we send a written validation demand, dispute the debt, and preserve FDCPA and New Jersey Consumer Fraud Act claims?",
        actor="AGENT-BLACKSTONE-2-0",
    )

    print("Status:", result["claim"]["status"])
    print("Confidence:", result["claim"]["confidence"])
    print("Recommendation:", result["recommendation"]["recommendation"])
    print("Rationale:", result["recommendation"]["rationale"])
    print(f"Risks ({len(result.get('risks', []))}):")
    for r in result.get("risks", []):
        print(f"  - [{r['category']}] {r['description']} (score={r['score']})")
    print("Provenance verified:", result["provenance"]["verified"])
    print("Chain length:", result["provenance"]["chain_length"])
    print("Conflicts:", result["authority"]["conflicts"])
