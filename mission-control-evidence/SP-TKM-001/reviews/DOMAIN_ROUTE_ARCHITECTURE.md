# Domain and Route Architecture — Consumer Evidence Landing Page

Mission: SP-TKM-001
Owner: Revenue Architect + Hermes
Status: Phase Three internal review — no public deployment

## Intended Public URL

```text
https://ops.ikesolutions.org/consumer-evidence
```

## Internal Route

```text
GET /consumer-evidence
POST /api/v1/consumer-evidence/interest
POST /api/v1/consumer-evidence/event
```

## Phase Three Status

- The route is implemented in `portal/routers/sp_tkm_001.py`.
- Registration is guarded by `settings.SP_TKM_001_PREVIEW_ENABLED` (default `false`).
- No public deployment has occurred.
- No DNS or reverse-proxy changes have been made for `ops.ikesolutions.org`.
- Public URL status: **TECHNICALLY RECOMMENDED — OWNER CONFIRMATION PENDING**.

## Hosting and Architecture Dependencies

| Component | Dependency | Status |
|---|---|---|
| SintraPrime portal | FastAPI application | Existing |
| Database | PostgreSQL for lead records | Not yet wired |
| Redis | Rate limiting and session store | Existing |
| DNS | `ops.ikesolutions.org` A/AAAA or CNAME record | Not configured |
| Reverse proxy | Cloudflare, Nginx, or equivalent | Not configured |
| TLS certificate | Required for public HTTPS | Not configured |
| Email service | Required for Starter Sheet delivery | Not wired |
| Authentication | Public landing page = no auth required; admin endpoints remain auth-gated | Confirmed |

## Public, Authenticated, or Staged?

**Phase Three decision:** Keep the route internal or feature-flagged. Do not deploy publicly.

### Recommended eventual architecture

- **Public:** `GET /consumer-evidence` — marketing page, no authentication.
- **Authenticated (existing portal):** Admin or owner dashboard for lead management remains behind existing JWT/session auth.
- **Staged:** Use a deployment branch or preview environment before production release.

## Isolation Requirements

- The landing page must not expose unrelated SintraPrime portal content.
- The static HTML must not contain admin links, client data, or internal routes.
- The lead-capture endpoint must be rate-limited and must not accept sensitive documents.
- The feature flag must remain `false` in production until deployment approval.

## DNS and Reverse-Proxy Notes

If `ops.ikesolutions.org` is intended to point to the SintraPrime portal:

1. Create DNS record for `ops.ikesolutions.org` pointing to the portal origin.
2. Configure reverse proxy to route `ops.ikesolutions.org/consumer-evidence` to the portal application.
3. Ensure TLS terminates with a valid certificate.
4. Confirm the route does not conflict with existing portal paths.
5. Set `SP_TKM_001_PREVIEW_ENABLED=true` only in the target environment after approval.

## Security Checklist Before Public Deployment

- [ ] Feature flag enabled only in intended environment.
- [ ] Rate limiting applied to lead-capture and event endpoints.
- [ ] No sensitive data fields exposed in HTML or API.
- [ ] UTM parameters sanitized before storage.
- [ ] Email verification implemented before Starter Sheet delivery.
- [ ] Privacy policy and terms pages linked.
- [ ] CSP headers reviewed.
- [ ] Automated tests pass.
- [ ] Owner approval issued.

## Current Decision

Keep internal. No production DNS, reverse-proxy, or TLS changes during Phase Three.

Domain status: **TECHNICALLY RECOMMENDED — OWNER CONFIRMATION PENDING**.