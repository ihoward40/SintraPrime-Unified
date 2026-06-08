import json
import shutil
import requests
import time
from datetime import datetime, timezone
from pathlib import Path
from difflib import get_close_matches

BASE_URL = "http://localhost:8000"
WATCH_INTERVAL_SECONDS = 10

INTAKE_DIR = Path("intake")
PROCESSED_DIR = Path("processed")
ERROR_DIR = Path("errors")
EXPORTS_DIR = Path("exports")

for folder in [INTAKE_DIR, PROCESSED_DIR, ERROR_DIR, EXPORTS_DIR]:
    folder.mkdir(exist_ok=True)


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def api_get(path):
    response = requests.get(f"{BASE_URL}{path}", timeout=10)
    response.raise_for_status()
    return response.json()


def api_post(path, payload):
    response = requests.post(f"{BASE_URL}{path}", json=payload, timeout=10)
    response.raise_for_status()
    return response.json()


def check_health():
    return api_get("/api/recovery/health")


def get_cases():
    data = api_get("/api/recovery/cases")
    return data.get("cases", [])


def normalize_text(value):
    return str(value or "").strip().lower()


def resolve_case_id(item):
    if item.get("case_id"):
        return item["case_id"]

    case_name = item.get("case_name")
    if not case_name:
        raise ValueError("Evidence item must include either case_id or case_name.")

    cases = get_cases()

    lookup = {
        normalize_text(case["case_name"]): case["case_id"]
        for case in cases
    }

    requested = normalize_text(case_name)

    if requested in lookup:
        return lookup[requested]

    partial_matches = []
    for full_name, case_id in lookup.items():
        if requested in full_name or full_name in requested:
            partial_matches.append((full_name, case_id))

    if len(partial_matches) == 1:
        return partial_matches[0][1]

    if len(partial_matches) > 1:
        names = [name for name, _ in partial_matches]
        raise ValueError(f"Ambiguous case_name '{case_name}'. Matches found: {names}")

    close = get_close_matches(requested, lookup.keys(), n=1, cutoff=0.55)

    if close:
        return lookup[close[0]]

    available = [case["case_name"] for case in cases]
    raise ValueError(
        f"Could not resolve case_name '{case_name}'. Available cases: {available}"
    )


def load_json_file(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def move_file(source_path, target_dir):
    target_path = target_dir / source_path.name

    if target_path.exists():
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_path = target_dir / f"{source_path.stem}_{stamp}{source_path.suffix}"

    shutil.move(str(source_path), str(target_path))
    return target_path


def prepare_evidence_item(item):
    item = dict(item)

    resolved_case_id = resolve_case_id(item)
    item["case_id"] = resolved_case_id
    item.pop("case_name", None)

    required = ["case_id", "evidence_type", "title", "source"]
    missing = [field for field in required if field not in item]

    if missing:
        raise ValueError(f"Missing required fields after case resolution: {missing}")

    return item


def normalize_intake_payload(raw):
    if "evidence_items" in raw:
        items = raw["evidence_items"]
    else:
        items = [raw]

    prepared_items = [prepare_evidence_item(item) for item in items]

    return {
        "evidence_items": prepared_items
    }


def submit_evidence_batch(payload):
    return api_post("/api/recovery/evidence/add-batch", payload)


def create_receipt(action, evidence_used=None, output_created=None, next_step=None, status="completed"):
    payload = {
        "agent": "Howard Intake Watch Agent",
        "action_performed": action,
        "evidence_used": evidence_used or [],
        "output_created": output_created,
        "external_action": False,
        "approval_required": True,
        "status": status,
        "next_step": next_step or "Continue evidence intake. External action remains locked."
    }

    return api_post("/api/recovery/receipts/create", payload)


def export_master_markdown():
    data = api_get("/api/recovery/export/markdown")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = EXPORTS_DIR / f"howard_recovery_master_{timestamp}.md"

    output_path.write_text(data["markdown"], encoding="utf-8")

    return {
        "file": str(output_path),
        "case_count": data.get("case_count"),
        "evidence_count": data.get("evidence_count"),
        "receipt_count": data.get("receipt_count")
    }


def process_file(path):
    print(f"[{now_iso()}] Processing: {path}")

    raw = load_json_file(path)
    payload = normalize_intake_payload(raw)

    print("Resolved intake payload:")
    print(json.dumps(payload, indent=2))

    result = submit_evidence_batch(payload)

    evidence_ids = [
        item["evidence_id"]
        for item in result.get("evidence", [])
    ]

    receipt = create_receipt(
        action=f"Watch agent processed intake evidence file: {path.name}",
        evidence_used=evidence_ids,
        output_created="Batch evidence records imported from intake folder.",
        next_step="Review evidence records and attach source files where available."
    )

    processed_path = move_file(path, PROCESSED_DIR)

    return {
        "file": path.name,
        "processed_path": str(processed_path),
        "evidence_ids": evidence_ids,
        "batch_receipt": result.get("receipt", {}).get("receipt_id"),
        "agent_receipt": receipt.get("receipt_id")
    }


def process_once():
    json_files = sorted(INTAKE_DIR.glob("*.json"))

    if not json_files:
        return []

    processed_results = []

    for path in json_files:
        try:
            result = process_file(path)
            processed_results.append(result)
            print("Processed:", result)

        except Exception as e:
            print(f"ERROR processing {path.name}: {e}")
            error_path = move_file(path, ERROR_DIR)
            print(f"Moved to errors: {error_path}")

            try:
                create_receipt(
                    action=f"Watch agent failed to process intake evidence file: {path.name}",
                    evidence_used=[],
                    output_created=str(error_path),
                    next_step=f"Review JSON format or case-name resolution error: {e}",
                    status="error"
                )
            except Exception as receipt_error:
                print(f"Could not create error receipt: {receipt_error}")

    if processed_results:
        print("Exporting updated master markdown...")
        export = export_master_markdown()
        print("Export saved:", export["file"])

        create_receipt(
            action="Howard Intake Watch Agent completed processing cycle.",
            evidence_used=[
                evidence_id
                for result in processed_results
                for evidence_id in result.get("evidence_ids", [])
            ],
            output_created=export["file"],
            next_step="Continue watching intake folder for new evidence files."
        )

    return processed_results


def run_watch_mode():
    print("Howard Intake Watch Agent starting...")
    print("Phase 2F Folder Watch Mode: ACTIVE")
    print(f"Watching folder: {INTAKE_DIR.resolve()}")
    print(f"Check interval: {WATCH_INTERVAL_SECONDS} seconds")
    print("Press Ctrl + C to stop.")
    print("External action remains locked.")

    health = check_health()
    print("Health:", health)

    create_receipt(
        action="Howard Intake Watch Agent started folder watch mode.",
        evidence_used=[],
        output_created=str(INTAKE_DIR.resolve()),
        next_step="Drop evidence JSON files into intake folder for automatic processing."
    )

    while True:
        try:
            results = process_once()

            if not results:
                print(f"[{now_iso()}] No new intake files. Watching...")

            time.sleep(WATCH_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            print("\nWatch mode stopped by user.")

            create_receipt(
                action="Howard Intake Watch Agent stopped by user.",
                evidence_used=[],
                output_created=None,
                next_step="Restart watch mode when ready."
            )

            break

        except Exception as e:
            print(f"Watch loop error: {e}")

            try:
                create_receipt(
                    action="Howard Intake Watch Agent encountered watch loop error.",
                    evidence_used=[],
                    output_created=None,
                    next_step=f"Review watch loop error: {e}",
                    status="error"
                )
            except Exception:
                pass

            time.sleep(WATCH_INTERVAL_SECONDS)


if __name__ == "__main__":
    run_watch_mode()
