"""JevDecisionProvider — Jev (typesafe-ai/jev) adapter.

The ONLY place Jev vocabulary (incl. "Noul") lives. Fail-closed: every transport
or response fault resolves to UNAVAILABLE/ERROR, never to deterministic execution.
Transport is injectable for deterministic tests; the default transport uses httpx
(optional) and requires explicit credentials — neither exists in R1.
"""
from __future__ import annotations

import json
import time
from typing import Awaitable, Callable, Optional, Tuple

from decision.engine.types import (
    Answer,
    DecisionContract,
    DecisionResult,
    Primitive,
    ResultKind,
)
from decision.providers.config import Settings

Transport = Callable[[str, str, dict, dict], Awaitable[Tuple[int, bytes]]]


def _ms(start: float) -> float:
    return round((time.monotonic() - start) * 1000.0, 3)


class JevTransportError(Exception):
    def __init__(self, kind: str):
        super().__init__(kind)
        self.kind = kind  # timeout | connection | dns | http


# Jev native -> canonical primitive (frozen directive normalization table).
_NORMALIZE = {
    "choice": "choice",
    "score": "score",
    "noul": "boolean",
    "boolean": "boolean",
}

_UNAVAILABLE_KINDS = {"timeout", "connection", "dns", "http"}


class JevDecisionProvider:
    name = "jev"
    model = "typesafe-ai/jev"

    def __init__(self, settings: Settings, transport: Optional[Transport] = None):
        self.settings = settings
        self._transport = transport or self._default_transport
        self.endpoint = f"{settings.jev_base_url.rstrip('/')}/v1/systemone"

    @staticmethod
    def normalize_primitive(raw):
        key = str(raw).lower()
        if key not in _NORMALIZE:
            raise ValueError(f"unknown jev primitive: {raw!r}")
        return _NORMALIZE[key]

    async def evaluate(self, *, state: dict, contract: DecisionContract) -> DecisionResult:
        start = time.monotonic()
        req = self._build_request(state, contract)
        request_id = "jev-" + str(abs(hash(json.dumps(req, sort_keys=True))))[:16]
        try:
            status, body = await self._transport("POST", self.endpoint, req, self._headers())
        except JevTransportError as exc:
            kind = exc.kind
            rk = ResultKind.UNAVAILABLE if kind in _UNAVAILABLE_KINDS else ResultKind.ERROR
            return self._result(rk, request_id, error=kind, latency_ms=_ms(start))
        return self._parse(status, body, contract, request_id, start)

    # ---- internal ---------------------------------------------------------
    def _build_request(self, state: dict, contract: DecisionContract) -> dict:
        clean = {k: v for k, v in state.items() if not str(k).startswith("_mock_")}
        return {
            "model": self.settings.jev_model,
            "contract": {"name": contract.name, "questions": contract.questions},
            "state": clean,
        }

    def _headers(self) -> dict:
        h = {"content-type": "application/json"}
        if self.settings.jev_api_key:
            h["authorization"] = f"Bearer {self.settings.jev_api_key}"
        return h

    def _parse(self, status, body, contract, request_id, start) -> DecisionResult:
        if status in (429, 500, 502, 503, 504):
            return self._result(ResultKind.UNAVAILABLE, request_id, error=f"http_{status}",
                                latency_ms=_ms(start))
        if status >= 400:
            return self._result(ResultKind.ERROR, request_id, error=f"http_{status}",
                                latency_ms=_ms(start))
        try:
            payload = json.loads(body)
        except (ValueError, TypeError):
            return self._result(ResultKind.ERROR, request_id, error="invalid_json",
                                latency_ms=_ms(start))
        answers_in = payload.get("answers")
        if not isinstance(answers_in, list):
            return self._result(ResultKind.ERROR, request_id, error="malformed",
                                latency_ms=_ms(start))
        by_name = {a.get("question"): a for a in answers_in}
        answers = []
        for q in contract.questions:
            a = by_name.get(q["name"])
            if a is None:
                return self._result(ResultKind.ERROR, request_id, error="schema_mismatch",
                                    latency_ms=_ms(start))
            try:
                canon = self.normalize_primitive(a.get("primitive"))
            except ValueError:
                return self._result(ResultKind.ERROR, request_id, error="unknown_primitive",
                                    latency_ms=_ms(start))
            prim = Primitive(canon)
            value = a.get("value")
            if prim is Primitive.CHOICE:
                if value not in q.get("choices", []):
                    return self._result(ResultKind.ERROR, request_id, error="contract_mismatch",
                                        latency_ms=_ms(start))
                dist = a.get("distribution")
                if not isinstance(dist, dict) or not dist:
                    return self._result(ResultKind.ERROR, request_id, error="missing_distribution",
                                        latency_ms=_ms(start))
                answers.append(Answer(question=q["name"], primitive=prim, value=value,
                                      confidence=float(a.get("confidence", 0.0)),
                                      distribution=dist,
                                      raw_primitive_names=[a.get("primitive")]))
            else:
                answers.append(Answer(question=q["name"], primitive=prim, value=value,
                                      confidence=float(a.get("confidence", 0.0)),
                                      raw_primitive_names=[a.get("primitive")]))
        return self._result(ResultKind.DECISION, request_id, answers=answers,
                            latency_ms=_ms(start))

    def _result(self, kind, request_id, error=None, answers=None, latency_ms=0.0):
        return DecisionResult(
            kind=kind, answers=answers or [], provider_name=self.name, model=self.model,
            provider_request_id=request_id, latency_ms=latency_ms, error=error,
        )

    async def _default_transport(self, method, url, json_body, headers):
        try:
            import httpx
        except ImportError as exc:  # pragma: no cover - live path only
            raise RuntimeError("httpx required for live Jev transport") from exc
        async with httpx.AsyncClient(timeout=self.settings.timeout_ms / 1000.0) as client:
            resp = await client.request(method, url, json=json_body, headers=headers)
            return resp.status_code, resp.content
