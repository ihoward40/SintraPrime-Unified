"""
LVNV Funding deficiency notice case — apply the Blackstone governance framework.

Evaluates: LVNV sent a debt-collection letter about an alleged debt. Debtor
has a live FDCPA/FCRA challenge.
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


def evaluate_lvnv_deficiency():
    orchestrator = BlackstoneOrchestrator(agents=["AGENT-HERMES-2-0", "AGENT-BLACKSTONE-2-0"])
    jurisdiction = Jurisdiction(name="United States", level="federal")
    orchestrator.register_jurisdiction(jurisdiction)

    sources = [
        Source(
            id="SRC-FDCPA",
            citation="15 U.S.C. § 1692g (Validation of debts)",
            classification=SourceClassification.PRIMARY_LEGAL,
            jurisdiction=jurisdiction,
            publisher="United States Code",
            url="https://www.govinfo.gov/content/pkg/USCODE-2023-title15/html/USCODE-2023-title15-chap41-subchapV-sec1692g.htm",
        ),
        Source(
            id="SRC-FDCPA-807",
            citation="15 U.S.C. § 1692e (False, deceptive, or misleading representations)",
            classification=SourceClassification.PRIMARY_LEGAL,
            jurisdiction=jurisdiction,
            publisher="United States Code",
        ),
        Source(
            id="SRC-FCRA-1681s-2",
            citation="15 U.S.C. § 1681s-2 (Furnisher duties)",
            classification=SourceClassification.PRIMARY_LEGAL,
            jurisdiction=jurisdiction,
            publisher="United States Code",
        ),
        Source(
            id="SRC-CFPB-DEBT-COLL",
            citation="CFPB — Fair Debt Collection Practices Act compliance bulletin",
            classification=SourceClassification.SECONDARY_LEGAL,
            jurisdiction=jurisdiction,
            publisher="Consumer Financial Protection Bureau",
        ),
        Source(
            id="SRC-LVNV-LETTER",
            citation="LVNV Funding collection letter dated 2026-06-15",
            classification=SourceClassification.PRIVATE_PUBLISHED,
            publisher="LVNV Funding LLC",
        ),
    ]
    for s in sources:
        orchestrator.register_source(s)

    claim = Claim(
        id="CLAIM-LVNV-GAP-2026",
        text="The LVNV deficiency notice fails to provide the required validation notice and may misstate the amount owed.",
        subject="debt_collection_validation",
        jurisdiction=jurisdiction,
        assumptions=[
            "The letter was sent by or on behalf of a debt collector as defined in 15 U.S.C. § 1692a(6).",
            "The recipient is a consumer debtor within the meaning of the FDCPA.",
        ],
        missing_evidence=[
            "Signed copy of the LVNV letter with full validation notice.",
            "Original creditor account statements or assignment chain.",
            "Debtor's written dispute/validation request and proof of mailing.",
            "Credit report entries showing furnisher reporting.",
        ],
        tags=["FDCPA", "FCRA", "debt_validation", "LVNV"],
    )

    evidence_items = [
        EvidenceItem(
            id="EV-LVNV-1",
            source=sources[0],
            claim_text="A debt collector must send a written validation notice within five days of initial communication.",
            quotation="Within five days after the initial communication with a consumer in connection with the collection of any debt, a debt collector shall, unless the following information is contained in the initial communication or the consumer has paid the debt, send the consumer a written notice containing—",
            context="15 U.S.C. § 1692g(a)",
            confidence=Confidence.HIGH,
        ),
        EvidenceItem(
            id="EV-LVNV-2",
            source=sources[3],
            claim_text="Collection notices must identify the creditor, the amount, and the consumer's right to dispute the debt.",
            confidence=Confidence.HIGH,
        ),
        EvidenceItem(
            id="EV-LVNV-3",
            source=sources[4],
            claim_text="LVNV letter appears to omit required validation details.",
            context="Alleged deficiency notice received by debtor describes an amount but lacks itemization and dispute instructions.",
            confidence=Confidence.MODERATE,
        ),
    ]
    for ev in evidence_items:
        orchestrator.add_evidence(ev, actor="AGENT-BLACKSTONE-2-0")
        claim.evidence.append(ev)

    orchestrator.add_claim(claim)

    counter = EvidenceItem(
        id="EV-LVNV-COUNTER-1",
        source=sources[4],
        claim_text="LVNV may have provided a full validation notice in a separate mailing.",
        context="Without the complete letter file, we cannot conclude the notice is deficient.",
        confidence=Confidence.LIMITED,
    )
    orchestrator.add_evidence(counter, actor="AGENT-BLACKSTONE-2-0")
    claim.counter_evidence.append(counter)

    orchestrator.add_risk(
        Risk(
            id="RISK-LVNV-STATUTE",
            category="litigation",
            description="One-year FDCPA statute of limitations may expire before filing suit; calendar immediately.",
            likelihood=Confidence.HIGH,
            impact=Confidence.HIGH,
            actor="AGENT-BLACKSTONE-2-0",
        )
    )
    orchestrator.add_risk(
        Risk(
            id="RISK-LVNV-REPORTING",
            category="credit_reporting",
            description="LVNV may be reporting the alleged debt to CRAs without proper furnisher investigation.",
            likelihood=Confidence.MODERATE,
            impact=Confidence.HIGH,
            actor="AGENT-BLACKSTONE-2-0",
        )
    )
    orchestrator.add_risk(
        Risk(
            id="RISK-LVNV-DOCS",
            category="documentation",
            description="Debtor must preserve envelope, letter, and any phone recordings; evidence gaps weaken claim.",
            likelihood=Confidence.HIGH,
            impact=Confidence.MODERATE,
            actor="AGENT-BLACKSTONE-2-0",
        )
    )

    result = orchestrator.evaluate(claim.id, question="Can the debtor assert a colorable FDCPA/FCRA claim against LVNV?", actor="AGENT-BLACKSTONE-2-0")
    return result, orchestrator


if __name__ == "__main__":
    result, _orch = evaluate_lvnv_deficiency()
    rec = result["recommendation"]
    print("=" * 70)
    print("Blackstone Case Evaluation: LVNV Funding Deficiency Notice")
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
