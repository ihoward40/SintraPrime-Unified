# Known limitations

This delivery remains Phase 1 only.

- Commands are intentionally disabled until server-side authorization, confirmation, idempotency, and audit events are implemented.
- Runs, decisions, incidents, and cost metrics remain `unavailable` unless an authoritative API supplies them.
- Detail surfaces use explicit empty states rather than demo data.
- When `VITE_API_BASE_URL` is not configured, Mission Control does not call localhost; telemetry is labeled offline/unavailable.
- Operations Floor integration is preserved as the restored `/operations-floor` route. Additive live telemetry enhancements belong to a separately authorized phase.