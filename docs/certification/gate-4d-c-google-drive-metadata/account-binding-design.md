# Account-binding design

## Principle

Authentication proves access to an account; it does not create connector authority. A Principal must approve one account binding before any OAuth execution, and a later implementation must bind every token lease and request to that immutable approval.

## Proposed lifecycle

1. **Design approval** — approves this package only.
2. **Implementation approval** — permits code and offline tests, not OAuth.
3. **Connection approval** — names the intended Google account through a privacy-preserving account-binding digest and exact scope.
4. **Interactive OAuth** — only after connection approval; PKCE, state, nonce, exact redirect URI, and explicit Google account selection required.
5. **Token validation** — validate issuer, audience/client, expiry, granted scopes, subject/account, and approved binding digest.
6. **Vault storage** — refresh token stored only in the approved secret store; records contain a credential reference and digest, never the token.
7. **Credential lease** — canonical authority issues a short-lived, single-operation lease after approval, identity, scope, kill-switch, and rate checks.
8. **Execution** — adapter receives the lease at I/O time; no token reaches model prompts, transcripts, request evidence, or exception text.
9. **Revocation/disconnection** — Principal can revoke the account binding; local secret deletion and Google revocation are reconciled and evidenced.

## Binding record

A future durable record must bind:

- gate and adapter IDs;
- Principal approval ID;
- governed service identity ID;
- Google issuer and OAuth client ID digest;
- Google subject/account digest (HMAC or keyed digest, not raw email);
- exact granted scope set;
- consent timestamp and credential reference;
- status: `PENDING | ACTIVE | SUSPENDED | REVOKED`;
- previous-record hash and record hash.

## Fail-closed rules

- No ambient ADC, browser session, cached CLI credential, or environment token.
- No default account and no first-account selection.
- Any mismatch in subject, client, issuer, scope, redirect URI, or binding digest blocks use.
- A token with additional scopes is rejected, even if it includes the approved scope.
- Refresh-token rotation is atomic and never logged.
- Account replacement requires a new Principal approval and binding record.
- One approval cannot cover multiple Google accounts.

## Redaction

Forbidden in logs/evidence: access token, refresh token, authorization code, PKCE verifier, client secret, raw email, raw subject ID, cookies, `Authorization` header. Allowed: keyed account digest, credential-reference ID, scope strings, token expiry, provider request ID, and redacted header names.

## Test identities

Certification must use a dedicated non-production Drive account and synthetic metadata-only corpus. Private production accounts and broad organizational delegation are prohibited.
