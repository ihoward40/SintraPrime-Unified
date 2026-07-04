"""
Migrate CASE-666234B709 from the old evidence_manager format to CaseTemplate.
Separates the old claim_ledger into fact_ledger + legal_analysis_ledger,
adds authority_ledger, and builds evidence dependency graphs.
Also preserves immutable packet versions.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from case_template import CaseTemplate

CASE_ID = "CASE-666234B709"
CASE_NAME = "Halsted / LVNV / Bank of Missouri / Milestone"
CASE_DIR = Path(r"C:\Users\admin\Desktop\SintraPrime-Unified\evidence") / CASE_ID

# Create CaseTemplate instance
case = CaseTemplate(
    case_id=CASE_ID,
    case_name=CASE_NAME,
    evidence_counter_start=420,
    description="Celtic Bank/Reflex account ending 9370. LVNV acquisition. Resurgent collection.",
    priority="high",
    external_action="locked",
)

# ── Migrate evidence items from old registry ─────────────────────────
old_reg = json.load(open(CASE_DIR / "evidence_registry.json", "r", encoding="utf-8"))
# The CaseTemplate initialized a fresh registry. We need to overwrite it with old data.
# But the old data already has the items. Just copy the registry over.
case._save_json(case.registry_path, old_reg)
print(f"Migrated {len(old_reg['evidence_items'])} evidence items")

# ── Migrate chronology ───────────────────────────────────────────────
old_chron = json.load(open(CASE_DIR / "chronology.json", "r", encoding="utf-8"))
case._save_json(case.chronology_path, old_chron)
print(f"Migrated {len(old_chron['events'])} chronology events")

# ── Split old claim_ledger into facts + legal analyses ───────────────
old_claims = json.load(open(CASE_DIR / "claim_ledger.json", "r", encoding="utf-8"))

for c in old_claims["claims"]:
    # Determine confidence based on status and evidence
    if c["status"] == "supported":
        confidence = "high"
    elif c["status"] == "partially_supported":
        confidence = "moderate"
    else:
        confidence = "low"

    if c["claim_type"] == "legal":
        entry = case.add_legal_analysis(
            analysis_text=c["claim"],
            supporting_evidence_ids=c["supporting_evidence_ids"],
            status=c["status"],
            confidence=confidence,
            conclusion=c["notes"],
            notes=c["missing"],
        )
        print(f"Legal: {entry['analysis_id']} - {entry['status']} ({entry['confidence']})")
    else:
        entry = case.add_fact(
            fact_text=c["claim"],
            supporting_evidence_ids=c["supporting_evidence_ids"],
            status=c["status"],
            confidence=confidence,
            missing=c["missing"],
            notes=c["notes"],
        )
        print(f"Fact: {entry['fact_id']} - {entry['status']} ({entry['confidence']})")

# ── Migrate evidence requests ────────────────────────────────────────
old_reqs = json.load(open(CASE_DIR / "evidence_request_register.json", "r", encoding="utf-8"))
case._save_json(case.request_register_path, old_reqs)
print(f"Migrated {len(old_reqs['requests'])} evidence requests")

# ── Add Authority Ledger ─────────────────────────────────────────────

authorities = [
    {
        "authority": "FDCPA Section 1692g - Validation of Debts",
        "citation": "15 U.S.C. 1692g",
        "supports": ["LEG-0001"],
        "status": "applicable",
        "quoted": False,
        "notes": "Requires debt collector to provide name of creditor, amount of debt, and statement that consumer disputes within 30 days. Resurgent's response is deficient under this section.",
    },
    {
        "authority": "FDCPA Section 1692e - False or Misleading Representations",
        "citation": "15 U.S.C. 1692e",
        "supports": [],
        "status": "potentially_applicable",
        "quoted": False,
        "notes": "Prohibits false or misleading representations in debt collection. May apply if Resurgent misrepresents the debt or its authority.",
    },
    {
        "authority": "FCRA - Accuracy and Dispute Requirements",
        "citation": "15 U.S.C. 1681",
        "supports": [],
        "status": "applicable",
        "quoted": False,
        "notes": "Requires accurate credit reporting. Account should be reported as disputed. Potential FCRA violation if not.",
    },
    {
        "authority": "UCC Article 9 - Secured Transactions",
        "citation": "UCC Article 9",
        "supports": [],
        "status": "potentially_applicable",
        "quoted": False,
        "notes": "Governs assignment of debts. Requires valid chain of assignment. LVNV has not provided bill of sale or assignment chain.",
    },
]

for a in authorities:
    entry = case.add_authority(
        authority=a["authority"],
        citation=a["citation"],
        supports=a["supports"],
        status=a["status"],
        quoted=a["quoted"],
        notes=a["notes"],
    )
    print(f"Authority: {entry['authority_id']} - {entry['citation']}")

# ── Build Evidence Dependency Graphs ─────────────────────────────────

# Load the fact/legal ledgers to get IDs
facts = case._load_json(case.fact_ledger_path)
legal = case._load_json(case.legal_ledger_path)
reqs = case._load_json(case.request_register_path)

# Map request descriptions to IDs
req_map = {r["document_requested"]: r["request_id"] for r in reqs["requests"]}

dependencies = [
    {
        "claim_id": facts["facts"][0]["fact_id"],  # FCT-0001: LVNV ownership
        "claim_text": "LVNV Funding LLC owns the Celtic Bank/Reflex account ending 9370",
        "required_evidence": ["Bill of sale", "Assignment chain", "Account-level transfer record"],
        "current_evidence": ["EV-2026-00420"],
        "outstanding_requests": [
            req_map.get("Bill of sale and complete chain of assignment", ""),
            req_map.get("Account-level transfer record identifying this account", ""),
        ],
    },
    {
        "claim_id": facts["facts"][1]["fact_id"],  # FCT-0002: Balance accuracy
        "claim_text": "The claimed balance of $2,121.52 is accurate",
        "required_evidence": ["Complete itemized transaction history", "Complete payment history"],
        "current_evidence": ["EV-2026-00420"],
        "outstanding_requests": [req_map.get("Complete itemized transaction and payment history", "")],
    },
    {
        "claim_id": facts["facts"][2]["fact_id"],  # FCT-0003: Resurgent authority
        "claim_text": "Resurgent Capital Services has authority to collect this debt",
        "required_evidence": ["Servicing agreement", "Collection authority documentation"],
        "current_evidence": ["EV-2026-00420"],
        "outstanding_requests": [req_map.get("Documentary proof of Resurgent's current collection authority", "")],
    },
    {
        "claim_id": legal["analyses"][0]["analysis_id"],  # LEG-0001: FDCPA validation
        "claim_text": "Resurgent's June 24, 2026 response constitutes adequate debt validation under FDCPA 1692g",
        "required_evidence": ["Signed agreement", "Complete payment history", "Assignment chain", "Custodian affidavit"],
        "current_evidence": ["EV-2026-00420"],
        "outstanding_requests": [
            req_map.get("Signed application/cardmember agreement", ""),
            req_map.get("Records custodian identification and basis of knowledge", ""),
        ],
    },
]

for d in dependencies:
    entry = case.add_dependency(
        claim_id=d["claim_id"],
        claim_text=d["claim_text"],
        required_evidence=d["required_evidence"],
        current_evidence=d["current_evidence"],
        outstanding_requests=d["outstanding_requests"],
    )
    print(f"Dependency: {entry['claim_id']} - gap={entry['gap_count']}")

# ── Generate Packet v001 (immutable) ─────────────────────────────────
print()
print("Generating case packet v001...")
packet = case.generate_packet()
print(f"Packet v001 generated")

# Print final status
print()
print(case.status())