"""Semantic contract normalization + semantic hashing (R1 contracts).

A contract is authored in YAML or JSON. Comments, whitespace, quoting, and key
order MUST NOT move the hash. Choice lists, thresholds, risk, question set, and
question types MUST. Only choice|score|boolean are valid canonical primitives; others are rejected.
"""
from __future__ import annotations

import hashlib
from typing import Any, Dict

from decision.canonical.jcs import canonical_bytes, contract_sha256
from decision.engine.types import ContractRisk, DecisionContract, Primitive

_ALLOWED_PRIMITIVES = {"choice", "score", "boolean"}
_METADATA_KEYS = {"metadata", "version", "description", "notes", "owner", "created", "doc"}


def parse_contract(raw: str) -> Dict[str, Any]:
    """Parse a YAML/JSON contract string into a dict."""
    text = raw.strip()
    if not text:
        raise ValueError("empty contract")
    # Try JSON first (subset-safe), then YAML.
    try:
        import json
        return json.loads(text)
    except Exception:
        pass
    try:
        import yaml
        return yaml.safe_load(text)
    except Exception as exc:  # pragma: no cover - depends on input
        raise ValueError(f"cannot parse contract as JSON or YAML: {exc}")


def normalize_contract(d: Dict[str, Any]) -> Dict[str, Any]:
    """Strip metadata, validate, and normalize structure into a canonical dict.

    Raises ValueError on: missing 'questions', unknown primitive (values outside choice|score|boolean),
    off-contract structure that cannot be normalized.
    """
    if not isinstance(d, dict):
        raise ValueError("contract root must be a mapping")
    questions = d.get("questions")
    if not isinstance(questions, list) or not questions:
        raise ValueError("contract requires a non-empty 'questions' list")

    norm_questions = []
    for q in questions:
        if not isinstance(q, dict) or "name" not in q or "primitive" not in q:
            raise ValueError("each question needs 'name' and 'primitive'")
        prim = str(q["primitive"]).lower()
        if prim not in _ALLOWED_PRIMITIVES:
            raise ValueError(f"rejected primitive {q['primitive']!r}: only choice|score|boolean allowed")
        nq: Dict[str, Any] = {"name": str(q["name"]), "primitive": prim}
        if prim == "choice":
            choices = q.get("choices")
            if not isinstance(choices, list) or not choices:
                raise ValueError("choice question requires a 'choices' list")
            nq["choices"] = sorted(str(c) for c in choices)
        if "threshold" in q:
            nq["threshold"] = float(q["threshold"])
        if "risk" in q:
            nq["risk"] = str(q["risk"]).upper()
        norm_questions.append(nq)

    norm: Dict[str, Any] = {"questions": norm_questions}
    if "name" in d:
        norm["name"] = str(d["name"])
    if "risk" in d:
        norm["risk"] = str(d["risk"]).upper()
    return norm


def semantic_contract_sha256(raw: str) -> str:
    parsed = parse_contract(raw)
    normalized = normalize_contract(parsed)
    return contract_sha256(normalized)


def build_contract(name: str, questions: list, risk: str = "LOW") -> "DecisionContract":
    """Convenience builder used by tests/engine. Questions: dicts as in normalize_contract."""
    norm = normalize_contract({"name": name, "risk": risk, "questions": questions})
    risk_enum = ContractRisk[norm.get("risk", "LOW")]
    return DecisionContract(name=norm.get("name", name), questions=norm["questions"], risk=risk_enum)


def hash_of_normalized(raw: str) -> str:
    return hashlib.sha256(canonical_bytes(normalize_contract(parse_contract(raw)))).hexdigest()
