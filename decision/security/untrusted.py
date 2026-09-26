"""Untrusted-input boundary.

External content is DATA, never authority. This module builds decision state
with explicit provenance segments so hostile text cannot alter contract,
schema, policy, or authority.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict

# strip control chars / bidi overrides / zero-width tricks from untrusted text
# (bidi overrides are the Trojan-Source vector; they are stripped, never obeyed)
_CTRL_RE = re.compile(
    "[\x00-\x08\x0b\x0c\x0e-\x1f\u200b\u200c\u200d\u2060\ufeff"
    "\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069]"
)


@dataclass
class AnnotatedState:
    """Decision state with explicit trust segments (frozen directive §11)."""

    system_context: Dict[str, Any] = field(default_factory=dict)   # trusted, program-set
    trusted_metadata: Dict[str, Any] = field(default_factory=dict)  # trusted (e.g. mailbox headers)
    untrusted_content: Dict[str, str] = field(default_factory=dict)  # DATA ONLY
    derived_features: Dict[str, Any] = field(default_factory=dict)   # computed, no raw text

    def to_state(self) -> dict:
        return {
            "system_context": dict(self.system_context),
            "trusted_metadata": dict(self.trusted_metadata),
            "untrusted_content": {k: sanitize_text(v) for k, v in self.untrusted_content.items()},
            "derived_features": dict(self.derived_features),
        }


def sanitize_text(text: str) -> str:
    """Remove control/zero-width characters; hard-cap length.

    This is hygiene only — it does NOT make content trusted.
    """
    if not isinstance(text, str):
        text = str(text)
    cleaned = _CTRL_RE.sub("", text)
    return cleaned[:20000]


# Content that attempts to exercise authority is STILL data. We do not parse
# it, obey it, or special-case it; we keep it as opaque evidence text.
_AUTHORITY_PHRASES = (
    "ignore policy", "ignore the router", "classify me", "route directly",
    "bypass", "approve", "execute", "authorize",
)


def looks_like_injection_attempt(text: str) -> bool:
    """Optional detector for alerting/telemetry. Detection NEVER changes
    semantics: the content stays untrusted data either way."""
    low = sanitize_text(text).lower()
    return any(p in low for p in _AUTHORITY_PHRASES)
