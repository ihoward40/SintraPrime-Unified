# SintraPrime — Freeze v1.0.0

## What this freeze guarantees
- Policy supremacy: policy decides; commands do not override policy.
- Approval boundary: write-capable actions require explicit operator approval.
- Deterministic artifacts: repeatable, stable audit exports and verification inputs.
- Audit bundles + verifier: audit bundles are verifiable offline using the canonical verifier.
- Court-safe posture by construction: evidence is append-only under `runs/**`, and verification is strict, zip-or-dir, JSON-last-line.

## What this freeze does not (yet) guarantee
- No claim of legal sufficiency, completeness, or correctness of any specific filing.
- No promise of production integrations being enabled by default.
- No promise of backwards compatibility for future tiers unless explicitly versioned.

## References
- Constitution: docs/CONSTITUTION.v1.md
- Freeze procedure: docs/tier-freeze-checklist.md
- Canonical verifier: scripts/verify.js
