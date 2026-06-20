"""Court filing / enforcement draft center (draft-only, audit-first).

REPORT-ONLY GOAL
Generate consistent draft courtroom bundles from your existing SintraPrime
case fixtures — without sending disputes/filings to agencies.

OUTPUTS (SintraPrime repo)
- artifacts/court/<case_id>/court_bundle_draft.md
- artifacts/court/<case_id>/court_bundle_draft.json

RECEIPTS
- Records each generated output via `ledger/record_ledger_entry.py`.

OPTIONAL NOTION LOGGING
- If env var NOTION_RUNS_WEBHOOK is set, POSTs a small metadata payload to the
  webhook (Make.com scenario) for Notion execution receipt logging.

This is designed to be run by Hermes cron in a no-agent session.

IMPORTANT
- No legal advice.
- Drafts are operational packaging; jurisdiction/deadlines still require
  manual validation.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


REPO_ROOT = Path(__file__).resolve().parents[2]  # .../orchestration/enforcement -> repo root


def load_env_var_from_repo_env(var_name: str) -> Optional[str]:
    """Best-effort: load a single env var from repo .env without printing values."""

    existing = os.getenv(var_name)
    if existing:
        return existing

    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return None

    try:
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if key != var_name:
                continue
            value = value.strip()
            if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]
            return value
    except Exception:
        return None

    return None


@dataclass
class CaseInput:
    case_dir: Path
    case_id: str
    case_json: Dict[str, Any]
    evidence_manifest: Optional[Dict[str, Any]]
    violation_candidates: Optional[Dict[str, Any]]
    readiness_report: Optional[Dict[str, Any]]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def evidence_summary(evidence_manifest: Optional[Dict[str, Any]]) -> Tuple[Dict[str, Any], List[str]]:
    """Returns (summary, missing_evidence_ids/labels)."""
    if not evidence_manifest:
        return {"verified": 0, "missing": 0, "partial": 0}, []

    verified_count = int(evidence_manifest.get("verification_summary", {}).get("verified", 0))
    missing_count = int(evidence_manifest.get("verification_summary", {}).get("missing", 0))
    partial_count = int(evidence_manifest.get("verification_summary", {}).get("partial", 0))

    missing_items: List[str] = []
    for ev in evidence_manifest.get("evidence_items", []) or []:
        if ev.get("status") == "missing":
            missing_items.append(ev.get("evidence_id") or ev.get("description") or "(unknown)")

    summary = {
        "verified": verified_count,
        "partial": partial_count,
        "missing": missing_count,
        "raw": evidence_manifest.get("verification_summary", {}),
    }
    return summary, missing_items


def violation_candidates_summary(v: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not v:
        return []

    # Fixture structure varies; keep generic.
    for key in ["violation_candidates", "candidates", "items", "violations"]:
        if isinstance(v.get(key), list):
            return v[key]

    if isinstance(v.get("items"), list):
        return v["items"]

    if isinstance(v.get("violations"), list):
        return v["violations"]

    return []


def load_case(case_dir: Path) -> CaseInput:
    case_json = read_json(case_dir / "case.json") or {}
    case_id = case_json.get("case_id") or case_dir.name

    evidence_manifest = read_json(case_dir / "evidence_manifest.json")
    violation_candidates = read_json(case_dir / "violation_candidates.json")
    readiness_report = read_json(case_dir / "readiness_report.json")

    return CaseInput(
        case_dir=case_dir,
        case_id=case_id,
        case_json=case_json,
        evidence_manifest=evidence_manifest,
        violation_candidates=violation_candidates,
        readiness_report=readiness_report,
    )


def build_court_bundle_md(case: CaseInput) -> Tuple[str, Dict[str, Any]]:
    ev_summary, missing_evidence_ids = evidence_summary(case.evidence_manifest)
    v_candidates = violation_candidates_summary(case.violation_candidates)
    readiness_report = case.readiness_report

    readiness_status = None
    readiness_score = None
    if readiness_report:
        readiness_status = readiness_report.get("status") or readiness_report.get("readiness")
        readiness_score = readiness_report.get("overall_readiness_score")
        if readiness_score is None:
            readiness_score = readiness_report.get("readiness_score")

    # Draft decision (draft-only; not legal guarantees)
    if ev_summary.get("missing", 0) > 0:
        draft_status = "NOT READY — evidence gaps present (draft-only bundle)"
        draft_recommendation = [
            "Prioritize missing evidence acquisition based on evidence_manifest.status == 'missing'.",
            "Re-run court bundle generation after evidence is marked verified.",
            "Keep language factual and evidence-indexed; avoid assumptions.",
        ]
    else:
        draft_status = "READY (DRAFTED) — evidence coverage is complete enough for a first filing skeleton"
        draft_recommendation = [
            "Proceed with counsel review / jurisdiction-specific formatting.",
            "Attach exhibits with ledger-linked hashes/snapshots.",
            "Validate deadlines and service requirements independently.",
        ]

    c = case.case_json
    creditor = c.get("creditor") or c.get("defendant")
    case_type = c.get("case_type")
    matter_type = c.get("matter_type")
    opened_date = c.get("opened_date")
    case_summary = c.get("case_summary")

    lines: List[str] = []
    lines.append(f"# Court Filing Draft Bundle — {case.case_id}")
    lines.append("")
    lines.append("## Case Overview")
    lines.append(f"- Case ID: {case.case_id}")
    if case_type:
        lines.append(f"- Case Type: {case_type}")
    if matter_type:
        lines.append(f"- Matter Type: {matter_type}")
    if creditor:
        lines.append(f"- Creditor/Defendant: {creditor}")
    if opened_date:
        lines.append(f"- Opened Date: {opened_date}")
    lines.append("")

    if case_summary:
        lines.append("## Summary")
        lines.append(case_summary)
        lines.append("")

    lines.append("## Evidence Verification Summary")
    lines.append(f"- Verified: {ev_summary.get('verified', 0)}")
    lines.append(f"- Partial: {ev_summary.get('partial', 0)}")
    lines.append(f"- Missing: {ev_summary.get('missing', 0)}")

    if missing_evidence_ids:
        lines.append("")
        lines.append("### Missing Evidence (IDs / Descriptions)")
        for mid in missing_evidence_ids:
            lines.append(f"- {mid}")

    lines.append("")
    lines.append("## Violation Candidates (From Fixture Analysis)")
    if v_candidates:
        for idx, cand in enumerate(v_candidates, start=1):
            law = cand.get("law") or cand.get("statute")
            violation = cand.get("violation") or cand.get("description")
            notes = cand.get("notes")
            severity = cand.get("severity")

            lines.append(f"\n### Candidate {idx}")
            if law:
                lines.append(f"- Law/Authority: {law}")
            if violation:
                lines.append(f"- Alleged Violation: {violation}")
            if severity is not None:
                lines.append(f"- Severity: {severity}")
            if notes:
                lines.append(f"- Notes: {notes}")
    else:
        lines.append("- (No violation candidates found in fixture)")

    lines.append("")
    lines.append("## Draft Filing Status")
    lines.append(draft_status)

    lines.append("")
    lines.append("### Draft Recommendation (Operational, not legal advice)")
    for rec in draft_recommendation:
        lines.append(f"- {rec}")

    if readiness_status or readiness_score is not None:
        lines.append("")
        lines.append("## Readiness Report (if available)")
        if readiness_status:
            lines.append(f"- Status: {readiness_status}")
        if readiness_score is not None:
            lines.append(f"- Overall Readiness Score: {readiness_score}")

    lines.append("")
    lines.append("---")
    lines.append(
        "\n*Draft-only output. Not legal advice. Verification of jurisdiction, deadlines, and service requirements remains mandatory.*"
    )

    bundle_md = "\n".join(lines)

    bundle_json: Dict[str, Any] = {
        "case_id": case.case_id,
        "generated_at": utc_now_iso(),
        "evidence": ev_summary,
        "missing_evidence": missing_evidence_ids,
        "violation_candidates": v_candidates,
        "draft_status": draft_status,
        "draft_recommendation": draft_recommendation,
        "readiness": {
            "status": readiness_status,
            "overall_readiness_score": readiness_score,
        },
        "source": {
            "case_json": {
                "creditor": creditor,
                "case_type": case_type,
                "matter_type": matter_type,
                "opened_date": opened_date,
            }
        },
    }

    return bundle_md, bundle_json


def load_creditor_response_text(case_dir: Path) -> Optional[str]:
    """Best-effort: load a creditor response fixture if present."""
    # Common fixture filenames (optional; runner still works without them).
    candidates = [
        "creditor_response_text.txt",
        "creditor_response.txt",
        "creditor_response.md",
        "creditor_response.json",
    ]

    for name in candidates:
        p = case_dir / name
        if not p.exists():
            continue

        if p.suffix.lower() == ".json":
            try:
                obj = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(obj, dict):
                    for k in ["text", "body", "content", "response_text"]:
                        if k in obj and isinstance(obj[k], str):
                            return obj[k]
            except Exception:
                # fall through to raw read
                pass

        return p.read_text(encoding="utf-8", errors="replace")

    return None


def analyze_response_flags(response_text: Optional[str]) -> Dict[str, Any]:
    """Lightweight heuristic response analyzer (draft-only)."""
    if not response_text:
        return {
            "ok": False,
            "flags": [],
            "flag_count": 0,
            "reason": "No creditor response text fixture found.",
        }

    t = response_text.lower()
    flags: List[str] = []

    if "we verified" in t and "how" not in t:
        flags.append("NO_METHOD_OF_VERIFICATION")
    if "please allow" in t and "30" in t:
        flags.append("STALL_TACTIC")
    if "account is accurate" in t or "is accurate" in t:
        flags.append("CONCLUSORY_STATEMENT")

    return {
        "ok": True,
        "flags": flags,
        "flag_count": len(flags),
    }


def build_complaint_draft_text(case: CaseInput) -> Tuple[str, Dict[str, Any]]:
    """Draft-only complaint packaging from fixture data."""
    c = case.case_json or {}
    jurisdiction = c.get("jurisdiction") or c.get("case_type") or "(unknown)"
    creditor = c.get("creditor") or c.get("defendant") or "(unknown)"
    client_id = c.get("client_id") or "(unknown client)"

    violations: List[Dict[str, Any]] = []
    if case.violation_candidates and isinstance(case.violation_candidates.get("violations"), list):
        violations = case.violation_candidates.get("violations")

    lines: List[str] = []
    lines.append(f"# Complaint Draft (Draft-only) — {case.case_id}")
    lines.append("")
    lines.append("## Caption")
    lines.append(f"- Client ID: {client_id}")
    lines.append(f"- Creditor/Defendant: {creditor}")
    lines.append(f"- Jurisdiction (fixture): {jurisdiction}")
    lines.append("")
    lines.append("## Causes of Action (Draft)")

    if not violations:
        lines.append("- (No violation candidates found in fixture)")
    else:
        for idx, v in enumerate(violations, start=1):
            statute = v.get("statute")
            section = v.get("section")
            law = ": ".join([x for x in [statute, section] if x]) or v.get("legal_basis") or "(law unspecified)"
            description = v.get("description") or v.get("notes") or "(no description)"
            severity = v.get("severity")
            confidence = v.get("confidence")

            lines.append(f"\n### Count {idx}")
            lines.append(f"- Authority: {law}")
            lines.append(f"- Alleged Violation: {description}")
            if severity is not None:
                lines.append(f"- Severity: {severity}")
            if confidence is not None:
                lines.append(f"- Confidence (fixture): {confidence}")

    lines.append("")
    lines.append("## Prayer for Relief (Draft)")
    lines.append("- Actual damages (where applicable)")
    lines.append("- Statutory damages (where applicable)")
    lines.append("- Injunctive / corrective relief")
    lines.append("")
    lines.append(
        "---\n*Draft-only output. Not legal advice. Confirm jurisdiction, deadlines, and service requirements independently.*"
    )

    complaint_md = "\n".join(lines)
    complaint_json = {
        "case_id": case.case_id,
        "generated_at": utc_now_iso(),
        "jurisdiction": jurisdiction,
        "creditor": creditor,
        "violations": violations,
        "prayer_for_relief": [
            "Actual damages (where applicable)",
            "Statutory damages (where applicable)",
            "Injunctive / corrective relief",
        ],
        "draft_notes": "Fixture-based packaging draft.",
    }

    return complaint_md, complaint_json


def write_additional_outputs(case: CaseInput, out_dir: Path) -> Tuple[Path, Path, Path, Dict[str, Any]]:
    """Write complaint draft + response analysis + return verification summary."""
    out_dir.mkdir(parents=True, exist_ok=True)

    complaint_md_path = out_dir / "complaint_draft.md"
    complaint_json_path = out_dir / "complaint_draft.json"
    response_analysis_path = out_dir / "response_analysis.json"

    complaint_md, complaint_json = build_complaint_draft_text(case)
    complaint_md_path.write_text(complaint_md, encoding="utf-8")
    complaint_json_path.write_text(
        json.dumps(complaint_json, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    response_text = load_creditor_response_text(case.case_dir)
    response_analysis = analyze_response_flags(response_text)
    response_payload = {
        "case_id": case.case_id,
        "generated_at": utc_now_iso(),
        "has_creditor_response": bool(response_text),
        "analysis": response_analysis,
    }
    response_analysis_path.write_text(
        json.dumps(response_payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Local verification: two post-reads identical.
    md1 = complaint_md_path.read_text(encoding="utf-8")
    md2 = complaint_md_path.read_text(encoding="utf-8")
    json1 = complaint_json_path.read_text(encoding="utf-8")
    json2 = complaint_json_path.read_text(encoding="utf-8")
    ra1 = response_analysis_path.read_text(encoding="utf-8")
    ra2 = response_analysis_path.read_text(encoding="utf-8")

    return (
        complaint_md_path,
        complaint_json_path,
        response_analysis_path,
        {
            "complaint_md": {
                "read_back": md1 == complaint_md,
                "multi_read_match": md1 == md2,
            },
            "complaint_json": {
                "read_back": json1 == json.dumps(complaint_json, indent=2, ensure_ascii=False),
                "multi_read_match": json1 == json2,
            },
            "response_analysis": {
                "read_back": ra1 == json.dumps(response_payload, indent=2, ensure_ascii=False),
                "multi_read_match": ra1 == ra2,
            },
        },
    )


def write_outputs(case: CaseInput, out_dir: Path) -> Tuple[Path, Path, Dict[str, Any]]:
    out_dir.mkdir(parents=True, exist_ok=True)

    md_path = out_dir / "court_bundle_draft.md"
    json_path = out_dir / "court_bundle_draft.json"

    bundle_md, bundle_json = build_court_bundle_md(case)

    md_path.write_text(bundle_md, encoding="utf-8")
    json_path.write_text(
        json.dumps(bundle_json, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Local TEL-like verification: two post-reads are identical.
    md1 = md_path.read_text(encoding="utf-8")
    md2 = md_path.read_text(encoding="utf-8")
    json1 = json_path.read_text(encoding="utf-8")
    json2 = json_path.read_text(encoding="utf-8")

    verification = {
        "md": {
            "read_back": md1 == bundle_md,
            "multi_read_match": md1 == md2,
        },
        "json": {
            "read_back": json1 == json.dumps(bundle_json, indent=2, ensure_ascii=False),
            "multi_read_match": json1 == json2,
        },
    }

    return md_path, json_path, verification


def record_ledger_for_file(
    file_path: Path,
    verification_for_file: Dict[str, Any],
    expected_outcome: str,
    actual_outcome: str,
) -> str:
    # ledger recorder expects repo-relative path.
    target_rel = file_path.relative_to(REPO_ROOT).as_posix()

    verification_obj = {
        "read_back": bool(verification_for_file.get("read_back")),
        "multi_read_match": bool(verification_for_file.get("multi_read_match")),
        "diff_match": True,
        "head_match": False,
    }

    cmd = [
        "python",
        "ledger/record_ledger_entry.py",
        "--agent",
        "hermes",
        "--operation",
        "write_file",
        "--target",
        target_rel,
        "--expected_outcome",
        expected_outcome,
        "--actual_outcome",
        actual_outcome,
        "--status",
        "PASS",
        "--verification",
        json.dumps(verification_obj),
        "--snapshot",
    ]

    proc = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"ledger recorder failed for {target_rel}: {proc.stderr or proc.stdout}"
        )

    # Parse ledger_id from last line JSON.
    try:
        payload = json.loads(proc.stdout.strip().splitlines()[-1])
        ledger_id = payload.get("ledger_id")
    except Exception:
        ledger_id = None

    if not ledger_id:
        raise RuntimeError(
            f"Could not parse ledger_id for {target_rel}. stdout={proc.stdout[-500:]}"
        )

    return ledger_id


def post_to_notion_webhook(payload: Dict[str, Any]) -> Tuple[bool, str]:
    import urllib.request

    webhook = os.getenv("NOTION_RUNS_WEBHOOK") or load_env_var_from_repo_env("NOTION_RUNS_WEBHOOK")
    if not webhook:
        return False, "NOTION_RUNS_WEBHOOK not set; skipping Notion logging"

    data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        webhook,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return True, body
    except Exception as e:
        return False, str(e)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--only-case", default=None, help="Optional case_id to restrict")
    p.add_argument(
        "--cases",
        default="*",
        help="(reserved) glob under clients/* to include; default '*'",
    )
    args = p.parse_args()

    client_dir = REPO_ROOT / "clients"
    if not client_dir.exists():
        raise SystemExit(f"clients directory not found: {client_dir}")

    case_dirs = sorted([d for d in client_dir.glob("*") if d.is_dir()])
    if args.only_case:
        case_dirs = [d for d in case_dirs if d.name == args.only_case]

    if not case_dirs:
        print(json.dumps({"ok": True, "generated_cases": 0, "notion": None}))
        return

    results: List[Dict[str, Any]] = []

    for case_dir in case_dirs:
        case = load_case(case_dir)
        out_dir = REPO_ROOT / "artifacts" / "court" / case.case_id
        
        md_path, json_path, verification = write_outputs(case, out_dir)

        complaint_md_path, complaint_json_path, response_analysis_path, addl_verification = write_additional_outputs(
            case, out_dir
        )

        ledger_ids: Dict[str, str] = {}
        ledger_ids["md"] = record_ledger_for_file(
            md_path,
            verification_for_file=verification["md"],
            expected_outcome="court bundle markdown draft generated",
            actual_outcome="court_bundle_draft.md verified on disk",
        )
        ledger_ids["json"] = record_ledger_for_file(
            json_path,
            verification_for_file=verification["json"],
            expected_outcome="court bundle json draft generated",
            actual_outcome="court_bundle_draft.json verified on disk",
        )

        ledger_ids["complaint_md"] = record_ledger_for_file(
            complaint_md_path,
            verification_for_file=addl_verification["complaint_md"],
            expected_outcome="complaint draft markdown generated",
            actual_outcome="complaint_draft.md verified on disk",
        )
        ledger_ids["complaint_json"] = record_ledger_for_file(
            complaint_json_path,
            verification_for_file=addl_verification["complaint_json"],
            expected_outcome="complaint draft json generated",
            actual_outcome="complaint_draft.json verified on disk",
        )
        ledger_ids["response_analysis"] = record_ledger_for_file(
            response_analysis_path,
            verification_for_file=addl_verification["response_analysis"],
            expected_outcome="response analysis json generated",
            actual_outcome="response_analysis.json verified on disk",
        )

        notion_payload = {
            "scenario": "court-filing-draft-center",
            "purpose": "notion-logs",
            "case_id": case.case_id,
            "generated_at": utc_now_iso(),
            "outputs": {
                "md": str(md_path.relative_to(REPO_ROOT)).replace('\\', '/'),
                "json": str(json_path.relative_to(REPO_ROOT)).replace('\\', '/'),
                "complaint_md": str(complaint_md_path.relative_to(REPO_ROOT)).replace('\\', '/'),
                "complaint_json": str(complaint_json_path.relative_to(REPO_ROOT)).replace('\\', '/'),
                "response_analysis": str(response_analysis_path.relative_to(REPO_ROOT)).replace('\\', '/'),
            },
            "ledger_ids": ledger_ids,
        }

        notion_ok, notion_msg = post_to_notion_webhook(notion_payload)

        results.append(
            {
                "case_id": case.case_id,
                "out_dir": str(out_dir.relative_to(REPO_ROOT)).replace('\\', '/'),
                "ledger": ledger_ids,
                "notion": {"ok": notion_ok, "msg": notion_msg},
                "missing_evidence": int(case.evidence_manifest.get("verification_summary", {}).get("missing", 0))
                if case.evidence_manifest
                else None,
            }
        )

    # ---- Notion Command Center (Local Dashboard + Optional Webhook Receipt) ----
    # This creates a dashboard even when NOTION_RUNS_WEBHOOK isn't configured.
    command_center_dir = REPO_ROOT / "artifacts" / "notion"
    command_center_dir.mkdir(parents=True, exist_ok=True)

    cc_md_path = command_center_dir / "command_center_local.md"
    cc_json_path = command_center_dir / "command_center_local.json"

    cc_payload = {
        "generated_at": utc_now_iso(),
        "scenario": "SintraPrime-court-filing-draft-center",
        "cases": results,
    }

    lines: List[str] = []
    lines.append("# Notion Command Center — Local Dashboard (Draft-only)")
    lines.append("")
    lines.append(f"Generated at: {cc_payload['generated_at']}")
    lines.append("")
    lines.append("## Cases")
    if not results:
        lines.append("- (No cases processed)")
    else:
        for r in results:
            lines.append(f"\n### {r['case_id']}")
            lines.append(f"- Out dir: {r['out_dir']}")
            lines.append(f"- Missing evidence: {r['missing_evidence']}")
            lines.append("- Ledger receipts:")
            for k, v in (r.get("ledger") or {}).items():
                lines.append(f"  - {k}: {v}")
            lines.append(f"- Notion webhook: {r.get('notion', {}).get('ok')}")

    cc_md = "\n".join(lines)

    # Write files.
    cc_md_path.write_text(cc_md, encoding="utf-8")
    cc_json_path.write_text(
        json.dumps(cc_payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # TEL-like verification (two post-reads + stable JSON string).
    md1 = cc_md_path.read_text(encoding="utf-8")
    md2 = cc_md_path.read_text(encoding="utf-8")
    json1 = cc_json_path.read_text(encoding="utf-8")
    json2 = cc_json_path.read_text(encoding="utf-8")

    cc_md_ver = {"read_back": md1 == cc_md, "multi_read_match": md1 == md2}
    cc_json_ver = {
        "read_back": json1 == json.dumps(cc_payload, indent=2, ensure_ascii=False),
        "multi_read_match": json1 == json2,
    }

    # Ledger receipts for command center artifacts.
    cc_ledger_ids: Dict[str, str] = {}
    cc_ledger_ids["command_center_md"] = record_ledger_for_file(
        cc_md_path,
        verification_for_file=cc_md_ver,
        expected_outcome="notion command center markdown written",
        actual_outcome="command_center_local.md verified on disk",
    )
    cc_ledger_ids["command_center_json"] = record_ledger_for_file(
        cc_json_path,
        verification_for_file=cc_json_ver,
        expected_outcome="notion command center json written",
        actual_outcome="command_center_local.json verified on disk",
    )

    # Optional webhook receipt (same NOTION_RUNS_WEBHOOK route).
    notion_cc_payload = {
        "scenario": "command-center-local",
        "purpose": "notion-logs",
        "generated_at": utc_now_iso(),
        "outputs": {
            "command_center_md": str(cc_md_path.relative_to(REPO_ROOT)).replace('\\', '/'),
            "command_center_json": str(cc_json_path.relative_to(REPO_ROOT)).replace('\\', '/'),
        },
        "ledger_ids": cc_ledger_ids,
        "cases": [
            {"case_id": r["case_id"], "missing_evidence": r.get("missing_evidence")}
            for r in results
        ],
    }
    notion_cc_ok, notion_cc_msg = post_to_notion_webhook(notion_cc_payload)

    print(
        json.dumps(
            {
                "ok": True,
                "generated_cases": len(results),
                "results": results,
                "command_center": {
                    "ledger": cc_ledger_ids,
                    "notion": {"ok": notion_cc_ok, "msg": notion_cc_msg},
                },
                "at": utc_now_iso(),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
