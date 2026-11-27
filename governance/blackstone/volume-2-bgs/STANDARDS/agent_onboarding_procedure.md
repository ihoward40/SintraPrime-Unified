# AOP-001 — Agent Onboarding Procedure

## Purpose

Define the governed, evidence-based process required before a new agent may operate in the institution.

## Derived From

BGS 1 (Evidence Handling), BGS 2 (Provenance), BGS 6 (Review Workflow), BGS 8 (Decision Ledger), and BKGC Article VII § 7.1.

## Onboarding Gate (Normative)

An agent MUST NOT be activated until all onboarding stages below are complete and recorded.

## Required Inputs

1. Proposed agent identity (name, owner, role).
2. Mission scope and explicit decision authority boundaries.
3. Source evidence package supporting need, risk profile, and expected outcomes.
4. Initial control profile (allowed systems, prohibited actions, escalation path).

## Procedure

### Stage 1 — Intake Registration

1. Register an onboarding record with a unique onboarding ID.
2. Link the onboarding record to all submitted evidence IDs.
3. Record collector identity, timestamp, and jurisdiction.

### Stage 2 — Evidence Sufficiency Review

1. An R1 reviewer MUST verify that the evidence package supports:
   - the institution's need for the agent,
   - the proposed authority scope,
   - known risks and mitigations,
   - measurable success criteria.
2. Missing or unverifiable evidence MUST result in rejection or quarantine.

### Stage 3 — Risk and Authority Validation

1. Verify role boundaries and prohibited actions.
2. Define required human-approval gates for consequential actions.
3. Confirm fallback and suspension conditions.
4. Record all controls in the onboarding record.

### Stage 4 — Governed Decision

1. Produce a formal onboarding decision with:
   - decision ID,
   - reviewer identity,
   - accepted scope,
   - required controls,
   - confidence score,
   - activation outcome (`Approved`, `Conditional`, or `Rejected`).
2. Conditional approvals MUST include explicit remediation requirements and due dates.

### Stage 5 — Activation and Monitoring Baseline

1. Approved agents MUST receive an initial monitoring baseline (metrics, cadence, owner).
2. The first post-activation review date MUST be scheduled at onboarding time.
3. Activation MUST be blocked if monitoring ownership is undefined.

## Required Outputs

- Onboarding record with full provenance metadata.
- Governed onboarding decision entry in the decision ledger.
- Control profile and review schedule attached to the agent's operational record.

## Failure Handling

- Evidence defect: reject or quarantine onboarding package.
- Authority mismatch: downgrade to conditional approval or reject.
- Missing reviewer identity or decision record: onboarding is invalid.
- Control profile drift after approval: suspend agent pending re-review.
