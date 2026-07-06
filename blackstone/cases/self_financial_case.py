"""
Self Financial credit-builder / collection case — apply the Blackstone governance framework.

Evaluates: Self Financial, Inc. reports a purported default on a credit-builder
loan. Debtor disputes the tradeline and collection attempts.
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


def evaluate_self_financial():
    orchestrator = BlackstoneOrchestrator(agents=["AGENT-HERMES-2-0", "AGENT-BLACKSTONE-2-0"])
    jurisdiction = Jurisdiction(name="United States", level="federal")
    orchestrator.register_jurisdiction(jurisdiction)

    sources = [
        Source(
            id="SRC-FCRA-1681e",
            citation="15 U.S.C. § 1681e(b) (Reasonable procedures to assure accuracy)",
            classification=SourceClassification.PRIMARY_LEGAL,
            jurisdiction=jurisdiction,
            publisher="United States Code",
        ),
        Source(
            id="SRC-FCRA-1681i",
            citation="15 U.S.C. § 1681i (Procedure in case of disputed accuracy)",
            classification=SourceClassification.PRIMARY_LEGAL,
            jurisdiction=jurisdiction,
            publisher="United States Code",
        ),
        Source(
            id="SRC-FCRA-1681s-2",
            citation="15 U.S.C. § 1681s-2 (Furnisher accuracy and investigation duties)",
            classification=SourceClassification.PRIMARY_LEGAL,
            jurisdiction=jurisdiction,
            publisher="United States Code",
        ),
        Source(
            id="SRC-SELF-AGREEMENT",
            citation="Self Financial Credit Builder Account Agreement",
            classification=SourceClassification.COMMERCIAL,
            publisher="Self Financial, Inc.",
        ),
        Source(
            id="SRC-CRA-REPORT",
            citation="Consumer credit report showing Self Financial tradeline",
            classification=SourceClassification.COMMERCIAL,
            publisher="Equifax/Experian/TransUnion",
        ),
    ]
    for s in sources:
        orchestrator.register_source(s)

    claim = Claim(
        id="CLAIM-SELF-FINANCIAL-2026",
        text="The Self Financial tradeline reported to consumer reporting agencies is inaccurate and Self has failed to conduct a reasonable investigation after dispute.",
        subject="credit_reporting_dispute",
        jurisdiction=jurisdiction,
        assumptions=[
            "Debtor opened a Self Financial credit-builder account.",
            "Self Financial is a furnisher under FCRA § 1681s-2.",
            "Debtor submitted a written dispute to CRAs and/or Self.",
        ],
        missing_evidence=[
            "Copy of credit report showing the disputed tradeline.",
            "Proof of dispute letters sent to CRAs and Self.",
            "Self's response or verification of the disputed information.",
            "Payment/administrative records from Self portal.",
        ],
        tags=["FCRA", "Self_Financial", "credit_builder", "furnisher_duty"],
    )

    evidence_items = [
        EvidenceItem(
            id="EV-SELF-1",
            source=sources[0],
            claim_text="CRAs must follow reasonable procedures to assure maximum possible accuracy.",
            confidence=Confidence.HIGH,
        ),
        EvidenceItem(
            id="EV-SELF-2",
            source=sources[2],
            claim_text="Furnishers must not report information after being notified that the information is inaccurate.",
            confidence=Confidence.HIGH,
        ),
        EvidenceItem(
            id="EV-SELF-3",
            source=sources[4],
            claim_text="Credit report shows Self Financial tradeline with balance or status the debtor disputes.",
            context="Debtor alleges the reported default or amount is wrong.",
            confidence=Confidence.MODERATE,
        ),
    ]
    for ev in evidence_items:
        orchestrator.add_evidence(ev, actor="AGENT-BLACKSTONE-2-0")
        claim.evidence.append(ev)

    counter = EvidenceItem(
        id="EV-SELF-COUNTER-1",
        source=sources[3],
        claim_text="Self agreement may define default and reporting triggers in a way that supports Self's position.",
        confidence=Confidence.MODERATE,
    )
    orchestrator.add_evidence(counter, actor="AGENT-BLACKSTONE-2-0")
    claim.counter_evidence.append(counter)

    orchestrator.add_claim(claim)

    orchestrator.add_risk(
        Risk(
            id="RISK-SELF-DISPUTE",
            category="credit_reporting",
            description="Debtor must prove dispute was actually sent to CRAs and furnisher; certified mail receipts needed.",
            likelihood=Confidence.HIGH,
            impact=Confidence.MODERATE,
            actor="AGENT-BLACKSTONE-2-0",
        )
    )
    orchestrator.add_risk(
        Risk(
            id="RISK-SELF-HARM",
            category="credit_reporting",
            description="Continued reporting suppresses credit score and may affect housing/employment.",
            likelihood=Confidence.HIGH,
            impact=Confidence.HIGH,
            actor="AGENT-BLACKSTONE-2-0",
        )
    )
    orchestrator.add_risk(
        Risk(
            id="RISK-SELF-ARBITRATION",
            category="litigation",
            description="Self agreement may include arbitration clause; litigation path may require opt-out analysis.",
            likelihood=Confidence.MODERATE,
            impact=Confidence.MODERATE,
            actor="AGENT-BLACKSTONE-2-0",
        )
    )

    result = orchestrator.evaluate(claim.id, question="Does the debtor have a colorable FCRA claim against Self Financial for inaccurate reporting?", actor="AGENT-BLACKSTONE-2-0")
    return result, orchestrator


if __name__ == "__main__":
    result, _orch = evaluate_self_financial()
    rec = result["recommendation"]
    print("=" * 70)
    print("Blackstone Case Evaluation: Self Financial Credit-Builder Dispute")
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
