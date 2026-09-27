"""Decision Register schema and relational storage model contract."""

from __future__ import annotations

from typing import Any

DECISION_REGISTER_SCHEMA_VERSION = "sp-decision-register-v1"
SHA256_HEX_PATTERN = r"^[0-9a-fA-F]{64}$"
ALLOWED_RELATION_TYPES = ("depends_on", "supersedes", "references", "derived_from")
HASHED_TRACE_LINK_TYPES = ("contract", "state", "receipt")
NON_HASHED_TRACE_LINK_TYPES = ("run", "evidence")
ALLOWED_TRACE_LINK_TYPES = HASHED_TRACE_LINK_TYPES + NON_HASHED_TRACE_LINK_TYPES

_SQL_ALLOWED_RELATION_TYPES = ", ".join(f"'{value}'" for value in ALLOWED_RELATION_TYPES)
_SQL_HASHED_TRACE_LINK_TYPES = ", ".join(f"'{value}'" for value in HASHED_TRACE_LINK_TYPES)
_SQL_NON_HASHED_TRACE_LINK_TYPES = ", ".join(f"'{value}'" for value in NON_HASHED_TRACE_LINK_TYPES)
_SQL_ALLOWED_TRACE_LINK_TYPES = ", ".join(f"'{value}'" for value in ALLOWED_TRACE_LINK_TYPES)

DECISION_REGISTER_ENTRY_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://sintraprime.ai/schemas/decision-register-entry.json",
    "title": "SintraPrime Decision Register Entry",
    "type": "object",
    "required": [
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
    ],
    "additionalProperties": False,
    "properties": {
        "schema_version": {"type": "string", "const": DECISION_REGISTER_SCHEMA_VERSION},
        "register_id": {"type": "string"},
        "decision_id": {"type": "string"},
        "run_id": {"type": "string"},
        "recorded_at": {
            "type": "string",
            "format": "date-time",
            "pattern": r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$",
        },
        "contract": {
            "type": "object",
            "required": ["name", "version", "semantic_sha256"],
            "additionalProperties": False,
            "properties": {
                "name": {"type": "string"},
                "version": {"type": "string"},
                "semantic_sha256": {"type": "string", "pattern": SHA256_HEX_PATTERN},
            },
        },
        "state": {
            "type": "object",
            "required": ["canonical_version", "sha256"],
            "additionalProperties": False,
            "properties": {
                "canonical_version": {"type": "string"},
                "sha256": {"type": "string", "pattern": SHA256_HEX_PATTERN},
            },
        },
        "result": {
            "type": "object",
            "required": ["kind"],
            "additionalProperties": False,
            "properties": {
                "kind": {"type": "string", "enum": ["DECISION", "ABSTAIN", "ERROR", "UNAVAILABLE"]},
                "provider": {"type": "string"},
                "model": {"type": "string"},
            },
        },
        "policy": {
            "type": "object",
            "required": ["decision", "risk"],
            "additionalProperties": False,
            "properties": {
                "decision": {"type": "string"},
                "risk": {"type": "string"},
            },
        },
        "traceability": {
            "type": "object",
            "required": ["receipt_hash", "links"],
            "additionalProperties": False,
            "properties": {
                "receipt_hash": {"type": "string", "pattern": SHA256_HEX_PATTERN},
                "prev_receipt_hash": {
                    "anyOf": [
                        {"type": "null"},
                        {"type": "string", "pattern": SHA256_HEX_PATTERN},
                    ]
                },
                "links": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "required": ["link_type", "target_id"],
                        "additionalProperties": False,
                        "properties": {
                            "link_type": {
                                "type": "string",
                                "enum": list(ALLOWED_TRACE_LINK_TYPES),
                            },
                            "target_id": {"type": "string"},
                            "target_ref": {"type": "string"},
                            "sha256": {"type": "string", "pattern": SHA256_HEX_PATTERN},
                        },
                        "allOf": [
                            {
                                "if": {
                                    "required": ["link_type"],
                                    "properties": {"link_type": {"enum": list(HASHED_TRACE_LINK_TYPES)}},
                                },
                                "then": {"required": ["sha256"]},
                                "else": {"not": {"required": ["sha256"]}},
                            }
                        ],
                    },
                },
            },
        },
    },
}


DECISION_REGISTER_STORAGE_MODEL = {
    "schema_version": DECISION_REGISTER_SCHEMA_VERSION,
    "tables": {
        "decision_register_entries": f"""
CREATE TABLE IF NOT EXISTS decision_register_entries (
    register_id TEXT PRIMARY KEY,
    schema_version TEXT NOT NULL,
    decision_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    contract_semantic_sha256 TEXT NOT NULL,
    state_sha256 TEXT NOT NULL,
    result_kind TEXT NOT NULL,
    policy_decision TEXT NOT NULL,
    policy_risk TEXT NOT NULL,
    receipt_hash TEXT NOT NULL UNIQUE,
    prev_receipt_hash TEXT,
    payload_json TEXT NOT NULL,
    CHECK(schema_version = '{DECISION_REGISTER_SCHEMA_VERSION}'),
    CHECK(
        recorded_at GLOB '????-??-??T??:??:??Z'
        AND strftime('%Y-%m-%dT%H:%M:%SZ', recorded_at) IS NOT NULL
        AND strftime('%Y-%m-%dT%H:%M:%SZ', recorded_at) = recorded_at
    ),
    CHECK(length(contract_semantic_sha256) = 64 AND contract_semantic_sha256 NOT GLOB '*[^0-9A-Fa-f]*'),
    CHECK(length(state_sha256) = 64 AND state_sha256 NOT GLOB '*[^0-9A-Fa-f]*'),
    CHECK(length(receipt_hash) = 64 AND receipt_hash NOT GLOB '*[^0-9A-Fa-f]*'),
    CHECK(
        prev_receipt_hash IS NULL
        OR (length(prev_receipt_hash) = 64 AND prev_receipt_hash NOT GLOB '*[^0-9A-Fa-f]*')
    )
)
""".strip(),
        "decision_register_relations": f"""
CREATE TABLE IF NOT EXISTS decision_register_relations (
    relation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_register_id TEXT NOT NULL,
    target_register_id TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(source_register_id) REFERENCES decision_register_entries(register_id) ON DELETE CASCADE,
    FOREIGN KEY(target_register_id) REFERENCES decision_register_entries(register_id) ON DELETE CASCADE,
    CHECK(source_register_id <> target_register_id),
    CHECK(
        created_at GLOB '????-??-??T??:??:??Z'
        AND strftime('%Y-%m-%dT%H:%M:%SZ', created_at) IS NOT NULL
        AND strftime('%Y-%m-%dT%H:%M:%SZ', created_at) = created_at
    ),
    CHECK(relation_type IN ({_SQL_ALLOWED_RELATION_TYPES})),
    UNIQUE(source_register_id, target_register_id, relation_type)
)
""".strip(),
        "decision_register_traceability_links": f"""
CREATE TABLE IF NOT EXISTS decision_register_traceability_links (
    link_id INTEGER PRIMARY KEY AUTOINCREMENT,
    register_id TEXT NOT NULL,
    link_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    target_ref TEXT,
    sha256 TEXT,
    metadata_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(register_id) REFERENCES decision_register_entries(register_id) ON DELETE CASCADE,
    CHECK(
        created_at GLOB '????-??-??T??:??:??Z'
        AND strftime('%Y-%m-%dT%H:%M:%SZ', created_at) IS NOT NULL
        AND strftime('%Y-%m-%dT%H:%M:%SZ', created_at) = created_at
    ),
    CHECK(link_type IN ({_SQL_ALLOWED_TRACE_LINK_TYPES})),
    CHECK(
        (link_type IN ({_SQL_HASHED_TRACE_LINK_TYPES}) AND sha256 IS NOT NULL)
        OR (link_type IN ({_SQL_NON_HASHED_TRACE_LINK_TYPES}) AND sha256 IS NULL)
    ),
    CHECK(sha256 IS NULL OR (length(sha256) = 64 AND sha256 NOT GLOB '*[^0-9A-Fa-f]*'))
)
""".strip(),
    },
    "indexes": {
        "decision_register_entries_decision_run_idx": (
            "CREATE INDEX IF NOT EXISTS decision_register_entries_decision_run_idx "
            "ON decision_register_entries(decision_id, run_id)"
        ),
        "decision_register_relations_source_idx": (
            "CREATE INDEX IF NOT EXISTS decision_register_relations_source_idx "
            "ON decision_register_relations(source_register_id)"
        ),
        "decision_register_relations_target_idx": (
            "CREATE INDEX IF NOT EXISTS decision_register_relations_target_idx "
            "ON decision_register_relations(target_register_id)"
        ),
        "decision_register_relations_references_pair_uq": (
            "CREATE UNIQUE INDEX IF NOT EXISTS decision_register_relations_references_pair_uq "
            "ON decision_register_relations(relation_type, min(source_register_id, target_register_id), "
            "max(source_register_id, target_register_id)) WHERE relation_type = 'references'"
        ),
        "decision_register_traceability_links_register_idx": (
            "CREATE INDEX IF NOT EXISTS decision_register_traceability_links_register_idx "
            "ON decision_register_traceability_links(register_id, link_type)"
        ),
        "decision_register_traceability_links_identity_uq": (
            "CREATE UNIQUE INDEX IF NOT EXISTS decision_register_traceability_links_identity_uq "
            "ON decision_register_traceability_links(register_id, link_type, target_id, ifnull(target_ref, ''))"
        ),
    },
}
