import requests
from datetime import datetime, timezone
from pathlib import Path

BASE_URL = "http://localhost:8000"

OUTPUT_DIR = Path("exports")
OUTPUT_DIR.mkdir(exist_ok=True)

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def check_health():
    r = requests.get(f"{BASE_URL}/api/recovery/health", timeout=10)
    r.raise_for_status()
    return r.json()

def export_master_markdown():
    r = requests.get(f"{BASE_URL}/api/recovery/export/markdown", timeout=10)
    r.raise_for_status()
    data = r.json()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = OUTPUT_DIR / f"howard_recovery_master_{timestamp}.md"

    output_path.write_text(data["markdown"], encoding="utf-8")

    return {
        "file": str(output_path),
        "case_count": data.get("case_count"),
        "evidence_count": data.get("evidence_count"),
        "receipt_count": data.get("receipt_count")
    }

def create_receipt(action, evidence_used=None, output_created=None, next_step=None):
    payload = {
        "agent": "Howard Recovery Local Agent",
        "action_performed": action,
        "evidence_used": evidence_used or [],
        "output_created": output_created,
        "external_action": False,
        "approval_required": True,
        "status": "completed",
        "next_step": next_step or "Continue evidence intake and case packet generation."
    }

    r = requests.post(f"{BASE_URL}/api/recovery/receipts/create", json=payload, timeout=10)
    r.raise_for_status()
    return r.json()

def main():
    print("Checking SintraPrime health...")
    health = check_health()
    print("Health:", health)

    print("Exporting master markdown...")
    export = export_master_markdown()
    print("Export saved:", export["file"])

    receipt = create_receipt(
        action="Local agent exported Howard Recovery master markdown packet.",
        output_created=export["file"],
        next_step="Review exported markdown, then upgrade to downloadable PDF packet generation."
    )

    print("Receipt created:", receipt["receipt_id"])
    print("Done. External action remained locked.")

if __name__ == "__main__":
    main()
