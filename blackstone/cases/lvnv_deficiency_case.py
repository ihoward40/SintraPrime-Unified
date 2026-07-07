"""
Live case script: LVNV Funding LLC deficiency notice dispute.

This script demonstrates the Blackstone BRA engines applied to a real consumer
protection case: a debt collector's deficiency notice that may violate FDCPA
and FCRA requirements.
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


def build_case() -> BlackstoneOrchestrator:
    orchestrator = BlackstoneOrchestrator(
        agents=["AGENT-HERMES-2-0", "AGENT-BLACKSTONE-2-0"]
    )
    orchestrator.register_jurisdiction(
        Jurisdiction(name="United States", level="federal")
    )

    fdcpa = Source(
        id="src-fdcpa",
        citation="15 U.S.C. § 1692g — Validation of debts",
        classification=SourceClassification.PRIMARY_LEGAL,
        publisher="United States Code",
        url="https://www.law.cornell.edu/uscode/text/15/1692g",
    )
    frca = Source(
        id="src-fcra",
        citation="15 U.S.C. § 1681e(b) — Accuracy of consumer reports",
        classification=SourceClassification.PRIMARY_LEGAL,
        publisher="United States Code",
    )
    cfpb = Source(
        id="src-cfpb",
        citation="CFPB Circular 2022-04 — Furnisher information accuracy",
        classification=SourceClassification.SECONDARY_LEGAL,
        publisher="Consumer Financial Protection Bureau",
    )
    letter = Source(
        id="src-letter",
        citation="LVNV Funding deficiency notice dated 2026-06-15",
        classification=SourceClassification.PRIVATE_PUBLISHED,
        publisher="LVNV Funding LLC",
    )
    credit_report = Source(
        id="src-credit",
        citation="TransUnion credit report showing LVNV tradeline",
        classification=SourceClassification.PRIVATE_PUBLISHED,
        publisher="TransUnion",
    )

    for s in [fdcpa, frca, cfpb, letter, credit_report]:
        orchestrator.register_source(s)

    evidence = [
        EvidenceItem(
            id="ev-1",
            source=fdcpa,
            claim_text="FDCPA requires a debt collector to provide written notice with the amount of debt, creditor name, and validation rights within five days of initial communication.",
            quotation="A debt collector shall, within five days after the initial communication with a consumer, send the consumer a written notice containing the amount of the debt, the name of the creditor to whom the debt is owed, and a statement that the consumer may dispute the debt.",
            confidence=Confidence.HIGH,
        ),
        EvidenceItem(
            id="ev-2",
            source=letter,
            claim_text="LVNV's deficiency notice does not identify the original creditor and omits the 30-day validation notice.",
            quotation="The letter lists 'Balance: $4,217.88' and 'Creditor: LVNV Funding LLC' but does not name the original creditor or include a validation notice.",
            confidence=Confidence.HIGH,
        ),
        EvidenceItem(
            id="ev-3",
            source=credit_report,
            claim_text="The LVNV tradeline reports an account opened date after the alleged charge-off date, suggesting inaccurate furnisher reporting.",
            quotation="Account opened: 2024-02; date of first delinquency: 2023-08; charge-off: 2023-11.",
            confidence=Confidence.MODERATE,
        ),
        EvidenceItem(
            id="ev-4",
            source=cfpb,
            claim_text="CFPB guidance requires furnishers to report accurate information and investigate disputes.",
            quotation="Furnishers must establish and implement reasonable written policies and procedures regarding the accuracy and integrity of information furnished.",
            confidence=Confidence.HIGH,
        ),
    ]

    for e in evidence:
        orchestrator.add_evidence(e, actor="AGENT-BLACKSTONE-2-0")

    claim = Claim(
        id="claim-lvnv-001",
        text="LVNV Funding LLC's deficiency notice violates FDCPA § 1692g by failing to identify the original creditor and omitting the validation notice, and its credit reporting violates FCRA § 1681e(b) because the tradeline contains inconsistent dates.",
        subject="LVNV Funding deficiency notice / credit reporting",
        assumptions=[
            "The consumer did not receive any prior validation notice.",
            "The dates on the credit report are as reported by LVNV's furnisher.",
        ],
        missing_evidence=[
            "Certified mail receipt for the deficiency notice.",
            "Debt validation request and LVNV's response.",
            "Original creditor account statements or assignment documents.",
        ],
        tags=["lvnv", "fdcpa", "fcra", "debt-collection", "deficiency"],
    )
    for e in evidence:
        claim.evidence.append(e)

    orchestrator.add_claim(claim)

    orchestrator.add_risk(
        Risk(
            id="risk-lvnv-001",
            category="litigation",
            description="Statute of limitations may bar FDCPA claim if the letter was sent more than one year ago.",
            likelihood=Confidence.LIMITED,
            impact=Confidence.HIGH,
            controls=["verify date of letter", "check state SOL for FDCPA"],
            owner="AGENT-BLACKSTONE-2-0",
            actor="AGENT-BLACKSTONE-2-0",
            tags=["lvnv", "fdcpa", "sol"],
        )
    )

    return orchestrator, claim.id


if __name__ == "__main__":
    orchestrator, claim_id = build_case()
    result = orchestrator.evaluate(
        claim_id,
        question="Should we dispute this LVNV deficiency notice and file an FCRA/FDCPA challenge?",
        actor="AGENT-BLACKSTONE-2-0",
    )

    print("Recommendation:", result["recommendation"]["recommendation"])
    print("Rationale:", result["recommendation"]["rationale"])
    print("Confidence:", result["claim"]["confidence"])
    print("Status:", result["claim"]["status"])
    print("Risks:")
    for r in result.get("risks", []):
        print(f"  - {r['description']} (impact={r['impact']}, likelihood={r['likelihood']})")
    print("Provenance verified:", result["provenance"]["verified"])
    print("Chain length:", result["provenance"]["chain_length"])
