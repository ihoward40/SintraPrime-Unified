# Gate 4D-C certification ladder

Every stage requires separate Principal authorization. Passing one stage does not authorize the next.

## C1 — Static authority proof

- Exact adapter, gate, risk, scope, operations, methods, destinations, fields, and denylist.
- Static checks show no content/write/export/download/permission API path.
- Canonical authority remains the sole approval and lifecycle owner.

**Exit:** contract hash frozen; zero unresolved blockers.

## C2 — Identity and account binding

- Dedicated certification account only.
- Exact issuer/client/subject/account digest and scope binding.
- PKCE/state/nonce/redirect checks.
- No ambient credential or silent switch.
- Secret redaction and revocation tests.

**Exit:** account binding independently verified; tokens absent from evidence.

## C3 — Network and API pinning

- Exact HTTPS host/path/method.
- DNS, TLS, proxy, redirect, userinfo, IDNA, alternate-port, and rebinding adversarial tests.
- Query/fields construction is structural and fail-closed.

**Exit:** only approved Drive metadata endpoints reachable.

## C4 — Negative capability tests

Prove blocking of content, media download, export, Docs/Sheets/Slides body access, upload, create, copy, update, move, rename, delete, trash, permissions, comments, revisions, arbitrary accounts, extra OAuth scopes, and arbitrary Google APIs.

**Exit:** every prohibited capability blocked before provider I/O where mechanically possible.

## C5 — Governance lifecycle

- Principal approval and governed service identity.
- Per-account and global rate limits.
- Kill switches at global/adapter/account/operation levels.
- Durable in-flight duplicate suppression and terminal replay.
- Timeout ambiguity reconciliation; no blind retry.
- Credential lease expiry and revocation.

**Exit:** crash/replay/timeouts preserve at-most-one governed attempt semantics.

## C6 — Evidence integrity

- Append-only hash-chain records.
- Request/result identity and provider attempt lifecycle.
- Metadata-field inventory and zero content-byte assertion.
- Secret scan and redaction.
- Tamper, deletion, reordering, and self-rewrite detection.

**Exit:** evidence independently verifies and contains zero secret material.

## C7 — Exact-head CI

Required terminal workflows on one immutable head:

- static authority/schema checks;
- unit and negative-capability tests;
- identity/account certification;
- network-boundary certification;
- governance/replay certification;
- evidence-integrity certification;
- full SintraPrime CI, Sigma, and IssueVerifier.

**Exit:** all required workflows terminal `SUCCESS`; no later commit inherits certification.

## C8 — Freeze and stop

- Record exact commit/tree, workflow run IDs, contract/design/evidence hashes, account-binding digest, and residual blockers.
- Verify Gate 4D-B exact-head boundary unchanged.
- Keep PR draft/unmerged unless separately authorized.
- Stop. Metadata certification does not authorize contents-read, writes, broader accounts, merge, release, or deployment.
