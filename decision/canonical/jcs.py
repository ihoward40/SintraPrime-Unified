"""RFC 8785 (JCS)-class canonicalization + deterministic state hashing (R1).

Behavior is pinned by tests, not by a library name: "verify the behavior, not
the name." Self-contained (stdlib only). Deviations from a full JCS library:
  * Input domain: dict/list/str/int/float/bool/None. Foreign types raise TypeError.
  * Object keys sorted by UTF-16 code-unit order (JCS rule).
  * Numbers formatted per ECMAScript Number::toString (0/-0/0.1/1e21/1e-7/0.000001;
    integral floats and equal ints hash identically; non-finite raise).
  * Strings: minimal escaping; control chars as \\u00XX; U+0085/U+2028/U+2029 literal.
  * Arrays: order preserved.
  * Output: UTF-8 bytes of the canonical document, no whitespace.
"""
from __future__ import annotations

import hashlib
import math
from decimal import Decimal

CANONICAL_VERSION = "sp-decision-state-v1"
CONTRACT_VERSION = "sp-decision-contract-v1"


def _format_number(x):
    if isinstance(x, bool):
        raise TypeError("bool is not a JSON number")
    if isinstance(x, int):
        return str(x)
    if isinstance(x, float):
        if math.isinf(x) or math.isnan(x):
            raise ValueError("non-finite floats are not representable")
        if x == 0:
            return "0"
        neg = x < 0
        ax = abs(x)
        d = Decimal(repr(ax))
        _sign, digits, exp = d.as_tuple()
        m = 0
        for dg in digits:
            m = m * 10 + dg
        e = exp
        while e < 0 and m % 10 == 0:  # shortest decimal form
            m //= 10
            e += 1
        k = len(str(m))
        if e >= 21 or e <= -7:
            et = e + k - 1
            s = str(m)
            mant = s if len(s) == 1 else s[0] + "." + s[1:]
            out = mant + "e" + ("+" if et >= 0 else "") + str(et)
        elif e >= 0:
            out = str(m) + ("0" * e)
        else:
            if k + e > 0:
                pos = k + e
                out = str(m)[:pos] + "." + str(m)[pos:]
            else:
                out = "0." + ("0" * (-(k + e))) + str(m)
        return ("-" + out) if neg else out
    raise TypeError(f"cannot serialize {type(x).__name__}")


def _dump_string(s: str) -> str:
    out = ['"']
    for ch in s:
        o = ord(ch)
        if o < 0x20:
            out.append("\\u%04x" % o)
        elif ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        else:
            out.append(ch)  # U+0085/U+2028/U+2029 and all other chars kept literal (JCS)
    out.append('"')
    return "".join(out)


def _dump(obj) -> str:
    if obj is None:
        return "null"
    if isinstance(obj, bool):
        return "true" if obj else "false"
    if isinstance(obj, (int, float)):
        return _format_number(obj)
    if isinstance(obj, str):
        return _dump_string(obj)
    if isinstance(obj, (list, tuple)):
        return "[" + ",".join(_dump(v) for v in obj) + "]"
    if isinstance(obj, dict):
        # sort keys by UTF-16 code-unit order
        keys = sorted(obj.keys(), key=lambda k: k.encode("utf-16-be"))
        return "{" + ",".join(_dump_string(k) + ":" + _dump(v) for k, v in ((kk, obj[kk]) for kk in keys)) + "}"
    raise TypeError(f"cannot serialize {type(obj).__name__}")


def canonical_bytes(obj) -> bytes:
    return _dump(obj).encode("utf-8")


def canonical_string(obj) -> str:
    return _dump(obj)


def state_sha256(state: dict) -> str:
    envelope = {"canonical_version": CANONICAL_VERSION, "state": state}
    return hashlib.sha256(canonical_bytes(envelope)).hexdigest()


def contract_sha256(contract: dict) -> str:
    envelope = {"canonical_version": CONTRACT_VERSION, "contract": contract}
    return hashlib.sha256(canonical_bytes(envelope)).hexdigest()
