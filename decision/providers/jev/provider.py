"""JevDecisionProvider — adapter for TypeSafe AI's Jev.

VENDOR BOUNDARY (frozen directive section 4/9):
- Native Jev primitives: Choice / Score / Noul.
- Canonical primitives:  choice / score / boolean.
- The word "Noul" may exist ONLY inside this adapter (raw metadata), never in
  canonical types, contracts, or ledger fields.

Transport: POST {JEV_BASE_URL}/v1/systemone  (default: documented Vercel AI
Gateway endpoint; overrides are provenance-bearing, see config.py).

Failure mapping (fail-closed):
  transport errors (timeout, DNS, connection, 429, 5xx) -> ResultKind.UNAVAILABLE
  malformed body / unknown primitive / missing fields / schema or contract
  mismatch                                              -> ResultKind.ERROR
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, Optional

from ...contracts.contracts import DecisionContract
from ...engine.types import Answer, DecisionResult, Primitive, ResultKind
from ..config import get_provider_config
from ..coerce import coerce_number

_DEFAULT_BASE_URL = "https://ai-gateway.vercel.com"  # documented Gateway root
_RAW_PRIMITIVE_NAMES = {"choice": "Choice", "score": "Score", "boolean": "Noul"}  # provider-local


class JevDecisionProvider:
    name = "jev"

    def __init__(self, *, base_url: Optional[str] = None, api_key: Optional[str] = None,
                 model: Optional[str] = None, timeout_s: Optional[float] = None,
                 transport=None) -> None:
        cfg = get_provider_config()
        self.base_url = (base_url or cfg.jev_base_url or _DEFAULT_BASE_URL).rstrip("/")
        self.api_key = api_key or cfg.jev_api_key
        self.model = model or cfg.jev_model or "typesafe-ai/jev"
        self.timeout_s = timeout_s if timeout_s is not None else cfg.timeout_ms / 1000.0
        self._transport = transport or self._httpx_transport
        # provenance: base-url override is a recorded configuration event
        self.base_url_override = bool(base_url) and base_url != cfg.jev_base_url

    # -- transport seam (injectable for deterministic tests) ----------------

    @staticmethod
    def _httpx_transport(url: str, payload: dict, api_key: Optional[str], timeout_s: float) -> dict:
        import httpx  # optional dependency; only needed for live use

        headers = {"content-type": "application/json"}
        if api_key:
            headers["authorization"] = f"Bearer {api_key}"
        resp = httpx.post(url, json=payload, headers=headers, timeout=timeout_s)
        if resp.status_code in (429,) or resp.status_code >= 500:
            raise TransportFault(f"http_{resp.status_code}")
        if resp.status_code >= 400:
            raise ResponseFault(f"http_{resp.status_code}")
        return resp.json()

    # -- evaluation ---------------------------------------------------------

    async def evaluate(self, *, state: dict, contract: DecisionContract) -> DecisionResult:
        started = time.perf_counter()
        payload_state = {k: v for k, v in state.items() if not k.startswith("_mock_")}
        payload = {
            "model": self.model,
            "state": payload_state,
            "questions": [
                self._question_payload(q) for q in contract.questions
            ],
        }
        url = f"{self.base_url}/v1/systemone"
        try:
            raw = self._transport(url, payload, self.api_key, self.timeout_s)
        except TransportFault as e:
            return self._result(ResultKind.UNAVAILABLE, started, reason=str(e))
        except ResponseFault as e:
            return self._result(ResultKind.ERROR, started, reason=str(e))
        except Exception as e:  # connection/DNS/timeout and any other transport fault
            return self._result(ResultKind.UNAVAILABLE, started, reason=f"transport: {type(e).__name__}")

        if not isinstance(raw, dict):
            return self._result(ResultKind.ERROR, started, reason="malformed: non-mapping response")
        raw_answers = raw.get("answers")
        if not isinstance(raw_answers, dict):
            return self._result(ResultKind.ERROR, started, reason="malformed: missing answers")

        answers: Dict[str, Answer] = {}
        raw_names: Dict[str, str] = {}
        contract_qs = {q.name: q for q in contract.questions}
        for qname, raw_a in raw_answers.items():
            q = contract_qs.get(qname)
            if q is None:
                return self._result(ResultKind.ERROR, started,
                                    reason=f"contract_mismatch: unknown question {qname!r}")
            if not isinstance(raw_a, dict):
                return self._result(ResultKind.ERROR, started, reason=f"malformed: answer {qname!r}")
            ptype = raw_a.get("type")
            try:
                primitive_key, ans = self._normalize_answer(q, raw_a)
            except _SchemaMismatch as e:
                return self._result(ResultKind.ERROR, started, reason=str(e))
            raw_names[qname] = _RAW_PRIMITIVE_NAMES[primitive_key]
            answers[qname] = ans
        missing = set(contract_qs) - set(answers)
        if missing:
            return self._result(ResultKind.ERROR, started,
                                reason=f"schema_mismatch: missing answers for {sorted(missing)}")
        return DecisionResult(
            kind=ResultKind.DECISION,
            answers=answers,
            provider=self.name,
            model=self.model,
            raw_primitive_names=raw_names,
            provider_request_id=raw.get("id"),
            latency_ms=(time.perf_counter() - started) * 1000.0,
        )

    # -- helpers -------------------------------------------------------------

    def _result(self, kind: ResultKind, started: float, reason: str = "") -> DecisionResult:
        return DecisionResult(kind=kind, provider=self.name, model=self.model,
                              latency_ms=(time.perf_counter() - started) * 1000.0, reason=reason)

    @staticmethod
    def _question_payload(q) -> dict:
        p = {"name": q.name, "type": q.primitive.value}
        if q.primitive is Primitive.CHOICE:
            p["choices"] = list(q.choices)
        elif q.primitive is Primitive.SCORE:
            p["criteria"] = [str(q.score_min), str(q.score_max)]
        return p

    def _normalize_answer(self, q, raw_a: dict):
        ptype = raw_a.get("type")
        confidence_raw = raw_a.get("confidence")
        confidence, conf_err = (None, None) if confidence_raw is None else coerce_number(confidence_raw, "confidence")
        if conf_err:
            raise _SchemaMismatch(conf_err)
        # ---- native Choice -> choice
        if ptype == "choice":
            if q.primitive is not Primitive.CHOICE:
                raise _SchemaMismatch(f"primitive mismatch on {q.name}: choice vs contract")
            probs = raw_a.get("probabilities")
            if not isinstance(probs, dict) or not probs:
                raise _SchemaMismatch(f"missing_distribution on {q.name}")
            sel = raw_a.get("choice")
            if sel is None:
                sel = max(probs, key=lambda k: probs[k])
            if q.choices and sel not in q.choices:
                raise _SchemaMismatch(f"contract_mismatch: {sel!r} not a contract choice on {q.name}")
            ordered = sorted(probs.items(), key=lambda kv: kv[1], reverse=True)
            top1 = ordered[0]
            top2 = ordered[1] if len(ordered) > 1 else (None, 0.0)
            ans = Answer(
                question=q.name, primitive=Primitive.CHOICE, selected=sel,
                probability=float(top1[1]),
                distribution={k: float(v) for k, v in probs.items()},
                runner_up=top2[0], runner_up_probability=float(top2[1]),
                margin=float(top1[1]) - float(top2[1]),
                confidence=confidence,
            )
            return "choice", ans
        # ---- native Score -> score
        if ptype == "score":
            if q.primitive is not Primitive.SCORE:
                raise _SchemaMismatch(f"primitive mismatch on {q.name}: score vs contract")
            if "score" not in raw_a:
                raise _SchemaMismatch(f"malformed: score missing on {q.name}")
            sv, sv_err = coerce_number(raw_a["score"], "score")
            if sv_err:
                raise _SchemaMismatch(sv_err)
            ans = Answer(
                question=q.name, primitive=Primitive.SCORE,
                score_value=sv,
                confidence=confidence,
            )
            return "score", ans
        # ---- native Noul / SDK boolean -> boolean
        if ptype in ("noul", "boolean"):
            if q.primitive is not Primitive.BOOLEAN:
                raise _SchemaMismatch(f"primitive mismatch on {q.name}: boolean vs contract")
            prob = raw_a.get("probability", raw_a.get("noul"))
            if prob is None:
                raise _SchemaMismatch(f"malformed: probability missing on {q.name}")
            pv, pv_err = coerce_number(prob, "probability")
            if pv_err:
                raise _SchemaMismatch(pv_err)
            ans = Answer(
                question=q.name, primitive=Primitive.BOOLEAN,
                value=pv >= 0.5, probability=pv,
                confidence=confidence,
            )
            return "boolean", ans
        # ---- unknown provider primitive: fail closed
        raise _SchemaMismatch(f"unknown_primitive {ptype!r} on {q.name}")


class TransportFault(Exception):
    pass


class ResponseFault(Exception):
    pass


class _SchemaMismatch(Exception):
    pass
