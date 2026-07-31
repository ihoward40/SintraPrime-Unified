# Advisory Service — Increment Two (Hermes Integration): Implementation Plan

**Status:** PLANNING (design only). No runtime code in this document.
**Protocol Version:** 1.0.0 (unchanged; Increment Two does not alter the protocol).
**Authorized by:** CDR-0006 (Increment Two planning scope bounded to five items).
**Governing authority:** GB-1; Advisory Protocol v1.0.0 (`PROTOCOL.md`).
**Supersedes:** None.

This plan designs the five items authorized by CDR-0006:

1. Hermes command registration
2. Context Manifest assembly
3. Provider interface
4. Slack formatter
5. Audit record generation

It is the engineering hand-off from Protocol Design (Increment One) to a future
Implementation Review. It contains **no execution paths, no provider clients, no
Slack network calls, and no runtime logic**. Per CDR-0006, the Advisory Service
retains **no execution authority**; Hermes remains the orchestration authority;
the Principal remains the decision authority.

---

## 0. Standing Boundary (must hold through implementation)

- The Advisory Service **never** approves, dispatches, or mutates system state.
- Every response carries `not_a_decision = true` and `human_override = true`.
- The `AdvisoryClassification` and `HumanOverride` safeguard blocks (PROTOCOL §15)
  are appended by the formatter on every outbound message.
- Provider selection is configuration, not protocol (PROTOCOL §14).
- This plan does **not** authorize Increment Two *implementation* — only its
  design. Implementation requires a separate review/authorization.

---

## 0.1 Execution Flow (Sequence Diagram)

Happy-path advisory request (no runtime code; flow only):

```
Principal
   │  (decides to request advice)
   ▼
Slack
   │  /advisor <cmd>
   ▼
Hermes Router
   │  parse, authenticate, allocate ADV-YYYY-NNNNNN
   ▼
Context Manifest Builder
   │  assemble manifest (§2); reject if required fields missing
   ▼
Provider Interface
   │  complete(packet, manifest) -> RawCompletion
   ▼
Advisory Response
   │  build AdvisoryResponse (scaffold); attach safeguard blocks
   ▼
Slack Formatter
   │  render + append AdvisoryClassification / HumanOverride blocks
   ▼
Audit Record
   │  append lifecycle transition; archive session
   ▼
Slack
   │  deliver to source_channel
   ▼
Principal
   │  reviews (non-binding; human_override = true)
```

Every arrow that crosses the Trust Boundary (§0.2) is the only point where
external data enters or leaves the trusted runtime.

## 0.2 Trust Boundary

```
Principal
    │
    ▼
Hermes   ───── TRUST BOUNDARY (internal / trusted runtime) ─────
    │
    ▼
Provider (OpenAI / Anthropic / Local LLM)
    │  ───── TRUST BOUNDARY (external, untrusted inference) ─────
    ▼
Advisory Response
    │
    ▼
Hermes   ───── TRUST BOUNDARY (internal / trusted runtime) ─────
    │
    ▼
Slack
```

**Context Manifest Trust Rule (MUST).** The Provider SHALL NOT receive more
information than is described by the Context Manifest. Context packaging MUST pass
only the assembled manifest fields; no ambient state, environment variables,
credentials, or out-of-manifest system data may be included. This minimizes
information leakage and keeps the advisory surface disciplined.

## 0.3 Failure-State Matrix

Behavior only — no implementation. Maps PROTOCOL §18 error conditions to Hermes
behavior.

| Failure                    | Detection point            | Hermes behavior                        | Result                          |
| -------------------------- | -------------------------- | -------------------------------------- | ------------------------------- |
| Missing Context            | Context Manifest Builder   | Reject before provider call; emit §18  | Error returned; no provider call |
| Invalid evidence reference | Context Manifest Builder   | Reject; emit §18                       | Error returned                  |
| Permission denied          | Hermes Router (authz)      | Reject; emit §18                       | Permission error                |
| Unsupported protocol ver.  | Packet validation          | Reject; no advisory content            | Hard refusal                    |
| Provider unavailable       | Provider Interface         | Return "advisory unavailable"; emit §18 | No retry / no auto-dispatch     |

## 0.4 Timing Boundaries

- Context assembly: **synchronous** (within the request path).
- Provider call: **synchronous** for Increment Two (no queue / async worker).
- Audit record: written **after** advisory returned (post-response, append-only).
- Slack delivery: synchronous, after formatting.
- **No asynchronous processing, no background workers, no scheduled jobs.**
- Implication: `/advisor` holds until the full flow completes. If latency becomes
  a concern, that is an Increment Three matter, not Two.

---

## 1. Hermes Command Registration (`/advisor …`)

**Owner:** Hermes command router (NOT the Advisory Service). The Advisory Service
is invoked by Hermes; it does not receive slash commands directly.

**Responsibility.** Parse an advisory command, authenticate the requester and
scope, allocate an Advisory Session ID, and trigger Context Manifest assembly.

**Command taxonomy** (maps to `RequestedAdvice` + `AdvisoryScope`):

| Command | Maps to `requested_advice` | Typical `advisory_scope` |
|---------|----------------------------|--------------------------|
| `/advisor review <target>` | `review` | Analytical, Engineering |
| `/advisor architecture <target>` | `architecture` | Architectural, Analytical |
| `/advisor governance <target>` | `governance` | Governance, Analytical |
| `/advisor strategy <target>` | `strategy` | Strategic, Analytical |

**Interface contract (planning).**

```
register_command(name="advisor", handler=advisory_command_handler)
advisory_command_handler(command: str, requester: str, source_channel: str)
    -> allocates ADV-YYYY-NNNNNN
    -> delegates to Context Manifest assembly
    -> returns nothing directly; result flows via Slack formatter
```

**Planning concerns.**

- Session-ID sequence allocation is per calendar year, performed by Hermes at
  session creation (PROTOCOL §4). The scaffold helper `format_advisory_session_id`
  formats only; allocation lives here.
- Authorization: invocation requires a permission check (PROTOCOL §18
  "Authorization failure"). Define which roles may invoke `/advisor` and at which
  `advisory_scope` (e.g., `Legal Research` may be restricted).
- The handler MUST NOT decide or execute. It packages and calls.

---

## 2. Context Manifest Assembly

**Owner:** Hermes (packaging layer).

**Responsibility.** Build the `ContextManifest` (scaffold dataclass, PROTOCOL §6)
from the command target and live ecosystem state.

**Inputs → fields.**

| Manifest field | Source |
|---------------|--------|
| `mission_id` | Reuse existing SintraPrime mission ID; mint none. |
| `evidence_ids` | Resolve from the evidence/vault store for the target. |
| `relevant_bkgc_requirements` | BKGC requirement registry lookup. |
| `relevant_cdrs` | CDR registry lookup (optional). |
| `repository_commit` | Git SHA of the codebase the advice concerns (reproducibility). |
| `requested_question` | Derived from the command target + type. |
| `expected_deliverable` | Mapped from `requested_advice` → `ResponseClassification`. |

**Planning concerns.**

- Evidence retrieval strategy: how a target (PR-219, GB-1, a subsystem) resolves
  to concrete `evidence_ids`. This is the primary open integration point.
- `repository_commit` MUST be captured at invocation time, not at advice time.
- Validation: if any required field is absent, emit PROTOCOL §18 "Missing context"
  error — do not call the provider.

---

## 3. Provider Interface

**Owner:** Advisory Service (fulfillment only; no governance authority).

**Responsibility.** Submit the assembled packet to a configured provider through a
provider-agnostic interface and return the raw completion plus provenance.

**Interface contract (planning).**

```
class AdvisorProvider(Protocol):
    def complete(packet: AdvisoryPacket, manifest: ContextManifest)
        -> RawCompletion
    # returns: text + provider, model, provider_api_version, completion_id
```

**Providers (PROTOCOL §14):** OpenAI (default), Anthropic, Local LLM, Future.
Model is configurable, never hardcoded. Response provenance records the provider
actually used (PROTOCOL §13).

**Planning concerns.**

- Config schema: `{ provider: enum, model: str, api_version: str }` selected by
  configuration, not by code branching.
- The completion is handed to the Slack formatter; the Advisory Service does not
  itself post to Slack.
- Error path: "Provider unavailable" (PROTOCOL §18) returns the reserved error
  envelope; no retry/auto-dispatch logic (that would be execution authority).

---

## 4. Slack Formatter

**Owner:** Hermes (presentation layer).

**Responsibility.** Render the `AdvisoryResponse` into a Slack message for delivery
to `source_channel` (from provenance).

**Content (PROTOCOL §9, §15, §17).**

- Assessment, Missing Evidence, Risks, Alternatives, Recommendation.
- Confidence + Coverage rendered together (high confidence on low coverage MUST be
  visually de-weighted).
- Evidence Snapshot summary: `generated_at`, `evidence_revision`,
  `repository_commit` (reproducibility).
- The two safeguard blocks appended verbatim:
  - `AdvisoryClassification` (Advisory / Decision: Principal / Execution: Hermes /
    Governance: GB-1)
  - `HumanOverride` (Principal Review Required; non-binding).

**Planning concerns.**

- Message schema (Slack blocks / MRKDOWN) is presentation only; it MUST NOT alter
  advice content or authority.
- Channel routing returns to `source_channel` from the request provenance.
- `not_a_decision` / `human_override` flags are surfaced, not hidden.

---

## 5. Audit Record Generation

**Owner:** Hermes (audit layer).

**Responsibility.** On each lifecycle transition (PROTOCOL §17), append an
immutable record to the audit trail; on `Archived`, store the full session
(AdvisoryResponse + Provenance + Evidence Snapshot + Context Manifest) for audit
and reproducibility. Session ID (`ADV-YYYY-NNNNNN`) is the audit key.

**Audit record fields (planning).**

- `advisory_session_id`, `mission_id`, `protocol_version`, `service_version`
- `requested_advice`, `advisory_scope`, `governance_basis`
- `provider`, `model`, `provider_api_version`, `completion_id`
- `lifecycle_state` (per transition), `transitioned_at`
- `evidence_revision`, `repository_commit`
- `confidence`, `coverage`, `response_classification`
- `requester`, `source_channel`

**Planning concerns — metrics readiness (links to Priority 3).** The audit schema
above is the evidence base for the operational metrics the Principal wants to begin
collecting. It MUST capture, from day one, the fields needed for:

- **Decision Rework Rate** — correlate `advisory_session_id` → later mission/decision rework.
- **Evidence Sufficiency Gate outcomes** — `coverage` per session.
- **Time mission → principal decision** — `transitioned_at` deltas.
- **Evidence requests per matter** — `evidence_ids` count per `mission_id`.
- **Unsupported assumptions identified** — derive from `missing_evidence`.
- **Advisory utilization** — session count by `requested_advice` / `advisory_scope` / channel.

Designing the audit schema now to support these avoids retrofitting when Priority 3
instrumentation begins.

---

## 6. Non-Goals (this planning phase)

Explicitly NOT designed here (consistent with CDR-0006 and PROTOCOL §20):

- Persistent advisory memory / cross-session state.
- Autonomous Slack participation or unattended mode.
- Agent dispatch / background orchestration / mission routing beyond command parsing.
- Runtime lifecycle *state machine* code (transitions are defined; implementation deferred).
- Error-handling *implementation* (contract defined in PROTOCOL §18; code deferred).
- Any new top-level governance construct or architectural layer.

---

## 7. Planning Acceptance Criteria

This planning deliverable is complete when:

- [ ] Each of the five items has an owner, responsibility statement, and interface contract.
- [ ] Command taxonomy maps unambiguously to `RequestedAdvice` + `AdvisoryScope`.
- [ ] Context Manifest field sources are identified for every required field.
- [ ] Provider interface signature is defined and provider-agnostic.
- [ ] Slack formatter content and safeguard-block handling are specified.
- [ ] Audit record schema is defined AND supports the Priority 3 metrics.
- [ ] Non-execution boundary is reaffirmed in every component.
- [ ] No runtime code has been written.

---

## 8. Open Questions for the Implementation Review

1. Where does `evidence_ids` resolution live — vault API, graph query, or manual?
2. What is the permission model for `/advisor` scopes (esp. `Legal Research`)?
3. Which store holds archived sessions (BKR audit log, database, object store)?
4. Is the provider call synchronous (blocking Slack response) or queued?
5. Does Increment Two require a protocol version bump, or stays at 1.0.0?

These are implementation concerns; resolution belongs to the separate
implementation review that CDR-0006 requires before any runtime work begins.
