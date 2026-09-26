"""Canonicalization for the SP Decision Fabric.

RFC 8785 (JCS) class JSON canonicalization, self-contained implementation.

Pin notes (directive section 10):
- objects: keys sorted by UTF-16 code-unit order (JCS rule)
- numbers: RFC 8785 serialization (ES6 Number::toString); integral floats in
  float64 range serialize WITHOUT a decimal point or exponent; -0 -> "0"
- strings: minimal JSON escaping, control chars \\u00XX, no \\u008X escapes
- arrays: order preserved (semantically ordered); the CALLER is responsible
  for normalizing semantically-unordered arrays before handing state in
- whitespace: none; separators (",", ":")
- output: UTF-8 bytes of the serialized JSON document
"""

from __future__ import annotations

import math
import re
from hashlib import sha256
from typing import Any

CANONICAL_STATE_VERSION = "sp-decision-state-v1"

# ---------------------------------------------------------------------------
# Number serialization (RFC 8785 section 3.2.2.3 / ECMAScript Number::toString)
# ---------------------------------------------------------------------------

_FLOAT_RE = re.compile(r"^(-?\d+)(?:\.(\d+))?(?:[eE]([+-]?\d+))?$")


def _number_to_string(value: float) -> str:
    """Serialize a finite float the way ECMAScript Number::toString(10) does.

    json.dumps would give "1.0" / "1e-06"; JCS requires "1" / "0.000001".
    """
    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError("non-finite numbers are not JSON-canonical")
    if value == 0:
        return "0"  # covers -0 as well: JCS serializes -0 as "0"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    # Integral floats (1.0, -25.0, 1e21 handled separately below)
    if math.isfinite(value) and value == int(value) and abs(value) < 1e21:
        return str(int(value))
    # Fall through to repr-based shortest round-trip, then normalize exponent
    # formatting to ECMAScript rules.
    r = repr(float(value))
    if _FLOAT_RE.match(r) is None:
        raise ValueError(f"unparseable float repr: {r}")
    from decimal import Decimal

    d = Decimal(r)
    sign, digits, exp = d.as_tuple()
    digits = list(digits)
    # k = number of digits, n = value = digits * 10^(exp)
    k = len(digits)
    n = exp + k - 1  # highest power of ten when written in scientific form
    if exp > 0 or n >= 21 or n <= -7:
        # exponential notation
        ds = "".join(map(str, digits))
        mant = ds[0] + ("." + ds[1:] if len(ds) > 1 else "")
        out = f"{mant}e{'+' if n >= 0 else '-'}{abs(n)}"
    else:
        if exp >= 0:
            out = "".join(map(str, digits)) + "0" * exp
        else:
            ip = digits[: k + exp] if k + exp > 0 else [0]
            fp = digits[k + exp :] if k + exp > 0 else digits
            out = (
                ("0." + "0" * (-k - exp) + "".join(map(str, fp)))
                if k + exp <= 0
                else "".join(map(str, ip)) + "." + "".join(map(str, fp))
            )
    return ("-" if sign and value != 0 else "") + out


def _canonical_number(value: Any) -> str:
    if isinstance(value, bool):  # bool check MUST precede int (bool subclass)
        raise TypeError("bool is not a number for canonicalization")
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return _number_to_string(value)
    raise TypeError(f"unsupported number type: {type(value)!r}")


# ---------------------------------------------------------------------------
# Key sorting: UTF-16 code-unit order (JCS), NOT code-point order
# ---------------------------------------------------------------------------


def _utf16_sort_key(key: str):
    return key.encode("utf-16-be")


# ---------------------------------------------------------------------------
# Serializer
# ---------------------------------------------------------------------------


def _escape_string(s: str) -> str:
    out = ['"']
    for ch in s:
        o = ord(ch)
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif ch == "\b":
            out.append("\\b")
        elif ch == "\f":
            out.append("\\f")
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        elif o < 0x20:
            out.append(f"\\u{o:04x}")
        else:
            out.append(ch)  # JCS: keep UTF-8 as-is (incl. U+0085, U+2028...)
    out.append('"')
    return "".join(out)


def _serialize(value: Any, out: list) -> None:
    if value is None:
        out.append("null")
    elif value is True:
        out.append("true")
    elif value is False:
        out.append("false")
    elif isinstance(value, str):
        out.append(_escape_string(value))
    elif isinstance(value, (int, float)):
        out.append(_canonical_number(value))
    elif isinstance(value, list):
        out.append("[")
        for i, item in enumerate(value):
            if i:
                out.append(",")
            _serialize(item, out)
        out.append("]")
    elif isinstance(value, dict):
        out.append("{")
        for i, key in enumerate(sorted(value.keys(), key=_utf16_sort_key)):
            if not isinstance(key, str):
                raise TypeError("object keys must be strings")
            if i:
                out.append(",")
            out.append(_escape_string(key))
            out.append(":")
            _serialize(value[key], out)
        out.append("}")
    else:
        raise TypeError(f"cannot canonicalize type: {type(value)!r}")


def canonicalize(value: Any) -> str:
    """Return the JCS-class canonical JSON string for *value*."""
    out: list = []
    _serialize(value, out)
    return "".join(out)


def canonical_bytes(value: Any) -> bytes:
    return canonicalize(value).encode("utf-8")


def sha256_canonical(value: Any) -> str:
    return sha256(canonical_bytes(value)).hexdigest()


# ---------------------------------------------------------------------------
# Canonical decision state
# ---------------------------------------------------------------------------


def canonical_state(state: dict) -> dict:
    """Wrap raw state into the versioned canonical envelope (sorted upstream)."""
    return {"canonical_version": CANONICAL_STATE_VERSION, "state": state}


def state_sha256(state: dict) -> str:
    return sha256_canonical(canonical_state(state))
