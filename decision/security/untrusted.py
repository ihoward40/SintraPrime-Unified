"""Untrusted-input boundary (R1 security).

State is trust-segmented. Untrusted text is sanitized (control + zero-width +
bidi override/isolate chars stripped; truncated at 20k). Sanitization is
hygiene, NOT elevation: text remains UNTRUSTED_CONTENT regardless. The injection
detector is advisory/telemetry only and never changes semantics.
"""
from __future__ import annotations

import re
import unicodedata

MAX_UNTRUSTED_CHARS = 20000

# Trojan-Source / RTL-spoofing + zero-width + control characters to strip.
_BIDI = set(range(0x202A, 0x202F)) | set(range(0x2066, 0x206A))  # LRE..PDF, LRI..RLI, FSI..PDI
_ZERO_WIDTH = {0x200B, 0x200C, 0x200D, 0xFEFF, 0x2060, 0x2061, 0x2062, 0x2063, 0x2064}
_CONTROL = set(range(0x00, 0x20))  # C0 controls

_STRIP = _BIDI | _ZERO_WIDTH | _CONTROL

# Adversarial phrases (advisory only — never semantic).
_INJECTION_RE = re.compile(
    r"(ignore\s+(previous|all|above|prior)\s+(instruction|policy|prompt))"
    r"|(classify\s+(me|this)\s+(low[-_ ]?risk|safe))"
    r"|(system\s*:\s*you\s+are\s+now)",
    re.IGNORECASE,
)


def sanitize_untrusted(text: str, max_len: int = MAX_UNTRUSTED_CHARS) -> str:
    if not isinstance(text, str):
        raise TypeError("untrusted content must be str")
    cleaned = [ch for ch in text if ord(ch) not in _STRIP]
    out = "".join(cleaned)
    return out[:max_len]


def segment_state(state: dict) -> dict:
    """Return trust-segmented state. Only SYSTEM_CONTEXT / TRUSTED_METADATA are
    program-controlled; UNTRUSTED_CONTENT is sanitized but never elevated."""
    seg = {
        "SYSTEM_CONTEXT": state.get("SYSTEM_CONTEXT", {}),
        "TRUSTED_METADATA": state.get("TRUSTED_METADATA", {}),
        "UNTRUSTED_CONTENT": sanitize_untrusted(str(state.get("UNTRUSTED_CONTENT", ""))),
        "DERIVED_FEATURES": state.get("DERIVED_FEATURES", {}),
    }
    return seg


def looks_like_injection_attempt(text: str) -> bool:
    """Advisory only. Telemetry. Never changes routing, policy, or authority."""
    if not isinstance(text, str):
        return False
    if _INJECTION_RE.search(text):
        return True
    # Reversed/obfuscated bidi already stripped upstream; heuristic fallback.
    return any(unicodedata.bidirectional(ch) in ("R", "AL") for ch in text)
