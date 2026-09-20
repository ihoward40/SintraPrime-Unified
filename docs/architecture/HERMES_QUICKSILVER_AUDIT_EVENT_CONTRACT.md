# Hermes Quicksilver — Adapter Boundary Audit Event Contract

## Destination

The redacted delegation audit event is intended for:

- `agents/nova/execution_ledger.py` (`ExecutionLedger`) for operational Nova audit trail.
- `blackstone/bra/cel.py` (`ConstitutionalEvidenceLedger`) for long-term evidence custody if the event has legal/evidentiary value.

The adapter does not choose the destination; the caller passes the destination ledger or a ledger identifier.

## Event schema

| Field | Type | Required | Description |
| ----- | ---- | :------: | ----------- |
| `event_type` | `str` | yes | `"hermes_delegation_attempt"` |
| `event_version` | `str` | yes | `"1.0.0"` |
| `occurred_at` | `datetime` (ISO 8601 UTC) | yes | Timestamp of the attempt |
| `tenant_id` | `str` (UUID) | yes | SintraPrime tenant identifier |
| `actor_id` | `str` (UUID) | yes | SintraPrime user identifier who initiated the request |
| `case_id` | `str \| None` | no | Associated case, if available |
| `correlation_id` | `str` | yes | End-to-end request correlation identifier |
| `session_id` | `str \| None` | no | Portal session identifier |
| `specialist_id` | `str` | yes | SintraPrime specialist identifier |
| `hermes_profile_id` | `str` | yes | Resolved Hermes profile identifier |
| `operation` | `str` | yes | Read-only operation intended (e.g., `"profile_discovery"`) |
| `decision` | `enum` | yes | `"allow"`, `"deny"`, `"pending"`, `"timeout"`, `"error"` |
| `policy_reason_code` | `str \| None` | yes if `decision != allow` | Machine-readable reason: `feature_disabled`, `unknown_specialist`, `missing_mapping`, `tenant_mismatch`, `hard_deny`, `unsupported_version`, `hermes_unavailable`, `approval_required`, `approval_expired`, `audit_failure` |
| `approval_reference` | `str \| None` | no | Reference to SintraPrime `ApprovalRequest.request_id` if applicable |
| `result_status` | `str \| None` | no | Normalized outcome if a read-only Hermes operation was attempted |
| `error_class` | `str \| None` | no | Exception class name on error, never a traceback or message containing secrets |
| `duration_ms` | `int` | yes | Time from request start to final decision |
| `source_version` | `str` | yes | Installed Hermes source version (`0.18.2`) or runtime CLI version (`v0.15.2`) observed |
| `redaction_version` | `str` | yes | Version of redaction rules applied |

## Explicitly prohibited fields

The following must never appear in the audit payload:

- API keys
- Tokens
- Authorization headers
- Raw prompts containing secrets
- Chain-of-thought
- Private model reasoning
- Unredacted environment values
- Full `config.yaml` content
- Credential-store paths
- Hermes `.env` contents
- Passwords, MFA secrets, backup codes
- Attorney-client privileged material

## Redaction responsibility

1. **Hermes layer**: `agent/redact.py` redacts dangerous command prompts and approval payloads inside Hermes.
2. **SintraPrime adapter layer**: constructs a new envelope containing only the allowed fields above; never forwards raw Hermes outputs verbatim.
3. **SintraPrime ledger layer**: verifies the envelope contains no prohibited fields before appending.

## Append-only rule

Events written to `ExecutionLedger` are appended to a hash-chained JSONL file. Events written to `ConstitutionalEvidenceLedger` become `EvidenceItemRecord` instances with chain-of-custody entries. In both cases, the event is immutable once appended. Corrections are appended as follow-up events.
