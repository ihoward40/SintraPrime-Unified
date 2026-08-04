# Delaware Pilot

Delaware is the Phase 3A pilot jurisdiction. Status: `TESTED`. It is not human reviewed and not production eligible.

Required warning:

```text
Educational and issue-spotting output only. This system does not provide a legal opinion or replace review by a licensed attorney.
```

## Covered Domains

- Delaware Trust Act (12 Del. C. §§ 3301-3334) for common-law express trusts.
- Delaware Statutory Trust Act / DSTA (12 Del. C. §§ 3342-3365) for statutory trusts, business trusts, and series structures.
- Delaware Qualified Dispositions in Trust Act / DAPT (12 Del. C. §§ 4901-4927) for self-settled asset protection.
- Delaware Directed Trust Act (12 Del. C. §§ 3527-3536) for directed trust structures.
- Trust creation: capacity, intent, property, lawful purpose, ascertainable beneficiaries.
- Revocable trust: settlor creditor exposure and modification.
- Spendthrift validity: third-party settled trusts and exception creditors.
- DAPT eligibility conditions, trustee requirements, fraudulent-transfer limits, bankruptcy override risk.
- Powers of withdrawal and Crummey notice considerations.
- Nonjudicial settlement agreements and trust modification.
- Trust decanting: authority, notice, and beneficiary/creditor challenges.
- Trust protector: appointment, powers, fiduciary duties, exculpation.
- Directed trusts: investment direction, administrative agents, exculpation limits.
- Governing law and principal place of administration.
- Trust migration to Delaware.
- Trustee removal, resignation, and successor appointment.
- Beneficiary information rights and trust accounting.
- UCC Article 9: filing office (SOS central, county recorder local), debtor naming, continuation window.
- Homestead exemption, wage garnishment, tenancy by entirety.
- Delaware trust taxation: situs, fiduciary filing, estate tax repeal (2015).
- Voidable transfers and UVTA.

## Source Posture

Primary authority records are in `data/jurisdictions/delaware/authorities.json`.
Rules are in `data/jurisdictions/delaware/rules.json`.
Research coverage is in `data/jurisdictions/delaware/research_manifest.json`.

Key Delaware authorities:
- 12 Del. C. §§ 3301-3334 (Delaware Trust Act — common-law express trusts)
- 12 Del. C. §§ 3342-3365 (Delaware Statutory Trust Act)
- 12 Del. C. §§ 4901-4927 (DAPT — self-settled asset protection)
- 12 Del. C. §§ 3527-3536 (Directed Trust Act)
- 6 Del. C. §§ 9-101 et seq. (UCC Article 9)
- 25 Del. C. §§ 101-115 (Homestead and exempt property)
- Conn. Gen. Stat. §§ 45a-287 to 45a-499 (CUTS — not DE law)

## Known Limitations

- DAPT provides strong state-law protection but federal bankruptcy courts may apply 11 U.S.C. § 548 fraudulent transfer provisions to void DAPT transfers.
- Delaware does not have a state income tax, but certain trust filing obligations still exist.
- Delaware's estate tax was repealed effective January 1, 2015.
- Connecticut and other states may not recognize Delaware DAPT transfers if their own laws conflict.
- Official Delaware Division of Revenue tax guidance is classified as `PRIMARY_SOURCE_LOCATED` pending full text capture.
- Delaware has no general state income tax; fiduciary trust income tax rules require separate verification.

## Conflicts

- `DE-CONFLICT-DAPT-BANKRUPTCY`: DAPT vs. federal bankruptcy fraudulent transfer override.
- `DE-CONFLICT-DAPT-SELF-SETTLED-VALIDITY`: DAPT "no direct benefit" requirement and ongoing litigation.

## Review Status

`reviews.json` and `challenges.json` exist as governed ledgers. No real licensed-attorney approval has been entered. Delaware DAPT and directed trust rules are especially high-risk and require licensed-attorney review before production eligibility.
