"""
Live case script: IRS 3176C CNC case — apply the Blackstone governance framework to a live case.

This script demonstrates how AGENT-HERMES-2-0 and AGENT-BLACKSTONE-2-0 would
evaluate a real legal/financial question using the BRA engines.

Question: "Is Isiah Howard currently eligible for IRS Currently Not Collectible
status based on hardship?"

Run:
    python blackstone/cases/irs_3176c_cnc_case.py
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
    federal_us = Jurisdiction(name="United States", level="federal")

    orch = BlackstoneOrchestrator(
        agents=["AGENT-HERMES-2-0", "AGENT-BLACKSTONE-2-0"]
    )
    orch.register_jurisdiction(federal_us)

    sources = [
        Source(
            id="SRC-IRC-6321",
            citation="26 U.S.C. § 6321 (Federal Tax Lien)",
            classification=SourceClassification.PRIMARY_LEGAL,
            jurisdiction=federal_us,
            publisher="United States Code",
            url="https://www.govinfo.gov/content/pkg/USCODE-2023-title26/html/USCODE-2023-title26-subtitleF-chap64-subchapA-sec6321.htm",
        ),
        Source(
            id="SRC-IRM-5-16-1-2",
            citation="IRM 5.16.1.2 — Currently Not Collectible",
            classification=SourceClassification.SECONDARY_LEGAL,
            jurisdiction=federal_us,
            publisher="Internal Revenue Manual",
        ),
        Source(
            id="SRC-TBOR-2",
            citation="Taxpayer Bill of Rights, Right #2: Quality Service",
            classification=SourceClassification.SECONDARY_LEGAL,
            jurisdiction=federal_us,
            publisher="IRS",
        ),
        Source(
            id="SRC-NCLC",
            citation="NCLC, Surviving Debt, Ch. 13 — IRS Collection",
            classification=SourceClassification.SCHOLARLY,
            publisher="National Consumer Law Center",
        ),
    ]
    for s in sources:
        orch.register_source(s)

    claim = Claim(
        id="CLAIM-IRS-3176C-CNC-2026",
        text="Isiah Howard is eligible for IRS Currently Not Collectible (CNC) status due to financial hardship, homelessness, Medicaid eligibility, and credit insufficiency, despite the existence of a federal tax lien under 26 U.S.C. § 6321.",
        subject="IRS_CNC_hardship",
        jurisdiction=federal_us,
        assumptions=[
            "Taxpayer income is below allowable living expenses per IRS standards.",
            "Taxpayer has no significant assets available to satisfy the liability.",
        ],
        missing_evidence=[
            "Completed Form 433-A or 433-F.",
            "Recent bank statements (last 3 months).",
            "Proof of income and necessary living expenses.",
            "Verification of homelessness and Medicaid status.",
        ],
        tags=["IRS", "CNC", "3176C", "hardship", "tax_lien", "Medicaid"],
    )

    evidence_items = [
        EvidenceItem(
            id="EV-IRS-1",
            source=sources[1],
            claim_text="IRS may classify an account as currently not collectible when the taxpayer cannot pay reasonable living expenses.",
            confidence=Confidence.HIGH,
        ),
        EvidenceItem(
            id="EV-IRS-2",
            source=sources[0],
            claim_text="Federal tax lien arises automatically by operation of law upon assessment and demand, regardless of CNC status.",
            confidence=Confidence.HIGH,
        ),
        EvidenceItem(
            id="EV-IRS-3",
            source=sources[3],
            claim_text="CNC status can protect a low-income taxpayer from levy while the account remains in uncollectible status.",
            confidence=Confidence.MODERATE,
        ),
        EvidenceItem(
            id="EV-IRS-4",
            source=sources[2],
            claim_text="Taxpayer has a right to clear explanations and assistance when resolving collection issues.",
            confidence=Confidence.MODERATE,
        ),
    ]
    for ev in evidence_items:
        orch.add_evidence(ev, actor="AGENT-BLACKSTONE-2-0")
        claim.evidence.append(ev)

    counter = EvidenceItem(
        id="EV-IRS-COUNTER-1",
        source=sources[0],
        claim_text="A federal tax lien may already be on file, and CNC does not automatically release it; the taxpayer remains subject to future collection if assets attach.",
        confidence=Confidence.HIGH,
    )
    orch.add_evidence(counter, actor="AGENT-BLACKSTONE-2-0")
    claim.counter_evidence.append(counter)

    orch.add_claim(claim)

    risks = [
        Risk(
            id="RISK-IRS-DOCS",
            category="documentation",
            description="Bank statements and Collection Information Statement not yet collected; eligibility cannot be confirmed without them.",
            likelihood=Confidence.HIGH,
            impact=Confidence.HIGH,
            controls=["upload bank statements", "complete Form 433-A/433-F"],
            actor="AGENT-BLACKSTONE-2-0",
        ),
        Risk(
            id="RISK-IRS-LIEN",
            category="collection",
            description="Federal tax lien may already exist or be filed while CNC request is pending.",
            likelihood=Confidence.MODERATE,
            impact=Confidence.HIGH,
            controls=["request account transcript", "file CNC immediately"],
            actor="AGENT-BLACKSTONE-2-0",
        ),
        Risk(
            id="RISK-IRS-PRIVACY",
            category="privacy",
            description="Taxpayer identifying information and financial records must be protected under least-privilege and audit-logging rules.",
            likelihood=Confidence.MODERATE,
            impact=Confidence.MODERATE,
            controls=["encrypt at rest", "access log", "tenant isolation"],
            actor="AGENT-BLACKSTONE-2-0",
        ),
    ]
    for r in risks:
        orch.add_risk(r)

    return orch, claim.id


if __name__ == "__main__":
    orch, claim_id = build_case()
    result = orch.evaluate(
        claim_id,
        question="Should the taxpayer file an IRS Currently Not Collectible request immediately?",
        actor="AGENT-BLACKSTONE-2-0",
    )
    rec = result["recommendation"]
    print("=" * 70)
    print("Blackstone Case Evaluation: IRS 3176C Currently Not Collectible")
    print("=" * 70)
    print(f"Claim status: {result['claim']['status']}")
    print(f"Confidence:   {result['claim']['confidence']}")
    print(f"Controlling authority: {result['authority']['controlling_authority']}")
    print(f"Conflicts:    {result['authority']['conflicts']}")
    print(f"Risks ({len(result['risks'])}):")
    for r in result["risks"]:
        print(f"  - [{r['category']}] {r['description']} (score={r['score']})")
    print("-" * 70)
    print(f"Recommendation: {rec['recommendation']}")
    print(f"Rationale:      {rec['rationale']}")
    print("-" * 70)
    print(f"Agents:          {', '.join(rec['agents'])}")
    print(f"Provenance verified: {result['provenance']['verified']}")
    print("=" * 70)
