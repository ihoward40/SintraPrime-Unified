"""
Live case script: UACC repossession deficiency.

Evaluates: UACC is collecting an alleged deficiency balance from a vehicle
repossession; debtor challenges the deficiency calculation and notices.
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
            id="SRC-UCC-9-625",
            citation="U.C.C. § 9-625 (Waiver)",
            classification=SourceClassification.PRIMARY_LEGAL,
            jurisdiction=jurisdiction,
            publisher="Uniform Commercial Code (adopted in NJ and most states)",
        ),
        Source(
            id="SRC-UCC-9-611",
            citation="U.C.C. § 9-611 (Notification before disposition of collateral)",
            classification=SourceClassification.PRIMARY_LEGAL,
            jurisdiction=jurisdiction,
            publisher="Uniform Commercial Code",
        ),
        Source(
            id="SRC-FDCPA-VALIDATION",
            citation="15 U.S.C. § 1692g (Validation of debts)",
            classification=SourceClassification.PRIMARY_LEGAL,
            jurisdiction=jurisdiction,
            publisher="United States Code",
        ),
        Source(
            id="SRC-UACC-LETTER",
            citation="UACC collection letter and repossession notice",
            classification=SourceClassification.PRIVATE_PUBLISHED,
            publisher="Unaffiliated Collections Company",
        ),
        Source(
            id="SRC-NJ-UCC",
            citation="N.J.S.A. 12A:9-611 (Notification before disposition)",
            classification=SourceClassification.PRIMARY_LEGAL,
            jurisdiction=Jurisdiction(name="New Jersey", level="state"),
            publisher="New Jersey Statutes",
        ),
    ]
    for s in sources:
        orchestrator.register_source(s)

    claim = Claim(
        id="CLAIM-UACC-REPO-2026",
        text="The deficiency claimed by UACC after vehicle repossession is overstated because required pre- and post-disposition notices were deficient or absent.",
        subject="vehicle_repossession_deficiency",
        jurisdiction=jurisdiction,
        assumptions=[
            "Vehicle was repossessed by or on behalf of the secured party.",
            "UACC is collecting a purported deficiency balance.",
            "New Jersey UCC Article 9 applies.",
        ],
        missing_evidence=[
            "Notice of intent to repossess and right to cure.",
            "Post-repossession notice of disposition with date/place/manner.",
            "Itemized calculation of proceeds credited to debtor.",
            "Evidence of commercially reasonable sale price.",
        ],
        tags=["UCC", "repossession", "deficiency", "FDCPA", "UACC"],
    )

    evidence_items = [
        EvidenceItem(
            id="EV-UACC-1",
            source=sources[1],
            claim_text="Secured party must give reasonable authenticated notification of disposition to debtor.",
            confidence=Confidence.HIGH,
        ),
        EvidenceItem(
            id="EV-UACC-2",
            source=sources[4],
            claim_text="New Jersey adopts UCC Article 9 notice requirements.",
            jurisdiction=sources[4].jurisdiction,
            confidence=Confidence.HIGH,
        ),
        EvidenceItem(
            id="EV-UACC-3",
            source=sources[3],
            claim_text="UACC letter demands deficiency payment but does not attach sale proceeds breakdown.",
            context="Debtor received demand only; no post-disposition accounting attached.",
            confidence=Confidence.HIGH,
        ),
    ]
    for ev in evidence_items:
        orchestrator.add_evidence(ev, actor="AGENT-BLACKSTONE-2-0")
        claim.evidence.append(ev)

    counter = EvidenceItem(
        id="EV-UACC-COUNTER-1",
        source=sources[0],
        claim_text="Debtor may have waived certain UCC notice rights in the security agreement.",
        confidence=Confidence.LIMITED,
    )
    orchestrator.add_evidence(counter, actor="AGENT-BLACKSTONE-2-0")
    claim.counter_evidence.append(counter)

    orchestrator.add_claim(claim)

    orchestrator.add_risk(
        Risk(
            id="RISK-UACC-SALE",
            category="litigation",
            description="If sale was not commercially reasonable, deficiency may be reduced or eliminated.",
            likelihood=Confidence.MODERATE,
            impact=Confidence.HIGH,
            actor="AGENT-BLACKSTONE-2-0",
        )
    )
    orchestrator.add_risk(
        Risk(
            id="RISK-UACC-SOL",
            category="litigation",
            description="State statute of limitations may bar deficiency suit depending on last payment or sale date.",
            likelihood=Confidence.MODERATE,
            impact=Confidence.HIGH,
            actor="AGENT-BLACKSTONE-2-0",
        )
    )
    orchestrator.add_risk(
        Risk(
            id="RISK-UACC-DOCS",
            category="documentation",
            description="Paperwork gap (repo notice, sale accounting) is the central evidence issue.",
            likelihood=Confidence.HIGH,
            impact=Confidence.HIGH,
            actor="AGENT-BLACKSTONE-2-0",
        )
    )

    return orchestrator, claim.id


if __name__ == "__main__":
    orchestrator, claim_id = build_case()
    result = orchestrator.evaluate(
        claim_id,
        question="Can the debtor challenge UACC's deficiency demand under UCC Article 9 and the FDCPA?",
        actor="AGENT-BLACKSTONE-2-0",
    )
    rec = result["recommendation"]
    print("=" * 70)
    print("Blackstone Case Evaluation: UACC Vehicle Repossession Deficiency")
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
