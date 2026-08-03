# Deadline and Evidence Graph Foundation

Phase 2C-3 adds persistent, tenant-scoped deadline and evidence graph records to the matter intelligence workspace.

## Deadlines

`MatterDeadline` stores the current calculation and `MatterDeadlineVersion` preserves append-only historical calculations. Calculations require timezone-aware trigger timestamps, an explicit calendar type, and retain rule IDs, authority IDs, assumptions, limitations, mailing-day inputs, and holiday inputs. Business-day calculations skip weekends and supplied holidays. Unknown timezones, naive timestamps, invalid calendars, and missing facts must remain human-reviewable rather than silently producing a date.

Supported API routes include deadline creation, calculation, listing, and version history under `/api/v1/matters/{matter_id}/intelligence/deadlines`.

## Evidence graph

`MatterEvidenceNode` represents claims, facts, documents, communications, authorities, rules, and deadlines. `MatterEvidenceLink` records support, contradiction, derivation, requirement, refutation, or corroboration. Missing nodes and contradiction links create persistent `MatterEvidenceFinding` records. Nodes, links, and findings are matter/tenant scoped; link and finding records are append-only.

Evidence statements and notes are untrusted content and pass through the existing sensitive-value redaction service. Professional approval remains role-gated.

## Limits

This increment does not add frontend matter views, packet export, new jurisdictions, or live PostgreSQL integration. Existing case-deadline behavior remains unchanged.
