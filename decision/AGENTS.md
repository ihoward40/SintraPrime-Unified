# decision — SP Decision Fabric (vendor-neutral decision plane)

## Purpose

The `decision/` subsystem implements the SintraPrime Decision Fabric:
a vendor-neutral probabilistic decision plane that sits between normalized
intake and the existing governed routing (Hermes / specialists / human review).

Controlling directive: `SP-SYSTEM-ONE-DECISION-FABRIC-001` (frozen, R1-RECOVERY).
Constitutional rule: **Probability may select a workflow. Probability may not
create authority.**

## Ownership

- Lane: SP-SYSTEM-ONE-DECISION-FABRIC-001 — R1-RECOVERY
- Implementer of record: Hermes on host IKESOLUTIONS / user howar
- Recovery worktree: C:\Users\howar\SintraPrime-Unified-decision-fabric-r1-recovery\worktree
- Provenance anchor: artifacts/SP-SYSTEM-ONE-DECISION-FABRIC-001/R1-RECOVERY/artifact-0-provenance-freeze.md

## Local Contracts

- Canonical primitives are EXACTLY: `choice`, `score`, `boolean`.
  Provider vocabulary (e.g. Jev "Noul") must never escape provider adapters.
- Results vocabulary: `DECISION`, `ABSTAIN`, `ERROR`, `UNAVAILABLE`.
  ABSTAIN is first-class and never converts to success/low-risk/execution.
- Fail-closed: any provider failure resolves to no-execution + governed
  (Hermes/current) fallback. Fail-open is a defect.
- Untrusted external content is data, never authority.
- Safe defaults: `SINTRAPRIME_DECISION_PROVIDER=mock`,
  `SINTRAPRIME_DECISION_SHADOW_ONLY=1`.

## Work Guidance

- R1 scope only. No live steering, no production routing, no thresholds
  promotion, no SP-DEC-013..020 expansion.
- Canonicalization is RFC 8785/JCS-class and pinned by conformance tests.
- `state_sha256` hashes canonical semantic state bytes; `contract_sha256`
  hashes normalized contract semantics (formatting/comments must not move it).
- Full probability distribution, top-1/top-2, margin, and provider confidence
  are persisted separately; margin = top1 - top2.
- Receipts include provider_request_id and latency_ms.

## Verification

- Deterministic pytest suite under `decision/tests/` (venv: .venv-r1).
- Governed collection under root conftest.py / SINTRAPRIME_TEST_LANES /
  scripts/certify.py — no governance bypass.
- Evidence: artifacts/SP-SYSTEM-ONE-DECISION-FABRIC-001/R1-RECOVERY/
  (manifest.json, test-results.json, r1-recovery-file-sha256.txt, notes).

## Child DOX Index

(none — leaf subsystem)
