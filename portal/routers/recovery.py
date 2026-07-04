import json
from datetime import UTC, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

STORE_PATH = DATA_DIR / "howard_recovery_case_board.json"


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def default_store() -> Dict[str, Dict[str, Any]]:
    return {
        "cases": {},
        "evidence": {},
        "receipts": {}
    }


def load_store() -> Dict[str, Dict[str, Any]]:
    if not STORE_PATH.exists():
        return default_store()

    try:
        with STORE_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)

        data.setdefault("cases", {})
        data.setdefault("evidence", {})
        data.setdefault("receipts", {})
        return data

    except Exception:
        return default_store()


def save_store() -> None:
    payload = {
        "cases": CASES,
        "evidence": EVIDENCE,
        "receipts": RECEIPTS,
        "updated_at": now_iso()
    }

    with STORE_PATH.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


STORE = load_store()
CASES: Dict[str, Dict[str, Any]] = STORE["cases"]
EVIDENCE: Dict[str, Dict[str, Any]] = STORE["evidence"]
RECEIPTS: Dict[str, Dict[str, Any]] = STORE["receipts"]


ACTIVE_CASE_DEFAULTS = [
    "PayPal Negative Balance / Account Block",
    "Halsted / LVNV / Bank of Missouri / Milestone",
    "UACC / Vroom",
    "AFF / FinWise",
    "Self Financial / Lead Bank",
    "Verizon",
    "Chase / Wells Fargo / EWS",
    "Unknown Collections",
    "SAP / FMCSA",
    "Expungement",
    "Funding / Grants",
    "TikTok Shop"
]


class CaseCreateRequest(BaseModel):
    case_name: str
    category: str = "recovery"
    priority: str = "medium"
    status: str = "evidence_intake"
    external_action: str = "locked"
    approval_required: bool = True
    notes: str | None = None


class EvidenceAddRequest(BaseModel):
    case_id: str
    evidence_type: str = Field(..., description="email, screenshot, PDF, credit report, statement, contract, notice, court record, receipt")
    title: str
    source: str
    date_found: str | None = None
    amount: str | None = None
    account_identifier: str | None = None
    gmail_link: str | None = None
    file_path: str | None = None
    notes: str | None = None


class EvidenceBatchRequest(BaseModel):
    evidence_items: List[EvidenceAddRequest]


class ReceiptCreateRequest(BaseModel):
    case_id: str | None = None
    agent: str = "SintraPrime"
    action_performed: str
    evidence_used: List[str] | None = []
    output_created: str | None = None
    external_action: bool = False
    approval_required: bool = True
    status: str = "recorded"
    next_step: str | None = None


@router.post("/api/recovery/cases/create")
async def create_case(request: CaseCreateRequest):
    case_id = f"CASE-{uuid4().hex[:10].upper()}"
    timestamp = now_iso()

    case = {
        "case_id": case_id,
        "case_name": request.case_name,
        "category": request.category,
        "priority": request.priority,
        "status": request.status,
        "external_action": request.external_action,
        "approval_required": request.approval_required,
        "notes": request.notes,
        "created_at": timestamp,
        "updated_at": timestamp,
    }

    CASES[case_id] = case
    save_store()
    return case


@router.get("/api/recovery/cases")
async def list_cases():
    return {
        "count": len(CASES),
        "cases": list(CASES.values()),
        "external_action": "locked",
        "approval_required_before": [
            "send", "file", "contact", "submit", "delete",
            "modify", "email", "call", "mail", "serve", "post"
        ]
    }


@router.post("/api/recovery/cases/initialize-defaults")
async def initialize_default_cases():
    created = []
    existing_names = {case["case_name"] for case in CASES.values()}

    for index, name in enumerate(ACTIVE_CASE_DEFAULTS, start=1):
        if name in existing_names:
            continue

        priority = "high" if index <= 5 else "medium"
        case_id = f"CASE-{uuid4().hex[:10].upper()}"
        timestamp = now_iso()

        case = {
            "case_id": case_id,
            "case_name": name,
            "category": "howard_recovery",
            "priority": priority,
            "status": "evidence_intake",
            "external_action": "locked",
            "approval_required": True,
            "notes": "Initialized under HOWARD_RECOVERY_SYSTEM_12_MONTH_MASTER.",
            "created_at": timestamp,
            "updated_at": timestamp,
        }

        CASES[case_id] = case
        created.append(case)

    save_store()

    return {
        "status": "initialized",
        "created_count": len(created),
        "created_cases": created,
        "total_cases": len(CASES),
        "store_path": str(STORE_PATH)
    }


def create_evidence_record(request: EvidenceAddRequest) -> Dict[str, Any]:
    if request.case_id not in CASES:
        raise HTTPException(status_code=404, detail=f"case_id not found: {request.case_id}")

    evidence_id = f"EVID-{uuid4().hex[:10].upper()}"
    timestamp = now_iso()

    evidence = {
        "evidence_id": evidence_id,
        "case_id": request.case_id,
        "evidence_type": request.evidence_type,
        "title": request.title,
        "source": request.source,
        "date_found": request.date_found,
        "amount": request.amount,
        "account_identifier": request.account_identifier,
        "gmail_link": request.gmail_link,
        "file_path": request.file_path,
        "notes": request.notes,
        "created_at": timestamp,
    }

    EVIDENCE[evidence_id] = evidence
    CASES[request.case_id]["updated_at"] = timestamp
    return evidence


@router.post("/api/recovery/evidence/add")
async def add_evidence(request: EvidenceAddRequest):
    evidence = create_evidence_record(request)
    save_store()
    return evidence


@router.post("/api/recovery/evidence/add-batch")
async def add_evidence_batch(request: EvidenceBatchRequest):
    created = []

    for item in request.evidence_items:
        created.append(create_evidence_record(item))

    save_store()

    receipt_id = f"RCP-{uuid4().hex[:10].upper()}"
    receipt = {
        "receipt_id": receipt_id,
        "case_id": None,
        "agent": "SintraPrime",
        "action_performed": "Batch evidence import completed.",
        "evidence_used": [item["evidence_id"] for item in created],
        "output_created": "Batch evidence records",
        "external_action": False,
        "approval_required": True,
        "status": "completed",
        "next_step": "Review batch evidence records and attach source files where available.",
        "created_at": now_iso(),
    }

    RECEIPTS[receipt_id] = receipt
    save_store()

    return {
        "status": "batch_created",
        "created_count": len(created),
        "evidence": created,
        "receipt": receipt,
        "store_path": str(STORE_PATH)
    }


@router.get("/api/recovery/evidence")
async def list_evidence(case_id: str | None = None):
    evidence_items = list(EVIDENCE.values())

    if case_id:
        evidence_items = [item for item in evidence_items if item["case_id"] == case_id]

    return {
        "count": len(evidence_items),
        "evidence": evidence_items
    }


@router.post("/api/recovery/receipts/create")
async def create_receipt(request: ReceiptCreateRequest):
    if request.case_id and request.case_id not in CASES:
        raise HTTPException(status_code=404, detail=f"case_id not found: {request.case_id}")

    receipt_id = f"RCP-{uuid4().hex[:10].upper()}"
    timestamp = now_iso()

    receipt = {
        "receipt_id": receipt_id,
        "case_id": request.case_id,
        "agent": request.agent,
        "action_performed": request.action_performed,
        "evidence_used": request.evidence_used,
        "output_created": request.output_created,
        "external_action": request.external_action,
        "approval_required": request.approval_required,
        "status": request.status,
        "next_step": request.next_step,
        "created_at": timestamp,
    }

    RECEIPTS[receipt_id] = receipt

    if request.case_id:
        CASES[request.case_id]["updated_at"] = timestamp

    save_store()
    return receipt


@router.get("/api/recovery/receipts")
async def list_receipts(case_id: str | None = None):
    receipt_items = list(RECEIPTS.values())

    if case_id:
        receipt_items = [item for item in receipt_items if item["case_id"] == case_id]

    return {
        "count": len(receipt_items),
        "receipts": receipt_items
    }


@router.get("/api/recovery/store")
async def recovery_store():
    return {
        "store_path": str(STORE_PATH),
        "case_count": len(CASES),
        "evidence_count": len(EVIDENCE),
        "receipt_count": len(RECEIPTS),
        "data": {
            "cases": CASES,
            "evidence": EVIDENCE,
            "receipts": RECEIPTS
        }
    }

@router.get("/api/recovery/case-packet/{case_id}")
async def get_case_packet(case_id: str):
    if case_id not in CASES:
        raise HTTPException(status_code=404, detail=f"case_id not found: {case_id}")

    case = CASES[case_id]
    evidence_items = [
        item for item in EVIDENCE.values()
        if item["case_id"] == case_id
    ]

    receipt_items = [
        item for item in RECEIPTS.values()
        if item.get("case_id") == case_id
        or any(eid in [ev["evidence_id"] for ev in evidence_items] for eid in item.get("evidence_used", []))
    ]

    return {
        "packet_type": "HOWARD_RECOVERY_CASE_PACKET",
        "generated_at": now_iso(),
        "case": case,
        "evidence_count": len(evidence_items),
        "receipt_count": len(receipt_items),
        "evidence": evidence_items,
        "receipts": receipt_items,
        "controls": {
            "mode": "evidence_intake_only",
            "external_action": "locked",
            "approval_required_before": [
                "send", "file", "contact", "submit", "delete",
                "modify", "email", "call", "mail", "serve", "post"
            ],
            "evidence_rule": "Every claim must be tied to email, screenshot, PDF, credit report, statement, contract, notice, court record, or payment receipt."
        },
        "recommended_next_steps": [
            "Verify each evidence item has a source file, email link, screenshot, or record reference.",
            "Separate public-facing claims from private strategy notes.",
            "Draft only after evidence review is complete.",
            "Do not send, file, contact, serve, mail, email, or call without explicit approval."
        ]
    }




@router.get("/api/recovery/export/json")
async def export_recovery_json():
    return {
        "export_type": "HOWARD_RECOVERY_FULL_JSON_EXPORT",
        "generated_at": now_iso(),
        "store_path": str(STORE_PATH),
        "counts": {
            "cases": len(CASES),
            "evidence": len(EVIDENCE),
            "receipts": len(RECEIPTS)
        },
        "data": {
            "cases": CASES,
            "evidence": EVIDENCE,
            "receipts": RECEIPTS
        },
        "controls": {
            "mode": "evidence_intake_only",
            "external_action": "locked",
            "approval_required": True
        }
    }


@router.get("/api/recovery/export/summary")
async def export_recovery_summary():
    case_summaries = []

    for case_id, case in CASES.items():
        evidence_items = [
            item for item in EVIDENCE.values()
            if item["case_id"] == case_id
        ]

        receipt_items = [
            item for item in RECEIPTS.values()
            if item.get("case_id") == case_id
            or any(eid in [ev["evidence_id"] for ev in evidence_items] for eid in item.get("evidence_used", []))
        ]

        evidence_types = sorted({item["evidence_type"] for item in evidence_items})

        case_summaries.append({
            "case_id": case_id,
            "case_name": case["case_name"],
            "priority": case["priority"],
            "status": case["status"],
            "external_action": case["external_action"],
            "approval_required": case["approval_required"],
            "evidence_count": len(evidence_items),
            "receipt_count": len(receipt_items),
            "evidence_types": evidence_types,
            "last_updated": case["updated_at"]
        })

    return {
        "export_type": "HOWARD_RECOVERY_SUMMARY_EXPORT",
        "generated_at": now_iso(),
        "counts": {
            "cases": len(CASES),
            "evidence": len(EVIDENCE),
            "receipts": len(RECEIPTS)
        },
        "case_summaries": case_summaries,
        "system_controls": {
            "mode": "evidence_intake_only",
            "external_action": "locked",
            "approval_required_before": [
                "send", "file", "contact", "submit", "delete",
                "modify", "email", "call", "mail", "serve", "post"
            ]
        },
        "next_recommended_upgrade": "Phase 2C: Markdown/PDF packet generation"
    }
def render_case_packet_markdown(case_id: str) -> str:
    if case_id not in CASES:
        raise HTTPException(status_code=404, detail=f"case_id not found: {case_id}")

    case = CASES[case_id]

    evidence_items = [
        item for item in EVIDENCE.values()
        if item["case_id"] == case_id
    ]

    receipt_items = [
        item for item in RECEIPTS.values()
        if item.get("case_id") == case_id
        or any(
            eid in [ev["evidence_id"] for ev in evidence_items]
            for eid in item.get("evidence_used", [])
        )
    ]

    lines = []

    lines.append("# Howard Recovery Case Packet")
    lines.append("")
    lines.append(f"Generated: {now_iso()}")
    lines.append("")
    lines.append(f"## Case: {case['case_name']}")
    lines.append("")
    lines.append(f"- **Case ID:** {case['case_id']}")
    lines.append(f"- **Category:** {case['category']}")
    lines.append(f"- **Priority:** {case['priority']}")
    lines.append(f"- **Status:** {case['status']}")
    lines.append(f"- **External Action:** {case['external_action']}")
    lines.append(f"- **Approval Required:** {case['approval_required']}")
    lines.append(f"- **Created:** {case['created_at']}")
    lines.append(f"- **Updated:** {case['updated_at']}")
    lines.append("")
    lines.append("## Evidence")
    lines.append("")

    if not evidence_items:
        lines.append("No evidence records logged yet.")
        lines.append("")
    else:
        for item in evidence_items:
            lines.append(f"### {item['evidence_id']} — {item['title']}")
            lines.append("")
            lines.append(f"- **Type:** {item['evidence_type']}")
            lines.append(f"- **Source:** {item['source']}")
            lines.append(f"- **Date Found:** {item.get('date_found')}")
            lines.append(f"- **Amount:** {item.get('amount')}")
            lines.append(f"- **Account Identifier:** {item.get('account_identifier')}")
            lines.append(f"- **Gmail Link:** {item.get('gmail_link')}")
            lines.append(f"- **File Path:** {item.get('file_path')}")
            lines.append(f"- **Notes:** {item.get('notes')}")
            lines.append("")

    lines.append("## Receipts")
    lines.append("")

    if not receipt_items:
        lines.append("No receipts connected to this case yet.")
        lines.append("")
    else:
        for receipt in receipt_items:
            lines.append(f"### {receipt['receipt_id']}")
            lines.append("")
            lines.append(f"- **Agent:** {receipt['agent']}")
            lines.append(f"- **Action:** {receipt['action_performed']}")
            lines.append(f"- **Evidence Used:** {', '.join(receipt.get('evidence_used', []))}")
            lines.append(f"- **Output Created:** {receipt.get('output_created')}")
            lines.append(f"- **External Action:** {receipt.get('external_action')}")
            lines.append(f"- **Approval Required:** {receipt.get('approval_required')}")
            lines.append(f"- **Status:** {receipt.get('status')}")
            lines.append(f"- **Next Step:** {receipt.get('next_step')}")
            lines.append(f"- **Created:** {receipt.get('created_at')}")
            lines.append("")

    lines.append("## Controls")
    lines.append("")
    lines.append("- **Mode:** evidence_intake_only")
    lines.append("- **External Action:** locked")
    lines.append("- **Evidence Rule:** Every claim must be tied to email, screenshot, PDF, credit report, statement, contract, notice, court record, or payment receipt.")
    lines.append("- **Approval Required Before:** send, file, contact, submit, delete, modify, email, call, mail, serve, post")
    lines.append("")

    lines.append("## Recommended Next Steps")
    lines.append("")
    lines.append("1. Verify each evidence item has a source file, email link, screenshot, or record reference.")
    lines.append("2. Separate public-facing claims from private strategy notes.")
    lines.append("3. Draft only after evidence review is complete.")
    lines.append("4. Do not send, file, contact, serve, mail, email, or call without explicit approval.")
    lines.append("")

    return "\n".join(lines)


@router.get("/api/recovery/case-packet/{case_id}/markdown")
async def get_case_packet_markdown(case_id: str):
    return {
        "format": "markdown",
        "case_id": case_id,
        "generated_at": now_iso(),
        "markdown": render_case_packet_markdown(case_id)
    }


@router.get("/api/recovery/export/markdown")
async def export_all_cases_markdown():
    sections = []

    sections.append("# Howard Recovery Master Case Board")
    sections.append("")
    sections.append(f"Generated: {now_iso()}")
    sections.append("")
    sections.append("## System Controls")
    sections.append("")
    sections.append("- **Mode:** evidence_intake_only")
    sections.append("- **External Action:** locked")
    sections.append("- **Approval Required:** true")
    sections.append("")
    sections.append("## Case Index")
    sections.append("")

    for case_id, case in CASES.items():
        evidence_count = len([
            item for item in EVIDENCE.values()
            if item["case_id"] == case_id
        ])

        sections.append(
            f"- **{case['case_name']}** — `{case_id}` — Evidence: {evidence_count}"
        )

    sections.append("")
    sections.append("---")
    sections.append("")

    for case_id in CASES:
        sections.append(render_case_packet_markdown(case_id))
        sections.append("")
        sections.append("---")
        sections.append("")

    return {
        "format": "markdown",
        "generated_at": now_iso(),
        "case_count": len(CASES),
        "evidence_count": len(EVIDENCE),
        "receipt_count": len(RECEIPTS),
        "markdown": "\n".join(sections)
    }
@router.get("/api/recovery/health")
async def recovery_health():
    return {
        "status": "ok",
        "module": "HOWARD_RECOVERY_CASE_BOARD_API",
        "phase": "Phase 2 JSON persistence",
        "mode": "evidence_intake_only",
        "external_action": "locked",
        "case_count": len(CASES),
        "evidence_count": len(EVIDENCE),
        "receipt_count": len(RECEIPTS),
        "store_path": str(STORE_PATH)
    }


@router.get("/api/recovery/dashboard")
async def recovery_dashboard():
    """Public dashboard stats — no auth required. Powers the frontend Dashboard."""
    high_priority = [c for c in CASES.values() if c.get("priority") == "high"]
    medium_priority = [c for c in CASES.values() if c.get("priority") == "medium"]
    evidence_intake = [c for c in CASES.values() if c.get("status") == "evidence_intake"]

    # Check evidence platform for readiness scores
    evidence_base = Path(__file__).parent.parent.parent / "evidence"
    case_readiness = []
    for case_dir in evidence_base.iterdir() if evidence_base.exists() else []:
        if case_dir.is_dir() and case_dir.name.startswith("CASE-"):
            readiness_file = case_dir / "readiness_score.json"
            if readiness_file.exists():
                try:
                    with readiness_file.open("r", encoding="utf-8") as f:
                        r = json.load(f)
                    case_readiness.append({
                        "case_id": r.get("case_id", case_dir.name),
                        "overall": r.get("overall_readiness", 0),
                        "grade": r.get("grade", "F"),
                        "repository": r.get("dimensions", {}).get("repository_completeness", {}).get("score", 0),
                        "evidence": r.get("dimensions", {}).get("evidence_strength", {}).get("score", 0),
                        "legal": r.get("dimensions", {}).get("legal_readiness", {}).get("score", 0),
                        "procedural": r.get("dimensions", {}).get("procedural_readiness", {}).get("score", 0),
                    })
                except Exception:
                    pass

    return {
        "status": "ok",
        "tenant": "IKE Solutions",
        "cases": {
            "total": len(CASES),
            "high_priority": len(high_priority),
            "medium_priority": len(medium_priority),
            "evidence_intake": len(evidence_intake),
        },
        "evidence": {
            "total_items": len(EVIDENCE),
            "total_receipts": len(RECEIPTS),
        },
        "case_readiness": case_readiness,
        "high_priority_cases": [
            {"case_id": c["case_id"], "name": c["case_name"], "status": c["status"]}
            for c in high_priority
        ],
        "external_action": "locked",
        "platform_version": "SintraPrime-Unified 1.0.0",
        "evidence_kernel": "CaseTemplate v2.1.0",
        "timestamp": now_iso(),
    }

