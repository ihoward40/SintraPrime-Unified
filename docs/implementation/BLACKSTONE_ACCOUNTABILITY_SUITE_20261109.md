# Blackstone Accountability Suite — Implementation Contract (Draft)
Date: 2026-11-09
Status: DESIGN ONLY — NOT DEPLOYED OR CERTIFIED
Branch: feature/blackstone-accountability-suite-20261109

## Objective
Integrate eight governed capabilities into existing SintraPrime-Unified without replacing established agent families or bypassing approvals.

## Components and acceptance gates
1. **Independent Inspector General**: read-only audit of task receipts, evidence provenance, permissions, and outcomes. Must not certify its own work. Gate: seeded failure and permission-breach fixtures are detected.
2. **Legal Red Team**: independent challenge of claims, defenses, limitations, standing, jurisdiction, arbitration, and contrary authority. Gate: unsupported legal claims are flagged before approval.
3. **Financial Harm Ledger**: link alleged harm to evidence, dates, causation, mitigation, and remedy categories; no invented amounts. Gate: reconciliation and traceable calculations.
4. **Executive Accountability Register**: record entity, role, actual duty, notice, evidence, response, and basis for any individual liability. Gate: title-only liability is rejected.
5. **Legal Authority Watchtower**: effective dates, jurisdiction, citator status, authority provenance, and change alerts; changes require human legal review. Gate: stale or overruled authority blocks final certification.
6. **Case Failure Risk Engine**: rules-based missing-element and procedural-risk checks, no invented success percentages. Gate: known deadline and standing defects surfaced.
7. **Agent Recovery Supervisor**: heartbeat, retry budget, idempotency keys, receipt reconciliation, and rollback; no automatic repeat of external actions. Gate: simulated crash recovers without duplicate side effects.
8. **Governed Case Assembly Line**: intake → evidence indexing → legal review → red team → harm/accountability mapping → inspector audit → human approval → local draft export. Gate: United Auto Credit fixture yields a sourced readiness packet, with no external contact.

## Existing systems to reuse
- agents/nova: approval gateway and execution ledger.
- agents/sigma: quality gates.
- agents/zero: reversible maintenance.
- agents/* Howard: evidence-intake-only.
- legal_authority, evidence, governance/blackstone, portal, decision, orchestration: assess existing APIs before changes.
- DOX: read root and each scoped AGENTS.md before implementation.

## Non-negotiable safety controls
- No autonomous filing, service, email, complaint submission, settlement, financial transaction, deletion, or external contact.
- Human approval for consequential actions; no silent elevation of privileges.
- Preserve original evidence, hashes, chain of custody, and source citations.
- Separate verified fact, allegation, inference, and unresolved issue.
- No claim of a confirmed legal violation without adequate factual and legal support.
- No automatic deployment or merge; protect dirty local working tree.

## Implementation phases
P0: snapshot and reconcile local dirty repository; inventory active services, agent APIs, and test baseline.
P1: design interfaces and schemas; threat model and migration plan.
P2: build ledger, authority, and accountability primitives with unit tests.
P3: implement red team and independent inspector; adversarial fixtures.
P4: recovery supervisor and orchestrated pipeline; integration tests.
P5: run read-only United Auto Credit pilot with synthetic/redacted fixtures first.
P6: independent review, permission audit, user acceptance, and staged deployment.

## Current verified limitations
Remote devices IKESOLUTIONS and DESKTOP-7RJIO6V were online during review. On DESKTOP-7RJIO6V, Hermes and OpenClaw processes were observed, but agent-to-agent communication and duty completion remain unverified. Local C:\\SintraPrime-Unified has uncommitted modifications and deletions. Do not overwrite or reset it.

## Definition of done
Each component has source code, schema, tests, threat-model controls, receipts, documentation, and verified integration; the full pipeline passes an end-to-end governed test. Until then, report each component as planned, in progress, or verified—not implemented by assertion.
