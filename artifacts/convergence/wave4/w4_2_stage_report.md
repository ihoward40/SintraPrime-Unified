# W4-2 — CANONICAL CAPABILITY RESOLVER (STAGE REPORT / PRE-COMMIT)

**Date:** 2026-09-09 · **Base:** W4-1 commit `51974cca` (on main @ `79deec88` + Wave-3)
**Change set (uncommitted, exact):** `agent_runtime/capability_resolver.py` (NEW) · `agent_runtime/tests/test_capability_resolver.py` (NEW, 25 tests) · `agent_runtime/tests/negative_outcome.py` (NEW — NegativeOutcome promoted to a permanent agent_runtime certification primitive per Principal ruling)

## Acceptance matrix

```
REGISTRY_LOAD_VALID = PASS
GENERATION_HASH_VALID = PASS (sha256 bound, verified)
CANONICAL_ID_RESOLUTION = 42/42
ALIAS_RESOLUTION = 23/23
ALIAS_CANONICAL_EQUIVALENCE = PASS (equal canonical objects incl. provenance)
UNKNOWN_REFUSAL = PASS (dotted + alias-shaped)
AMBIGUOUS_ALIAS_REFUSAL = PASS (grammar-ambiguity detection)
GENERATION_MISMATCH_REFUSAL = PASS
INVALID_FORMAT_REFUSAL = PASS
DISABLED_REFUSAL = PASS (status gate, DEPRECATED/REVOKED)
DORMANT_REFUSAL = PASS (status gate; resolution succeeds as data, execution path refused)
CORRUPTED_REGISTRY_REFUSAL = PASS (8 variants: dup canonical, alias collision,
    alias→unknown, missing field, bad class, EC-without-approval, missing
    generation, ACTIVE executor-origin without bindings)
REGISTRY_MISSING/NOT_JSON = PASS (fail-closed)
NO_FALLBACK_TO_KNOWN_CAPABILITIES = PASS (empty registry resolves nothing)
PRODUCTION_CONSUMERS_CHANGED = 0 (git diff vs W4-1 commit: only the 3 new files)
MANIFEST_IDS_REWRITTEN = 0
ENVELOPE_HASHING_CHANGED = 0 (explicitly deferred to W4-4)
BROWSER_BINDING_CHANGED = 0
AUTHORITY_EXPANSION = 0
CANONICAL_CAPABILITY = immutable frozen data; provenance (generation id + hash)
    carried and non-strippable; possession ≠ permission (documented + tested)
RUFF = PASS · agent_runtime suite = 187/187 (166 + 25 resolver − 4 overlaps)
```

## Implementation notes (two recorded loader decisions)

1. **Manifest-origin ACTIVE-without-bindings is legal**: the sealed ZD-002 artifact marks the 23 Wave-3 vocabulary capabilities `ACTIVE` without executor bindings (bindings arrive with W4-3/W4-4 executor registration). The loader invariant therefore requires bindings only for **executor-origin** capabilities (browser et al.). This aligns the loader with the sealed artifact instead of rewriting the artifact — no weakening of the EC/IR⇒ALWAYS_REQUIRED invariant, which still holds and is enforced.
2. **NegativeOutcome primitive relocated** to `agent_runtime/tests/negative_outcome.py` — the Principal designated it a permanent certification primitive; it now lives with the agent_runtime certification tree (also usable by mission_wiring later via import).

## Failure states implemented (exact ZD-004 codes)

`UNKNOWN_CAPABILITY` · `AMBIGUOUS_ALIAS` · `REGISTRY_GENERATION_MISMATCH` · `INVALID_CAPABILITY_FORMAT` · `DISABLED_CAPABILITY` · `DORMANT_CAPABILITY` · `REGISTRY_NOT_TRUSTED`

## Boundary held

No envelope/receipt/certification hashing changes (W4-4). No consumer migrations (W4-3: manifest validator, delegation set_delegatable, registry validate, browser gate, portal classification set — inventory evidence preserved). No executor rebinding. No push/merge. Nothing committed yet — change set is exact and ready for the W4-2 commit.
