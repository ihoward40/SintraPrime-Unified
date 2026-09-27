from __future__ import annotations

import json
from pathlib import Path

import jsonschema


REPO_ROOT = Path(__file__).resolve().parents[1]
BOE_ROOT = REPO_ROOT / "BOE"
ACCEPTANCE_REVIEW = BOE_ROOT / "05-Acceptance" / "M1_Acceptance_Review.md"
DECISION_SCHEMA = BOE_ROOT / "01-Decision-Register" / "Decision_Register.schema.json"
DECISION_REGISTER = BOE_ROOT / "01-Decision-Register" / "Decision_Register.jsonl"
COMPLETED_PASSPORTS = BOE_ROOT / "02-Agent-Passports" / "Completed"


def test_m1_acceptance_review_evidences_required_baseline_artifacts():
    content = ACCEPTANCE_REVIEW.read_text(encoding="utf-8")

    for criterion in [
        "Decision Register operational",
        "Five Agent Passports completed",
        "Portfolio Registry established",
        "First Weekly Life Board held",
        "DR-0001 recorded",
        "First institutional asset created",
    ]:
        assert f"- [x] {criterion}" in content

    for relative_path in [
        "00-Program/BOE-001_Master_Implementation_Spec.md",
        "01-Decision-Register/DRS-001.md",
        "01-Decision-Register/Decision_Register.schema.json",
        "01-Decision-Register/Decision_Register.jsonl",
        "02-Agent-Passports/AOP-001.md",
        "02-Agent-Passports/Agent_Passport_Template.md",
        "03-Portfolio-Registry/Portfolio_Registry.md",
        "04-Weekly-Life-Board/Weekly_Life_Board_Packet.md",
    ]:
        assert (BOE_ROOT / relative_path).exists()

    assert len(sorted(COMPLETED_PASSPORTS.glob("AP-*.md"))) == 5


def test_dr_0001_matches_required_decision_register_fields():
    schema = json.loads(DECISION_SCHEMA.read_text(encoding="utf-8"))
    records = [
        json.loads(line)
        for line in DECISION_REGISTER.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    record = next(item for item in records if item["decision_id"] == "DR-0001")

    validator_class = jsonschema.validators.validator_for(schema)
    validator_class.check_schema(schema)
    validator_class(schema).validate(record)
    assert record["decision_id"] == "DR-0001"
    assert record["status"] == "active"
    assert record["execution_items"]
    assert record["evidence"]

    for evidence_entry in record["evidence"]:
        assert {"source", "captured_on", "note"} == set(evidence_entry)
        assert (REPO_ROOT / evidence_entry["source"]).exists()
