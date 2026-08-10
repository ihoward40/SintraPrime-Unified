"""Trust authority dispatch metadata for Hermes/SintraPrime channel routing.

This module performs only deterministic request classification. It never claims
that current law has been verified. Downstream orchestration must satisfy the
current-law verifier and approval gates before a legal-effect conclusion or
external execution is allowed.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

_TRUST_PATTERNS = [
    re.compile(r"\bisiah\s+tarik\s+howard\s+trust\b", re.I),
    re.compile(r"\btrust instrument\b", re.I),
    re.compile(r"\bcertification of trust\b", re.I),
    re.compile(r"\bdeclaration of trust\b", re.I),
    re.compile(r"\btrustee\b", re.I),
    re.compile(r"\bco-?trustee\b", re.I),
    re.compile(r"\bbeneficiar(?:y|ies)\b", re.I),
    re.compile(r"\bsettlor\b", re.I),
    re.compile(r"\btrust corpus\b", re.I),
    re.compile(r"\bfiduciary dut(?:y|ies)\b", re.I),
    re.compile(r"\btrust administration\b", re.I),
    re.compile(r"\btrust banking\b", re.I),
]

_LEGAL_EFFECT_PATTERNS = [
    re.compile(r"\blegal effect\b", re.I),
    re.compile(r"\blegally binding\b", re.I),
    re.compile(r"\benforce(?:able|ment)?\b", re.I),
    re.compile(r"\bperfect(?:ion|ed)?\b", re.I),
    re.compile(r"\blien\b", re.I),
    re.compile(r"\bjurisdiction\b", re.I),
    re.compile(r"\btax(?:able|ation| filing| status)?\b", re.I),
    re.compile(r"\bcourt\b", re.I),
    re.compile(r"\bcreditor\b", re.I),
    re.compile(r"\bborrow(?:ing)?\b", re.I),
    re.compile(r"\bencumber\b", re.I),
    re.compile(r"\bdistribut(?:e|ion)\b", re.I),
    re.compile(r"\btransfer\b", re.I),
    re.compile(r"\bamend(?:ment)?\b", re.I),
]

_EXTERNAL_PATTERNS = [
    re.compile(r"\bfile\b", re.I),
    re.compile(r"\bsubmit\b", re.I),
    re.compile(r"\bsend\b", re.I),
    re.compile(r"\bmail\b", re.I),
    re.compile(r"\bemail\b", re.I),
    re.compile(r"\btransmit\b", re.I),
    re.compile(r"\bexecute\b", re.I),
    re.compile(r"\bsign\b", re.I),
    re.compile(r"\brecord\b", re.I),
    re.compile(r"\bpublish\b", re.I),
    re.compile(r"\bserve\b", re.I),
    re.compile(r"\bopen (?:an )?account\b", re.I),
]


def build_trust_authority_route(text: str) -> Optional[Dict[str, Any]]:
    """Return governed dispatch metadata for a trust-related message."""
    if not any(pattern.search(text) for pattern in _TRUST_PATTERNS):
        return None

    legal_effect = any(pattern.search(text) for pattern in _LEGAL_EFFECT_PATTERNS)
    external_execution = any(pattern.search(text) for pattern in _EXTERNAL_PATTERNS)

    return {
        "route_id": "HOWARD-TRUST-AUTHORITY",
        "authority_order": [
            "trust-instrument-authority",
            "weisss-trustee-handbook",
            "current-law-verifier",
        ],
        "legal_effect_requested": legal_effect,
        "external_execution_requested": external_execution,
        "current_law_status": "NOT_YET_VERIFIED",
        "principal_approval": False,
        "fail_closed": bool(legal_effect or external_execution),
    }
