# UCC Filing Assessment

Phase 2B adds a nonpersistent evidence-based UCC filing assessment workflow.

## API

- `POST /ucc-filings/evaluate`
- `GET /ucc-filings/{evaluation_id}`

The write endpoint requires reviewer authorization headers under the existing Phase 2A controlled-write pattern.

## Inputs

The assessment accepts filing jurisdiction, filing number, filing office, filing date, debtor type, debtor name, secured party, collateral summary, security-agreement evidence, value evidence, debtor-rights evidence, amendments, continuation records, termination status, and duration exceptions.

The frontend does not request full Social Security numbers. Redaction helpers mask SSN-like, account-like, and long payment-card-like numeric strings in display output.

## Conclusions Supported

- Filing-office acceptance as a filing fact.
- Correct filing-location risk.
- Debtor-name risk.
- Missing security-agreement, value, and debtor-rights evidence.
- Ordinary five-year continuation window with six-month continuation period.
- Early continuation, lapse, special-duration review, privacy risk, and unsupported collateral assertions.

## Conclusions Prohibited

The assessment does not conclude attachment, enforceability, ownership, perfection, priority, or validity merely from a filing-office acknowledgment.

It always displays:

```text
A filing-office acknowledgment confirms receipt and indexing. It does not independently establish attachment, enforceability, ownership, priority, or the legal validity of every collateral claim.
```

Collateral text is untrusted data and is not treated as instructions to the application.
