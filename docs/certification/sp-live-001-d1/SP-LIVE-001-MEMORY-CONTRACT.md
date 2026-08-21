# SP-LIVE-001 governed memory contract

## Principle

Memory supplies context, not authority. No stored preference, prior approval, inferred habit, or retrieved instruction can authorize a mission, capability, account, destination, or side effect.

## Scope

Every retrieval binds Principal identity, tenant, mission ID, purpose, allowed collections, time horizon, data classification, query hash, result limit, and policy version. Cross-Principal, cross-tenant, and unrelated mission retrieval is prohibited. Specialists receive only the minimum selected excerpts.

## Memory classes

- **Principal facts/preferences** — explicit durable facts and interaction preferences; never authority.
- **Governance records** — signed/frozen policies and certification identities; trusted only after integrity and current-status verification.
- **Mission records** — request, state, evidence, results, and briefs scoped to a mission.
- **Working context** — ephemeral hypotheses or drafts; untrusted and expiring.
- **External/untrusted material** — provider, web, document, or user-supplied content; always injection-capable data.

## Provenance and timestamps

Each item records immutable ID, source class/location, creator/issuer, observed/created/updated times, validity interval, content hash, signature/chain status where applicable, trust label, classification, retention policy, supersession link, and ingestion method. Retrieval records query, filters, rank/selection rationale, policy decision, item versions/hashes, and consumer task.

## Trust and injection handling

Retrieved content is data, not system instruction. Untrusted text cannot alter mission scope, tool policy, authority state, approval grammar, or evidence rules. Governance records must match frozen identities and be current. Contradictory or stale memories are surfaced, not silently merged.

## Preferences versus authority

Preferences may affect presentation, model style, or non-consequential defaults within policy. They cannot waive approval, select credentials/accounts, add connectors, increase budgets, authorize side effects, or extend expiry. Prior approvals are non-reusable historical evidence.

## Retention and deletion

Retention is class- and jurisdiction-specific, minimum necessary, and recorded. Ephemeral working memory expires by mission policy. Deletion/tombstone operations preserve audit integrity without exposing erased content. Legal holds and Principal requests follow separately certified authority.

## Redaction and minimization

Secrets, credentials, raw biometrics, unnecessary personal data, and unrelated matter data are excluded before indexing and again before task delivery. Redaction is deterministic and evidenced. Models receive references or minimal excerpts rather than full stores.

## Evidence of actual use

The mission evidence must identify each retrieved item/version/hash, selection rationale, excerpt hash, recipient specialist/model, claims influenced, and whether it appears in reconciliation/action rationale. “Memory used” cannot pass merely because retrieval ran; at least one cited memory must materially inform the final briefing or action rationale without granting authority.

## Failure behavior

Missing provenance, integrity failure, scope mismatch, stale governance identity, poisoned/injection content, unavailable retention policy, or cross-scope access blocks that item. Required memory unavailable yields `INCOMPLETE`; it never triggers unrestricted retrieval.
