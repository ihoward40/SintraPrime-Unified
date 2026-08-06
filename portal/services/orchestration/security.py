"""Security helpers for mock orchestration boundaries."""

from __future__ import annotations

import re
from typing import Any


SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|token|password|session[_-]?cookie)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
]

INJECTION_MARKERS = (
    "ignore previous instructions",
    "reveal system prompt",
    "exfiltrate",
    "bypass policy",
)

DENIED_ACTIONS = (
    "merge code",
    "deploy",
    "spend money",
    "publish public content",
    "send external communications",
    "change legal positions",
    "modify payment settings",
)


def redact_text(value: str) -> str:
    redacted = value
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def sanitize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, str):
            sanitized[key] = redact_text(value)
        elif isinstance(value, dict):
            sanitized[key] = sanitize_payload(value)
        elif isinstance(value, list):
            sanitized[key] = [redact_text(item) if isinstance(item, str) else item for item in value]
        else:
            sanitized[key] = value
    return sanitized


def detect_prompt_injection(value: str) -> list[str]:
    lowered = value.lower()
    return [marker for marker in INJECTION_MARKERS if marker in lowered]


def denied_actions(value: str) -> list[str]:
    lowered = value.lower()
    return [action for action in DENIED_ACTIONS if action in lowered]
