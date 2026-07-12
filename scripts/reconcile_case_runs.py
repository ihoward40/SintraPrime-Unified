"""Reconcile interrupted monetization case runs.

Detects and repairs published artifacts that have a pending run manifest but did
not finish ledger/idempotency finalization. Dry-run is the default recommended
mode for operators; this script never deletes evidence automatically.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def load_service():
    sys.path.insert(0, str(REPO_ROOT))
    from backend.stripe_payments.services.case_security import VerifiedPaymentEvent
    from backend.stripe_payments.services.case_starter_service import case_starter_service
    return VerifiedPaymentEvent, case_starter_service


def inspect_manifest(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    case_id = data.get("case_id")
    final_client = REPO_ROOT / "clients" / str(case_id)
    final_artifact = REPO_ROOT / "artifacts" / "court" / str(case_id)
    return {
        "manifest": path.relative_to(REPO_ROOT).as_posix(),
        "case_id": case_id,
        "stage": data.get("stage"),
        "final_client_exists": final_client.exists(),
        "final_artifact_exists": final_artifact.exists(),
        "repairable": data.get("stage") in {"LEDGER_PENDING", "PUBLISHED"} and final_client.exists() and final_artifact.exists(),
    }


def reconcile_manifest(path: Path, *, dry_run: bool) -> dict:
    status = inspect_manifest(path)
    if dry_run or not status["repairable"]:
        status["action"] = "would_repair" if status["repairable"] else "inspect_only"
        return status
    payment_event_cls, service = load_service()
    data = json.loads(path.read_text(encoding="utf-8"))
    event = payment_event_cls(
        event_id=data["event_id"],
        event_type="checkout.session.completed",
        payment_session_id=data["payment_session_id"],
        payment_status="paid",
        session_status="complete",
        amount_total=0,
        currency="usd",
        tier="reconcile",
        case_id=data["case_id"],
        stripe_created_at=data.get("created_at", data.get("updated_at")),
        verified_at=data.get("created_at", data.get("updated_at")),
        key_id="reconcile",
        schema_version="internal_payment_event.v1",
        body_sha256=data["body_sha256"],
    )
    response = service._recover_published_run(
        manifest_path=path,
        case_id=data["case_id"],
        verified_event=event,
        final_client_dir=REPO_ROOT / "clients" / data["case_id"],
        final_artifact_dir=REPO_ROOT / "artifacts" / "court" / data["case_id"],
    )
    status["action"] = "repaired" if response else "not_repaired"
    return status


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--case-id")
    group.add_argument("--all", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    manifest_root = REPO_ROOT / ".case_runs" / "manifests"
    manifests = sorted(manifest_root.glob("*.json")) if manifest_root.exists() else []
    if args.case_id:
        manifests = [p for p in manifests if json.loads(p.read_text(encoding="utf-8")).get("case_id") == args.case_id]
    results = [reconcile_manifest(path, dry_run=args.dry_run) for path in manifests]
    if args.as_json:
        print(json.dumps({"results": results}, indent=2, sort_keys=True))
    else:
        for result in results:
            print(f"{result['case_id']} {result['stage']} {result['action']} repairable={result['repairable']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
