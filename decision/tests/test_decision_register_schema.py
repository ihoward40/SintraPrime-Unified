import copy

import pytest
from jsonschema import ValidationError, validate

from decision.register.schema import (
    DECISION_REGISTER_ENTRY_SCHEMA,
    DECISION_REGISTER_SCHEMA_VERSION,
    DECISION_REGISTER_STORAGE_MODEL,
)


def _entry_with_link(link_type: str, include_sha256: bool) -> dict:
    link = {"link_type": link_type, "target_id": "TGT-1"}
    if include_sha256:
        link["sha256"] = "a" * 64
    return {
        "schema_version": DECISION_REGISTER_SCHEMA_VERSION,
        "register_id": "REG-1",
        "decision_id": "DEC-1",
        "run_id": "RUN-1",
        "recorded_at": "2026-01-01T00:00:00Z",
        "contract": {"name": "case_route", "version": "1", "semantic_sha256": "b" * 64},
        "state": {"canonical_version": "sp-decision-state-v1", "sha256": "c" * 64},
        "result": {"kind": "DECISION"},
        "policy": {"decision": "SHADOW_ONLY", "risk": "ELEVATED"},
        "traceability": {"receipt_hash": "d" * 64, "links": [link]},
    }


def test_decision_register_entry_required_fields():
    required = set(DECISION_REGISTER_ENTRY_SCHEMA["required"])
    assert required == {
        "schema_version",
        "register_id",
        "decision_id",
        "run_id",
        "recorded_at",
        "contract",
        "state",
        "result",
        "policy",
        "traceability",
    }
    assert DECISION_REGISTER_ENTRY_SCHEMA["properties"]["schema_version"]["const"] == (
        DECISION_REGISTER_SCHEMA_VERSION
    )


def test_decision_register_traceability_links_require_targets():
    traceability = DECISION_REGISTER_ENTRY_SCHEMA["properties"]["traceability"]
    assert "receipt_hash" in traceability["required"]
    assert "links" in traceability["required"]
    prev_hash = traceability["properties"]["prev_receipt_hash"]
    assert prev_hash["anyOf"][0]["type"] == "null"
    assert prev_hash["anyOf"][1] == {"type": "string", "minLength": 64, "maxLength": 64}
    links = traceability["properties"]["links"]
    assert links["minItems"] == 1
    assert set(links["items"]["required"]) == {"link_type", "target_id"}
    assert set(links["items"]["properties"]["link_type"]["enum"]) == {
        "contract",
        "state",
        "receipt",
        "run",
        "evidence",
    }
    rule = links["items"]["allOf"][0]
    assert set(rule["if"]["properties"]["link_type"]["enum"]) == {"contract", "state", "receipt"}
    assert rule["then"]["required"] == ["sha256"]


def test_decision_register_storage_model_relations_and_traceability():
    storage = DECISION_REGISTER_STORAGE_MODEL
    assert storage["schema_version"] == DECISION_REGISTER_SCHEMA_VERSION
    tables = storage["tables"]
    assert "decision_register_entries" in tables
    assert "decision_register_relations" in tables
    assert "decision_register_traceability_links" in tables
    assert "receipt_hash TEXT NOT NULL UNIQUE" in tables["decision_register_entries"]
    assert "prev_receipt_hash TEXT" in tables["decision_register_entries"]
    assert "UNIQUE(decision_id, run_id)" not in tables["decision_register_entries"]
    assert "UNIQUE(source_register_id, target_register_id, relation_type)" in tables["decision_register_relations"]
    assert "FOREIGN KEY(source_register_id)" in tables["decision_register_relations"]
    assert "FOREIGN KEY(target_register_id)" in tables["decision_register_relations"]
    assert "FOREIGN KEY(register_id)" in tables["decision_register_traceability_links"]
    assert "CHECK(link_type NOT IN ('contract', 'state', 'receipt') OR sha256 IS NOT NULL)" in tables[
        "decision_register_traceability_links"
    ]
    indexes = storage["indexes"]
    assert "decision_register_entries_decision_run_idx" in indexes
    assert "decision_register_relations_source_idx" in indexes
    assert "decision_register_traceability_links_register_idx" in indexes


@pytest.mark.parametrize("link_type", ["contract", "state", "receipt"])
def test_schema_requires_sha256_for_hashed_link_types(link_type: str):
    payload = _entry_with_link(link_type=link_type, include_sha256=False)
    with pytest.raises(ValidationError):
        validate(instance=payload, schema=DECISION_REGISTER_ENTRY_SCHEMA)


@pytest.mark.parametrize("link_type", ["run", "evidence"])
def test_schema_allows_non_hashed_link_types_without_sha256(link_type: str):
    payload = _entry_with_link(link_type=link_type, include_sha256=False)
    validate(instance=payload, schema=DECISION_REGISTER_ENTRY_SCHEMA)


def test_schema_allows_nullable_previous_receipt_hash():
    payload = _entry_with_link(link_type="receipt", include_sha256=True)
    payload["traceability"]["prev_receipt_hash"] = None
    validate(instance=payload, schema=DECISION_REGISTER_ENTRY_SCHEMA)
    payload2 = copy.deepcopy(payload)
    payload2["traceability"]["prev_receipt_hash"] = "e" * 64
    validate(instance=payload2, schema=DECISION_REGISTER_ENTRY_SCHEMA)
