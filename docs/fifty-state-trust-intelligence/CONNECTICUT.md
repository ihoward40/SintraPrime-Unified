# Connecticut Pilot

Connecticut is the Phase 3A pilot jurisdiction. Status: `TESTED`. It is not human reviewed and not production eligible.

Required warning:

```text
Educational and issue-spotting output only. This system does not provide a legal opinion or replace review by a licensed attorney.
```

## Covered Domains

- Connecticut Uniform Trust Code / CUTS (Conn. Gen. Stat. §§ 45a-287 to 45a-499) with significant nonuniform provisions from model UTC.
- Trust creation: capacity, intent, property, lawful purpose, ascertainable beneficiaries.
- Connecticut's explicit prohibition of self-settled spendthrift protection.
- Spendthrift validity for third-party settled trusts only.
- Revocable trust: settlor creditor exposure.
- Nonjudicial settlement agreements and trust modification.
- Trust decanting: authority, notice requirements, and court approval.
- Directed trusts: investment advisers and distribution advisers.
- Trust protector: appointment, powers, fiduciary duties, exculpation.
- Trustee removal, resignation, and successor appointment.
- Governing law and principal place of administration.
- Beneficiary information rights and trust accounting.
- UCC Article 9: filing office (Secretary of State central, town clerk for fixtures), debtor naming, continuation window.
- Homestead exemption (Conn. Gen. Stat. §§ 49-31q to 49-31t).
- Wage garnishment and exempt funds.
- Tenancy by entirety.
- Connecticut trust taxation: situs, fiduciary filing, estate tax (separate from federal).
- Powers of withdrawal and Crummey notice.

## Source Posture

Primary authority records are in `data/jurisdictions/connecticut/authorities.json`.
Rules are in `data/jurisdictions/connecticut/rules.json`.
Research coverage is in `data/jurisdictions/connecticut/research_manifest.json`.

Key Connecticut authorities:
- Conn. Gen. Stat. §§ 45a-287 to 45a-499 (Connecticut Uniform Trust Code / CUTS)
- Conn. Gen. Stat. §§ 45a-478 to 45a-499 (Creditor claims — explicit self-settled prohibition)
- Conn. Gen. Stat. §§ 42a-9-101 et seq. (UCC Article 9)
- Conn. Gen. Stat. §§ 49-31q to 49-31t (Homestead exemption)
- Connecticut DRS tax guidance (classified `PRIMARY_SOURCE_LOCATED`)

## Key Contrast with Delaware

Connecticut explicitly prohibits spendthrift protection for self-settled trusts. Delaware DAPT explicitly authorizes it. This creates a fundamental conflict record (`CT-CONFLICT-SELF-SETTLED-NO-PROTECTION`) when comparing the two jurisdictions.

## Known Limitations

- Connecticut's CUTS has material nonuniform departures from the model UTC; UTC-derived interpretations from other states may not apply in Connecticut.
- Connecticut has its own estate tax (separate from the federal estate tax) with a lower exemption threshold.
- Connecticut DRS tax guidance is classified as `PRIMARY_SOURCE_LOCATED` pending full text capture.
- Specific Connecticut homestead dollar value caps require official compiler verification.
- Connecticut does not have a DAPT statute; self-settled trusts are NOT protected.
- Directed trust exculpation provisions may be overridden in ERISA employee benefit plan contexts.

## Conflicts

- `CT-CONFLICT-SELF-SETTLED-NO-PROTECTION`: Connecticut's explicit self-settled prohibition vs. Delaware DAPT availability.

## Review Status

`reviews.json` and `challenges.json` exist as governed ledgers. No real licensed-attorney approval has been entered. Connecticut's self-settled prohibition rule is high-risk and requires licensed-attorney review before any production eligibility consideration.
