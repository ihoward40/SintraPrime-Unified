# Mission Control Foundation Architecture

**Status:** COMPLETE
**ADR:** ADR-002
**Phase:** 3A — Foundation (read-only projection)

## 1. Overview

The Mission Control Foundation establishes a read-only projection layer over the Brain's command authority. Mission Control does not own state; it projects state that the Brain owns. This document describes the architecture under ADR-002, including authority boundaries, data contracts, API surface, frontend shell, and the deliberate non-mutation posture of this phase.

## 2. Authority Boundaries

Under ADR-002, authority is split between the Brain and Mission Control as follows.

### 2.1 Brain (System of Record)

The Brain is the sole owner of:

- **Intent state** — command ledger entries, their lifecycle, and ordering
- **Dispatch state** — which executor receives a command and when
- **Cancellation state** — approval, retry, replay, lease, and dispatch transitions

The Brain holds the canonical command ledger. All mutation authority over intent, dispatch, and cancellation lives exclusively in the Brain.

### 2.2 Mission Control (Read-Only Projection)

Mission Control is a **read-only projection** of Brain-owned state. It:

- Projects command ledger entries as "intents"
- Projects run-control state derived from the command ledger
- Surfaces causation chains for traceability
- Exposes the Sigma gate status (read-only)

Mission Control performs **no mutation** of Brain-owned state. It does not issue commands, approve cancellations, retry, replay, lease, or dispatch. It observes and presents.

## 3. Data Contracts

### 3.1 Command Ledger

The command ledger is the Brain's authoritative record of every command issued. Mission Control projects ledger entries as intents. The projection is read-only; Mission Control never writes to the ledger.

### 3.2 Run-Control Projection

Run-control is a derived projection from the command ledger. It summarizes the execution-control surface (state, workflow association, lease timing) without introducing independent state. The projection is recomputed from ledger data on read.

### 3.3 Causation Chain

The causation chain traces command lineage — which command caused which command, enabling dependency and impact analysis. The chain is assembled from ledger metadata and is read-only.

### 3.4 Sigma Gate

The Sigma gate (`SIGMA_LEASE_EXPIRY_CONTINUATION_GATE`) is a read-only status surface in Mission Control. Its current state is **BLOCKED**. Mission Control reports the gate status but does not control it. Gate control is governed by ADR-002 Section 2.5. ADR-MC-001 was ratified on 2026-08-05 (status: ACCEPTED); the gate remains BLOCKED pending implementation and certification of the ADR criteria.

## 4. Read-Only API Surface

Mission Control introduces **6 new GET endpoints** plus the existing summary endpoint. No new POST, PUT, PATCH, or DELETE routes were added.

| Method | Path | Status |
|--------|------|--------|
| GET | /api/v1/mission-control/summary | Existing, unchanged |
| GET | /api/v1/mission-control/intents | NEW, tenant-scoped |
| GET | /api/v1/mission-control/intents/{command_id} | NEW, tenant-scoped |
| GET | /api/v1/mission-control/run-controls | NEW, tenant-scoped |
| GET | /api/v1/mission-control/run-controls/{run_control_id} | NEW, tenant-scoped |
| GET | /api/v1/mission-control/intents/{command_id}/causation-chain | NEW, tenant-scoped |
| GET | /api/v1/mission-control/sigma-gate | NEW, read-only gate status |

All new endpoints require the `MISSION_COMMAND_READ` permission.

### 4.1 Pre-Existing POST /commands Endpoint

A pre-existing `POST /api/v1/mission-control/commands` endpoint remains **unchanged**. It is **refusal-only**: it cannot execute commands and returns `COMMAND_EXECUTION_NOT_ENABLED`. This endpoint predates the Foundation phase and is not a new mutation route introduced by this work.

## 5. Frontend Shell

The frontend shell is a thin, read-only presentation layer.

### 5.1 Layout

The Layout component provides the structural shell (navigation, routing frame) for the Mission Control surface. It contains no mutation controls.

### 5.2 Home (Intent & Run-Control Projections)

The Home view renders two read-only projections:

- **Intent projection** — list/detail of projected command ledger entries
- **Run-control projection** — list/detail of derived run-control state

Both projections consume the read-only GET endpoints. No mutation actions are wired.

### 5.3 Surface (Data Adapters)

The Surface layer uses data adapters to shape backend responses for the frontend views. Adapters perform no side effects and issue no writes.

## 6. Non-Mutation Posture

This phase deliberately introduces **no new mutation routes**:

- No cancellation mutation added
- No approval mutation added
- No retry mutation added
- No replay mutation added
- No lease mutation added
- No dispatch mutation added

The pre-existing refusal-only `POST /commands` endpoint remains unchanged and cannot execute commands.

## 7. Persistence

**No persistence migrations were added.** Mission Control reads from existing projections and ledger data. No new tables, no schema changes, no migrations.

## 8. Sigma Gate & Cancellation Controls

- `SIGMA_LEASE_EXPIRY_CONTINUATION_GATE` is **BLOCKED**.
- All cancellation controls are **DISABLED**.
- `is_cancellation_blocked()` returns `True`.
- The gate remains blocking until ADR-MC-001's criteria are implemented and certified (ADR-MC-001 ratified 2026-08-05; see ADR-MC-001).

## 9. Transport Neutrality

Transport neutrality is preserved. No transport technology (e.g., WebSocket, SSE, polling mechanism) was selected or coupled into this phase. The projection is consumed over standard HTTP GET requests. Any future transport selection is deferred to a later ADR.

## 10. ADR-002 Conformance

This architecture conforms to ADR-002:

- Brain retains full mutation authority over intent, dispatch, and cancellation.
- Mission Control is a read-only projection.
- No new mutation routes introduced.
- No persistence migrations added.
- Sigma gate remains BLOCKED.
- Cancellation controls DISABLED.
- Transport neutrality preserved.