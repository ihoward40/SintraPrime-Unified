# New Jersey Pilot

New Jersey is the Phase 2A pilot jurisdiction. Status: `TESTED`. It is not human reviewed and not production eligible.

Required warning:

```text
Educational and issue-spotting output only. This system does not provide a legal opinion or replace review by a licensed attorney.
```

## Covered Domains

- Trust formation and administration under the New Jersey Uniform Trust Code.
- Trust creditor exposure, including spendthrift, discretionary, mandatory, overdue distributions, settlor-creditor, revocable exposure, and settlor-benefit warnings.
- Trust administration depth: directed-trust issues, powers to direct, advisers, delegation, bond, trustee removal, virtual representation, nonjudicial settlement, limitation periods, consent/release/ratification, principal and income, tax-objective modification, special-needs trust issue spotting, charitable oversight, and decanting limitations.
- Creditor and levy depth: wage execution, bank levy and turnover procedure, protected benefit overlays, pension/retirement issue spotting, limited personal property exemption issue spotting, support/government/tax exception warnings, and UVTA timing/remedy warnings.
- Bankruptcy interface: estate-property, revocable and self-settled trust exposure, beneficiary interests, spendthrift exclusions, exemption selection, fraudulent-transfer lookback, stay, and discharge-limit issue spotting. These remain labeled `FEDERAL_BANKRUPTCY_REVIEW_REQUIRED`.
- UCC Article 9 filing office, debtor naming, trust debtors, financing statements, amendments, continuations, terminations, search/rejection procedures, electronic filing, fees, and N.J.A.C. 17:33 source limitations.

## Source Posture

Primary authority records are in `data/jurisdictions/new_jersey/authorities.json`. Rules are in `data/jurisdictions/new_jersey/rules.json`. Research coverage is in `data/jurisdictions/new_jersey/research_manifest.json`.

N.J.A.C. 17:33 remains constrained. Official OAL/Treasury sources confirm the official Administrative Code access path and adoption notice, but Phase 2A did not capture full current official N.J.A.C. 17:33 text. Rules depending on that regulation remain human-review gated.

Several creditor and exemption authorities are locator-copy records. They are intentionally not promoted to production eligibility.

## Review Status

`reviews.json` and `challenges.json` exist as governed ledgers, but no real licensed-attorney approval has been entered. The implemented workflow can approve legal rules only through `LICENSED_ATTORNEY` review records with authenticated approval events, unexpired scope, satisfied conditions, primary authority verification, no unresolved conflicts, no stale-source blockers, and no critical deficiencies.
