"""Core types for the SP Decision Fabric (canonical vocabulary only)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Primitive(StrEnum):
    """Canonical Decision Fabric primitives. Provider terminology is forbidden here."""

    CHOICE = "choice"
    SCORE = "score"
    BOOLEAN = "boolean"


class ResultKind(StrEnum):
    """First-class result kinds. ABSTAIN may never become success/execution."""

    DECISION = "DECISION"
    ABSTAIN = "ABSTAIN"
    ERROR = "ERROR"
    UNAVAILABLE = "UNAVAILABLE"


class Risk(StrEnum):
    LOW = "LOW"
    ELEVATED = "ELEVATED"
    CONSEQUENTIAL = "CONSEQUENTIAL"
    HIGH = "HIGH"


@dataclass(frozen=True)
class Question:
    name: str
    primitive: Primitive
    choices: tuple = ()
    score_min: int = 0
    score_max: int = 10
    instructions: str = ""


@dataclass(frozen=True)
class DecisionContract:
    """A versioned, semantic contract. Hashing is done by contracts.py."""

    name: str
    version: str
    questions: tuple
    risk: Risk = Risk.ELEVATED
    raw: dict = field(default_factory=dict, repr=False)


@dataclass(frozen=True)
class Answer:
    question: str
    primitive: Primitive
    # choice
    selected: str | None = None
    distribution: dict[str, float] | None = None
    runner_up: str | None = None
    runner_up_probability: float | None = None
    margin: float | None = None
    # score
    score_value: float | None = None
    # boolean
    value: bool | None = None
    probability: float | None = None  # boolean P(true) / choice top prob
    # separate axes (never merged with probability)
    confidence: float | None = None

    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "question": self.question,
            "primitive": self.primitive.value,
        }
        if self.primitive is Primitive.CHOICE:
            d["selected"] = self.selected
            d["top_probability"] = self.probability
            d["distribution"] = dict(self.distribution or {})
            d["runner_up"] = self.runner_up
            d["runner_up_probability"] = self.runner_up_probability
            d["margin"] = self.margin
        elif self.primitive is Primitive.SCORE:
            d["score"] = self.score_value
            d["confidence"] = self.confidence
        else:
            d["value"] = self.value
            d["probability"] = self.probability
        d["confidence"] = self.confidence
        return d


@dataclass(frozen=True)
class DecisionResult:
    kind: ResultKind
    answers: dict[str, Answer] = field(default_factory=dict)
    provider: str = ""
    model: str = ""
    raw_primitive_names: dict[str, str] = field(default_factory=dict)
    provider_request_id: str | None = None
    latency_ms: float | None = None
    reason: str = ""

    @property
    def is_decision(self) -> bool:
        return self.kind is ResultKind.DECISION
