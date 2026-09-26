"""Shared provider-side scalar coercion for the Decision Fabric.

R1.1 (SP-SYSTEM-ONE-DECISION-FABRIC-001-R1-DEFECT-001 remediation):
provider-supplied numeric fields (confidence, probability, score) that are
malformed/non-coercible must normalize to a first-class ERROR result — never
an escaping exception. This helper performs the NARROW conversion and reports
failure so each provider can return ResultKind.ERROR with diagnostic context.

Not a broad except-Exception: only expected coercion failures from
float()/int() on provider-supplied scalars are caught here.
"""

from __future__ import annotations

from typing import Any, Optional, Tuple


def coerce_number(value: Any, field: str) -> Tuple[Optional[float], Optional[str]]:
    """Coerce a provider-supplied scalar to float.

    Returns (value, None) on success, (None, reason) on failure.
    None passes through as (None, None) — missing-vs-malformed is the
    caller's distinction (R1.1 scope note: None semantics unchanged).
    Non-scalar types (dict/list/bool) are malformed by definition.
    """
    if value is None:
        return None, None
    if isinstance(value, bool):
        return None, f"malformed_{field}: boolean is not a number"
    if isinstance(value, (int, float)):
        try:
            return float(value), None
        except (OverflowError, ValueError) as exc:
            return None, f"malformed_{field}: {type(exc).__name__}"
    if isinstance(value, str):
        try:
            return float(value.strip()), None
        except (ValueError, TypeError):
            return None, f"malformed_{field}: non-numeric string {value!r:.40}"
    return None, f"malformed_{field}: non-scalar type {type(value).__name__}"
