"""MockDecisionProvider — deterministic, offline, certification-safe."""

from __future__ import annotations

from ..canonical.jcs import state_sha256
from ..contracts.contracts import DecisionContract
from ..engine.types import Answer, DecisionResult, Primitive, ResultKind
from .coerce import coerce_number


class MockDecisionProvider:
    """Fully deterministic provider.

    Behavior is driven ONLY by the canonical state hash + contract contents,
    so the same inputs always produce the same result (replay-safe).

    Failure injection for certification tests:
      state["_mock_fault"] = "timeout" | "connection" | "http_429" | "http_500"
                           | "malformed" | "invalid_json" | "unknown_primitive"
                           | "missing_confidence" | "missing_distribution"
                           | "schema_mismatch" | "contract_mismatch"
      state["_mock_abstain"] = true  -> provider abstains
      state["_mock_answers"] = {"<question>": primitive-specific dict} for
                               scripted deterministic answers (tests/fixtures)
    """

    name = "mock"
    model = "mock/deterministic-v1"

    async def evaluate(self, *, state: dict, contract: DecisionContract) -> DecisionResult:
        fault = state.get("_mock_fault")
        if fault:
            kind = {
                "timeout": ResultKind.UNAVAILABLE,
                "connection": ResultKind.UNAVAILABLE,
                "dns": ResultKind.UNAVAILABLE,
                "http_429": ResultKind.UNAVAILABLE,
                "http_500": ResultKind.UNAVAILABLE,
            }.get(fault, ResultKind.ERROR)
            return DecisionResult(
                kind=kind,
                provider=self.name,
                model=self.model,
                reason=f"injected fault: {fault}",
            )
        if state.get("_mock_abstain"):
            return DecisionResult(
                kind=ResultKind.ABSTAIN,
                provider=self.name,
                model=self.model,
                reason="mock abstain requested",
            )
        answers: dict[str, Answer] = {}
        scripted: dict | None = state.get("_mock_answers")
        if scripted and not isinstance(scripted, dict):
            return DecisionResult(kind=ResultKind.ERROR, provider=self.name, model=self.model,
                                  reason="schema_mismatch: _mock_answers not a mapping")
        names = {q.name for q in contract.questions}
        if scripted:
            extra = set(scripted) - names
            if extra:
                return DecisionResult(kind=ResultKind.ERROR, provider=self.name, model=self.model,
                                      reason=f"contract_mismatch: unknown questions {sorted(extra)}")
        for q in contract.questions:
            s = (scripted or {}).get(q.name)
            if q.primitive is Primitive.CHOICE:
                if s is None:
                    # deterministic default: distribute mass on the FIRST choice
                    probs = {c: (0.9 if i == 0 else 0.1 / max(1, len(q.choices) - 1))
                             for i, c in enumerate(q.choices)}
                    s = {"probabilities": probs}
                probs = s.get("probabilities")
                if not isinstance(probs, dict) or not probs:
                    return DecisionResult(kind=ResultKind.ERROR, provider=self.name, model=self.model,
                                          reason="missing_distribution")
                conf = s.get("confidence", 0.9)
                conf_val, conf_err = coerce_number(conf, "confidence")
                if conf_err:
                    return DecisionResult(kind=ResultKind.ERROR, provider=self.name, model=self.model,
                                          reason=conf_err)
                if conf_val is None:
                    return DecisionResult(kind=ResultKind.ERROR, provider=self.name, model=self.model,
                                          reason="missing_confidence")
                conf = conf_val
                sel = max(probs, key=lambda k: probs[k])
                if q.choices and sel not in q.choices:
                    return DecisionResult(kind=ResultKind.ERROR, provider=self.name, model=self.model,
                                          reason=f"schema_mismatch: {sel!r} not in contract choices")
                ordered = sorted(probs.items(), key=lambda kv: kv[1], reverse=True)
                top1 = ordered[0]
                top2 = ordered[1] if len(ordered) > 1 else (None, 0.0)
                answers[q.name] = Answer(
                    question=q.name,
                    primitive=Primitive.CHOICE,
                    selected=top1[0],
                    probability=float(top1[1]),
                    distribution={k: float(v) for k, v in probs.items()},
                    runner_up=top2[0],
                    runner_up_probability=float(top2[1]),
                    margin=float(top1[1]) - float(top2[1]),
                    confidence=float(conf),
                )
            elif q.primitive is Primitive.SCORE:
                if s is None:
                    s = {"score": 0.0, "confidence": 0.5}
                sv, sv_err = coerce_number(s.get("score", 0.0), "score")
                if sv_err:
                    return DecisionResult(kind=ResultKind.ERROR, provider=self.name, model=self.model,
                                          reason=sv_err)
                cv, cv_err = coerce_number(s.get("confidence"), "confidence")
                if cv_err:
                    return DecisionResult(kind=ResultKind.ERROR, provider=self.name, model=self.model,
                                          reason=cv_err)
                answers[q.name] = Answer(
                    question=q.name,
                    primitive=Primitive.SCORE,
                    score_value=sv if sv is not None else 0.0,
                    confidence=cv,
                )
            else:  # boolean
                if s is None:
                    s = {"value": False, "probability": 0.5, "confidence": 0.5}
                cv, cv_err = coerce_number(s.get("confidence"), "confidence")
                if cv_err:
                    return DecisionResult(kind=ResultKind.ERROR, provider=self.name, model=self.model,
                                          reason=cv_err)
                if cv is None:
                    return DecisionResult(kind=ResultKind.ERROR, provider=self.name, model=self.model,
                                          reason="missing_confidence")
                pv, pv_err = coerce_number(s.get("probability", 0.5), "probability")
                if pv_err:
                    return DecisionResult(kind=ResultKind.ERROR, provider=self.name, model=self.model,
                                          reason=pv_err)
                answers[q.name] = Answer(
                    question=q.name,
                    primitive=Primitive.BOOLEAN,
                    value=bool(s.get("value")),
                    probability=pv if pv is not None else 0.5,
                    confidence=cv,
                )
        return DecisionResult(
            kind=ResultKind.DECISION,
            answers=answers,
            provider=self.name,
            model=self.model,
            raw_primitive_names={},
            provider_request_id=f"mock-{state_sha256(state)[:12]}",
            latency_ms=0.0,
        )
