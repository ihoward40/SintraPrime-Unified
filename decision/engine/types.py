"""Canonical primitives, result kinds, answers, and results (R1 engine/types)."""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class Primitive(str, enum.Enum):
    CHOICE = "choice"
    SCORE = "score"
    BOOLEAN = "boolean"

    @classmethod
    def from_canonical(cls, value: str) -> "Primitive":
        v = str(value).lower()
        for m in cls:
            if m.value == v:
                return m
        raise ValueError(f"unknown canonical primitive: {value!r}")


class ResultKind(str, enum.Enum):
    DECISION = "DECISION"
    ABSTAIN = "ABSTAIN"
    ERROR = "ERROR"
    UNAVAILABLE = "UNAVAILABLE"


class PolicyDisposition(str, enum.Enum):
    FALLBACK_HERMES = "FALLBACK_HERMES"        # pre-existing governed path (fail-closed)
    HERMES_REVIEW = "HERMES_REVIEW"            # ambiguous; human/governed review, never auto-execute
    AUTO_ROUTE_CANDIDATE = "AUTO_ROUTE_CANDIDATE"  # unreachable under R1 shadow default


class ContractRisk(str, enum.Enum):
    LOW = "LOW"
    ELEVATED = "ELEVATED"
    CONSEQUENTIAL = "CONSEQUENTIAL"
    HIGH = "HIGH"


@dataclass
class Answer:
    question: str
    primitive: Primitive
    value: Any
    confidence: float
    distribution: Optional[Dict[str, float]] = None
    raw_primitive_names: Optional[List[str]] = None


@dataclass
class DecisionResult:
    kind: ResultKind
    answers: List[Answer] = field(default_factory=list)
    provider_name: str = ""
    model: str = ""
    provider_request_id: str = ""
    latency_ms: float = 0.0
    raw: Optional[str] = None
    error: Optional[str] = None
    raw_primitive_names: Optional[List[str]] = None

    @property
    def is_decision(self) -> bool:
        return self.kind is ResultKind.DECISION


@dataclass
class DecisionContract:
    name: str = "decision.health.v1"
    questions: List[Dict[str, Any]] = field(default_factory=list)
    risk: ContractRisk = ContractRisk.LOW

    def question_names(self) -> List[str]:
        return [q["name"] for q in self.questions]
