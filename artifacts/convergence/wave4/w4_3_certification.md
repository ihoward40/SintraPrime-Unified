# W4-3 — CORRECTION + RECERTIFICATION (PRE-COMMIT)

**Base:** W4-2 `98bc9b70` · **status:** CERTIFICATION PASS / COMMIT AUTHORIZED BY PRINCIPAL

## Correction applied

Removed the production fallback from `agent_runtime/manifest.py`:

```text
registry present + trusted   → resolve through CapabilityResolver
registry missing             → REGISTRY_NOT_TRUSTED / refuse
registry corrupt             → REGISTRY_NOT_TRUSTED / refuse
registry generation mismatch→ refuse
```

There is now **no automatic consultation of `KNOWN_CAPABILITIES`** in any of the three migrated consumers. The legacy set remains only as historical declaration in `manifest.py`; it is not a fallback authority.

## Matrix

| Gate | Result |
|---|---|
| MANIFEST_RESOLUTION | PASS |
| DELEGATION_RESOLUTION | PASS |
| REGISTRY_VALIDATION_RESOLUTION | PASS |
| REGISTRY_MISSING_REFUSAL | PASS |
| REGISTRY_CORRUPTED_REFUSAL | PASS |
| REGISTRY_GENERATION_MISMATCH_REFUSAL | PASS |
| NO_FALLBACK_TO_KNOWN_CAPABILITIES | PASS (static + negative path) |
| ALIAS_CANONICAL_EQUIVALENCE | PASS |
| UNKNOWN_REFUSAL | PASS |
| ALIAS_PERMISSION_EXPANSION | 0 |
| AUTHORITY_EXPANSION | 0 |
| PORTAL_CLASSIFICATION_SET | EXCLUDED_BY_NAMESPACE |
| BROWSER_GATE_RESOLUTION | NOT_APPLICABLE_ON_PRODUCTION_LINE |
| agent_runtime | PASS (195/195; 187 prior + 8 W4-3 tests) |
| swarm canonical | PASS (177/177: 125 + 52) |
| Ruff | PASS |

No envelope, receipt, certification hashing, manifest rewrite, portal, or browser-executor change.

## READY TO SEAL

Narrow W4-3 commit remains held only until the commit command; no W4-4 work is started.
