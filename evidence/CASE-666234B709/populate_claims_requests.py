"""
Populate claim ledger and evidence request register for CASE-666234B709.
Run once to initialize the reference implementation with structured data.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from evidence_manager import (
    add_claim,
    add_evidence_request,
    calculate_readiness,
    generate_case_packet,
)

# ── Claims ───────────────────────────────────────────────────────────

claims = [
    {
        "claim_text": "LVNV Funding LLC owns the Celtic Bank/Reflex account ending 9370",
        "claim_type": "factual",
        "supporting_evidence_ids": ["EV-2026-00420"],
        "status": "partially_supported",
        "missing": "Bill of sale, complete assignment chain, account-level transfer record",
        "notes": "Resurgent's response claims LVNV acquired the account on Jan 27, 2026, but provides no assignment chain documentation.",
    },
    {
        "claim_text": "The claimed balance of $2,121.52 is accurate",
        "claim_type": "factual",
        "supporting_evidence_ids": ["EV-2026-00420"],
        "status": "partially_supported",
        "missing": "Complete itemized transaction and payment history",
        "notes": "Resurgent provided an account summary and March 2025 billing statement, but not complete payment history.",
    },
    {
        "claim_text": "Resurgent Capital Services has authority to collect this debt",
        "claim_type": "factual",
        "supporting_evidence_ids": ["EV-2026-00420"],
        "status": "partially_supported",
        "missing": "Documentary proof of current servicing/collection authority",
        "notes": "Resurgent's letter implies authority but does not provide a servicing agreement or assignment documentation.",
    },
    {
        "claim_text": "A payment was made on March 2, 2025",
        "claim_type": "factual",
        "supporting_evidence_ids": ["EV-2026-00420"],
        "status": "partially_supported",
        "missing": "Records supporting the alleged last-payment date",
        "notes": "Claimed by Resurgent — no payment record provided. Needs verification. Could affect statute of limitations.",
    },
    {
        "claim_text": "The account was charged off on August 31, 2025",
        "claim_type": "factual",
        "supporting_evidence_ids": ["EV-2026-00420"],
        "status": "partially_supported",
        "missing": "Original creditor charge-off documentation",
        "notes": "Stated in Resurgent's response. Needs verification with original creditor records.",
    },
    {
        "claim_text": "The account is being reported as disputed to credit bureaus",
        "claim_type": "factual",
        "supporting_evidence_ids": [],
        "status": "unsupported",
        "missing": "Credit reporting status documentation, bureau dispute confirmations",
        "notes": "No evidence that the account is being reported as disputed. This is a FCRA compliance concern.",
    },
    {
        "claim_text": "Resurgent's June 24, 2026 response constitutes adequate debt validation under FDCPA 1692g",
        "claim_type": "legal",
        "supporting_evidence_ids": ["EV-2026-00420"],
        "status": "unsupported",
        "missing": "Signed agreement, complete payment history, assignment chain",
        "notes": "The response is deficient under FDCPA validation requirements. Missing 8 categories of documentation.",
    },
]

for c in claims:
    entry = add_claim(
        claim_text=c["claim_text"],
        claim_type=c["claim_type"],
        supporting_evidence_ids=c["supporting_evidence_ids"],
        status=c["status"],
        missing=c["missing"],
        notes=c["notes"],
    )
    print(f"Claim: {entry['claim_id']} — {entry['status']} — {entry['claim'][:60]}")

print()

# ── Evidence Requests ────────────────────────────────────────────────

requests = [
    {"doc": "Signed application/cardmember agreement", "frm": "Resurgent Capital Services"},
    {"doc": "Complete itemized transaction and payment history", "frm": "Resurgent Capital Services"},
    {"doc": "Bill of sale and complete chain of assignment", "frm": "LVNV Funding LLC"},
    {"doc": "Account-level transfer record identifying this account", "frm": "LVNV Funding LLC"},
    {"doc": "Documentary proof of Resurgent's current collection authority", "frm": "Resurgent Capital Services"},
    {"doc": "Records supporting alleged March 2, 2025 last-payment date", "frm": "Resurgent Capital Services"},
    {"doc": "Records custodian identification and basis of knowledge", "frm": "Resurgent Capital Services"},
    {"doc": "Credit reporting status and dispute notation", "frm": "Resurgent Capital Services"},
]

for r in requests:
    entry = add_evidence_request(
        document_requested=r["doc"],
        requested_from=r["frm"],
        date_requested="2026-07-03",
        status="outstanding",
        notes="Requested via deficiency notice (EV-2026-00421). Not yet submitted — awaiting approval.",
    )
    print(f"Request: {entry['request_id']} — {entry['status']} — {entry['document_requested'][:60]}")

print()

# ── Regenerate Case Packet v2 ────────────────────────────────────────

print("Regenerating case packet v2 with claims and requests...")
packet = generate_case_packet()
print()

# Print updated readiness
readiness = calculate_readiness()
print(f"Overall: {readiness['overall_readiness']}% (Grade {readiness['grade']})")
print(f"Repository Completeness: {readiness['repository_completeness']['score']}%")
print(f"Evidentiary Strength: {readiness['evidentiary_strength']['score']}%")
print(f"  Claims: {readiness['evidentiary_strength']['total_claims']} ({readiness['evidentiary_strength']['supported']} supported, {readiness['evidentiary_strength']['partially_supported']} partial, {readiness['evidentiary_strength']['unsupported']} unsupported)")
print(f"  Requests: {readiness['evidence_requests']['total']} ({readiness['evidence_requests']['outstanding']} outstanding)")