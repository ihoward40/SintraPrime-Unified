"""
Populate v2.1.0 features for CASE-666234B709:
- Decision ledger
- Contradiction detection
- Evidence sufficiency rules
Then regenerate packet with all new sections.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from case_template import CaseTemplate, KERNEL_VERSION

case = CaseTemplate(
    case_id="CASE-666234B709",
    case_name="Halsted / LVNV / Bank of Missouri / Milestone",
    evidence_counter_start=420,
    description="Celtic Bank/Reflex account ending 9370. LVNV acquisition. Resurgent collection.",
    priority="high",
    external_action="locked",
)

# Enable module
case.enable_module("debt_collection")

# ── Decision Ledger ──────────────────────────────────────────────────

decisions = [
    {
        "question": "Should a deficiency notice be sent to Resurgent Capital?",
        "decision": "Yes",
        "reason": "Resurgent's June 24, 2026 response is deficient under FDCPA 1692g. Missing 8 categories of documentation including signed agreement, assignment chain, and custodian identification.",
        "inputs": ["LEG-0001"],
        "alternatives_considered": ["Wait for CFPB response", "Accept the verification as adequate", "Send a simpler dispute letter"],
        "decision_date": "2026-07-03",
        "author": "ChatGPT (strategic reviewer) + Hermes (chief of staff)",
        "notes": "Deficiency notice drafted as EV-2026-00421. External submission locked pending Isiah's approval.",
    },
    {
        "question": "Should we submit via Resurgent's online portal or mail?",
        "decision": "Portal submission (electronic)",
        "reason": "Resurgent's packet directs consumers to the online portal. Electronic delivery is faster, free, and creates a timestamped confirmation.",
        "inputs": ["EV-2026-00420"],
        "alternatives_considered": ["Certified mail", "Regular mail", "Fax"],
        "decision_date": "2026-07-03",
        "author": "ChatGPT",
        "notes": "Must select Celtic Bank/Reflex account ending 9370 in portal, NOT Bank of Missouri accounts. Take screenshots of submission.",
    },
    {
        "question": "Should we acknowledge the debt or make any payment?",
        "decision": "No",
        "reason": "Acknowledging the debt or making a payment could restart the statute of limitations. The deficiency notice explicitly states this is not an acknowledgment.",
        "inputs": ["LEG-0001", "AUTH-0001"],
        "alternatives_considered": ["Accept settlement offer", "Make partial payment", "Set up payment plan"],
        "decision_date": "2026-07-03",
        "author": "ChatGPT",
        "notes": "Do not enter payment information, accept settlement, or click anything acknowledging liability.",
    },
]

for d in decisions:
    entry = case.add_decision(**d)
    print(f"Decision: {entry['decision_id']} - {entry['decision']}")

# ── Contradiction Detection ──────────────────────────────────────────

contras = case.detect_contradictions()
print(f"Contradictions detected: {len(contras)}")

# ── Evidence Sufficiency Rules ───────────────────────────────────────

rules = [
    {
        "rule_name": "Ownership Established",
        "claim_description": "LVNV Funding LLC legally owns the Celtic Bank/Reflex account ending 9370",
        "required_documents": ["Bill of sale", "Assignment chain", "Account-level transfer record"],
        "minimum_required": 3,
        "notes": "All 3 required for ownership to be established. Currently 0 of 3 held.",
    },
    {
        "rule_name": "Balance Verified",
        "claim_description": "The claimed balance of $2,121.52 is accurate",
        "required_documents": ["Complete itemized transaction history", "Complete payment history", "Original creditor statement"],
        "minimum_required": 2,
        "notes": "At least 2 of 3 required. Currently 1 of 3 (March 2025 billing statement).",
    },
    {
        "rule_name": "Collection Authority Established",
        "claim_description": "Resurgent Capital Services has authority to collect this debt",
        "required_documents": ["Servicing agreement", "Collection authority documentation", "Records custodian identification"],
        "minimum_required": 2,
        "notes": "At least 2 of 3 required. Currently 0 of 3.",
    },
    {
        "rule_name": "FDCPA Validation Satisfied",
        "claim_description": "Resurgent's response satisfies FDCPA 1692g validation requirements",
        "required_documents": ["Signed cardmember agreement", "Complete payment history", "Bill of sale", "Assignment chain", "Custodian affidavit"],
        "minimum_required": 4,
        "notes": "4 of 5 required for adequate validation. Currently 1 of 5 (account summary only).",
    },
]

for r in rules:
    entry = case.add_sufficiency_rule(**r)
    print(f"Rule: {entry['rule_id']} - {entry['rule_name']}")

# Evaluate sufficiency
print()
print("Sufficiency evaluation:")
evals = case.evaluate_sufficiency()
for e in evals:
    status = "SATISFIED" if e["satisfied"] else "NOT SATISFIED"
    print(f"  {e['rule_id']}: {e['rule_name']} - {e['found_count']}/{e['minimum_required']} - {status}")

# ── Generate packet v001 with all v2.1.0 sections ───────────────────
print()
print("Generating packet v001 (v2.1.0 format)...")
packet = case.generate_packet()
print("Packet generated")

print()
print(case.status())