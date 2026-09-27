from decision.register.schema import (
    DECISION_REGISTER_ENTRY_SCHEMA,
    DECISION_REGISTER_SCHEMA_VERSION,
    DECISION_REGISTER_STORAGE_MODEL,
)


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
    assert "FOREIGN KEY(source_register_id)" in tables["decision_register_relations"]
    assert "FOREIGN KEY(target_register_id)" in tables["decision_register_relations"]
    assert "FOREIGN KEY(register_id)" in tables["decision_register_traceability_links"]
    indexes = storage["indexes"]
    assert "decision_register_entries_decision_run_idx" in indexes
    assert "decision_register_relations_source_idx" in indexes
    assert "decision_register_traceability_links_register_idx" in indexes
