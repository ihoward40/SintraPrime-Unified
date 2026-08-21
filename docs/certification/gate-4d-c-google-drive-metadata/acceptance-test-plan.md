# Gate 4D-C acceptance and negative test plan

No case in this plan may connect an account or call Google until separately authorized. Offline stages use fakes and synthetic tokens with unmistakably non-secret values.

## C1 static authority

| ID | Test | Expected |
|---|---|---|
| AU-01 | Adapter ID, gate ID, E0 risk, environment, canonical authority exact | PASS |
| AU-02 | OAuth scope set differs by missing or additional scope | BLOCK |
| AU-03 | Operation outside `files.list/files.get` | BLOCK |
| AU-04 | HTTP method outside GET | BLOCK |
| AU-05 | Design authority presented as implementation/connection authority | BLOCK |
| AU-06 | Gate 4D-B authority reused for Drive | BLOCK |

## C2 identity/account

| ID | Test | Expected |
|---|---|---|
| ID-01 | Approved account digest, issuer, client, subject, exact scope | PASS |
| ID-02 | Silent/default/ambient account selection | BLOCK |
| ID-03 | Account digest or token subject differs | BLOCK |
| ID-04 | Additional granted OAuth scope | BLOCK |
| ID-05 | Expired/revoked token or credential lease | BLOCK |
| ID-06 | State, nonce, PKCE, or redirect mismatch | BLOCK |
| ID-07 | Account switching after approval | BLOCK |
| ID-08 | Token/code/secret appears in logs, errors, prompts, evidence | FAIL CERTIFICATION |
| ID-09 | Refresh rotation and revocation crash windows | RECONCILE, NO LEAK |

## C3 network and request

| ID | Test | Expected |
|---|---|---|
| NET-01 | Exact HTTPS Drive files endpoint | PASS |
| NET-02 | Other Google/non-Google host, suffix trick, userinfo, IDNA confusion | BLOCK |
| NET-03 | HTTP, alternate port, proxy route, invalid TLS | BLOCK |
| NET-04 | Any redirect, including same-host | BLOCK |
| NET-05 | DNS rebinding/private/link-local/loopback destination | BLOCK |
| NET-06 | Path traversal, encoded slash, unexpected API version | BLOCK |
| NET-07 | Query duplicate/unknown key | BLOCK |
| NET-08 | Caller-controlled fields mask | BLOCK |
| NET-09 | Unbound pagination token or query change across pages | BLOCK |
| NET-10 | Page/byte/time limits exceeded | INCOMPLETE/THROTTLED |

## C4 prohibited capability

Each test must prove rejection before provider I/O and confirm zero provider attempt where possible.

| ID | Capability | Expected |
|---|---|---|
| NEG-01 | `alt=media`, download, abuse acknowledgement | BLOCK |
| NEG-02 | `files.export` | BLOCK |
| NEG-03 | Docs/Sheets/Slides content API | BLOCK |
| NEG-04 | upload/create/copy | BLOCK |
| NEG-05 | update/move/rename/trash/delete | BLOCK |
| NEG-06 | permission/share mutation | BLOCK |
| NEG-07 | comments/revisions mutation | BLOCK |
| NEG-08 | private organizational/domain-wide delegation expansion | BLOCK |
| NEG-09 | response contains content-bearing or unknown fields | INVALID RESPONSE; NO FORWARDING |
| NEG-10 | content link followed by downstream component | BLOCK |

## C5 governance

| ID | Test | Expected |
|---|---|---|
| GOV-01 | Missing/expired Principal approval | BLOCK |
| GOV-02 | Missing/wrong durable service identity | BLOCK |
| GOV-03 | Global/adapter/account/operation kill switch | BLOCK |
| GOV-04 | Rate bucket exhausted | THROTTLE |
| GOV-05 | Concurrent same idempotency key | ONE PROVIDER ATTEMPT |
| GOV-06 | Terminal replay | RETURN SEALED PRIOR RESULT |
| GOV-07 | Crash before/after attempt and before/after evidence | DETERMINISTIC RECONCILIATION |
| GOV-08 | Timeout with ambiguous provider state | INCOMPLETE; NO BLIND RETRY |
| GOV-09 | Adapter tries to mint approval/select account | BLOCK |

## C6 evidence

| ID | Test | Expected |
|---|---|---|
| EV-01 | Valid hash chain and externally bound record hash | PASS |
| EV-02 | Modify/delete/reorder a record | DETECT |
| EV-03 | Rewrite record and self-declared hash | DETECT |
| EV-04 | Authorization/token/code/client secret inserted | SECRET SCAN FAIL |
| EV-05 | Raw account email/subject inserted | PRIVACY SCAN FAIL |
| EV-06 | `content_bytes_captured` nonzero | FAIL CERTIFICATION |
| EV-07 | Missing request, result, provider attempt, account digest, or approval identity | INCOMPLETE |
| EV-08 | Response metadata field outside allowlist | FAIL CLOSED |

## C7/C8 integration and freeze

- All tests above pass on one exact head.
- Full CI/Sigma/IssueVerifier and certification workflows are terminal-success.
- Recompute contract, schema, test-plan, and evidence hashes.
- Reconfirm Gate 4D-B commit and authority files unchanged.
- Record no token/account secret in repository or CI artifacts.
- Freeze exact head and stop without contents-read, write, merge, or deployment authority.

## Mechanical decision

- Any usable security/authority blocker → `FAIL`.
- Missing required test/evidence → `INCOMPLETE`.
- All required domains pass on one exact head → `PASS` for the exact metadata-only boundary only.
