# R1-RECOVERY — Canonicalization Note

## Contract

`decision/canonical/jcs.py` implements RFC 8785 (JCS) behavior for the
Decision Fabric. It is self-contained (stdlib only) and pinned by conformance
tests. Deviations from a full JCS library are documented here:

- **Input domain**: `dict` (string keys), `list`, `str`, `int`, `float`,
  `bool`, `None`. Foreign types raise `TypeError` (fail loud).
- **Object keys**: sorted by UTF-16 code-unit order (the JCS rule, which
  differs from code-point order for surrogate-pair characters — pinned by
  test with U+1D400 vs U+FFFD).
- **Numbers**: ECMAScript `Number::toString` formatting. `1.0` → `1`,
  `-0.0` → `0`, `0.1` → `0.1`, `1e21` → `1e+21`, `1e-7` → `1e-7`,
  `0.000001` → `0.000001`. Integral floats and equal ints hash identically.
  Non-finite floats raise.
- **Strings**: minimal JSON escaping; control characters as `\u00XX`;
  U+0085/U+2028/U+2029 preserved literally (JCS behavior).
- **Arrays**: order preserved. Semantically-unordered collections MUST be
  normalized by the caller before hashing (frozen directive §5 leaves array
  ordering policy to the state designer; the conformance suite pins the
  primitive behavior).
- **Output**: UTF-8 bytes of the canonical document; no whitespace;
  separators `,` and `:`.

## Hashes

- `state_sha256(state)` = SHA-256 over canonical bytes of
  `{"canonical_version": "sp-decision-state-v1", "state": {...}}`.
- `semantic_contract_sha256(raw)` = SHA-256 over canonical bytes of the
  NORMALIZED contract (parsed → validated → metadata stripped → structure
  normalized → canonicalized). YAML comments, quoting, indentation, and key
  order cannot move it. Choice lists, thresholds, risk, question set, and
  question types can and do.

## Why not a third-party JCS library?

R1 recovery runs in an isolated venv with a minimal dependency surface.
The behavior is fully pinned by tests (`TestCanonicalization`), which any
independent verifier can re-run; swapping in a conforming library later is a
drop-in behind the same tests. "RFC 8785-class" here means: **verify the
behavior, not the name** — the tests are the spec.
