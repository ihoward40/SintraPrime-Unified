# voice_concierge/governed — SP-VOICE-001 Governed Voice Operations

## Purpose

Governed foundation that converts voice-originated requests into the same typed,
policy-inspected command path used by typed requests. Enforces the rule: *voice
may request and coordinate; existing SintraPrime policy decides, records,
approves, executes, or refuses.*

Increment One (Foundation): envelope, classifier, policy decision, session
state machine, confirmation, receipts, feature flags.

Increment Two (Orchestrator + Mock Providers): capability resolution, the
orchestrator that ties the foundation to execution, and mock-only capability
providers. Still no real telephony/calendar/messaging/filing/payment I/O —
execution means invoking a sandboxed mock provider, nothing else.

## Ownership

- `command_envelope.py` — immutable `VoiceCommandEnvelope`, enums, ID generation
- `classifier.py` — deterministic, policy-first risk classifier
- `policy.py` — pure risk-class → decision + confirmation matrix (no execution)
- `confirmation.py` — 5-minute expiry, changed-target invalidation, ambiguous-yes rules
- `session.py` — session state machine, cancellation/interruption, child-task propagation
- `receipts.py` — correlated machine-readable receipts, hash-only transcript retention
- `flags.py` — disabled-by-default feature flags
- `providers.py` — `VoiceActionProvider` protocol, `VoiceCapability` resolution (no I/O)
- `mock_providers.py` — mock-only provider implementations (email, calendar,
  messaging, task, filing, payment, generic); every result is `mock=True` with
  a `mock-` prefixed resource id
- `orchestrator.py` — `handle_voice_command` / `confirm_voice_command` /
  `cancel_voice_command`; the only place that invokes a provider
- `tests/` — unit tests for every foundation and orchestrator behavior

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
- Reads and drafts execute immediately (against mock providers only) once policy
  allows; writes and sensitive writes execute (against mock providers only)
  strictly after an explicit, exact-target confirmation — never before.
- Every `mock_providers.py` provider is a simulation: `ProviderResult.mock` is
  always `True` and `resource_id` is always `mock-`-prefixed. No provider in
  this package may contact a real phone/calendar/messaging/filing/payment
  backend; adding a real adapter requires a new, separately governed increment.

## Work Guidance

- Persistence, API surface, RBAC, and frontend for voice commands live in
  `portal/` (models/services/routers) and `web/`, not in this package. Keep
  this package pure/in-memory; the service layer owns tenant scoping, audit,
  and durability.
- Add new sensitive verbs to `classifier.py` conservatively; prefer over- to
  under-classification.
- Add new capability keywords to `providers.py::resolve_capability`
  conservatively; unmatched intents must keep failing safe to `GENERIC`.

## Verification

- `python -m pytest voice_concierge/governed/tests/ -q`

## Child DOX Index

*(None — leaf modules.)*
