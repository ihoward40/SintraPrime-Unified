"""Semantic contract normalization + hashing.

contract_sha256 hashes CONTRACT SEMANTICS, never raw YAML/file bytes:
comments, quoting style, indentation, and key order must not move the hash.
Semantic changes (choices, thresholds, risk, questions) MUST move it.
"""

from __future__ import annotations

from hashlib import sha256
from typing import Any, Dict

from ..canonical.jcs import canonical_bytes
from ..engine.types import DecisionContract, Primitive, Question, Risk

_ALLOWED_TOP_KEYS = {"contract_id", "version", "risk", "questions"}


def _normalize_question(name: str, q: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(q, dict):
        raise ValueError(f"question {name!r} must be a mapping")
    ptype = q.get("type")
    mapping = {"choice": "choice", "score": "score", "boolean": "boolean"}
    if ptype not in mapping:
        raise ValueError(f"question {name!r}: unsupported primitive type {ptype!r}")
    out: Dict[str, Any] = {"type": mapping[ptype]}
    if ptype == "choice":
        choices = q.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ValueError(f"question {name!r}: choice requires non-empty choices")
        out["choices"] = [str(c) for c in choices]
    if ptype == "score":
        out["min"] = int(q.get("min", 0))
        out["max"] = int(q.get("max", 10))
        if out["min"] >= out["max"]:
            raise ValueError(f"question {name!r}: score min >= max")
    instr = q.get("instructions")
    if instr is not None:
        out["instructions"] = str(instr)
    return out


def normalize_contract(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Parse/validate/strip non-semantic metadata -> normalized structure."""
    if not isinstance(raw, dict):
        raise ValueError("contract must be a mapping")
    unknown = set(raw.keys()) - _ALLOWED_TOP_KEYS
    if unknown:
        # non-semantic metadata is stripped silently ONLY if harmless;
        # unknown semantic-looking keys are rejected to fail loud.
        unknown = {k for k in unknown if not k.startswith("x_") and k != "description"}
        if unknown:
            raise ValueError(f"unknown contract keys: {sorted(unknown)}")
    cid = raw.get("contract_id")
    if not cid or not isinstance(cid, str):
        raise ValueError("contract_id required")
    version = str(raw.get("version", "1"))
    risk_raw = str(raw.get("risk", "ELEVATED")).upper()
    if risk_raw not in Risk.__members__:
        raise ValueError(f"unknown risk {risk_raw!r}")
    questions_raw = raw.get("questions") or {}
    if not isinstance(questions_raw, dict) or not questions_raw:
        raise ValueError("questions must be a non-empty mapping")
    questions = {qn: _normalize_question(qn, q) for qn, q in questions_raw.items()}
    return {
        "contract_id": cid,
        "version": version,
        "risk": risk_raw,
        "questions": questions,
    }


def contract_from_raw(raw: Dict[str, Any]) -> DecisionContract:
    norm = normalize_contract(raw)
    qs = []
    for n, q in norm["questions"].items():
        qs.append(
            Question(
                name=n,
                primitive=Primitive(q["type"]),
                choices=tuple(q.get("choices", ())),
                score_min=q.get("min", 0),
                score_max=q.get("max", 10),
                instructions=q.get("instructions", ""),
            )
        )
    return DecisionContract(
        name=norm["contract_id"],
        version=norm["version"],
        questions=tuple(qs),
        risk=Risk(norm["risk"]),
        raw=norm,
    )


def semantic_contract_sha256(raw: Dict[str, Any]) -> str:
    return sha256(canonical_bytes(normalize_contract(raw))).hexdigest()


def load_contract_text(text: str) -> Dict[str, Any]:
    """Parse YAML or JSON contract text into raw dict (yaml.safe_load)."""
    import json

    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text)
    except ImportError:  # pragma: no cover
        data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("contract text must parse to a mapping")
    return data
