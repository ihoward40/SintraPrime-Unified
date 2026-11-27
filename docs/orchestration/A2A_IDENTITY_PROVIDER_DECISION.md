# A2A Identity Provider Decision

## Decision: Option C for production design; Option A only for private development

The current implementation uses `A2A_AGENT_CREDENTIALS`, a static runtime-injected token map. This is appropriate for local/private development validation, but it is not sufficient as a production identity authority.

The recommended production direction is **Option C: internal signed service tokens with rotation and tenant binding**, provided by a secret manager or internal identity service. The token claims must bind:

- `agent_id`
- `tenant_id`
- issuer
- audience
- issued-at and expiry
- token ID for replay tracking
- key ID for rotation

The A2A boundary must verify signature, issuer, audience, expiry, tenant scope, and registry status before dispatch. Key rotation and revocation must be tested before production enablement.

## Current validation result

| Probe | Result |
|---|---:|
| Runtime token map loads | PASS |
| Unknown token rejected | PASS |
| Wrong tenant rejected | PASS |
| Sender/body mismatch rejected | PASS |
| Blocked Dispatch Desk rejected | PASS |
| Production identity-provider integration | NOT IMPLEMENTED |

## Safe boundary

Until Option C is implemented and tested:

- Keep `A2A_AGENT_CREDENTIALS` limited to local/private environments.
- Do not treat static tokens as production identity proof.
- Keep Dispatch Desk blocked.
- Keep all `can_send_external` values false.
- Do not enable external executor side effects.

## Required production acceptance tests

1. Valid signed service token is accepted.
2. Unknown key ID is rejected.
3. Invalid signature is rejected.
4. Expired token is rejected.
5. Wrong issuer/audience is rejected.
6. Tenant crossing is rejected.
7. Revoked token ID is rejected.
8. Rotated signing keys remain verifiable during overlap.
9. Failed identity attempts are audit-linked without leaking token material.
10. Registry status is checked after token validation.
