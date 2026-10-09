"""Safe defaults + provenance-bearing overrides (R1 configuration contract).

Configuration contract:
  SINTRAPRIME_DECISION_PROVIDER    mock   (unknown values fall back to mock)
  SINTRAPRIME_DECISION_SHADOW_ONLY 1      (0/false/no disables -> provenance event)
  SINTRAPRIME_DECISION_TIMEOUT_MS  2500   (positive int; invalid -> default)
  JEV_BASE_URL                     Gateway root (override = provenance event)
  JEV_MODEL                       typesafe-ai/jev
  JEV_API_KEY                     none (live auth requires explicit env; never in source)
"""
from __future__ import annotations

import os
from typing import Dict, List

DEFAULT_BASE_URL = "https://ai-gateway.vercel.com"
DEFAULT_MODEL = "typesafe-ai/jev"
KNOWN_PROVIDERS = {"mock", "jev"}

# Process-global provenance log (advisory; never serialized into receipts/state).
PROVENANCE_EVENTS: List[Dict] = []


def _parse_shadow(v: str) -> bool:
    return str(v).strip().lower() not in ("0", "false", "no")


def _parse_int(v: str, default: int) -> int:
    try:
        n = int(v)
        return n if n > 0 else default
    except (TypeError, ValueError):
        return default


def reset_provenance() -> None:
    PROVENANCE_EVENTS.clear()


class Settings:
    def __init__(self, env: Dict[str, str] | None = None):
        e = dict(os.environ if env is None else env)
        raw_provider = e.get("SINTRAPRIME_DECISION_PROVIDER", "mock").lower()
        self.provider = raw_provider if raw_provider in KNOWN_PROVIDERS else "mock"
        if raw_provider not in KNOWN_PROVIDERS:
            self._emit("unknown_provider_fallback", {"requested": raw_provider, "used": "mock"})
        self.shadow_only = _parse_shadow(e.get("SINTRAPRIME_DECISION_SHADOW_ONLY", "1"))
        self.timeout_ms = _parse_int(e.get("SINTRAPRIME_DECISION_TIMEOUT_MS", "2500"), 2500)
        self.jev_base_url = e.get("JEV_BASE_URL", DEFAULT_BASE_URL)
        self.jev_model = e.get("JEV_MODEL", DEFAULT_MODEL)
        self.jev_api_key = e.get("JEV_API_KEY")
        # Provenance-bearing overrides.
        if e.get("JEV_BASE_URL"):
            self._emit("base_url_override", {"base_url": self.jev_base_url})
        if str(e.get("SINTRAPRIME_DECISION_SHADOW_ONLY", "1")).strip().lower() in ("0", "false", "no"):
            self._emit("shadow_disabled", {})

    def provider_is_live(self) -> bool:
        return self.provider == "jev" and bool(self.jev_api_key)

    def _emit(self, kind: str, payload: Dict) -> None:
        PROVENANCE_EVENTS.append({"kind": kind, **payload})

    def provenance_events(self) -> List[Dict]:
        return list(PROVENANCE_EVENTS)
