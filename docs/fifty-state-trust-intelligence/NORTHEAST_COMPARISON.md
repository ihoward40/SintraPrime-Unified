# Phase 3A Five-State Comparison

Phase 3A expands the Northeast Trust Comparison to five states: New Jersey, New York, Pennsylvania, Delaware, and Connecticut.

## Jurisdiction Coverage Matrix

| Jurisdiction | Status | Self-Settled Trust | DAPT Available | UTC | Statutory Trust Act |
|---|---|---|---|---|---|
| New Jersey | `TESTED` | No protection | No | Yes (UTC) | No |
| New York | `TESTED` | No protection | No | Yes (DREPA) | No |
| Pennsylvania | `TESTED` | No protection | No | No (DREPA) | No |
| **Delaware** | `TESTED` | **DAPT protection** | **Yes (12 Del. C. §§ 4901-4927)** | No (DTA) | **Yes (DSTA)** |
| **Connecticut** | `TESTED` | **Explicitly prohibited** | **No** | **Yes (CUTS — nonuniform)** | No |

## Comparison Topics

### Spendthrift Validity

- NJ, NY, PA: Third-party settled spendthrift clauses are generally enforceable, subject to exception creditors.
- DE: Third-party settled spendthrift enforceable; DAPT provides additional self-settled protection.
- CT: Third-party settled spendthrift enforceable; self-settled spendthrift **explicitly prohibited**.

### Self-Settled Asset Protection

- NJ, NY, PA: No domestic asset-protection trust available. Self-settled irrevocable trusts receive **no** creditor protection under state law.
- DE: **DAPT (12 Del. C. §§ 4901-4927) provides strong self-settled protection subject to strict conditions**: irrevocable, independent trustee, no direct benefit to settlor, not fraudulent.
- CT: **Explicitly prohibited**. Connecticut courts have held that self-settled trusts are not entitled to spendthrift protection.

### Revocable Trust Creditor Exposure

All five states treat revocable trust assets as accessible to settlor's creditors during lifetime. No state provides asset-protection insulation for revocable trusts.

### Directed Trusts

- NJ: Directed trust issues are covered under UTC provisions.
- NY, PA: Directed trust structures recognized; specific statutory authority varies.
- DE: Dedicated Directed Trust Act (12 Del. C. §§ 3527-3536).
- CT: CUTS directed trust provisions (Conn. Gen. Stat. §§ 45a-292 to 45a-298).

### UCC Filing Office

- NJ: Secretary of State central; county clerk for fixtures.
- NY: Secretary of State central; county clerk for fixtures.
- PA: Department of State central; county recorder for fixtures.
- **DE**: **Secretary of State central; county recorder for fixtures and local filings**.
- **CT**: **Secretary of State central; town clerk for fixtures only. No separate local filing system for non-fixture collateral**.

### Continuation Window

All five states follow the UCC Article 9 five-year lapse / six-month pre-lapse continuation window (effective 2013-07-01 under RUCC Article 9).

### Homestead and Exempt Property

- NJ, NY, PA: State homestead and personal property exemptions apply.
- DE: Delaware Homestead Act (25 Del. C. §§ 101-115); Delaware has no state income tax.
- CT: Connecticut Homestead Exemption (Conn. Gen. Stat. §§ 49-31q to 49-31t) with income/age eligibility conditions.

### Wage Garnishment

All five states limit wage garnishment for judgment creditors. Connecticut limits to 15% of gross weekly wages above minimum wage. Delaware, NJ, NY, PA each have their own statutory limits. Child support and government claims generally override standard limits in all states.

### Trust Taxation

- NJ: Trust income tax with fiduciary filing requirements.
- NY: Trust income tax; substantial nexus rules apply to nonresident trusts.
- PA: Trust income tax; flat rate on PA-source income.
- DE: **No state income tax. Trust situs established via governing law designation or Delaware trustee**. Delaware estate tax repealed 2015.
- CT: Trust income tax; **Connecticut has its own estate tax** (separate from federal) with lower exemption threshold. DRS guidance is `PRIMARY_SOURCE_LOCATED`.

### Tenancy by Entirety

All five states recognize tenancy by the entirety for real property held by married couples. Protection generally shields entirety property from single-spouse creditors in all five states, subject to joint-debtor and divorce exceptions.

## Conflict-of-Laws Warnings

The comparison engine produces a conflict-of-laws warning that applies to all five states:

> Applicable law depends on governing-law rules, trust situs, administration, party contacts, asset location, public policy, and other facts. A favorable rule in another jurisdiction may not govern the matter.

## Missing Rule Handling

When a jurisdiction lacks a matching rule for the selected topic, the comparison engine shows `rule: null` with `missing_data` populated and `confidence: 0.0`. No jurisdiction is ranked as better or safer.

## Source Quality Tracking

Each rule in the comparison output carries the provenance of authority IDs, effective dates, verification statuses, and limitations. Connecticut's DRS tax guidance and Delaware's tax guidance are `PRIMARY_SOURCE_LOCATED` — they are included for issue-spotting but require professional review before production use.

## Open Conflicts

- `DE-CONFLICT-DAPT-BANKRUPTCY`: Delaware DAPT vs. federal bankruptcy fraudulent transfer law.
- `DE-CONFLICT-DAPT-SELF-SETTLED-VALIDITY`: Delaware DAPT "no direct benefit" requirement ongoing litigation.
- `CT-CONFLICT-SELF-SETTLED-NO-PROTECTION`: Connecticut's explicit self-settled prohibition vs. Delaware DAPT availability.

## Review Status

All five states are `TESTED`, none are `HUMAN_REVIEWED`, and none are `PRODUCTION_ELIGIBLE`. Licensed-attorney review is required for any rule to advance toward production eligibility.
