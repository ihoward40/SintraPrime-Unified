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
and automatic agent dispatch are explicitly out of scope (see §13).

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

## 6. Advisory Packet Schema (request)

Hermes constructs an Advisory Packet and sends it to the Advisory Service.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| advisory_session_id | string | yes | Per §3 (`ADV-YYYY-NNNNNN`). |
| protocol_version | string | yes | Per §4 (`1.0.0`). |
| mission_id | string | yes | From Context Manifest. |
| context_manifest | object | yes | Per §5. |
| requested_advice | enum | yes | review \| architecture \| governance \| strategy. |
| governance_basis | string | yes | Governing document the advice must respect (e.g., "GB-1"). |
| provenance | object | yes | Per §10. |
| deadline | ISO-8601 | no | Advisory; not enforced as SLA. |

## 7. Response Schema & Service Contract (response)

The Advisory Service returns a structured response. The **Service Contract**
defines the boundary:

- **Inputs:** Mission, Context (Context Manifest), Question.
- **Outputs:** Assessment, Missing Evidence, Risks, Alternatives,
  Recommendation, Confidence, Coverage, Classification.

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
| response_classification | enum | yes | Per §8. |
| not_a_decision | const | yes | Always true. The response is advice, not authorization. |
| human_override | const | yes | Always true (see §12). |
| advisory_classification | object | yes | Safeguard block (§12). |
| provenance | object | yes | Echo + extend of request provenance. |

## 8. Response Classification

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

## 9. Confidence & Coverage

Two independent axes:

- **Confidence** — how strongly the recommendation is supported by the evidence
  that was present.
- **Coverage** — what fraction of the *relevant* evidence was actually available
  (0.0–1.0).

A high-confidence recommendation on partial coverage (e.g., 0.4) is materially
different from one on comprehensive coverage (0.95) and MUST be read as such. Low
coverage lowers the weight Hermes / the Principal should give the advice.

## 10. Provenance Metadata

Request provenance: requester, mission_id, source_channel, timestamp (UTC),
governance_basis, repository_commit.

Response provenance (extends request): provider (interface name), model
(configurable), provider_api_version, completion_id, advisory_service_version,
advisory_session_id, protocol_version.

Every packet and response carries provenance so advice is auditable (consistent
with Principle Zero / the Engineering Rule — objects without provenance are not
trustworthy).

## 11. Provider Abstraction (future-proofing)

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

## 12. Safeguards

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

## 13. Out of Scope (explicitly NOT authorized)

- Autonomous Slack participation (the Advisor is invoked by Hermes, not present).
- Persistent advisory memory (stateless per request in Increment One).
- Runtime orchestration (no agent dispatch, no job scheduling).
- Automatic agent dispatch.
- Production deployment.
- Provider *implementation* (the interface is specified; engines are Increment Two+).

These are deferred to Increment Three and require separate authorization after
protocol review.

## 14. Capability Registration (BKR)

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

## 15. Increment Roadmap

- **Increment One (this document):** Protocol design, schemas, session ID,
  versioning, context manifest, service contract, classification, confidence +
  coverage, provenance, provider abstraction, capability registration. No runtime.
- **Increment Two (Hermes Integration):** Hermes command handler (`/advisor …`),
  context packaging (incl. Context Manifest), provider call via the interface,
  session-ID allocation, response formatting. Still no autonomous behavior.
- **Increment Three (Advisory Services):** context cache, conversation continuity,
  evidence references, advisory history, mission replay, governance compliance
  tagging — only after the protocol proves itself.

## 16. Acceptance for Increment One

- [ ] Advisory Session ID scheme defined (§3)
- [ ] Protocol versioning defined (§4)
- [ ] Context Manifest defined (§5)
- [ ] Advisory Packet Schema defined (§6)
- [ ] Response Schema + Service Contract defined (§7)
- [ ] Response Classification defined (§8)
- [ ] Confidence + Coverage defined (§9)
- [ ] Provenance defined (§10)
- [ ] Provider Abstraction defined (§11)
- [ ] Safeguards (classification + human override) defined (§12)
- [ ] Capability registered (§14)
- [ ] No runtime code implementing execution paths
