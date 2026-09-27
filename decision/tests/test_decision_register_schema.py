import copy
import sqlite3

import pytest
from jsonschema import Draft202012Validator, FormatChecker, ValidationError

from decision.register.schema import (
    ALLOWED_RELATION_TYPES,
    ALLOWED_TRACE_LINK_TYPES,
    DECISION_REGISTER_ENTRY_SCHEMA,
    DECISION_REGISTER_SCHEMA_VERSION,
    DECISION_REGISTER_STORAGE_MODEL,
    HASHED_TRACE_LINK_TYPES,
    NON_HASHED_TRACE_LINK_TYPES,
    SHA256_HEX_PATTERN,
)

_VALIDATOR = Draft202012Validator(
    DECISION_REGISTER_ENTRY_SCHEMA, format_checker=FormatChecker()
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


def _sql_enum(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


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
    assert DECISION_REGISTER_ENTRY_SCHEMA["additionalProperties"] is False


def test_decision_register_traceability_links_require_targets():
    traceability = DECISION_REGISTER_ENTRY_SCHEMA["properties"]["traceability"]
    assert "receipt_hash" in traceability["required"]
    assert "links" in traceability["required"]
    prev_hash = traceability["properties"]["prev_receipt_hash"]
    assert prev_hash["anyOf"][0]["type"] == "null"
    assert prev_hash["anyOf"][1] == {"type": "string", "pattern": SHA256_HEX_PATTERN}
    links = traceability["properties"]["links"]
    assert links["minItems"] == 1
    assert set(links["items"]["required"]) == {"link_type", "target_id"}
    assert set(links["items"]["properties"]["link_type"]["enum"]) == set(ALLOWED_TRACE_LINK_TYPES)
    rule = links["items"]["allOf"][0]
    assert set(rule["if"]["properties"]["link_type"]["enum"]) == set(HASHED_TRACE_LINK_TYPES)
    assert rule["then"]["required"] == ["sha256"]
    assert rule["else"] == {"not": {"required": ["sha256"]}}
    assert links["items"]["additionalProperties"] is False


def test_decision_register_storage_model_relations_and_traceability():
    storage = DECISION_REGISTER_STORAGE_MODEL
    assert storage["schema_version"] == DECISION_REGISTER_SCHEMA_VERSION
    tables = storage["tables"]
    assert "decision_register_entries" in tables
    assert "decision_register_relations" in tables
    assert "decision_register_traceability_links" in tables
    assert "schema_version TEXT NOT NULL" in tables["decision_register_entries"]
    assert "CHECK(schema_version = 'sp-decision-register-v1')" in tables["decision_register_entries"]
    assert "recorded_at GLOB '????-??-??T??:??:??Z'" in tables["decision_register_entries"]
    assert "strftime('%Y-%m-%dT%H:%M:%SZ', recorded_at) IS NOT NULL" in tables[
        "decision_register_entries"
    ]
    assert "strftime('%Y-%m-%dT%H:%M:%SZ', recorded_at) = recorded_at" in tables[
        "decision_register_entries"
    ]
    assert "receipt_hash TEXT NOT NULL UNIQUE" in tables["decision_register_entries"]
    assert "prev_receipt_hash TEXT" in tables["decision_register_entries"]
    assert "UNIQUE(decision_id, run_id)" not in tables["decision_register_entries"]
    assert "UNIQUE(source_register_id, target_register_id, relation_type)" in tables["decision_register_relations"]
    assert f"CHECK(relation_type IN ({_sql_enum(ALLOWED_RELATION_TYPES)}))" in tables[
        "decision_register_relations"
    ]
    assert "CHECK(source_register_id <> target_register_id)" in tables["decision_register_relations"]
    assert "strftime('%Y-%m-%dT%H:%M:%SZ', created_at) IS NOT NULL" in tables["decision_register_relations"]
    assert "strftime('%Y-%m-%dT%H:%M:%SZ', created_at) = created_at" in tables["decision_register_relations"]
    assert "CHECK(length(contract_semantic_sha256) = 64" in tables["decision_register_entries"]
    assert "CHECK(length(state_sha256) = 64" in tables["decision_register_entries"]
    assert "CHECK(length(receipt_hash) = 64" in tables["decision_register_entries"]
    assert "FOREIGN KEY(source_register_id) REFERENCES decision_register_entries(register_id) ON DELETE CASCADE" in tables[
        "decision_register_relations"
    ]
    assert "FOREIGN KEY(target_register_id) REFERENCES decision_register_entries(register_id) ON DELETE CASCADE" in tables[
        "decision_register_relations"
    ]
    assert "FOREIGN KEY(register_id) REFERENCES decision_register_entries(register_id) ON DELETE CASCADE" in tables[
        "decision_register_traceability_links"
    ]
    assert f"CHECK(link_type IN ({_sql_enum(ALLOWED_TRACE_LINK_TYPES)}))" in tables[
        "decision_register_traceability_links"
    ]
    assert "strftime('%Y-%m-%dT%H:%M:%SZ', created_at) IS NOT NULL" in tables[
        "decision_register_traceability_links"
    ]
    assert "strftime('%Y-%m-%dT%H:%M:%SZ', created_at) = created_at" in tables[
        "decision_register_traceability_links"
    ]
    assert "CHECK(" in tables["decision_register_traceability_links"]
    assert f"OR (link_type IN ({_sql_enum(NON_HASHED_TRACE_LINK_TYPES)}) AND sha256 IS NULL)" in tables[
        "decision_register_traceability_links"
    ]
    assert "CHECK(sha256 IS NULL OR (length(sha256) = 64" in tables["decision_register_traceability_links"]
    assert f"(link_type IN ({_sql_enum(HASHED_TRACE_LINK_TYPES)}) AND sha256 IS NOT NULL)" in tables[
        "decision_register_traceability_links"
    ]
    indexes = storage["indexes"]
    assert "decision_register_entries_decision_run_idx" in indexes
    assert "decision_register_relations_source_idx" in indexes
    assert "decision_register_relations_target_idx" in indexes
    assert "decision_register_traceability_links_register_idx" in indexes
    assert "decision_register_traceability_links_identity_uq" in indexes


@pytest.mark.parametrize("link_type", ["contract", "state", "receipt"])
def test_schema_requires_sha256_for_hashed_link_types(link_type: str):
    payload = _entry_with_link(link_type=link_type, include_sha256=False)
    with pytest.raises(ValidationError):
        _VALIDATOR.validate(payload)


@pytest.mark.parametrize("link_type", ["run", "evidence"])
def test_schema_allows_non_hashed_link_types_without_sha256(link_type: str):
    payload = _entry_with_link(link_type=link_type, include_sha256=False)
    _VALIDATOR.validate(payload)


@pytest.mark.parametrize("link_type", ["run", "evidence"])
def test_schema_rejects_non_hashed_link_types_with_sha256(link_type: str):
    payload = _entry_with_link(link_type=link_type, include_sha256=True)
    with pytest.raises(ValidationError):
        _VALIDATOR.validate(payload)


def test_schema_allows_nullable_previous_receipt_hash():
    payload = _entry_with_link(link_type="receipt", include_sha256=True)
    payload["traceability"]["prev_receipt_hash"] = None
    _VALIDATOR.validate(payload)
    payload2 = copy.deepcopy(payload)
    payload2["traceability"]["prev_receipt_hash"] = "e" * 64
    _VALIDATOR.validate(payload2)


def test_schema_rejects_invalid_recorded_at_format():
    payload = _entry_with_link(link_type="receipt", include_sha256=True)
    payload["recorded_at"] = "not-a-timestamp"
    with pytest.raises(ValidationError):
        _VALIDATOR.validate(payload)


def test_schema_rejects_non_zulu_timestamp_offset():
    payload = _entry_with_link(link_type="receipt", include_sha256=True)
    payload["recorded_at"] = "2026-01-01T00:00:00+00:00"
    with pytest.raises(ValidationError):
        _VALIDATOR.validate(payload)


def test_schema_rejects_non_hex_sha256_values():
    payload = _entry_with_link(link_type="receipt", include_sha256=True)
    payload["traceability"]["receipt_hash"] = "g" * 64
    with pytest.raises(ValidationError):
        _VALIDATOR.validate(payload)


def test_schema_rejects_unknown_traceability_link_fields():
    payload = _entry_with_link(link_type="receipt", include_sha256=True)
    payload["traceability"]["links"][0]["extra_field"] = "unexpected"
    with pytest.raises(ValidationError):
        _VALIDATOR.validate(payload)


def test_storage_constraints_reject_invalid_hashes_and_link_rules():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    for ddl in DECISION_REGISTER_STORAGE_MODEL["tables"].values():
        conn.execute(ddl)
    for ddl in DECISION_REGISTER_STORAGE_MODEL["indexes"].values():
        conn.execute(ddl)

    valid_entry = (
        "REG-1",
        DECISION_REGISTER_SCHEMA_VERSION,
        "DEC-1",
        "RUN-1",
        "2026-01-01T00:00:00Z",
        "a" * 64,
        "b" * 64,
        "DECISION",
        "SHADOW_ONLY",
        "ELEVATED",
        "c" * 64,
        None,
        "{}",
    )
    conn.execute(
        """
        INSERT INTO decision_register_entries (
            register_id, schema_version, decision_id, run_id, recorded_at,
            contract_semantic_sha256, state_sha256, result_kind, policy_decision,
            policy_risk, receipt_hash, prev_receipt_hash, payload_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        valid_entry,
    )

    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """
            INSERT INTO decision_register_entries (
                register_id, schema_version, decision_id, run_id, recorded_at,
                contract_semantic_sha256, state_sha256, result_kind, policy_decision,
                policy_risk, receipt_hash, prev_receipt_hash, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "REG-2",
                DECISION_REGISTER_SCHEMA_VERSION,
                "DEC-1",
                "RUN-1",
                "2026-01-01T00:00:01Z",
                "a" * 64,
                "Z" * 64,
                "DECISION",
                "SHADOW_ONLY",
                "ELEVATED",
                "d" * 64,
                None,
                "{}",
            ),
        )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """
            INSERT INTO decision_register_entries (
                register_id, schema_version, decision_id, run_id, recorded_at,
                contract_semantic_sha256, state_sha256, result_kind, policy_decision,
                policy_risk, receipt_hash, prev_receipt_hash, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "REG-2C",
                DECISION_REGISTER_SCHEMA_VERSION,
                "DEC-1",
                "RUN-3",
                "2026-99-99T99:99:99Z",
                "a" * 64,
                "b" * 64,
                "DECISION",
                "SHADOW_ONLY",
                "ELEVATED",
                "1" * 64,
                None,
                "{}",
            ),
        )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """
            INSERT INTO decision_register_entries (
                register_id, schema_version, decision_id, run_id, recorded_at,
                contract_semantic_sha256, state_sha256, result_kind, policy_decision,
                policy_risk, receipt_hash, prev_receipt_hash, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "REG-2B",
                DECISION_REGISTER_SCHEMA_VERSION,
                "DEC-1",
                "RUN-2",
                "2026-01-01T00:00:00+00:00",
                "a" * 64,
                "b" * 64,
                "DECISION",
                "SHADOW_ONLY",
                "ELEVATED",
                "f" * 64,
                None,
                "{}",
            ),
        )

    conn.execute(
        """
        INSERT INTO decision_register_entries (
            register_id, schema_version, decision_id, run_id, recorded_at,
            contract_semantic_sha256, state_sha256, result_kind, policy_decision,
            policy_risk, receipt_hash, prev_receipt_hash, payload_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "REG-3",
            DECISION_REGISTER_SCHEMA_VERSION,
            "DEC-2",
            "RUN-2",
            "2026-01-01T00:00:05Z",
            "a" * 64,
            "b" * 64,
            "DECISION",
            "SHADOW_ONLY",
            "ELEVATED",
            "e" * 64,
            None,
            "{}",
        ),
    )
    conn.execute(
        """
        INSERT INTO decision_register_relations (
            source_register_id, target_register_id, relation_type, created_at
        ) VALUES (?, ?, ?, ?)
        """,
        ("REG-1", "REG-3", ALLOWED_RELATION_TYPES[0], "2026-01-01T00:00:06Z"),
    )
    conn.execute(
        """
        INSERT INTO decision_register_traceability_links (
            register_id, link_type, target_id, target_ref, sha256, metadata_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        ("REG-3", "receipt", "REC-3", None, "f" * 64, "{}", "2026-01-01T00:00:06Z"),
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """
            INSERT INTO decision_register_traceability_links (
                register_id, link_type, target_id, target_ref, sha256, metadata_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("REG-3", "receipt", "REC-3", None, "f" * 64, "{}", "2026-01-01T00:00:06Z"),
        )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """
            INSERT INTO decision_register_relations (
                source_register_id, target_register_id, relation_type, created_at
            ) VALUES (?, ?, ?, ?)
            """,
            ("REG-1", "REG-3", ALLOWED_RELATION_TYPES[0], "2026-01-01T00:00:07Z"),
        )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """
            INSERT INTO decision_register_relations (
                source_register_id, target_register_id, relation_type, created_at
            ) VALUES (?, ?, ?, ?)
            """,
            ("REG-1", "REG-3", "invalid_relation", "2026-01-01T00:00:08Z"),
        )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """
            INSERT INTO decision_register_relations (
                source_register_id, target_register_id, relation_type, created_at
            ) VALUES (?, ?, ?, ?)
            """,
            ("REG-1", "REG-1", ALLOWED_RELATION_TYPES[1], "2026-01-01T00:00:08Z"),
        )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """
            INSERT INTO decision_register_relations (
                source_register_id, target_register_id, relation_type, created_at
            ) VALUES (?, ?, ?, ?)
            """,
            ("REG-1", "REG-3", ALLOWED_RELATION_TYPES[1], "2026-99-99T99:99:99Z"),
        )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """
            INSERT INTO decision_register_relations (
                source_register_id, target_register_id, relation_type, created_at
            ) VALUES (?, ?, ?, ?)
            """,
            ("REG-1", "REG-404", ALLOWED_RELATION_TYPES[1], "2026-01-01T00:00:09Z"),
        )

    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """
            INSERT INTO decision_register_traceability_links (
                register_id, link_type, target_id, target_ref, sha256, metadata_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("REG-1", "contract", "C-1", None, None, "{}", "2026-01-01T00:00:02Z"),
        )

    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """
            INSERT INTO decision_register_traceability_links (
                register_id, link_type, target_id, target_ref, sha256, metadata_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("REG-1", "invalid", "X-1", None, None, "{}", "2026-01-01T00:00:03Z"),
        )

    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """
            INSERT INTO decision_register_traceability_links (
                register_id, link_type, target_id, target_ref, sha256, metadata_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("REG-1", "run", "RUN-2", None, "z" * 64, "{}", "2026-01-01T00:00:04Z"),
        )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """
            INSERT INTO decision_register_traceability_links (
                register_id, link_type, target_id, target_ref, sha256, metadata_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("REG-1", "run", "RUN-2", None, None, "{}", "2026-99-99T99:99:99Z"),
        )
    conn.execute("DELETE FROM decision_register_entries WHERE register_id = ?", ("REG-3",))
    relation_count = conn.execute(
        "SELECT COUNT(*) FROM decision_register_relations WHERE source_register_id = ? OR target_register_id = ?",
        ("REG-3", "REG-3"),
    ).fetchone()[0]
    trace_link_count = conn.execute(
        "SELECT COUNT(*) FROM decision_register_traceability_links WHERE register_id = ?",
        ("REG-3",),
    ).fetchone()[0]
    assert relation_count == 0
    assert trace_link_count == 0
    conn.close()
