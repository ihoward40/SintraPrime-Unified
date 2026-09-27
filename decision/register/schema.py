"""Decision Register schema and relational storage model contract."""

from __future__ import annotations

from typing import Any

DECISION_REGISTER_SCHEMA_VERSION = "sp-decision-register-v1"
SHA256_HEX_PATTERN = r"^[0-9a-fA-F]{64}$"
ALLOWED_RELATION_TYPES = ("depends_on", "supersedes", "references", "derived_from")

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
            "properties": {
                "name": {"type": "string"},
                "version": {"type": "string"},
                "semantic_sha256": {"type": "string", "pattern": SHA256_HEX_PATTERN},
            },
        },
        "state": {
            "type": "object",
            "required": ["canonical_version", "sha256"],
            "properties": {
                "canonical_version": {"type": "string"},
                "sha256": {"type": "string", "pattern": SHA256_HEX_PATTERN},
            },
        },
        "result": {
            "type": "object",
            "required": ["kind"],
            "properties": {
                "kind": {"type": "string", "enum": ["DECISION", "ABSTAIN", "ERROR", "UNAVAILABLE"]},
                "provider": {"type": "string"},
                "model": {"type": "string"},
            },
        },
        "policy": {
            "type": "object",
            "required": ["decision", "risk"],
            "properties": {
                "decision": {"type": "string"},
                "risk": {"type": "string"},
            },
        },
        "traceability": {
            "type": "object",
            "required": ["receipt_hash", "links"],
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
                        "properties": {
                            "link_type": {
                                "type": "string",
                                "enum": ["contract", "state", "receipt", "run", "evidence"],
                            },
                            "target_id": {"type": "string"},
                            "target_ref": {"type": "string"},
                            "sha256": {"type": "string", "pattern": SHA256_HEX_PATTERN},
                        },
                        "allOf": [
                            {
                                "if": {
                                    "required": ["link_type"],
                                    "properties": {"link_type": {"enum": ["contract", "state", "receipt"]}},
                                },
                                "then": {"required": ["sha256"]},
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
        "decision_register_entries": """
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
    CHECK(schema_version = 'sp-decision-register-v1'),
    CHECK(length(contract_semantic_sha256) = 64 AND contract_semantic_sha256 NOT GLOB '*[^0-9A-Fa-f]*'),
    CHECK(length(state_sha256) = 64 AND state_sha256 NOT GLOB '*[^0-9A-Fa-f]*'),
    CHECK(length(receipt_hash) = 64 AND receipt_hash NOT GLOB '*[^0-9A-Fa-f]*'),
    CHECK(
        prev_receipt_hash IS NULL
        OR (length(prev_receipt_hash) = 64 AND prev_receipt_hash NOT GLOB '*[^0-9A-Fa-f]*')
    )
)
""".strip(),
        "decision_register_relations": """
CREATE TABLE IF NOT EXISTS decision_register_relations (
    relation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_register_id TEXT NOT NULL,
    target_register_id TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(source_register_id) REFERENCES decision_register_entries(register_id),
    FOREIGN KEY(target_register_id) REFERENCES decision_register_entries(register_id),
    CHECK(relation_type IN ('depends_on', 'supersedes', 'references', 'derived_from')),
    UNIQUE(source_register_id, target_register_id, relation_type)
)
""".strip(),
        "decision_register_traceability_links": """
CREATE TABLE IF NOT EXISTS decision_register_traceability_links (
    link_id INTEGER PRIMARY KEY AUTOINCREMENT,
    register_id TEXT NOT NULL,
    link_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    target_ref TEXT,
    sha256 TEXT,
    metadata_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(register_id) REFERENCES decision_register_entries(register_id),
    CHECK(link_type IN ('contract', 'state', 'receipt', 'run', 'evidence')),
    CHECK(sha256 IS NULL OR (length(sha256) = 64 AND sha256 NOT GLOB '*[^0-9A-Fa-f]*')),
    CHECK(link_type NOT IN ('contract', 'state', 'receipt') OR sha256 IS NOT NULL)
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
        "decision_register_traceability_links_register_idx": (
            "CREATE INDEX IF NOT EXISTS decision_register_traceability_links_register_idx "
            "ON decision_register_traceability_links(register_id, link_type)"
        ),
    },
}
