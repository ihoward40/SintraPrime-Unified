# Matter Export Packets

Phase 2C-5 exposes `POST /api/v1/matters/{matter_id}/exports` for authorized internal users. The request accepts `{ "format": "JSON" }` or `{ "format": "PDF" }`.

## Packet contents

Each packet is a read-only projection of tenant- and matter-scoped records:

- matter summary;
- parties, accounts, filings, disputes, and communications;
- chronological communications, deadlines, and audit events;
- current deadlines and append-only deadline versions;
- evidence nodes, links, findings, contradictions, and missing-evidence entries;
- assessments and append-only assessment versions;
- review status;
- audit-chain verification summary;
- redacted evidence manifest with available checksums and redaction state;
- limitations stating that the packet is educational and issue-spotting output, not a legal opinion.

Raw source documents are not embedded. The export uses the redacted fields maintained by persistent matter intelligence and applies recursive redaction again at packet assembly.

## Integrity and audit

The canonical packet body is hashed with SHA-256. The JSON/PDF response includes packet, redacted-manifest, and export-audit identifiers in headers. The export creates a `matter_export` immutable audit event containing the format, hashes, and byte count. The packet states that its packet hash covers the canonical packet excluding the integrity object, avoiding a circular hash.

The PDF is a text-only, dependency-free rendering of the same redacted packet JSON. It is intended as a review artifact, not a signed legal filing or source-document replacement.

## Authorization

The dedicated `matter_intelligence:export` permission is granted to `FIRM_ADMIN` and `ATTORNEY`. Clients and paralegals cannot invoke the endpoint. The frontend displays export controls only for its internal attorney/admin posture; the API remains the enforcement boundary.