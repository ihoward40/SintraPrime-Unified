# Advisory Service — Increment One: Protocol Design

**Status:** DESIGN ONLY (Increment One). No runtime.
**Version:** 0.1
**Provider:** OpenAI (model configurable)
**Classification:** Advisory Only
**Authority:** None
**Decision Rights:** None
**Supersedes:** None.

## 1. Purpose & Scope

The Advisory Service is a governed capability that provides strategic advisory
input to the Blackstone ecosystem. It is invoked by Hermes, which packages
context, calls the OpenAI API, and posts the response back through Slack. The
Advisor never orchestrates, dispatches, or decides; it advises.

This document is **Increment One (Protocol Design)**. It specifies the protocol
and architectural scaffold only. Runtime implementation (Hermes command handler,
OpenAI client, Slack formatter) is **Increment Two** and is NOT authorized here.
Persistent advisory memory, autonomous Slack participation, and automatic agent
dispatch are explicitly out of scope (see §9).

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
OpenAI (Strategic Advisory)
   │
   ▼
Hermes
   │
   ▼
Slack
```

Hermes remains the trusted runtime and audit layer. The Advisory Service is a
capability Hermes invokes; it does not replace or parallel Hermes.

## 3. Advisory Packet Schema (request)

Hermes constructs an Advisory Packet and sends it to the Advisory Service.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| mission_id | string | yes | Existing SintraPrime mission identifier (reuse, do not mint). |
| question | string | yes | The specific question or decision under advisement. |
| current_evidence | string[] | yes | Evidence already known, with source references where available. |
| known_risks | string[] | no | Risks already identified. |
| alternatives | string[] | no | Candidate options under consideration. |
| requested_advice | enum | yes | One of: review, architecture, governance, strategy. |
| deadline | ISO-8601 | no | When a response is needed (advisory; not enforced as SLA). |
| provenance | object | yes | See §7. |
| governance_basis | string | yes | The governance document the advice must respect (e.g., "GB-1"). |

## 4. Response Schema

The Advisory Service returns a structured response.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| assessment | string | yes | Overall assessment of the question. |
| strengths | string[] | yes | Strengths of the current position/approach. |
| weaknesses | string[] | yes | Weaknesses or gaps. |
| missing_evidence | string[] | yes | Evidence that, if present, would change the analysis. |
| recommendation | string | yes | The advisory recommendation. |
| confidence | enum | yes | low \| medium \| high. |
| questions | string[] | no | Clarifying questions for the Principal. |
| not_a_decision | const | yes | Always true. The response is advice, not authorization. |
| advisory_classification | object | yes | See §8 safeguard block. |
| provenance | object | yes | Echo + extend of request provenance; includes model/provider/version used. |

## 5. Slack Command Specification

Hermes exposes a command interface. All commands are handled by Hermes; the
Advisory Service performs no Slack parsing.

| Command | Arguments | Meaning |
|---------|-----------|---------|
| `/advisor review <target>` | PR-219, strategy CP23, … | Review a concrete artifact. |
| `/advisor architecture <topic>` | Evidence Graph, … | Architecture review/advice. |
| `/advisor governance <ref>` | GB-1, CDR-0006, … | Governance conformance advice. |
| `/advisor strategy <mission>` | CP23, … | Strategic prioritization advice. |

Hermes translates the command into an Advisory Packet (filling mission_id,
question, current_evidence from its own context), calls the Advisory Service,
and posts the formatted Response to the originating Slack channel.

## 6. Mission Routing Diagram

```text
User / Principal
      │  /advisor <cmd> <arg>
      ▼
Slack (channel)
      │
      ▼
Hermes Gateway
      │  parse → Advisory Packet
      ▼
Mission Router
      │  route by requested_advice
      ▼
Advisory Service
      │  package + call OpenAI
      ▼
OpenAI (Strategic Advisory, model configurable)
      │  raw completion
      ▼
Advisory Service
      │  structure → Response Schema + classification block
      ▼
Hermes
      │  format + post
      ▼
Slack (channel)  →  Audit Log
```

The Audit Log is written by Hermes (the existing audit/evidence subsystem), not
by the Advisory Service.

## 7. Provenance Metadata

Every packet and response carries provenance so advice is auditable (consistent
with Principle Zero / the Engineering Rule — objects without provenance are not
trustworthy).

Request provenance:
- requester (Principal / agent / slack_user_id)
- mission_id
- source_channel
- timestamp (UTC)
- governance_basis

Response provenance (extends request):
- provider (OpenAI)
- model (configurable; recorded, not hardcoded)
- provider_api_version
- completion_id
- advisory_service_version (0.1)
- advisory_classification (§8)

## 8. Safeguard — Advisory Classification Block

Every advisor response MUST automatically append the following block, so
recommendations are never confused with approvals:

```text
Advisor Classification: Advisory
Decision Authority: Principal
Execution Authority: Hermes
Governance Authority: GB-1
```

The Advisory Service has **no decision rights** and **no execution authority**.
It cannot approve, reject, dispatch, or mutate system state. Any
governance-affecting recommendation routes through the CDR / BKGC amendment
process; the Advisory Service never bypasses GB-1.

## 9. Out of Scope (explicitly NOT authorized)

- Autonomous Slack participation (the Advisor is invoked by Hermes, not present).
- Persistent advisory memory (no cross-session state; stateless per request in Increment One).
- Runtime orchestration (no agent dispatch, no job scheduling).
- Automatic agent dispatch.
- Production deployment.

These are deferred to Increment Three (Advisory Services) and require separate
authorization after protocol review.

## 10. Model Configuration

The architecture is NOT bound to a specific model name. Register:

| Field | Value |
|-------|-------|
| Provider | OpenAI |
| Capability | Strategic Advisory |
| Model | Configurable (set via configuration; upgrade without architecture change) |

## 11. Capability Registration (BKR)

Registered as a Capability under the Blackstone Knowledge Registry (canonical
registry) and the Product Capability Index (`docs/CAPABILITY_INDEX.md`). Record:

| Field | Value |
|-------|-------|
| Capability | Advisor |
| Status | Engineering (design) |
| Version | 0.1 |
| Provider | OpenAI |
| Classification | Advisory Only |
| Authority | None |
| Decision Rights | None |

This is a capability record, not a new governance volume. It does not change the
seven-volume architecture (frozen by ARCHITECTURAL_FREEZE_NOTICE.md).

## 12. Increment Roadmap

- **Increment One (this document):** Protocol design, schemas, command spec,
  routing, audit model, provenance, capability registration. No runtime.
- **Increment Two (Hermes Integration):** Hermes command handler (`/advisor …`),
  context packaging, OpenAI call, response formatting. Still no autonomous behavior.
- **Increment Three (Advisory Services):** context cache, conversation continuity,
  evidence references, advisory history, mission replay, governance compliance
  tagging — only after the protocol proves itself.

## 13. Acceptance for Increment One

- [ ] Advisory Packet Schema defined (§3)
- [ ] Response Schema defined (§4)
- [ ] Slack command specification defined (§5)
- [ ] Mission routing diagram defined (§6)
- [ ] Audit model defined (§6, §7)
- [ ] Provenance metadata defined (§7)
- [ ] Safeguard classification block defined (§8)
- [ ] Capability registered (§11)
- [ ] No runtime code implementing execution paths
