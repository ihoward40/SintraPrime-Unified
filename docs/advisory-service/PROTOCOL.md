# Advisory Service — Increment One: Protocol Design

**Status:** DESIGN ONLY (Increment One). No runtime.
**Protocol Version:** 1.0.0
**Provider:** Provider-agnostic (OpenAI default; see §11)
**Classification:** Advisory Only
**Authority:** None
**Decision Rights:** None
**Supersedes:** None.

## 1. Purpose & Scope

The Advisory Service is a governed capability that provides strategic advisory
input to the Blackstone ecosystem. It is invoked by Hermes, which packages
context, calls a provider (default OpenAI), and posts the response back through
Slack. The Advisor never orchestrates, dispatches, or decides; it advises.

This document is **Increment One (Protocol Design)**. It specifies the protocol
and architectural scaffold only. Runtime implementation (Hermes command handler,
context packaging, provider client, Slack formatter) is **Increment Two** and is
NOT authorized here. Persistent advisory memory, autonomous Slack participation,
and automatic agent dispatch are explicitly out of scope (see §15).

## 2. Naming

"Advisor Lane" is renamed to **Advisory Service**. "Lane" implies a routing path;
this is a capability. The architecture:

```text
Principal
   │
   ▼
Hermes (Chief Orchestrator)
   │
   ▼
Mission Router
   │
   ▼
Advisory Service
   │
   ▼
Advisor Provider Interface (OpenAI / Anthropic / Local LLM / Future)
   │
   ▼
Hermes
   │
   ▼
Slack
```

Hermes remains the trusted runtime and audit layer. The Advisory Service is a
capability Hermes invokes; it does not replace or parallel Hermes.

## 3. Advisory Session ID

Every advisory interaction is assigned its own **Advisory Session ID**, distinct
from the Mission ID. A single mission may spawn multiple advisory sessions
(e.g., one for architecture review, another for strategy).

```text
ADV-YYYY-NNNNNN
```

Example: `ADV-2026-000001`. The sequence is per calendar year, allocated by
Hermes at session creation. The Session ID is the audit key for the interaction;
the Mission ID links it to the broader work. A mission may have many sessions;
a session belongs to exactly one mission.

## 4. Protocol Versioning

The protocol is versioned independently of software releases so Hermes and future
services can negotiate compatibility without coupling to deploy versions.

- Current: `1.0.0`.
- Header field `protocol_version` on every Packet and Response.
- Compatibility rule: a responder MUST accept any packet with the same MAJOR
  version; MINOR/PATCH differences are advisory. A MAJOR mismatch is a hard
  refusal (responder returns no advisory content).

## 5. Context Manifest (request)

Instead of passing arbitrary context, Hermes MUST supply an explicit **Context
Manifest**. This bounds prompt size and makes each session reproducible.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| mission_id | string | yes | Existing SintraPrime mission identifier (reuse, do not mint). |
| evidence_ids | string[] | yes | Handles/IDs of the evidence supplied. |
| relevant_bkgc_requirements | string[] | yes | BKGC requirement IDs in scope (e.g., `BKGC-R-001`). |
| relevant_cdrs | string[] | no | Related Constitutional Decision Records. |
| repository_commit | string | yes | Commit the advice is based on (reproducibility). |
| requested_question | string | yes | The specific question/decision. |
| expected_deliverable | enum | yes | One of the response classifications (§8). |

## 6. Advisory Scope (request)

Every advisory request explicitly declares what kind of authority/depth is being
requested. This prevents scope creep and calibrates the advisor's response.

Check one or more:

- **Informational** — summarize or explain.
- **Analytical** — examine tradeoffs / strengths / weaknesses.
- **Strategic** — prioritization / long-term direction.
- **Governance** — conformance with GB-1 / BKGC / CDRs.
- **Architectural** — structure / layers / subsystems.
- **Engineering** — code / implementation / technical fit.
- **Legal Research** — applicable law / precedent / compliance.

Example: "Does this PR violate BKGC?" = Governance + Analytical. "Should we
refactor this subsystem?" = Architectural + Strategic. The scope helps both
Hermes and the responder calibrate effort and completeness.

## 7. Advisory Packet Schema (request)

Hermes constructs an Advisory Packet and sends it to the Advisory Service.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| advisory_session_id | string | yes | Per §3 (`ADV-YYYY-NNNNNN`). |
| protocol_version | string | yes | Per §4 (`1.0.0`). |
| mission_id | string | yes | From Context Manifest. |
| context_manifest | object | yes | Per §5. |
| advisory_scope | string[] | yes | Per §6; one or more scope flags. |
| requested_advice | enum | yes | review \| architecture \| governance \| strategy. |
| governance_basis | string | yes | Governing document the advice must respect (e.g., "GB-1"). |
| provenance | object | yes | Per §11. |
| deadline | ISO-8601 | no | Advisory; not enforced as SLA. |

## 8. Response Schema & Service Contract (response)

The Advisory Service returns a structured response. The **Service Contract**
defines the boundary:

- **Inputs:** Mission, Context (Context Manifest), Question, Advisory Scope.
- **Outputs:** Assessment, Missing Evidence, Risks, Alternatives,
  Recommendation, Confidence, Coverage, Classification, Evidence Snapshot.

Everything else is implementation detail and is NOT part of the contract.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| assessment | string | yes | Overall assessment of the question. |
| missing_evidence | string[] | yes | Evidence that, if present, would change the analysis. |
| risks | string[] | yes | Risks identified. |
| alternatives | string[] | yes | Options considered. |
| recommendation | string | yes | The advisory recommendation. |
| confidence | enum | yes | low \| medium \| high — how strongly supported. |
| coverage | number[0..1] | yes | Fraction of relevant evidence that was available. |
| response_classification | enum | yes | Per §9. |
| evidence_snapshot | object | yes | Per §10 — reproducibility record. |
| not_a_decision | const | yes | Always true. The response is advice, not authorization. |
| human_override | const | yes | Always true (see §13). |
| advisory_classification | object | yes | Safeguard block (§13). |
| provenance | object | yes | Echo + extend of request provenance. |

## 9. Response Classification

Every response is classified into exactly one category to ease downstream
automation:

- **Information** — factual context only.
- **Analysis** — examination of a position/approach.
- **Recommendation** — prescriptive advice.
- **Architecture Review** — assessment of structure / layers.
- **Governance Review** — assessment against GB-1 / BKGC / CDRs.
- **Risk Review** — assessment of threats / likelihood / impact.

`expected_deliverable` in the request SHOULD hint the classification; the
responder confirms it.

## 10. Evidence Snapshot (immutable record)

Every advisory response includes an Evidence Snapshot so later readers know
exactly what evidence existed when the advice was given. This makes every
advisory reproducible and defensible.

| Field | Type | Description |
|-------|------|-------------|
| generated_at | ISO-8601 timestamp | When the advice was generated. |
| evidence_revision | string | Hash or version ID of the evidence set (e.g., git commit, database snapshot version). |
| repository_commit | string | Git SHA of the codebase the advice refers to. |

Example: if someone later asks "Why did the Advisor recommend this?", you can
look up the exact evidence set, the repository state, and the timestamp and
reproduce the context.

## 11. Confidence & Coverage

Two independent axes:

- **Confidence** — how strongly the recommendation is supported by the evidence
  that was present.
- **Coverage** — what fraction of the *relevant* evidence was actually available
  (0.0–1.0).

A high-confidence recommendation on partial coverage (e.g., 0.4) is materially
different from one on comprehensive coverage (0.95) and MUST be read as such. Low
coverage lowers the weight Hermes / the Principal should give the advice.

## 12. Provenance Metadata

Request provenance: requester, mission_id, source_channel, timestamp (UTC),
governance_basis, repository_commit.

Response provenance (extends request): provider (interface name), model
(configurable), provider_api_version, completion_id, advisory_service_version,
advisory_session_id, protocol_version.

Every packet and response carries provenance so advice is auditable (consistent
with Principle Zero / the Engineering Rule — objects without provenance are not
trustworthy).

## 13. Provider Abstraction (future-proofing)

The protocol does not care which engine fulfills the request. Define an
**Advisor Provider Interface** with at least:

| Provider | Notes |
|----------|-------|
| OpenAI | Default; model configurable (not hardcoded). |
| Anthropic | Alternative LLM provider. |
| Local LLM | On-prem / private-weight inference. |
| Future Provider | Reserved extension point. |

Selection is a configuration concern, not a protocol concern. The Response
records the provider actually used. The architecture is never bound to a single
model name.

## 14. Safeguards

Two blocks are appended to every response.

Advisory Classification block:

```text
Advisor Classification: Advisory
Decision Authority: Principal
Execution Authority: Hermes
Governance Authority: GB-1
```

Human Override block:

```text
Principal Review Required
This advisory is non-binding and requires Principal judgment before implementation.
```

The Advisory Service has **no decision rights** and **no execution authority**.
It cannot approve, reject, dispatch, or mutate system state. Any
governance-affecting recommendation routes through the CDR / BKGC amendment
process; the Advisory Service never bypasses GB-1.

## 15. Advisory Lifecycle

Even though Increment One does not implement transitions, the lifecycle is
defined now for operational clarity:

```text
Requested
   ↓
Prepared
   ↓
Submitted
   ↓
Analyzed
   ↓
Returned
   ↓
Acknowledged
   ↓
Archived
```

States:

- **Requested** — Advisory packet created; session ID allocated.
- **Prepared** — Context manifest and evidence gathered.
- **Submitted** — Packet sent to the Advisory Service.
- **Analyzed** — Advice being generated.
- **Returned** — Response received; formatted for Slack delivery.
- **Acknowledged** — Principal has reviewed and acknowledged the advice.
- **Archived** — Session stored for audit and reproducibility.

All transitions are immutable (append-only audit trail). No advisory can be
modified once returned.

## 16. Out of Scope (explicitly NOT authorized in Increment One)

This proposal does **not** implement:

- Slack integration / Slack message posting.
- OpenAI API integration / provider client libraries.
- Persistent advisory memory / cross-session state.
- Autonomous execution / unattended mode.
- Mission routing / automatic session allocation.
- Agent dispatch / background orchestration.
- Runtime lifecycle state transitions.

Those capabilities belong to **Increment Two (Hermes Integration)** and
**Increment Three (Advisory Services)** and are intentionally excluded from this
design review. This proposal is **protocol and service contract only**.

## 17. Capability Registration (BKR)

Registered as a Capability under the Blackstone Knowledge Registry (canonical
registry) and the Product Capability Index (`docs/CAPABILITY_INDEX.md`). Record:

| Field | Value |
|-------|-------|
| Capability | Advisor |
| Status | Engineering (design) |
| Version | 0.1 |
| Protocol Version | 1.0.0 |
| Provider | Provider-agnostic (OpenAI default) |
| Classification | Advisory Only |
| Authority | None |
| Decision Rights | None |

This is a capability record, not a new governance volume. It does not change the
seven-volume architecture (frozen by ARCHITECTURAL_FREEZE_NOTICE.md).

## 18. Increment Roadmap

- **Increment One (this document):** Protocol design, schemas, session ID,
  versioning, context manifest, advisory scope, service contract, classification,
  confidence + coverage, evidence snapshot, provenance, provider abstraction,
  lifecycle definition, capability registration. No runtime.
- **Increment Two (Hermes Integration):** Hermes command handler (`/advisor …`),
  context packaging (incl. Context Manifest), provider call via the interface,
  session-ID allocation, lifecycle state transitions, response formatting. Still
  no autonomous behavior.
- **Increment Three (Advisory Services):** context cache, conversation continuity,
  evidence references, advisory history, mission replay, governance compliance
  tagging — only after the protocol proves itself in Increment Two.

## 19. Acceptance for Increment One

- [ ] Advisory Session ID scheme defined (§3)
- [ ] Protocol versioning defined (§4)
- [ ] Context Manifest defined (§5)
- [ ] Advisory Scope defined (§6)
- [ ] Advisory Packet Schema defined (§7)
- [ ] Response Schema + Service Contract defined (§8)
- [ ] Response Classification defined (§9)
- [ ] Evidence Snapshot defined (§10)
- [ ] Confidence + Coverage defined (§11)
- [ ] Provenance defined (§12)
- [ ] Provider Abstraction defined (§13)
- [ ] Safeguards (classification + human override) defined (§14)
- [ ] Advisory Lifecycle defined (§15)
- [ ] Out-of-scope (explicitly NOT implemented) listed (§16)
- [ ] Capability registered (§17)
- [ ] No runtime code implementing execution paths
