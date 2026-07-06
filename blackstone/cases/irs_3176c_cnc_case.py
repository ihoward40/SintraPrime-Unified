"""
IRS 3176C CNC case — apply the Blackstone governance framework to a live case.

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


def main() -> None:
    federal_us = Jurisdiction(name="United States", level="federal")

    orch = BlackstoneOrchestrator(agents=["AGENT-HERMES-2-0", "AGENT-BLACKSTONE-2-0"])
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
            citation="IRM 5.16.1.2, Currently Not Collectible",
            classification=SourceClassification.PRIMARY_LEGAL,
            jurisdiction=federal_us,
            publisher="Internal Revenue Manual",
            url="https://www.irs.gov/irm/part5/irm_05-016-001",
        ),
        Source(
            id="SRC-TBOR-2",
            citation="Taxpayer Bill of Rights, Right to Challenge and Be Heard",
            classification=SourceClassification.SECONDARY_LEGAL,
            jurisdiction=federal_us,
            publisher="Internal Revenue Service",
            url="https://www.irs.gov/taxpayer-bill-of-rights",
        ),
        Source(
            id="SRC-NCLC",
            citation="National Consumer Law Center, Surviving Debt",
            classification=SourceClassification.SCHOLARLY,
            publisher="NCLC",
            url="https://www.nclc.org/",
        ),
    ]
    for source in sources:
        orch.register_source(source)

    claim = Claim(
        id="CLAIM-3176C-CNC",
        text="Taxpayer is eligible for Currently Not Collectible status based on economic hardship.",
        subject="irs_cnc_hardship",
        jurisdiction=federal_us,
        assumptions=[
            "Taxpayer has filed all required returns or is in compliance arrangement.",
            "Collection Information Statement will substantiate income/expense figures.",
            "Liquid asset equity is below allowable threshold.",
        ],
        missing_evidence=[
            "Completed Form 433-A or 433-F.",
            "Recent bank statements (last 3 months).",
            "Proof of income and necessary living expenses.",
            "Verification of homelessness and Medicaid status.",
        ],
    )

    evidence_items = [
        EvidenceItem(
            id="EV-IRC-6321",
            source=next(s for s in sources if s.id == "SRC-IRC-6321"),
            claim_text="IRS has a general lien for assessed taxes, but collection action can be suspended when collection would create hardship.",
            quotation="If any person liable to pay any tax neglects or refuses to pay the same after demand, the amount ... shall be a lien in favor of the United States upon all property and rights to property.",
            context="General lien statute; hardship suspension is an administrative practice under IRM and IRC § 6343(a)(1)(D).",
            confidence=Confidence.HIGH,
        ),
        EvidenceItem(
            id="EV-IRM-5-16-1-2",
            source=next(s for s in sources if s.id == "SRC-IRM-5-16-1-2"),
            claim_text="Currently Not Collectible status is available when taxpayer has no ability to pay and collection would cause economic hardship.",
            quotation="Economic hardship occurs when a taxpayer is unable to pay reasonable basic living expenses.",
            context="IRS internal guidance; not controlling statute but primary administrative authority for CNC determinations.",
            confidence=Confidence.MODERATE,
        ),
        EvidenceItem(
            id="EV-TBOR-2",
            source=next(s for s in sources if s.id == "SRC-TBOR-2"),
            claim_text="Taxpayer has the right to challenge IRS position and be heard.",
            quotation="Taxpayers have the right to raise objections and provide additional documentation in response to formal IRS actions or proposed actions.",
            context="Supports procedural fairness but does not establish CNC eligibility.",
            confidence=Confidence.MODERATE,
        ),
        EvidenceItem(
            id="EV-NCLC",
            source=next(s for s in sources if s.id == "SRC-NCLC"),
            claim_text="Low-income taxpayers facing hardship should request CNC status and provide documentation of income and expenses.",
            quotation="Currently Not Collectible status can stop collection for taxpayers whose income is below allowable living expenses.",
            context="Consumer-advocacy reference; not binding authority.",
            confidence=Confidence.LIMITED,
        ),
    ]

    for ev in evidence_items:
        orch.add_evidence(ev, actor="AGENT-BLACKSTONE-2-0")
        claim.evidence.append(ev)

    # A credible counter-position: CNC is discretionary and requires full financial disclosure.
    counter_source = Source(
        id="SRC-IRM-DISC",
        citation="IRM 5.16.1.2, Discretionary Determination",
        classification=SourceClassification.PRIMARY_LEGAL,
        jurisdiction=federal_us,
        publisher="Internal Revenue Manual",
    )
    orch.register_source(counter_source)
    counter_evidence = EvidenceItem(
        id="EV-COUNTER-CNC",
        source=counter_source,
        claim_text="CNC is not automatic; IRS may deny if future income collection potential exists or financial documentation is incomplete.",
        confidence=Confidence.MODERATE,
    )
    orch.add_evidence(counter_evidence, actor="AGENT-BLACKSTONE-2-0")
    claim.counter_evidence.append(counter_evidence)

    orch.add_claim(claim)

    orch.add_risk(
        Risk(
            id="RISK-3176C-DOCS",
            category="documentation",
            description="Bank statements and Collection Information Statement not yet collected; eligibility cannot be confirmed without them.",
            likelihood=Confidence.HIGH,
            impact=Confidence.HIGH,
            owner="AGENT-HERMES-2-0",
        )
    )
    orch.add_risk(
        Risk(
            id="RISK-3176C-LIEN",
            category="collection",
            description="Federal tax lien may already exist or be filed while CNC request is pending.",
            likelihood=Confidence.MODERATE,
            impact=Confidence.HIGH,
            owner="AGENT-SINTRAPRIME-2-0",
        )
    )
    orch.add_risk(
        Risk(
            id="RISK-3176C-SSN",
            category="privacy",
            description="Taxpayer identifying information and financial records must be protected under least-privilege and audit-logging rules.",
            likelihood=Confidence.MODERATE,
            impact=Confidence.MODERATE,
            owner="AGENT-HERMES-2-0",
        )
    )

    # Tag the claim with risk-relevant terms so the RiskEngine links them.
    claim.tags = ["documentation", "collection", "privacy", "irs_cnc_hardship"]

    result = orch.evaluate(
        "CLAIM-3176C-CNC",
        question="Is the taxpayer eligible for IRS Currently Not Collectible status based on hardship?",
        actor="AGENT-BLACKSTONE-2-0",
    )

    print("=" * 72)
    print("Blackstone Case Evaluation: IRS 3176C Currently Not Collectible")
    print("=" * 72)
    print(f"Claim status: {result['claim']['status']}")
    print(f"Confidence:   {result['claim']['confidence']}")
    print(f"Controlling authority: {result['authority']['controlling_authority']}")
    print(f"Conflicts:    {result['authority']['conflicts']}")
    print(f"Risks ({len(result['risks'])}):")
    for risk in result["risks"]:
        print(f"  - [{risk['category']}] {risk['description']} (score={risk['likelihood']} x {risk['impact']})")
    print("-" * 72)
    print(f"Recommendation: {result['recommendation']['recommendation']}")
    print(f"Rationale:      {result['recommendation']['rationale']}")
    print("-" * 72)
    print("Agents:         ", ", ".join(result["recommendation"]["agents"]))
    print("Provenance verified:", result["provenance"]["verified"])
    print("=" * 72)


if __name__ == "__main__":
    main()
