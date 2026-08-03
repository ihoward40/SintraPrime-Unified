# Professional Review

Phase 2A implements a formal professional-review workflow. It does not verify professional credentials automatically and it does not create any real legal approval for New Jersey.

## Roles

Supported reviewer roles:

- `LEGAL_RESEARCHER`
- `LICENSED_ATTORNEY`
- `CPA`
- `SECURITY_REVIEWER`
- `PRIVACY_REVIEWER`
- `PLATFORM_ADMIN`

Only `LICENSED_ATTORNEY` may approve legal rules for production eligibility. Only `CPA` may approve accounting-rule review status.

## Statuses

Review statuses:

- `NOT_SUBMITTED`
- `SUBMITTED`
- `IN_REVIEW`
- `CHANGES_REQUESTED`
- `APPROVED_WITH_CONDITIONS`
- `APPROVED`
- `REJECTED`
- `WITHDRAWN`
- `SUPERSEDED`

## Required Fields

Review records capture object type, object ID, jurisdiction, domain, reviewer role, reviewer identity, declared credentials, credential verification status, findings, conditions, reviewed authorities, rejected authorities, approval scope, effective date, expiration date, digital signature/authenticated approval event, reviewed timestamp, and immutable audit event ID.

## Production Eligibility

A rule may become `PRODUCTION_ELIGIBLE` only if all gates pass:

- cited controlling authorities are primary-source verified;
- effective dates are known and current;
- conflicts are resolved or disclosed;
- tests pass;
- no unresolved critical deficiency affects the rule;
- a licensed-attorney review is approved;
- approval conditions are satisfied;
- approval has not expired;
- no cited authority has been superseded;
- no open professional challenge remains;
- no source hash change or stale-source invalidation remains pending.

No administrator override silently bypasses this logic. Override behavior would need an explicit reason, immutable audit event, visible marking, and would still prevent ordinary production representation.

## Endpoints

Read endpoints expose review state and queues. Write endpoints require reviewer role and identity headers:

```text
X-Reviewer-Role
X-Reviewer-Identity
```

Phase 2A does not claim these headers verify credentials; they are a repository-local authorization gate until a real identity and credential verification system is connected.
