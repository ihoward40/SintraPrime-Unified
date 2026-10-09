"""MockDecisionProvider — deterministic, fault-injectable (R1 mandatory provider).

Deterministic: identical inputs -> identical outputs (provider_request_id derived
from the canonical state hash). Fault injection via state keys (_mock_fault,
_mock_abstain, _mock_answers) — these are test hooks and are stripped before any
live transport would see them.
"""
from __future__ import annotations

import time

from decision.engine.types import (
    Answer,
    DecisionContract,
    DecisionResult,
    Primitive,
    ResultKind,
)
from decision.canonical.jcs import state_sha256

# Fault names mirror the frozen directive failure matrix (semantic equivalence).
_UNAVAILABLE_FAULTS = {"timeout", "connection", "dns", "http_429", "http_500"}
_ERROR_FAULTS = {
    "malformed",
    "invalid_json",
    "unknown_primitive",
    "missing_confidence",
    "missing_distribution",
    "schema_mismatch",
    "contract_mismatch",
}


class MockDecisionProvider:
    name = "mock"
    model = "mock-deterministic-v1"

    def __init__(self, settings=None):
        self.settings = settings

    async def evaluate(self, *, state: dict, contract: DecisionContract) -> DecisionResult:
        start = time.monotonic()
        request_id = "mock-" + state_sha256(_strip_mock(state))[:16]
        fault = state.get("_mock_fault")
        if fault in _UNAVAILABLE_FAULTS:
            return self._result(ResultKind.UNAVAILABLE, request_id, error=fault,
                                latency_ms=_ms(start))
        if fault in _ERROR_FAULTS:
            return self._result(ResultKind.ERROR, request_id, error=fault,
                                latency_ms=_ms(start))
        if state.get("_mock_abstain"):
            return self._result(ResultKind.ABSTAIN, request_id, latency_ms=_ms(start))

        answers = []
        for q in contract.questions:
            prim = Primitive(q["primitive"])
            if prim is Primitive.CHOICE:
                choices = q["choices"]
                answers.append(Answer(
                    question=q["name"], primitive=prim, value=choices[0],
                    confidence=0.9,
                    distribution={c: round(1.0 / len(choices), 4) for c in choices},
                ))
            elif prim is Primitive.SCORE:
                answers.append(Answer(question=q["name"], primitive=prim, value=0.5,
                                      confidence=0.9))
            else:  # BOOLEAN
                answers.append(Answer(question=q["name"], primitive=prim, value=True,
                                      confidence=0.9))
        return self._result(ResultKind.DECISION, request_id, answers=answers,
                            latency_ms=_ms(start))

    def _result(self, kind, request_id, error=None, answers=None, latency_ms=0.0):
        return DecisionResult(
            kind=kind, answers=answers or [], provider_name=self.name,
            model=self.model, provider_request_id=request_id,
            latency_ms=latency_ms, error=error,
        )


def _strip_mock(state: dict) -> dict:
    return {k: v for k, v in state.items() if not str(k).startswith("_mock_")}


def _ms(start: float) -> float:
    return round((time.monotonic() - start) * 1000.0, 3)
