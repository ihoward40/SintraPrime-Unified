"""
Live case script: Affirm / American First Finance (AFR) credit reporting dispute.

Scenario: the consumer settled or paid an Affirm/AFR point-of-sale loan, but the
account still reports as delinquent or with a balance on one or more credit
reports.
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

    sources = [
        Source(
            id="src-fcra",
            citation="15 U.S.C. § 1681e(b) — Reasonable procedures to assure accuracy",
            classification=SourceClassification.PRIMARY_LEGAL,
        ),
        Source(
            id="src-fcra-623",
            citation="15 U.S.C. § 1681s-2(a)(1)(A) — Prohibition against reporting inaccurate information",
            classification=SourceClassification.PRIMARY_LEGAL,
        ),
        Source(
            id="src-cfpb-dispute",
            citation="CFPB, How to dispute credit report errors",
            classification=SourceClassification.SECONDARY_LEGAL,
            url="https://www.consumerfinance.gov/consumer-tools/credit-reports-and-scores/disputing-errors/",
        ),
        Source(
            id="src-credit-report",
            citation="Experian credit report showing Affirm/AFR tradeline",
            classification=SourceClassification.PRIVATE_PUBLISHED,
        ),
        Source(
            id="src-settlement-letter",
            citation="Settlement/paid-in-full letter from Affirm/AFR",
            classification=SourceClassification.PRIVATE_PUBLISHED,
        ),
    ]
    for s in sources:
        orchestrator.register_source(s)

    evidence = [
        EvidenceItem(
            id="ev-affirm-1",
            source=sources[0],
            claim_text="Consumer reporting agencies must follow reasonable procedures to assure maximum possible accuracy.",
            confidence=Confidence.HIGH,
        ),
        EvidenceItem(
            id="ev-affirm-2",
            source=sources[1],
            claim_text="Furnishers must not report information they know or should know is inaccurate.",
            confidence=Confidence.HIGH,
        ),
        EvidenceItem(
            id="ev-affirm-3",
            source=sources[3],
            claim_text="The tradeline currently reports a past-due balance after a settlement/payment was made.",
            confidence=Confidence.HIGH,
        ),
        EvidenceItem(
            id="ev-affirm-4",
            source=sources[4],
            claim_text="The settlement letter confirms the account was paid in full or settled in satisfaction on 2026-04-12.",
            confidence=Confidence.HIGH,
        ),
    ]
    for e in evidence:
        orchestrator.add_evidence(e, actor="AGENT-BLACKSTONE-2-0")

    claim = Claim(
        id="claim-affirm-001",
        text="Affirm/AFR is continuing to report an inaccurate balance/delinquency in violation of FCRA § 1681e(b) and § 1681s-2(a)(1)(A), despite the account having been settled/paid in full.",
        subject="Affirm / AFR credit reporting dispute",
        assumptions=[
            "The settlement letter is authentic and correctly identifies the account.",
            "The consumer has disputed the tradeline with the CRA and received no correction.",
        ],
        missing_evidence=[
            "Copies of credit reports from all three CRAs showing the same tradeline.",
            "Certified dispute letters sent to CRAs and Affirm/AFR.",
            "Proof of payment or settlement funds transfer.",
            "Any response or verification from the furnisher.",
        ],
        tags=["affirm", "afr", "fcra", "credit-report", "point-of-sale"],
    )
    for e in evidence:
        claim.evidence.append(e)

    risks = [
        Risk(
            id="risk-affirm-sol",
            category="litigation",
            description="State statute of limitations for FCRA damages may be two years from discovery; confirm date of first inaccurate report.",
            likelihood=Confidence.LIMITED,
            impact=Confidence.HIGH,
            controls=["pull all three credit reports", "mark discovery date"],
            owner="AGENT-BLACKSTONE-2-0",
            actor="AGENT-BLACKSTONE-2-0",
            tags=["affirm", "fcra", "sol"],
        ),
        Risk(
            id="risk-affirm-doc",
            category="documentation",
            description="Settlement letter may not match account number or may omit zero-balance language, weakening the dispute.",
            likelihood=Confidence.MODERATE,
            impact=Confidence.MODERATE,
            controls=["verify account match", "request updated letter if needed"],
            owner="consumer",
            actor="AGENT-BLACKSTONE-2-0",
            tags=["affirm", "docs"],
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
        question="Should we send a formal FCRA dispute to the CRAs and Affirm/AFR, and preserve a record for potential litigation?",
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
