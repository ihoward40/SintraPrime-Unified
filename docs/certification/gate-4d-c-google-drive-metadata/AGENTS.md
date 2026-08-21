# Gate 4D-C Google Drive metadata design package

## Scope

This directory contains design and test-plan artifacts only for the proposed `provider.google-drive-metadata-read-v1` boundary.

## Authority

- Implementation is not authorized.
- OAuth execution, account connection, credential requests, token issuance, Google API calls, and Drive metadata retrieval are not authorized.
- Content read/export/download and every write or permission operation are prohibited.
- Gate 4D-B remains frozen at `457f69be6714797f2332e20dfc6a245c817099e5`; this package does not alter or extend it.

## Design invariants

Every artifact must preserve metadata-only least privilege, Principal-selected account binding, exact Google endpoint pinning, secret-redacted evidence, fail-closed negative capability rules, and freeze/stop separation between design, implementation, account connection, and certification.

## Package contents

- `authority-contract.json` — normative proposed allowlist, denylist, and authority separation.
- `threat-model.md` — assets, trust boundaries, threats, and mandatory controls.
- `account-binding-design.md` — OAuth/account lifecycle without executing it.
- `network-and-metadata-enforcement.md` — destination and field-level restrictions.
- `acceptance-test-plan.md` — positive, negative, adversarial, and governance cases.
- `evidence-schema.json` — secret-redacted certification evidence shape.
- `certification-ladder.md` — C1–C8 exact-head ladder.
- `freeze-and-stop.md` — freeze record and non-expansion procedure.
- `DESIGN_MANIFEST.json` — hashes of the complete package.

## Change discipline

This design package must not contain credentials, refresh tokens, authorization codes, client secrets, live account identifiers, or provider responses. Any future implementation must be separately authorized and must not infer authority from these documents.
