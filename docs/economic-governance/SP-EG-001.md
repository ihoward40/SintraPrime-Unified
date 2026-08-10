# SP-EG-001 — Economic Governance & Asset Provenance

## Purpose

SP-EG-001 converts macro/investment lessons into governed SintraPrime primitives without
turning market theses, private records, public filings, or agent recommendations into
unreviewed financial or legal actions.

The subsystem provides five controls:

1. Asset provenance records.
2. Value-accrual records.
3. Scenario/thesis discipline.
4. A six-layer capital-reserve model.
5. Mission-scoped, default-deny agent spending evaluation.

## Non-negotiable evidence rule

A public filing, filing acknowledgment, notice, private agreement, or recorded claim is
stored as evidence of that document or event. The existence of that evidence does **not**
by itself establish ownership, attachment, perfection, priority, enforceability, debt,
liability, agency, fiduciary acceptance, or any other legal effect.

Those effects remain explicit status fields and must be separately supported and reviewed.
No function in this package automatically promotes them.

## Provenance chain

The intended review sequence is:

`ASSET -> ORIGIN -> CLAIMED OWNER -> TRANSFER -> CONSIDERATION -> TRUST ACCEPTANCE -> SCHEDULE A -> ACCOUNTING RECORD -> CONTROL/POSSESSION -> LEGAL CLASSIFICATION -> PUBLIC FILING (IF APPLICABLE)`

`assess_provenance()` reports documentary gaps. It does not render a legal opinion.

## Claim maturity

- `claimed` — an assertion exists.
- `documented` — one or more records support the assertion.
- `verified` — designated review has verified the proposition against appropriate evidence.
- `adjudicated` — a competent adjudicative authority has resolved the proposition.

Legal-effect fields are separately tracked as `not_assessed`, `asserted`, `verified`, or
`adjudicated` so that a document cannot silently bootstrap itself into a legal conclusion.

## Value accrual

`ValueAccrualRecord` answers a simple governance question: if an activity produces value,
where is that value intended to accrue, under what governing instrument, and how will the
result be measured and evidenced?

This can be used for software IP, educational products, licensing, royalties, services,
research assets, or other lawful business assets. It is an administrative record and does
not substitute for an assignment, license, accounting entry, tax analysis, or other
instrument required by applicable law.

## Scenario discipline

`ScenarioRecord` stores forecasts as theses rather than facts. Every scenario requires:

- assumptions;
- a confidence level;
- failure conditions; and
- a time horizon.

This prevents a bullish narrative, price target, or technology forecast from becoming an
unqualified operating assumption.

## Capital reserve model

The default six-layer stack is:

1. Daily liquidity.
2. 30-day operating reserve.
3. Business revolving credit.
4. Revenue-producing digital assets.
5. Strategic investment capital.
6. Long-duration family/trust capital.

The model does not recommend amounts or authorize deployment. Targets and deployability
must be explicitly set by the principal or an authorized governance process.

## Agent spending boundary

`evaluate_spend()` is an evaluation function only. It never sends money.

Default allowlist:

- mission-scoped research;
- public-record purchases; and
- API credits.

Software spending requires principal approval by default.

Autonomous execution is hard-denied for:

- transfers to humans;
- borrowing;
- opening financial accounts;
- purchasing securities; and
- moving trust assets.

Requests must match both the authorized mission and agent, stay within the per-transaction
limit, and stay within remaining mission budget. Unknown categories remain denied.

## Integration posture

Phase 1 is intentionally domain-only. It adds no database migration, payment-provider
integration, wallet, brokerage connection, bank connection, deployment configuration, or
autonomous execution path.

A later integration phase should require explicit approval and add:

- immutable decision/audit events;
- principal approval receipts;
- tenant scoping;
- persistence;
- idempotency;
- cumulative budget reservations;
- reconciliation after payment-provider responses; and
- tests proving that no agent can bypass the policy evaluator.

## Review gates

Before production integration:

- legal-risk review for every field presented as a legal effect;
- financial-control review for execution adapters;
- privacy review for provenance evidence;
- threat-model review for agent authorization;
- unit and integration tests;
- explicit principal authorization for any real-money execution capability.
