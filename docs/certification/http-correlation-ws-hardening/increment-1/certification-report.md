# HTTP Correlation Middleware and WebSocket Transport Hardening Certification — Increment 1

Repository: `ihoward40/SintraPrime-Unified`
Branch: `cert/http-correlation-ws-hardening-increment-1`
Baseline: `ee240ddcac201ab8d1a1613311008c49b4448fb6`
Implementation commit: `9bc2e0c04f77d7a961e3e4b7b68a5e28a36339aa`

Conclusion: CERTIFIED FOR THE RECORDED SCOPE

## Summary
- HTTP correlation middleware validates inbound X-Request-ID, generates secure IDs, binds CorrelationContext, and returns X-Request-ID on all supported response paths.
- ContextVar tokens are reset LIFO; request-state token stacks are independent per request.
- Trusted actor and tenant claims are bound through the real HTTP dependency (get_current_user with Request injection).
- WebSocket capacity controls (global, per-actor, per-tenant, per-address) are process-local and enforced.
- Capacity cleanup covers accept-failure, send-failure, cancellation, idle-timeout, max-lifetime, and normal-disconnect paths.
- WebSocket rate control is fixed-interval (burst_limit was removed).
- WebSocket payload-size enforcement prevents oversized sends; oversized inbound frames close with code 4413.
- WebSocket idle timeout tracks client activity (not server sends); max connection lifetime is independent.
- WebSocket receiver, sender, and closer ownership is exclusive (receiver=sole receive owner, sender=sole send_text owner, closer=sole close owner).
- Heartbeat protocol accepts ping and sends pong.
- Outcome enums are required and exercised on real endpoint paths (authorization denial, capacity denial, idle timeout, max lifetime, oversized payload).
- Authentication-failure throttling prevents brute-force WS auth.
- Trusted-proxy boundary: X-Forwarded-For ignored unless from configured trusted proxy.
- Token transport: query param (deprecated) and subprotocol bearer (preferred); expired, refresh, and invalid tokens rejected.
- Dynamic ws/wss URL uses the current host; exact mounted path is /api/v1/admin/ws.
- Close codes 4408 (timeout) and 4413 (oversized) are registered.
- No payload or bearer-token content is logged or written to audit metadata.
- All controls are process-local (single-process architecture).

## Known limitations
- All WebSocket controls are process-local, not cluster-wide.
- Query-parameter token transport remains for browser compatibility (deprecated).
- TLS does not prevent server-side URL logging for query-parameter tokens.
- CORS expose_headers does not currently include X-Request-ID (deferred).
- Unhandled server-level exceptions that bypass the middleware are not covered for X-Request-ID.
- No distributed enforcement; WebSocket controls remain process-local.

## Evidence provenance
Every JSON artifact uses generated_from_commit tied to the immutable implementation commit 9bc2e0c04f77d7a961e3e4b7b68a5e28a36339aa. No self-referential pending placeholders. No stale implementation SHA remains.