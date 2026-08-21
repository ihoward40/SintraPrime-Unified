# SP-IKE-004 — Restricted External Adapter Gate

**Status:** CLOSED — DESIGN / INVENTORY ONLY  
**Activation authority:** Principal-controlled, separately certified gate required  
**Depends on:** Gate 2 durable authority = CLOSED/CERTIFIED; Gate 3 canonical scheduler = CLOSED/CERTIFIED  
**Production external side effects:** NOT AUTHORIZED

## 1. Purpose

This gate defines the minimum authority, evidence, isolation, and certification contract required before SintraPrime may permit any governed worker, IKE-Bot adapter, Hermes worker, scheduled mission, or Mission Control path to cause a consequential effect in an external system.

Gate 3 authorizes durable scheduling and bounded internal orchestration only. It does **not** authorize outbound execution.

The restricted external-adapter gate therefore begins closed and fail-safe. Its first certification target must be disposable/non-production and must prove the governance envelope before any production credential or destination is admitted.

## 2. Existing consequential surfaces discovered in the repository

The current repository already contains code capable of, or intended for, communication with external systems. These surfaces are inventory inputs only; their existence does not confer authority.

### Communication
- `apps/sintraprime/src/connectors/emailConnector.ts`
  - Gmail authentication/read paths
  - Gmail `messages/send` outbound write path
  - SMTP configuration path; SMTP sending remains placeholder

### Cloud/document mutation
- `apps/sintraprime/src/connectors/googleDriveConnector.ts`
- `legal_integrations/dms_connectors.py`

### Commerce/advertising/platform mutation
- `apps/sintraprime/src/connectors/shopifyConnector.ts`
- `apps/sintraprime/src/connectors/metaAdsConnector.ts`
- `apps/sintraprime/src/connectors/platforms/tiktokAdapter.ts`
- `apps/sintraprime/src/connectors/platforms/discordAdapter.ts`
- additional platform adapters under `apps/sintraprime/src/connectors/platforms/`

### Legal submission
- `legal_integrations/court_efiling.py`
  - connector interfaces include document filing/submission operations
  - filing may carry legal consequences and fees

### Financial-data systems
- `legal_integrations/financial_connectors.py`
  - Plaid, Yodlee, Finicity, EDGAR, Bloomberg Law, and bankruptcy/PACER-related integrations
  - current inspected Plaid methods are primarily data retrieval/report operations, but all credentialed external access remains governed input to this gate

No listed surface is activated by this document.

## 3. Non-negotiable gate invariants

An external action MUST fail closed unless every invariant below is satisfied.

1. **Named adapter allowlist**
   - exact adapter identifier
   - exact operation identifier
   - explicit risk class
   - explicit environment (`sandbox`, `test`, or later separately approved `production`)

2. **Resource/destination allowlist**
   - exact recipient, account, tenant, repository, court sandbox, test mailbox, test store, test drive/folder, or equivalent resource boundary
   - wildcard destinations forbidden for consequential writes

3. **Durable service identity / capability lease**
   - tenant bound
   - Principal-created or Principal-approved
   - explicit adapter + operation capability
   - expiration required
   - revocable before execution
   - credentials referenced indirectly; secrets never copied into mission/evidence payloads

4. **Exact Principal approval binding**
   - adapter
   - operation
   - destination/resource
   - canonical payload hash
   - human-readable diff/summary
   - risk class
   - expected observable effect
   - estimated monetary/legal impact where applicable
   - expiry timestamp
   - one-time approval nonce/idempotency key

5. **Payload immutability after approval**
   - any material mutation invalidates approval
   - stale approval cannot execute
   - adapter must compare the execution payload hash with the approved payload hash immediately before side effect

6. **Idempotency / replay protection**
   - one durable execution intent per idempotency key
   - repeated calls return the existing outcome or fail safely
   - retries cannot produce duplicate outbound effects

7. **Pre-execution simulation**
   - generate the exact proposed request without sending it
   - validate destination, content, permissions, cost/fee estimates, and policy
   - produce a preflight receipt

8. **Atomic durable evidence**
   - durable intent before outbound call
   - approval reference before outbound call
   - attempt receipt
   - provider response/confirmation hash
   - final outcome receipt
   - correlation and causation IDs
   - tamper-evident/hash-chained evidence

9. **Destination and credential separation**
   - credentials cannot choose or widen destination scope
   - mission payload cannot substitute credentials
   - adapter implementation cannot silently fall back to a second provider/destination

10. **Timeout, retry, and ambiguity policy**
    - bounded retries
    - retry only when provider semantics make duplicate effects impossible or idempotency is provider-backed
    - ambiguous timeout after possible submission becomes `UNKNOWN_REQUIRES_RECONCILIATION`, not automatic retry

11. **Compensation / rollback declaration**
    - every adapter action classified as reversible, compensatable, or irreversible
    - rollback/compensation workflow documented where technically possible
    - irreversible actions receive the highest approval tier

12. **Kill switch and revocation check**
    - global external-execution kill switch
    - tenant kill switch
    - adapter kill switch
    - service identity revocation rechecked immediately before execution

13. **No scheduler bypass**
    - a scheduled mission carries no independent external authority
    - when its time arrives it must reacquire/validate the external action lease and exact approval at execution time
    - expired/revoked authority causes a blocked outcome, not execution

14. **No Mission Control bypass**
    - command ingestion cannot directly call an external adapter outside this gate
    - workers cannot self-authorize by generating their own approval artifacts

## 4. Risk classes

### E0 — Read-only external observation
Examples: read/list/query a sandbox or explicitly allowed data source.

Required controls:
- durable identity
- tenant/resource allowlist
- credential reference
- audit receipt
- rate limits

E0 is still not automatically activated by this design document.

### E1 — Reversible sandbox write
Examples: create a draft/test object in a disposable account that can be deleted without consequence.

Required controls:
- all E0 controls
- exact Principal approval or purpose-built certification authority
- canonical payload hash
- preflight + postflight receipts
- idempotency
- compensation/delete path

**E1 is the first eligible certification target.**

### E2 — Consequential but reversible production write
Examples: create/update an external production object that has business effect but can be reliably reversed.

Requires a later explicit production activation decision after E1 certification. Not authorized here.

### E3 — Irreversible/high-consequence external action
Examples:
- send an external email/message
- publish content publicly
- submit a court/legal filing
- initiate or authorize payment/financial transfer
- destructive account/file mutation
- production computer/browser action with material consequence

E3 remains CLOSED until separately designed, reviewed, and explicitly authorized after lower-risk certification.

## 5. Proposed canonical execution envelope

Every external execution candidate should be represented as a durable immutable intent similar to:

```text
ExternalActionIntent
  intent_id
  tenant_id
  principal_id
  service_identity_id
  mission_id
  schedule_id?                # provenance only; never authority
  adapter_id
  operation_id
  environment
  destination/resource
  risk_class
  canonical_payload_hash
  payload_summary
  approval_id
  approval_payload_hash
  approval_expires_at
  idempotency_key
  credential_ref
  status
  preflight_receipt_hash
  provider_request_hash
  provider_response_hash
  created_at / updated_at
```

Required states:

```text
DRAFT
→ PREFLIGHTED
→ APPROVAL_REQUIRED
→ APPROVED
→ CLAIMED
→ EXECUTING
→ SUCCEEDED | FAILED | UNKNOWN_REQUIRES_RECONCILIATION | CANCELLED | BLOCKED
```

No transition may skip `PREFLIGHTED` and `APPROVED` for E1+ writes.

## 6. Adapter contract

A restricted adapter must expose distinct phases. A single generic `call(method, args)` surface is insufficient for consequential execution.

```text
describe_capability()
validate_destination()
preflight()
canonicalize_payload()
execute_once()
reconcile_unknown_outcome()
compensate()               # when supported
```

The governance layer owns approval, identity, persistence, scheduling, idempotency, evidence, and state transitions. The adapter owns only protocol-specific translation and provider interaction.

Adapters MUST NOT:
- mint approval
- widen scopes
- select credentials outside the approved credential reference
- select an unapproved destination
- silently alter payload content after preflight
- retry ambiguous irreversible writes autonomously
- suppress provider confirmation/error evidence

## 7. First certification target

The first executable certification should use a **disposable synthetic E1 adapter**, not Gmail, court e-filing, payments, social publishing, or another real production service.

Recommended target: `sandbox.echo-write-v1`

Behavior:
- accepts one structured payload
- writes only to an isolated temporary/test destination controlled by the test harness
- returns deterministic provider-style confirmation
- supports lookup/reconciliation by idempotency key
- supports deletion/compensation
- has no path to production credentials or production destinations

Certification must prove:
1. unapproved action is blocked
2. expired approval is blocked
3. revoked identity is blocked
4. changed payload after approval is blocked
5. changed destination after approval is blocked
6. duplicate execution produces one external sandbox effect
7. scheduler dispatch does not bypass approval
8. restart between approval and execution preserves authority state
9. restart after ambiguous provider response reconciles before retry
10. kill switch blocks execution
11. compensation is logged and hash-linked
12. complete preflight/attempt/result evidence chain survives restart
13. cross-tenant access/execution fails closed
14. no production hostname/credential/destination is reachable from the certification adapter

## 8. Activation ladder

```text
Gate 2 Durable Authority                CLOSED / CERTIFIED
        ↓
Gate 3 Canonical Scheduler              CLOSED / CERTIFIED
        ↓
Gate 4A Restricted Adapter Contract     CLOSED / DESIGN COMPLETE WHEN REVIEWED
        ↓
Gate 4B Disposable E1 Sandbox           NOT STARTED
        ↓
Gate 4C Independent replay/red-team     NOT STARTED
        ↓
Gate 4D Selected production adapter     NOT AUTHORIZED
        ↓
E3 high-consequence adapters            NOT AUTHORIZED
```

Passing a lower stage does not automatically authorize the next stage.

## 9. Explicit exclusions from current authority

This design does not authorize:
- real Gmail sending
- SMTP sending
- real Google Drive mutation
- Shopify production mutation
- Meta Ads changes
- TikTok/Discord/social publishing
- court e-filing
- PACER/ECF submission
- payments/transfers
- destructive production file/account actions
- unrestricted browser/computer use
- generic connector writes

## 10. Gate 4A exit criteria

Gate 4A may be considered design-complete only when:
- the adapter registry schema is defined
- durable external-intent/evidence schema is defined
- approval-binding contract is defined
- capability-lease contract is defined
- reconciliation and ambiguity semantics are defined
- sandbox isolation requirements are defined
- E1 disposable adapter test plan is accepted
- existing consequential connectors are explicitly denied by default
- no code path can interpret Gate 4A documentation as execution authorization

Until a later gate is explicitly authorized and certified, external execution remains fail-closed.
