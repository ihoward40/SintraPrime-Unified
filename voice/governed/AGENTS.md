# voice/governed — SP-VOICE-001 Governed Voice Operations

## Purpose

Governed foundation that converts voice-originated requests into the same typed,
policy-inspected command path used by typed requests. Enforces the rule: *voice
may request and coordinate; existing SintraPrime policy decides, records,
approves, executes, or refuses.*

Increment One (Foundation) scope only: envelope, classifier, policy decision,
session state machine, confirmation, receipts, feature flags, unit tests.

## Ownership

- `command_envelope.py` — immutable `VoiceCommandEnvelope`, enums, ID generation
- `classifier.py` — deterministic, policy-first risk classifier
- `policy.py` — pure risk-class → decision + confirmation matrix (no execution)
- `confirmation.py` — 5-minute expiry, changed-target invalidation, ambiguous-yes rules
- `session.py` — session state machine, cancellation/interruption, child-task propagation
- `receipts.py` — correlated machine-readable receipts, hash-only transcript retention
- `flags.py` — disabled-by-default feature flags
- `tests/` — unit tests for every foundation behavior

## Local Contracts

- Envelope is immutable after creation; state advances by producing new envelopes.
- Correlation ID propagates verbatim from envelope into every receipt.
- Classification is deterministic and runs before any model assistance; model
  assistance may never lower a risk class.
- Unknown/unmatched intent fails safe to `sensitive_write` (exact-target confirm).
- All capability flags default false; only transcript retention defaults, to `hash_only`.
- Raw transcript is persisted only when retention is `full`; otherwise hash only.
- This package routes NO production actions and touches NO production Hermes state.
- Prohibited actions are refused and logged; a flag can gate down to refusal but
  never up to execution.

## Work Guidance

- Keep this layer pure and side-effect-free. Orchestrator routing, real
  capabilities, and I/O belong to Increment Two and beyond.
- Add new sensitive verbs to `classifier.py` conservatively; prefer over- to
  under-classification.

## Verification

- `python -m pytest voice/governed/tests/ -q`

## Child DOX Index

*(None — leaf modules.)*
