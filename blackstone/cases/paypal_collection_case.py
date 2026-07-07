"""
Live case script: PayPal collections case.

Evaluates: PayPal Credit / Synchrony alleges a default and may have sold or
collected the debt. Debtor disputes the balance and reporting.
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
    jurisdiction = Jurisdiction(name="United States", level="federal")
    orchestrator.register_jurisdiction(jurisdiction)

    sources = [
        Source(
            id="SRC-TILA",
            citation="15 U.S.C. § 1637 (Open end consumer credit plans)",
            classification=SourceClassification.PRIMARY_LEGAL,
            jurisdiction=jurisdiction,
            publisher="United States Code",
        ),
        Source(
            id="SRC-FDCPA-809",
            citation="15 U.S.C. § 1692g(a) (Validation notice)",
            classification=SourceClassification.PRIMARY_LEGAL,
            jurisdiction=jurisdiction,
            publisher="United States Code",
        ),
        Source(
            id="SRC-FDCPA-811",
            citation="15 U.S.C. § 1692i (Legal actions by debt collectors)",
            classification=SourceClassification.PRIMARY_LEGAL,
            jurisdiction=jurisdiction,
            publisher="United States Code",
        ),
        Source(
            id="SRC-PP-USER-AGREEMENT",
            citation="PayPal User Agreement — Credit products (most recent)",
            classification=SourceClassification.COMMERCIAL,
            publisher="PayPal, Inc.",
        ),
        Source(
            id="SRC-SYNCHRONY-STATEMENT",
            citation="Synchrony Bank billing statement for PayPal Credit",
            classification=SourceClassification.COMMERCIAL,
            publisher="Synchrony Bank",
        ),
    ]
    for s in sources:
        orchestrator.register_source(s)

    claim = Claim(
        id="CLAIM-PAYPAL-COLLECTION-2026",
        text="The PayPal/Synchrony debt cannot be enforced as stated because the debtor disputes the balance and the collector has not provided verification.",
        subject="credit_card_debt_dispute",
        jurisdiction=jurisdiction,
        assumptions=[
            "The account is a consumer credit plan subject to TILA.",
            "A third-party debt collector is attempting collection or litigation.",
        ],
        missing_evidence=[
            "Complete PayPal/Synchrony transaction history.",
            "Written validation request and proof of delivery.",
            "Any assignment or sale agreement to a debt buyer.",
            "Current credit report showing tradeline.",
        ],
        tags=["PayPal", "Synchrony", "TILA", "FDCPA", "debt_dispute"],
    )

    evidence_items = [
        EvidenceItem(
            id="EV-PP-1",
            source=sources[1],
            claim_text="A debt collector must provide validation information in writing after initial communication.",
            confidence=Confidence.HIGH,
        ),
        EvidenceItem(
            id="EV-PP-2",
            source=sources[0],
            claim_text="Open-end credit plans must provide periodic statements showing how the balance was computed.",
            confidence=Confidence.HIGH,
        ),
        EvidenceItem(
            id="EV-PP-3",
            source=sources[4],
            claim_text="Synchrony statement may not account for credits, returns, or fees the debtor disputes.",
            context="Debtor asserts unauthorized or erroneous charges.",
            confidence=Confidence.MODERATE,
        ),
    ]
    for ev in evidence_items:
        orchestrator.add_evidence(ev, actor="AGENT-BLACKSTONE-2-0")
        claim.evidence.append(ev)

    counter = EvidenceItem(
        id="EV-PP-COUNTER-1",
        source=sources[3],
        claim_text="PayPal user agreement may contain arbitration or venue clauses that affect litigation strategy.",
        confidence=Confidence.MODERATE,
    )
    orchestrator.add_evidence(counter, actor="AGENT-BLACKSTONE-2-0")
    claim.counter_evidence.append(counter)

    orchestrator.add_claim(claim)

    orchestrator.add_risk(
        Risk(
            id="RISK-PP-ARBITRATION",
            category="litigation",
            description="User agreement may compel individual arbitration, limiting court remedies.",
            likelihood=Confidence.MODERATE,
            impact=Confidence.HIGH,
            actor="AGENT-BLACKSTONE-2-0",
        )
    )
    orchestrator.add_risk(
        Risk(
            id="RISK-PP-STATEMENTS",
            category="documentation",
            description="Without original statements, debtor cannot prove credits/charge errors.",
            likelihood=Confidence.HIGH,
            impact=Confidence.HIGH,
            actor="AGENT-BLACKSTONE-2-0",
        )
    )
    orchestrator.add_risk(
        Risk(
            id="RISK-PP-CREDIT",
            category="credit_reporting",
            description="Continued reporting of disputed balance may violate FCRA § 1681s-2(a).",
            likelihood=Confidence.MODERATE,
            impact=Confidence.MODERATE,
            actor="AGENT-BLACKSTONE-2-0",
        )
    )

    return orchestrator, claim.id


if __name__ == "__main__":
    orchestrator, claim_id = build_case()
    result = orchestrator.evaluate(
        claim_id,
        question="Can the debtor successfully dispute the PayPal/Synchrony debt under FDCPA and TILA?",
        actor="AGENT-BLACKSTONE-2-0",
    )
    rec = result["recommendation"]
    print("=" * 70)
    print("Blackstone Case Evaluation: PayPal/Synchrony Collection")
    print("=" * 70)
    print(f"Status:           {result['claim']['status']}")
    print(f"Confidence:       {result['claim']['confidence']}")
    print(f"Recommendation: {rec['recommendation']}")
    print(f"Rationale:        {rec['rationale']}")
    print("=" * 70)
    for r in result["risks"]:
        print(f"  - [{r['category']}] {r['description']} (score={r['score']})")
    print("=" * 70)
    print(f"Provenance verified: {result['provenance']['verified']}")
    print(f"Agents: {', '.join(rec['agents'])}")
    print("=" * 70)
