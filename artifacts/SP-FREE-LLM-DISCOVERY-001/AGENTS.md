# SP-FREE-LLM-DISCOVERY-001 — Free LLM Discovery Registry

## Purpose

Owns the governed discovery and verification record for third-party "free LLM API" catalogs, starting with `open-free-llm-api/awesome-freellm-apis`, and the eligibility evidence that the existing `governed_inference/` model router may consume.

## Ownership

- Phase 1 catalog audit artifacts and their provenance records
- Candidate provider records, catalog state transitions, and their evidence
- Verification checklists and canary evidence for Phases 2–4

Owned elsewhere: routing, policy, adapters, cost accounting, and receipts stay in `governed_inference/`. This track never owns or duplicates router logic.

## Local Contracts

- Phase 1 is read-only: no provider registration, no credential use, no key acquisition, no spending, no network calls to provider endpoints.
- A catalog listing is a lead, not an entitlement. Counts published by the upstream project are recorded as project-advertised, never as verified inventories.
- Provider records progress only `DISCOVERED → DOCUMENTED → ENTITLEMENT_VERIFIED → CANARY_PASSED → APPROVED`. No state may be skipped, and no state may be set by a catalog sync.
- Withdrawn free tiers, price changes, and model retirements may suspend eligibility but must never silently authorize a paid replacement.
- Do not copy upstream `.env` examples, credential configurations, shell-profile exports, install instructions, or bulk model tables into this repository. Record references, hashes, and derived counts instead.
- Confidential IKE Solutions legal-education materials, consumer documents, and trust-related workflows are out of scope for any free-tier model regardless of price. Free-tier output may assist drafting and research and cannot certify legal conclusions.
- Attribution: the upstream catalog is MIT-licensed. Any quoted excerpt must carry its source URL and commit pin.

## Work Guidance

- Pin every claim to a commit SHA plus a retrieval timestamp; record file hashes so a later sync is detectable.
- Report published counts and independently derived counts side by side and label which is which.
- Record upstream data-quality defects as findings with line references instead of silently normalizing them.
- Keep provider records vendor-neutral and evidence-linked; store the evidence, not the vendor's marketing copy.

## Verification

- `python3 -m json.tool artifacts/SP-FREE-LLM-DISCOVERY-001/phase_1_provenance.json` parses the provenance record.
- Re-derive the counts in `phase_1_catalog_audit.md` §6 with the reproduction commands in §12; the numbers must match the recorded values.
- Confirm no file in this track contains an API key, `.env` example, or shell export line.

## Child DOX Index

None.
