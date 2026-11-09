"""Read-only, deterministic Blackstone case-readiness checks.

This module never executes external actions or makes findings of legal liability.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Status = Literal["documented", "alleged", "unknown"]
Action = Literal["review", "draft", "send", "file", "serve", "settle", "pay", "delete"]


@dataclass(frozen=True)
class CaseFact:
    key: str
    status: Status
    evidence_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class CaseRequest:
    case_id: str
    facts: tuple[CaseFact, ...]
    action: Action = "review"
    human_approved: bool = False


@dataclass(frozen=True)
class ReadinessResult:
    case_id: str
    permitted: bool
    ready_for_legal_review: bool
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]


_REQUIRED = ("specific_inaccuracy", "dispute_notice", "post_dispute_reporting", "injury")
_EXTERNAL = frozenset(("send", "file", "serve", "settle", "pay", "delete"))


def assess_case(request: CaseRequest) -> ReadinessResult:
    """Apply conservative procedural gates; does not certify an FCRA claim."""
    if not request.case_id.strip():
        raise ValueError("case_id is required")
    if request.action not in ("review", "draft", "send", "file", "serve", "settle", "pay", "delete"):
        raise ValueError("unknown action")
    facts = {fact.key: fact for fact in request.facts}
    if len(facts) != len(request.facts):
        raise ValueError("duplicate fact keys")
    blockers: list[str] = []
    warnings: list[str] = []
    for key in _REQUIRED:
        fact = facts.get(key)
        if fact is None or fact.status != "documented" or not fact.evidence_ids:
            blockers.append(f"missing_documented_evidence:{key}")
    for fact in request.facts:
        if fact.status == "documented" and not fact.evidence_ids:
            warnings.append(f"unsupported_documented_fact:{fact.key}")
    if request.action in _EXTERNAL:
        blockers.append("external_action_not_executable_by_readiness_checker")
        if not request.human_approved:
            blockers.append("human_approval_required")
    return ReadinessResult(
        case_id=request.case_id,
        permitted=request.action not in _EXTERNAL,
        ready_for_legal_review=not any(x.startswith("missing_documented_evidence:") for x in blockers),
        blockers=tuple(blockers),
        warnings=tuple(warnings),
    )
