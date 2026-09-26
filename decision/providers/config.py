"""Configuration with provenance-bearing overrides. No secrets in source."""

from __future__ import annotations

import os
from dataclasses import dataclass

_DEFAULT_PROVIDER = "mock"
_DEFAULT_SHADOW_ONLY = "1"
_DEFAULT_TIMEOUT_MS = "2500"
# Documented Vercel AI Gateway root for typesafe-ai/jev (frozen directive §16)
_DEFAULT_JEV_BASE_URL = "https://ai-gateway.vercel.com"
_DEFAULT_JEV_MODEL = "typesafe-ai/jev"

_ENV_PREFIX = "SINTRAPRIME_DECISION_"


@dataclass(frozen=True)
class DecisionConfig:
    provider: str
    shadow_only: bool
    timeout_ms: int
    jev_base_url: str
    jev_model: str
    jev_api_key: str | None  # from env only, never from source
    overrides: dict


def load_config(env=None) -> DecisionConfig:
    env = os.environ if env is None else env

    def get(name: str, default: str) -> str:
        return env.get(_ENV_PREFIX + name, env.get(name.replace("SINTRAPRIME_DECISION_", ""), default))

    provider = get("PROVIDER", _DEFAULT_PROVIDER).lower()
    if provider not in ("mock", "jev"):
        provider = _DEFAULT_PROVIDER  # unknown value -> safest default
    shadow = get("SHADOW_ONLY", _DEFAULT_SHADOW_ONLY) not in ("0", "false", "no")
    timeout_raw = get("TIMEOUT_MS", _DEFAULT_TIMEOUT_MS)
    try:
        timeout_ms = max(1, int(timeout_raw))
    except ValueError:
        timeout_ms = int(_DEFAULT_TIMEOUT_MS)
    jev_base = env.get("JEV_BASE_URL", _DEFAULT_JEV_BASE_URL)
    jev_model = env.get("JEV_MODEL", _DEFAULT_JEV_MODEL)
    jev_key = env.get("JEV_API_KEY")  # None unless explicitly configured

    overrides = {}
    if jev_base != _DEFAULT_JEV_BASE_URL:
        # a base-url override is a provenance-bearing configuration event
        overrides["jev_base_url_override"] = {
            "from": _DEFAULT_JEV_BASE_URL,
            "to": jev_base,
            "source": "env:JEV_BASE_URL",
        }
    if provider != _DEFAULT_PROVIDER:
        overrides["provider_override"] = {"from": _DEFAULT_PROVIDER, "to": provider,
                                          "source": "env:SINTRAPRIME_DECISION_PROVIDER"}
    if not shadow:
        overrides["shadow_only_disabled"] = {"from": True, "to": False,
                                             "source": "env:SINTRAPRIME_DECISION_SHADOW_ONLY"}
    return DecisionConfig(provider=provider, shadow_only=shadow, timeout_ms=timeout_ms,
                          jev_base_url=jev_base, jev_model=jev_model, jev_api_key=jev_key,
                          overrides=overrides)


def get_provider_config() -> DecisionConfig:
    return load_config()
