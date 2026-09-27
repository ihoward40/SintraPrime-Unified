# SP-AGENTIC-RUNTIME-CERT-001 — Certification Record

## Controlling rule

**Agents may become more capable without becoming more authoritative.**

## Provenance

- Base: `051e2594c67a805ceacc66ea2a6fc6db9c0bc793`
- Branch: `feat/sp-agentic-runtime-20260927`
- Pull request: #352
- Merge/deploy: NOT AUTHORIZED / NOT PERFORMED

## Gate state

| Gate | State | Evidence |
|---|---|---|
| Native approval/ledger/model adapters | IMPLEMENTED | Slice 2 source + tests |
| ContextPack | IMPLEMENTED | bounded/provenance-aware builder |
| Governed ComfyUI adapter | IMPLEMENTED | policy admission precedes transport |
| Budget/circuit breaker | IMPLEMENTED | execution loop integration |
| Concrete checkpoint/rollback | IMPLEMENTED | approval-gated restore + ref verification |
| Consolidated SHA-256 receipt | IMPLEMENTED | canonical receipt + ledger hash binding |
| Focused runtime tests | PENDING_EXECUTION | GitHub Actions run required |
| Broader regression universe | PENDING_EXECUTION | canonical `scripts/certify.py` lane |
| Installed-model inventory | HOST_REQUIRED | must observe actual SintraPrime/Ollama host |
| Context-window verification | HOST_REQUIRED | runtime observation required |
| Capability benchmark | HOST_REQUIRED | benchmark receipt required |
| Model promotion | CLOSED | no promotion until all evidence gates pass |

## Promotion rule

A configured model name, model card, environment setting, or advertised context
window is not sufficient evidence. Promotion to `VERIFIED` requires:

1. observed installed model identity;
2. observed effective context capacity;
3. benchmark suite receipt for each required capability;
4. benchmark score at/above the configured floor;
5. non-empty evidence references;
6. successful `ModelPromotionGate` admission.

Until then the model remains UNVERIFIED and is excluded by verified-only routing.
