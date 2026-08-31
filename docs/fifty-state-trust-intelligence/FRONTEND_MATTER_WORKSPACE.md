# Frontend Matter Workspace

The Phase 2C-4 matter workspace is available at `/matters/:matterId` and consumes the persistent matter intelligence APIs established in Phase 2C-2 and the deadline/evidence APIs established in Phase 2C-3.

## Workspace views

- Matter dashboard with tenant-scoped party, account, deadline, finding, and review metrics.
- Party and account summaries using redacted identifiers.
- Deadline calendar showing calculation status, version, timezone, and due date.
- Chronology combining communications, deadlines, and immutable audit events.
- Evidence graph showing redacted nodes and typed relationships.
- Contradiction and missing-evidence queue.
- Assessment history with version and professional-review posture.
- Immutable audit history and provenance posture.

The workspace displays: `Educational and issue-spotting output only. This system does not provide a legal opinion or replace review by a licensed attorney.`

## Security behavior

The frontend does not grant review authority. It presents attorney review posture based on authenticated state while the API remains the authorization source. API failures are surfaced as errors and empty states; the UI does not synthesize matter records. Evidence statements and identifiers use the redacted fields returned by the protected API.

## Validation

`npm run type-check`, `npm run lint`, and `npm run build` pass. Direct Playwright smoke coverage passed at desktop and mobile widths, including no horizontal overflow. The existing Playwright test runner could not be executed because this checkout does not install `@playwright/test`; that is recorded as an environment limitation and is not concealed by changing the test suite.

Export packet generation, additional jurisdictions, and matter-workspace write actions remain deferred.