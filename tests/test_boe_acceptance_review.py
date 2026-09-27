from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BOE_ROOT = REPO_ROOT / "BOE"
ACCEPTANCE_REVIEW = BOE_ROOT / "05-Acceptance" / "M1_Acceptance_Review.md"
DECISION_SCHEMA = BOE_ROOT / "01-Decision-Register" / "Decision_Register.schema.json"
DECISION_REGISTER = BOE_ROOT / "01-Decision-Register" / "Decision_Register.jsonl"
COMPLETED_PASSPORTS = BOE_ROOT / "02-Agent-Passports" / "Completed"


def _assert_matches_schema(value, schema):
    schema_type = schema.get("type")

    if schema_type == "object":
        assert isinstance(value, dict)
        required = schema.get("required", [])
        assert set(required) == set(value)
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            assert set(value).issubset(properties)
        for key, item_schema in properties.items():
            if key in value:
                _assert_matches_schema(value[key], item_schema)
        return

    if schema_type == "array":
        assert isinstance(value, list)
        assert len(value) >= schema.get("minItems", 0)
        item_schema = schema.get("items")
        if item_schema is not None:
            for item in value:
                _assert_matches_schema(item, item_schema)
        return

    if schema_type == "string":
        assert isinstance(value, str)
        assert len(value) >= schema.get("minLength", 0)
        pattern = schema.get("pattern")
        if pattern is not None:
            assert re.fullmatch(pattern, value)
        enum = schema.get("enum")
        if enum is not None:
            assert value in enum
        if schema.get("format") == "date":
            date.fromisoformat(value)
        return


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
    record = json.loads(DECISION_REGISTER.read_text(encoding="utf-8").strip())

    _assert_matches_schema(record, schema)
    assert record["decision_id"] == "DR-0001"
    assert record["status"] == "active"
    assert record["execution_items"]
    assert record["evidence"]

    for evidence_entry in record["evidence"]:
        assert {"source", "captured_on", "note"} == set(evidence_entry)
        assert (REPO_ROOT / evidence_entry["source"]).exists()
