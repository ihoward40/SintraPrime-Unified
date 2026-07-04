"""
Litigation-Grade Evidence Repository for CASE-666234B709
Halsted / LVNV / Bank of Missouri / Milestone (Celtic Bank/Reflex ending 9370)

Provides:
- Immutable evidence IDs (EV-2026-NNNNN format)
- SHA-256 hashing for every file
- Chain-of-custody metadata
- Chronology tracking
- Litigation readiness scoring
- Case packet generation
"""

import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── Configuration ────────────────────────────────────────────────────

CASE_ID = "CASE-666234B709"
CASE_NAME = "Halsted / LVNV / Bank of Missouri / Milestone"
EVIDENCE_BASE = Path(r"C:\Users\admin\Desktop\SintraPrime-Unified\evidence")
CASE_DIR = EVIDENCE_BASE / CASE_ID
REGISTRY_PATH = CASE_DIR / "evidence_registry.json"
CHRONOLOGY_PATH = CASE_DIR / "chronology.json"
READINESS_PATH = CASE_DIR / "readiness_score.json"

FOLDER_MAP = {
    "01_Intake": "Intake and initial case documentation",
    "02_Credit_Reports": "Credit bureau reports and tradeline screenshots",
    "03_Original_Creditor": "Documents from original creditor (Celtic Bank/Reflex)",
    "04_Collection_Agency": "Documents from LVNV/Resurgent/Halsted",
    "05_Correspondence": "All correspondence (incoming and outgoing)",
    "06_Evidence": "General evidence documents",
    "07_Legal_Research": "Legal research, statutes, case law",
    "08_Drafts": "Draft documents (not yet submitted)",
    "09_Submitted": "Documents submitted to courts, agencies, creditors",
    "10_Responses": "Responses received from courts, agencies, creditors",
    "11_Deadlines": "Deadline tracking and calendar",
    "Audit": "Audit trail and system-generated receipts",
}

EVIDENCE_ID_COUNTER = 420  # Starting at EV-2026-00420 per ChatGPT's suggestion


# ── Core Functions ───────────────────────────────────────────────────

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(filepath: Path) -> str:
    h = hashlib.sha256()
    with filepath.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_registry() -> Dict[str, Any]:
    if REGISTRY_PATH.exists():
        with REGISTRY_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "case_id": CASE_ID,
        "case_name": CASE_NAME,
        "created_at": now_iso(),
        "evidence_items": [],
        "next_evidence_number": EVIDENCE_ID_COUNTER,
    }


def save_registry(reg: Dict[str, Any]) -> None:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REGISTRY_PATH.open("w", encoding="utf-8") as f:
        json.dump(reg, f, indent=2, ensure_ascii=False)


def load_chronology() -> Dict[str, Any]:
    if CHRONOLOGY_PATH.exists():
        with CHRONOLOGY_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "case_id": CASE_ID,
        "case_name": CASE_NAME,
        "events": [],
    }


def save_chronology(chron: Dict[str, Any]) -> None:
    with CHRONOLOGY_PATH.open("w", encoding="utf-8") as f:
        json.dump(chron, f, indent=2, ensure_ascii=False)


# ── Version Management ───────────────────────────────────────────────

def _get_next_version(reg: Dict[str, Any], parent_id: str) -> int:
    """Find the highest version number for a parent evidence ID."""
    max_version = 0
    for item in reg["evidence_items"]:
        if item.get("parent_evidence_id") == parent_id or item.get("evidence_id") == parent_id:
            max_version = max(max_version, item.get("version", 1))
    return max_version + 1


# ── Claim Ledger ─────────────────────────────────────────────────────

CLAIM_LEDGER_PATH = CASE_DIR / "claim_ledger.json"

def load_claims() -> Dict[str, Any]:
    if CLAIM_LEDGER_PATH.exists():
        with CLAIM_LEDGER_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {"case_id": CASE_ID, "claims": []}

def save_claims(claims: Dict[str, Any]) -> None:
    with CLAIM_LEDGER_PATH.open("w", encoding="utf-8") as f:
        json.dump(claims, f, indent=2, ensure_ascii=False)

def add_claim(
    claim_text: str,
    claim_type: str = "factual",
    supporting_evidence_ids: Optional[List[str]] = None,
    status: str = "unsupported",
    missing: str = "",
    notes: str = "",
) -> Dict[str, Any]:
    """
    Register a factual assertion in the claim ledger.
    claim_type: factual | legal | procedural
    status: supported | partially_supported | unsupported | contradicted
    """
    claims = load_claims()
    claim_id = f"CLM-{len(claims['claims']) + 1:04d}"
    entry = {
        "claim_id": claim_id,
        "claim": claim_text,
        "claim_type": claim_type,
        "supporting_evidence_ids": supporting_evidence_ids or [],
        "status": status,
        "missing": missing,
        "notes": notes,
        "registered_at": now_iso(),
    }
    claims["claims"].append(entry)
    save_claims(claims)
    return entry


# ── Evidence Request Register ────────────────────────────────────────

REQUEST_REGISTER_PATH = CASE_DIR / "evidence_request_register.json"

def load_requests() -> Dict[str, Any]:
    if REQUEST_REGISTER_PATH.exists():
        with REQUEST_REGISTER_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {"case_id": CASE_ID, "requests": []}

def save_requests(reqs: Dict[str, Any]) -> None:
    with REQUEST_REGISTER_PATH.open("w", encoding="utf-8") as f:
        json.dump(reqs, f, indent=2, ensure_ascii=False)

def add_evidence_request(
    document_requested: str,
    requested_from: str,
    date_requested: str,
    status: str = "outstanding",
    response_received: str = "",
    response_date: str = "",
    notes: str = "",
) -> Dict[str, Any]:
    """
    Track outstanding evidence requests.
    status: outstanding | partially_received | received | denied | overdue
    """
    reqs = load_requests()
    req_id = f"REQ-{len(reqs['requests']) + 1:04d}"
    entry = {
        "request_id": req_id,
        "document_requested": document_requested,
        "requested_from": requested_from,
        "date_requested": date_requested,
        "status": status,
        "response_received": response_received,
        "response_date": response_date,
        "notes": notes,
        "registered_at": now_iso(),
    }
    reqs["requests"].append(entry)
    save_requests(reqs)
    return entry


# ── Evidence Registration ────────────────────────────────────────────

def register_evidence(
    source_file: Optional[Path] = None,
    text_content: Optional[str] = None,
    evidence_type: str = "document",
    title: str = "",
    description: str = "",
    source: str = "",
    custodian: str = "Isiah Howard",
    folder: str = "06_Evidence",
    date_of_event: str = "",
    notes: str = "",
    acquisition_method: str = "",
    acquisition_date: str = "",
    obtained_from: str = "",
    authenticity_status: str = "unverified",
    verification_status: str = "unverified",
    parent_evidence_id: str = "",
) -> Dict[str, Any]:
    """
    Register a piece of evidence with immutable ID, SHA-256 hash,
    timestamp, chain-of-custody metadata, and provenance fields.
    If parent_evidence_id is set, this is a new version of an existing item.
    """
    reg = load_registry()
    ev_num = reg["next_evidence_number"]
    evidence_id = f"EV-2026-{ev_num:05d}"
    reg["next_evidence_number"] = ev_num + 1

    timestamp = now_iso()

    # Compute hash
    if source_file and source_file.exists():
        file_hash = sha256_file(source_file)
        file_size = source_file.stat().st_size
        file_name = source_file.name
        # Copy to evidence folder
        dest_folder = CASE_DIR / folder
        dest_folder.mkdir(parents=True, exist_ok=True)
        dest_path = dest_folder / f"{evidence_id}_{file_name}"
        shutil.copy2(source_file, dest_path)
        stored_path = str(dest_path)
    elif text_content:
        file_hash = sha256_text(text_content)
        file_size = len(text_content.encode("utf-8"))
        safe_title = title.replace(" ", "_").replace("/", "-").replace("\\", "-").replace(":", "-").replace("\u2014", "-").replace("\u2013", "-").replace("|", "-").replace("?", "").replace("*", "").replace("<", "").replace(">", "").replace('"', "")
        file_name = f"{evidence_id}_{safe_title}.txt"
        dest_folder = CASE_DIR / folder
        dest_folder.mkdir(parents=True, exist_ok=True)
        dest_path = dest_folder / file_name
        dest_path.write_text(text_content, encoding="utf-8")
        stored_path = str(dest_path)
    else:
        file_hash = ""
        file_size = 0
        file_name = ""
        stored_path = ""

    item = {
        "evidence_id": evidence_id,
        "parent_evidence_id": parent_evidence_id,
        "version": 1 if not parent_evidence_id else _get_next_version(reg, parent_evidence_id),
        "title": title,
        "description": description,
        "evidence_type": evidence_type,
        "source": source,
        "custodian": custodian,
        "folder": folder,
        "file_name": file_name,
        "stored_path": stored_path,
        "sha256": file_hash,
        "file_size_bytes": file_size,
        "registered_at": timestamp,
        "date_of_event": date_of_event,
        "notes": notes,
        "provenance": {
            "acquisition_method": acquisition_method,
            "acquisition_date": acquisition_date,
            "obtained_from": obtained_from,
            "authenticity_status": authenticity_status,
            "verification_status": verification_status,
            "verified_by": "SHA-256" if file_hash else "",
            "verification_date": timestamp if file_hash else "",
        },
        "chain_of_custody": [
            {
                "action": "registered",
                "actor": "Hermes",
                "timestamp": timestamp,
                "notes": "Initial registration into evidence repository",
            }
        ],
    }

    reg["evidence_items"].append(item)
    save_registry(reg)

    return item


# ── Chronology ───────────────────────────────────────────────────────

def add_chronology_event(
    date: str,
    event: str,
    category: str = "general",
    evidence_ids: Optional[List[str]] = None,
    notes: str = "",
) -> Dict[str, Any]:
    chron = load_chronology()
    entry = {
        "date": date,
        "event": event,
        "category": category,
        "evidence_ids": evidence_ids or [],
        "notes": notes,
        "recorded_at": now_iso(),
    }
    chron["events"].append(entry)
    chron["events"].sort(key=lambda x: x["date"])
    save_chronology(chron)
    return entry


# ── Litigation Readiness Score ───────────────────────────────────────

def calculate_readiness() -> Dict[str, Any]:
    reg = load_registry()
    chron = load_chronology()
    claims = load_claims()
    reqs = load_requests()
    items = reg["evidence_items"]

    # Count items by folder
    folder_counts = {}
    for item in items:
        f = item["folder"]
        folder_counts[f] = folder_counts.get(f, 0) + 1

    # ── Repository Completeness (file set completeness) ──
    completeness_categories = {
        "Evidence": {
            "weight": 0.25,
            "score": min(100, len(items) * 10) if items else 0,
            "detail": f"{len(items)} items registered",
        },
        "Timeline": {
            "weight": 0.20,
            "score": min(100, len(chron["events"]) * 15) if chron["events"] else 0,
            "detail": f"{len(chron['events'])} chronological events",
        },
        "Authentication": {
            "weight": 0.20,
            "score": 100 if all(i["sha256"] for i in items) else (0 if not items else 50),
            "detail": "All items have SHA-256 hashes" if items else "No items yet",
        },
        "Correspondence": {
            "weight": 0.15,
            "score": min(100, folder_counts.get("05_Correspondence", 0) * 20),
            "detail": f"{folder_counts.get('05_Correspondence', 0)} correspondence items",
        },
        "Preservation": {
            "weight": 0.20,
            "score": 100 if all(i["stored_path"] for i in items) else (0 if not items else 50),
            "detail": "All items have stored copies" if items else "No items yet",
        },
    }

    # Missing documents check
    expected_docs = [
        "Signed cardmember agreement",
        "Complete transaction and payment history",
        "Bill of sale and assignment chain",
        "Account-level transfer record",
        "Resurgent collection authority proof",
        "Credit reporting status",
        "Records custodian identification",
    ]
    found_titles = " ".join(i["title"].lower() for i in items)
    missing = [d for d in expected_docs if not any(w in found_titles for w in d.lower().split()[:3])]
    missing_count = len(missing)

    completeness_score = sum(c["score"] * c["weight"] for c in completeness_categories.values())
    completeness_score = max(0, min(100, round(completeness_score - (missing_count * 2))))

    # ── Evidentiary Strength (how well evidence supports claims) ──
    all_claims = claims.get("claims", [])
    if all_claims:
        supported = sum(1 for c in all_claims if c["status"] == "supported")
        partial = sum(1 for c in all_claims if c["status"] == "partially_supported")
        unsupported = sum(1 for c in all_claims if c["status"] == "unsupported")
        total_claims = len(all_claims)
        strength_score = round(((supported * 100) + (partial * 50)) / total_claims)
    else:
        strength_score = 0
        supported = partial = unsupported = total_claims = 0

    # Outstanding requests
    all_reqs = reqs.get("requests", [])
    outstanding_reqs = sum(1 for r in all_reqs if r["status"] == "outstanding")
    received_reqs = sum(1 for r in all_reqs if r["status"] == "received")

    # Overall combines both
    overall = round(completeness_score * 0.6 + strength_score * 0.4)

    result = {
        "case_id": CASE_ID,
        "calculated_at": now_iso(),
        "repository_completeness": {
            "score": completeness_score,
            "categories": {k: v for k, v in completeness_categories.items()},
        },
        "evidentiary_strength": {
            "score": strength_score,
            "total_claims": total_claims,
            "supported": supported,
            "partially_supported": partial,
            "unsupported": unsupported,
        },
        "evidence_requests": {
            "total": len(all_reqs),
            "outstanding": outstanding_reqs,
            "received": received_reqs,
        },
        "missing_documents": missing,
        "missing_count": missing_count,
        "overall_readiness": overall,
        "grade": "A" if overall >= 90 else "B" if overall >= 80 else "C" if overall >= 70 else "D" if overall >= 60 else "F",
        "note": "Repository Completeness measures file set completeness. Evidentiary Strength measures how well available evidence supports specific claims. Overall is weighted 60/40.",
    }

    with READINESS_PATH.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    return result


# ── Case Packet Generation ───────────────────────────────────────────

def generate_case_packet() -> str:
    reg = load_registry()
    chron = load_chronology()
    claims = load_claims()
    reqs = load_requests()
    readiness = calculate_readiness()

    lines = []
    lines.append(f"# Case Packet — {CASE_ID}")
    lines.append(f"# {CASE_NAME}")
    lines.append(f"# Generated: {readiness['calculated_at']}")
    lines.append(f"# Litigation Readiness: {readiness['overall_readiness']}% (Grade {readiness['grade']})")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Cover Sheet
    lines.append("## Cover Sheet")
    lines.append("")
    lines.append(f"- Case ID: {CASE_ID}")
    lines.append(f"- Case Name: {CASE_NAME}")
    lines.append(f"- Category: Howard Recovery")
    lines.append(f"- Priority: HIGH")
    lines.append(f"- Status: Evidence Intake")
    lines.append(f"- External Action: LOCKED")
    lines.append(f"- Approval Required: YES")
    lines.append(f"- Evidence Items: {len(reg['evidence_items'])}")
    lines.append(f"- Chronology Events: {len(chron['events'])}")
    lines.append(f"- Litigation Readiness: {readiness['overall_readiness']}%")
    lines.append("")

    # Case Summary
    lines.append("## Case Summary")
    lines.append("")
    lines.append("Celtic Bank/Reflex credit card account ending 9370.")
    lines.append("Claimed balance: $2,121.52. Charge-off date: August 31, 2025.")
    lines.append("Acquired by LVNV Funding LLC on or about January 27, 2026.")
    lines.append("Serviced by Resurgent Capital Services L.P. (reference 835167536).")
    lines.append("")
    lines.append("Resurgent's June 24, 2026 response provided an internally generated")
    lines.append("account summary and March 2025 billing statement — but did NOT include:")
    lines.append("- Signed application/cardmember agreement")
    lines.append("- Complete itemized transaction and payment history")
    lines.append("- Bill of sale and complete assignment chain")
    lines.append("- Account-level transfer record identifying this account")
    lines.append("- Documentary proof of Resurgent's current collection authority")
    lines.append("- Records supporting the alleged March 2, 2025 last-payment date")
    lines.append("- Records custodian identification and basis of knowledge")
    lines.append("")

    # Timeline
    lines.append("## Timeline")
    lines.append("")
    if chron["events"]:
        for e in chron["events"]:
            lines.append(f"- {e['date']} [{e['category']}]: {e['event']}")
            if e["evidence_ids"]:
                lines.append(f"  Evidence: {', '.join(e['evidence_ids'])}")
            if e["notes"]:
                lines.append(f"  Notes: {e['notes']}")
    else:
        lines.append("(No chronology events yet)")
    lines.append("")

    # Evidence Index
    lines.append("## Evidence Index")
    lines.append("")
    if reg["evidence_items"]:
        lines.append("| Evidence ID | Title | Type | SHA-256 (first 16) | Date | Folder |")
        lines.append("|---|---|---|---|---|---|")
        for item in reg["evidence_items"]:
            sha_short = item["sha256"][:16] if item["sha256"] else "N/A"
            lines.append(f"| {item['evidence_id']} | {item['title']} | {item['evidence_type']} | {sha_short}... | {item['date_of_event']} | {item['folder']} |")
    else:
        lines.append("(No evidence items yet)")
    lines.append("")

    # Authority Index
    lines.append("## Authority Index")
    lines.append("")
    lines.append("Legal authorities relevant to this case:")
    lines.append("- 15 U.S.C. 1692g — FDCPA Validation of Debts")
    lines.append("- 15 U.S.C. 1692e — FDCPA False or Misleading Representations")
    lines.append("- 15 U.S.C. 1681 — FCRA Accuracy and Dispute Requirements")
    lines.append("- UCC Article 9 — Secured Transactions (assignment chain)")
    lines.append("(To be expanded with case law citations in 07_Legal_Research)")
    lines.append("")

    # Outstanding Requests
    lines.append("## Outstanding Requests (Deficiency Notice)")
    lines.append("")
    requests = [
        "Signed application/cardmember agreement",
        "Complete itemized transaction and payment history",
        "Bill of sale and every assignment from Celtic Bank to LVNV",
        "Account-level data identifying this exact account in the sale",
        "Resurgent's current servicing/collection authority",
        "Explanation of the claimed 'last payment' dated March 2, 2025",
        "Credit-reporting status and dispute notation",
        "Name and basis of knowledge of the records custodian",
    ]
    for i, r in enumerate(requests, 1):
        lines.append(f"{i}. {r}")
    lines.append("")

    # Evidence Request Register
    lines.append("## Evidence Request Register")
    lines.append("")
    all_reqs = reqs.get("requests", [])
    if all_reqs:
        lines.append("| Request ID | Document | Requested From | Date | Status |")
        lines.append("|---|---|---|---|---|")
        for r in all_reqs:
            lines.append(f"| {r['request_id']} | {r['document_requested']} | {r['requested_from']} | {r['date_requested']} | {r['status']} |")
    else:
        lines.append("(No formal evidence requests tracked yet)")
    lines.append("")

    # Claim Ledger
    lines.append("## Claim Ledger")
    lines.append("")
    all_claims = claims.get("claims", [])
    if all_claims:
        lines.append("| Claim ID | Claim | Type | Status | Supporting Evidence | Missing |")
        lines.append("|---|---|---|---|---|---|")
        for c in all_claims:
            ev_ids = ", ".join(c["supporting_evidence_ids"]) if c["supporting_evidence_ids"] else "None"
            missing = c["missing"] or "None"
            lines.append(f"| {c['claim_id']} | {c['claim']} | {c['claim_type']} | {c['status']} | {ev_ids} | {missing} |")
    else:
        lines.append("(No claims registered yet)")
    lines.append("")

    # Next Deadlines
    lines.append("## Next Deadlines")
    lines.append("")
    lines.append("(To be populated — check 11_Deadlines folder)")
    lines.append("")

    # Readiness Score
    lines.append("## Litigation Readiness Score")
    lines.append("")
    lines.append(f"Overall: {readiness['overall_readiness']}% (Grade {readiness['grade']})")
    lines.append("")
    lines.append(f"Repository Completeness: {readiness['repository_completeness']['score']}%")
    lines.append("")
    lines.append("| Category | Score | Weight | Detail |")
    lines.append("|---|---|---|---|")
    for cat, info in readiness["repository_completeness"]["categories"].items():
        lines.append(f"| {cat} | {info['score']}% | {info['weight']} | {info['detail']} |")
    lines.append("")
    lines.append(f"Evidentiary Strength: {readiness['evidentiary_strength']['score']}%")
    lines.append(f"  Claims: {readiness['evidentiary_strength']['total_claims']} total ({readiness['evidentiary_strength']['supported']} supported, {readiness['evidentiary_strength']['partially_supported']} partial, {readiness['evidentiary_strength']['unsupported']} unsupported)")
    lines.append(f"  Evidence Requests: {readiness['evidence_requests']['total']} total ({readiness['evidence_requests']['outstanding']} outstanding, {readiness['evidence_requests']['received']} received)")
    lines.append("")
    lines.append(f"Note: {readiness['note']}")
    lines.append("")
    if readiness["missing_documents"]:
        lines.append(f"Missing Documents ({readiness['missing_count']}):")
        for m in readiness["missing_documents"]:
            lines.append(f"- {m}")
        lines.append("")

    # Audit Receipt
    lines.append("## Audit Receipt")
    lines.append("")
    lines.append(f"- Packet generated at: {readiness['calculated_at']}")
    lines.append(f"- Generated by: Hermes (automated)")
    lines.append(f"- Evidence items included: {len(reg['evidence_items'])}")
    lines.append(f"- Chronology events included: {len(chron['events'])}")
    lines.append(f"- External action: LOCKED")
    lines.append(f"- Approval required for submission: YES")
    lines.append("")

    lines.append("---")
    lines.append(f"# End of Case Packet for {CASE_ID}")

    packet_text = "\n".join(lines)

    # Save packet to 08_Drafts (not 09_Submitted — this is a draft)
    packet_path = CASE_DIR / "08_Drafts" / f"case_packet_v1_{now_iso()[:10]}.md"
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    packet_path.write_text(packet_text, encoding="utf-8")

    return packet_text


# ── CLI ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    if cmd == "status":
        reg = load_registry()
        chron = load_chronology()
        readiness = calculate_readiness()
        print(f"Case: {CASE_ID} — {CASE_NAME}")
        print(f"Evidence items: {len(reg['evidence_items'])}")
        print(f"Chronology events: {len(chron['events'])}")
        print(f"Readiness: {readiness['overall_readiness']}% (Grade {readiness['grade']})")
        print(f"Missing documents: {readiness['missing_count']}")
        print(f"Registry: {REGISTRY_PATH}")
        print(f"Case dir: {CASE_DIR}")

    elif cmd == "register":
        print("Use register_evidence() function from Python")

    elif cmd == "packet":
        packet = generate_case_packet()
        print(packet[:500] + "...")
        print(f"\n[Full packet saved to 08_Drafts/]")

    elif cmd == "readiness":
        r = calculate_readiness()
        print(f"Overall: {r['overall_readiness']}% (Grade {r['grade']})")
        print(f"Repository Completeness: {r['repository_completeness']['score']}%")
        for cat, info in r["repository_completeness"]["categories"].items():
            print(f"  {cat}: {info['score']}% - {info['detail']}")
        print(f"Evidentiary Strength: {r['evidentiary_strength']['score']}%")
        print(f"  Claims: {r['evidentiary_strength']['total_claims']} ({r['evidentiary_strength']['supported']} supported, {r['evidentiary_strength']['partially_supported']} partial, {r['evidentiary_strength']['unsupported']} unsupported)")
        print(f"  Requests: {r['evidence_requests']['total']} ({r['evidence_requests']['outstanding']} outstanding)")
        if r["missing_documents"]:
            print(f"Missing ({r['missing_count']}):")
            for m in r["missing_documents"]:
                print(f"  - {m}")