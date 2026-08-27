# SP-LIVE-001 threat model

## Assets and trust boundaries

Assets: Principal identity/session, voice/audio/transcripts, mission authority, governed memory, specialist inputs/outputs, model decisions, action envelope/approval, capability/credential leases, provider attempts/receipts, verification evidence, and Principal Brief.

Trust boundaries: audio device → transcription; Principal Gateway → mission authority; memory stores → retrieval filter; orchestrator → isolated specialists/models; reconciler → proposed action; voice/display renderer → Principal; approval record → capability resolver; canonical executor → provider; provider receipt → independent verifier; evidence writers → sealed chain; canonical brief → voice/text renderers.

## Threats and mandatory controls

| Threat | Mandatory control | Failure behavior |
|---|---|---|
| Spoofed Principal voice | Voice is never sole factor; current Principal Gateway session and step-up for consequence | `IDENTITY_AMBIGUOUS`; block |
| Transcription error | Confidence/segment evidence, read-back, explicit proposal short code | Clarify; no approval |
| Prompt injection | Treat speech, memory, provider, and documents as data; immutable policy hierarchy | Quarantine/block instruction |
| Poisoned memory | Provenance, trust labels, frozen governance identities, contradiction surfacing | Exclude item or `INCOMPLETE` |
| Specialist collusion/leakage | Fresh isolation, enumerated inputs, no direct channels/credentials, sealed outputs | Invalidate affected lanes |
| Authority escalation | Non-transitive grants, exact mission/capability checks at every transition | `AUTHORITY_MISSING`; block |
| Stale approval | Explicit expiry, session/certification/mission currentness checks immediately before I/O | `APPROVAL_EXPIRED` |
| Action substitution | Canonical action hash in spoken/display proposal, approval, executor, receipt | `APPROVAL_INVALID`; block |
| Destination substitution | Exact canonical destination/account binding in envelope and adapter allowlist | Block before I/O |
| Duplicate execution | Durable idempotency, atomic attempt counter, in-flight suppression, terminal replay | Stop second attempt |
| Timeout ambiguity | Attempt lifecycle and independent reconciliation; no blind retry | `INCOMPLETE` pending evidence |
| Provider success without receipt | Preserve request/attempt; verify external state without retry | `EVIDENCE_INCOMPLETE` |
| Fake verification | Separate verifier identity/capability/request; external state observation and receipt comparison | `VERIFICATION_FAILED` |
| Evidence tampering | Append-only hash chain, external chain root, immutable raw artifacts, secret scan | `FAIL` |
| Replay | Mission/session/nonces, expiries, version/CAS, one-time approval/idempotency | Return prior result or block |
| Kill-switch failure | Global/program/mission/capability/account switches checked at readiness and immediately before I/O | `FAIL`; incident stop |
| Voice echo approving itself | Output-channel suppression and speaker/source separation | Approval ignored |
| Barge-in race | Atomic cancellation/attempt transition and durable event order | Cancel or reconcile; never retry |
| Model/provider drift | Exact provider/model policy and response identity evidence | Block or re-propose |
| Brief fabrication | Spoken/written brief generated from one sealed canonical brief | `INCOMPLETE` |

## Safety invariants

1. Conversation has no consequential authority.
2. Memory and specialists cannot approve or execute.
3. Approval cannot widen mission or capability authority.
4. Capability certification cannot substitute for approval.
5. Exactly one provider attempt may represent the certified side effect.
6. Execution cannot self-verify.
7. Missing evidence cannot be narrated into completion.

## Out of scope for D1

No microphone, speaker, biometric, account, credential, provider, connector, external tool, or side effect is activated. Threat controls are design requirements pending later implementation and certification.
