# Legacy Engine — Controlled Knowledge Pilot

Default state: READ-ONLY.

Allowed operations: retrieve, classify, summarize, cross-reference, route.

Blocked by default: confidential trust/beneficiary/banking/tax/medical data, external API calls, production modifications, legal/financial execution, automatic memory injection.

## Pilot acceptance matrix
- Source integrity: hashes or equivalent provenance.
- Retrieval: exact-source retrieval without truncation/corruption.
- Routing: officer route must be backed by an approved charter.
- Adversarial: prohibited operations must fail closed.
- Persistence: must be tested separately; never infer cross-session persistence from same-session visibility.
- Evidence labels: DIRECTLY OBSERVED, FILESYSTEM VERIFIED, RUNTIME VERIFIED, INFERRED, NOT TESTED, FAILED.

Activation remains separate from pilot success.
