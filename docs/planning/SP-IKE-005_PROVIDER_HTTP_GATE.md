# SP-IKE-005 — Gate 4C Provider-Owned HTTP Boundary

**Status:** OPEN — IMPLEMENTATION / CERTIFICATION IN PROGRESS  
**Target:** `provider.postman-echo-v1`  
**Provider:** Postman Echo  
**Environment:** provider-owned non-production HTTP test surface  
**Risk class:** E1  
**Production connector authority:** CLOSED

## Purpose

Gate 4C proves that the Gate 4B durable external-action authority envelope can cross a real HTTPS/provider boundary without granting meaningful real-world authority. Postman Echo is used only as a provider-owned request/response test surface. It is not a user production account and does not authorize later live connectors.

## Exact network allowlist

- scheme: `https`
- hostname: `postman-echo.com`
- port: `443`
- path: `/post`
- query string: forbidden
- URL credentials: forbidden
- redirects: never followed
- alternate hosts/subdomains: forbidden unless separately added by a later gate

## Redirect escape prevention — mandatory certification

A destination allowlist is insufficient if the HTTP client automatically follows redirects. Gate 4C therefore requires:

1. outbound requests use `allow_redirects=False` (or equivalent)
2. every `30x` response becomes a blocked provider outcome
3. `Location` is captured only as evidence and is never followed
4. request body, Authorization header, cookies, credential material, or other sensitive headers may never be replayed to the redirect target
5. same-host redirects are also blocked at this gate; no redirect class is implicitly trusted
6. a certification test must prove that a redirect to an attacker-controlled hostname results in exactly one request to the approved Postman host and zero requests to the redirect host

## DNS / host pinning — mandatory certification

Initial hostname string validation alone does not prevent DNS rebinding or resolver drift. Gate 4C therefore requires:

1. resolve only the exact approved hostname
2. reject loopback, link-local, private, multicast, unspecified, reserved/non-global addresses
3. capture the approved resolved IP set immediately before the provider request
4. inject that exact set into the HTTP transport resolver
5. disable independent DNS cache/re-resolution inside the transport for the request
6. preserve TLS hostname verification for `postman-echo.com` while the socket connects only to a pinned approved address
7. reject any resolver request for a second hostname
8. persist/hash the resolved IP set in provider evidence for the certification execution

Explicit tests must prove both host escape rejection and that the actual connector receives only the preapproved IP set.

## Gate 4C remaining certification matrix

Gate 4C is not closed until exact-head evidence proves:

- credential lease creation, expiry, revocation, tenant binding, and secret-reference-only persistence
- exact destination allowlist
- exact Principal approval binding
- payload mutation rejection
- destination mutation rejection
- service identity revocation
- scheduler/Mission Control non-bypass
- provider idempotency / local duplicate suppression
- timeout ambiguity transitions to reconciliation rather than blind retry
- restart/replay reconciliation
- local rate limiting and provider `429` handling
- global, tenant, and adapter kill switches
- cross-tenant denial
- redirect escape prevention
- DNS/public-address validation
- pinned resolver transport enforcement
- durable provider request/response hashes
- evidence-chain verification after restart
- logical compensation with `provider_rollback_required=false` for Echo because no durable provider object exists to delete
- all Gate 2, Gate 3, and Gate 4B certification workflows remain green

## Gate 4D separation rule

Gate 4D is **not an automatic continuation** of Gate 4C.

Only after Gate 4C is exact-head, terminal-green may the project perform a **read-only inventory** of candidates for one live-but-low-risk connector. Candidate selection requires a separate Principal authorization decision. A green Gate 4C does not authorize implementation, credentials, account connection, test writes, or production activation for Gate 4D.

Until that separate decision:

```text
GATE_4C = OPEN / CERTIFICATION IN PROGRESS
GATE_4D_CANDIDATE_INVENTORY = BLOCKED UNTIL GATE_4C GREEN
GATE_4D_SELECTION = REQUIRES SEPARATE PRINCIPAL AUTHORIZATION
GMAIL = CLOSED
GOOGLE_DRIVE_WRITES = CLOSED
COURT_EFILING = CLOSED
PAYMENTS = CLOSED
SOCIAL_PUBLISHING = CLOSED
PRODUCTION_BROWSER_CONTROL = CLOSED
REAL_ACCOUNT_WRITES = CLOSED
```
