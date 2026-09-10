# W4-3 — CONSUMER MIGRATION LANE (charter + namespace classification)

**Date:** 2026-09-09 · **Base:** W4-2 commit `98bc9b70` · **Rule:** RESOLVED = KNOWN CANONICAL VOCABULARY ONLY (≠ DELEGATED, ≠ APPROVED, ≠ EXECUTABLE)

## Namespace classification (ruling applied to consumer #5 FIRST)

**`PORTAL_CLASSIFICATION_SET = EXCLUDED_BY_NAMESPACE`.**

Evidence: `_CAPABILITY_CLASSIFICATIONS` in `portal/services/mission_control_capability_policy.py` contains exactly one entry — `"legal_workflow"` — a **workflow name** for the server-owned MC run path, not a member of the capability-registry vocabulary (42 canonical / 23 aliases; no overlap). It classifies server workflow approval posture (`APPROVAL_REQUIRED`), which is policy-over-workflows, not capability identity. Forcing it through `CapabilityResolver` would create a fake identity mapping with zero governance benefit. Recorded: **separate classification namespace, preserved as-is.**

## The four migration targets (all ARE mission capability identity)

1. `agent_runtime/manifest.py` validator (`KNOWN_CAPABILITIES` membership)
2. `agent_runtime/delegation.py::set_delegatable` (membership + subset invariant)
3. `agent_runtime/registry.py::validate` (membership)
4. `mission_wiring/browser_executor.py::_gate` (pre-contact capability gate)

## Migration semantics per target (all fail-closed, pre-contact)

- **Manifest validation:** resolve alias → canonical before recognition; manifests may keep storing aliases (backward compat, MANIFEST_REWRITE = 0).
- **Delegation:** canonical-equivalence enforced — `DOCUMENT_READ` and `document.read` are the SAME authority; permitting one automatically permits the other; no alias trick can expand permissions.
- **Registry validation:** same resolution-before-recognition.
- **Browser gate:** resolution happens before ANY browser/external contact; UNKNOWN/AMBIGUOUS/DORMANT/DISABLED/GENERATION_MISMATCH/NOT_TRUSTED all refuse pre-contact.

## Permanent distinction (restated)

`RESOLVED ≠ DELEGATED ≠ APPROVED ≠ EXECUTABLE` — the resolver only establishes known canonical vocabulary; every authority check downstream remains exactly as certified.

## Acceptance matrix (directive) tracked in `w4_3_certification.md` upon completion
