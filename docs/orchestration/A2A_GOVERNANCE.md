# A2A governance controls

The A2A transport now separates **internal collaboration** from **external action**.

## Enforced defaults

- External actions are **blocked by default**.
- Unsupported or risky evidence claims are blocked from dispatch.
- Approval receipts bind approval to the exact recipient and final content hash.
- Attachment hashes must match the approved receipt.
- Every message carries a final content hash in its headers for auditability.
- Agent permissions are described in [`orchestration/agent_registry.json`](../../orchestration/agent_registry.json), including the orchestrator plus Blackstone Verifier, Justice Scribe, Source Hunter, Trust Vault Clerk, SintraPrime Builder, Covenant Auditor, and the blocked Dispatch Desk candidate.
- Autonomous self-improvement, deployment, publishing, filing, payments, and third-party contact remain disabled for the default orchestrator profile.

## Evidence classifications

Claims should be explicitly classified as one of:

`PROVEN`, `USER-STATED`, `INFERRED`, `UNVERIFIED`, `UNSUPPORTED`, or `RISKY`.

`UNSUPPORTED` and `RISKY` claims require review before a message can be dispatched.

## Approval receipt

An external action must include:

- `approved_by`
- `approved_output_id`
- `recipient`
- `final_content_hash`
- `attachment_hashes`
- approval timestamp
- delivery method

Changing even one character after approval causes the content hash check to fail.

## Verification matrix

| Control | Status | Proof |
|---|---|---|
| Internal A2A delivery | DONE | Existing A2A tests and Redis transport tests |
| Cross-process Redis delivery | DONE | `orchestration/tests/test_redis_a2a.py` |
| Approval gate for external messages | DONE | `orchestration/tests/test_a2a_governance.py` |
| Evidence gate | DONE | Unsupported/risky claim test |
| Content and attachment hash binding | DONE | Governance validator and mismatch test |
| Agent registry | PATCH A COMPLETE | `orchestration/agent_registry.json` plus registry-completeness test |
| Durable append-only audit storage | PENDING | A future storage adapter should persist `DispatchAudit` records |
| Restart persistence and bypass-resistance integration test | PENDING | Requires the production runtime and persistence owner |
| Broad external-action enablement | BLOCKED BY DEFAULT | Requires explicit approval and a reviewed agent profile |

The implementation status intentionally distinguishes technical enforcement from rules that only exist in documentation. No agent collaboration capability should be treated as production-complete until it has **proof, enforcement, and an audit trail**.
