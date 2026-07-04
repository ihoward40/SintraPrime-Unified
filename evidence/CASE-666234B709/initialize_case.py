"""
Initialize CASE-666234B709 with known chronology and the deficiency notice.
Run once to populate the evidence repository with initial data.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from evidence_manager import (
    register_evidence,
    add_chronology_event,
    calculate_readiness,
    generate_case_packet,
)

# ── Chronology Events ────────────────────────────────────────────────

events = [
    {
        "date": "2025-08-31",
        "event": "Celtic Bank/Reflex account charged off (account ending 9370)",
        "category": "original_creditor",
        "notes": "Charge-off date per Resurgent's June 24, 2026 response",
    },
    {
        "date": "2026-01-27",
        "event": "Account acquired by LVNV Funding LLC",
        "category": "collection",
        "notes": "Acquisition date per Resurgent's response",
    },
    {
        "date": "2026-03-02",
        "event": "Alleged last payment date",
        "category": "payment_history",
        "notes": "Claimed by Resurgent — needs verification. No payment evidence provided.",
    },
    {
        "date": "2026-06-24",
        "event": "Resurgent Capital Services response received (reference 835167536)",
        "category": "correspondence_incoming",
        "notes": "6-page response with account summary and March 2025 billing statement. Did NOT include signed agreement, complete payment history, bill of sale, assignment chain, or custodian identification.",
    },
    {
        "date": "2026-07-02",
        "event": "Evidence repository established for CASE-666234B709",
        "category": "system",
        "notes": "Litigation-grade evidence repository created with immutable evidence IDs, SHA-256 hashing, and chain-of-custody metadata.",
    },
    {
        "date": "2026-07-03",
        "event": "Deficiency notice drafted for Resurgent portal submission",
        "category": "correspondence_outgoing",
        "notes": "Notice of Specific Deficiencies prepared. NOT YET SUBMITTED. External action locked pending approval.",
    },
]

for e in events:
    add_chronology_event(
        date=e["date"],
        event=e["event"],
        category=e["category"],
        notes=e["notes"],
    )
    print(f"Chronology: {e['date']} — {e['event']}")

print()

# ── Register Resurgent Response as Evidence ──────────────────────────

# The Resurgent response PDF
resurgent_pdf = Path(r"C:\Users\admin\Google Drive")
# Check if the PDF exists in common locations
pdf_locations = [
    Path.home() / "Downloads" / "Resurgent Capital for LVNV Funding.pdf",
    Path.home() / "Desktop" / "Resurgent Capital for LVNV Funding.pdf",
    Path.home() / "Documents" / "Resurgent Capital for LVNV Funding.pdf",
    Path(r"C:\Users\admin\Google Drive") / "Resurgent Capital for LVNV Funding.pdf",
]

resurgent_path = None
for p in pdf_locations:
    if p.exists():
        resurgent_path = p
        break

if resurgent_path:
    item = register_evidence(
        source_file=resurgent_path,
        evidence_type="pdf",
        title="Resurgent Capital response packet (June 24, 2026)",
        description="6-page response from Resurgent Capital Services re: Celtic Bank/Reflex account ending 9370, reference 835167536. Contains account summary and March 2025 billing statement.",
        source="Resurgent Capital Services L.P.",
        custodian="Isiah Howard",
        folder="10_Responses",
        date_of_event="2026-06-24",
        notes="Deficient response — missing signed agreement, complete payment history, bill of sale, assignment chain, and custodian identification.",
    )
    print(f"Evidence: {item['evidence_id']} — {item['title']}")
    print(f"  SHA-256: {item['sha256'][:32]}...")
    print(f"  Stored: {item['stored_path']}")
else:
    print("Resurgent PDF not found in common locations — will register as text placeholder")
    item = register_evidence(
        text_content="Resurgent Capital response packet received June 24, 2026. 6-page response with account summary and March 2025 billing statement. Reference 835167536. Physical/digital file to be imported.",
        evidence_type="record",
        title="Resurgent Capital response packet (June 24, 2026) — PLACEHOLDER",
        description="Placeholder record for Resurgent response. Source PDF to be imported when located.",
        source="Resurgent Capital Services L.P.",
        custodian="Isiah Howard",
        folder="10_Responses",
        date_of_event="2026-06-24",
        notes="PLACEHOLDER — import actual PDF to replace this record.",
    )
    print(f"Evidence: {item['evidence_id']} — {item['title']} (placeholder)")

print()

# ── Register Deficiency Notice as Evidence ───────────────────────────

deficiency_text = """NOTICE OF SPECIFIC DEFICIENCIES

Re: Celtic Bank/Reflex Account Ending 9370
Resurgent Reference: 835167536
Date: July 3, 2026

To: Resurgent Capital Services L.P. / LVNV Funding LLC

I continue to dispute the Celtic Bank/Reflex account ending 9370, Resurgent reference 835167536, including the amount claimed, LVNV Funding LLC's alleged ownership, and Resurgent Capital Services L.P.'s authority to collect.

Your June 24, 2026 response did not provide:

1. The signed application or complete cardmember agreement
2. Complete itemized transaction and payment history
3. Bill of sale and complete chain of assignment
4. Account-level transfer record identifying this specific account
5. Documentary proof of Resurgent's current collection authority
6. Records supporting the alleged March 2, 2025 last-payment date
7. Records custodian identification and basis of knowledge
8. Credit reporting status and dispute notation

Please provide those records, identify the records custodian and the basis of that person's knowledge, explain any discrepancies in the alleged payment information, and identify all credit bureaus receiving information about this account. Please ensure all reporting accurately states that the account is disputed.

This communication is not an acknowledgment of liability, a promise to pay, consent to restart any limitations period, or a waiver of any rights, claims, defenses, or objections.

Status: DRAFT — READY FOR USER REVIEW
External Submission: LOCKED
Approval Required: YES
"""

item2 = register_evidence(
    text_content=deficiency_text,
    evidence_type="draft",
    title="Notice of Specific Deficiencies — Resurgent/LVNV (DRAFT)",
    description="Deficiency notice demanding 8 categories of missing documentation from Resurgent Capital. Draft — not yet submitted. External action locked pending approval.",
    source="Isiah Howard (drafted with ChatGPT assistance)",
    custodian="Isiah Howard",
    folder="08_Drafts",
    date_of_event="2026-07-03",
    notes="DRAFT. Portal submission instructions prepared. Do not submit without explicit approval.",
)
print(f"Evidence: {item2['evidence_id']} — {item2['title']}")
print(f"  SHA-256: {item2['sha256'][:32]}...")
print(f"  Stored: {item2['stored_path']}")

# Link deficiency notice to chronology
add_chronology_event(
    date="2026-07-03",
    event="Deficiency notice registered as evidence (DRAFT — not submitted)",
    category="system",
    evidence_ids=[item2["evidence_id"]],
    notes=f"Registered as {item2['evidence_id']}. SHA-256: {item2['sha256'][:16]}...",
)

print()

# ── Generate Case Packet v1 ──────────────────────────────────────────

print("Generating case packet v1...")
packet = generate_case_packet()
print()
print("=" * 60)
print("CASE PACKET v1 GENERATED")
print("=" * 60)

# Print readiness
readiness = calculate_readiness()
print(f"Litigation Readiness: {readiness['overall_readiness']}% (Grade {readiness['grade']})")
print()
for cat, info in readiness["categories"].items():
    print(f"  {cat}: {info['score']}% — {info['detail']}")
print()
if readiness["missing_documents"]:
    print(f"Missing Documents ({readiness['missing_count']}):")
    for m in readiness["missing_documents"]:
        print(f"  - {m}")