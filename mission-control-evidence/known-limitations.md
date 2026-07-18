# Known limitations

This delivery is Phase 1 of the seven-phase directive.

- Commands are intentionally disabled until server-side authorization,
  confirmation, idempotency, and audit events are implemented.
- Runs, decisions, incidents, and cost metrics are marked `unavailable`;
  SintraPrime does not yet expose authoritative sources for them.
- Detail surfaces use explicit empty states rather than demo data.
- Browser screenshots, console audit, and live responsive verification require
  an authenticated running Portal instance. No claim is made without that
  evidence.
- Operations Floor integration is represented by its route in this baseline;
  additive telemetry enhancements belong to Phase 2.
