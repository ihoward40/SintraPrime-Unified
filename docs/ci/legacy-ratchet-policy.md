# Legacy Ratchet CI Policy

The repository currently has legacy lint/test debt that is not remediated by the monetization security branch. CI separates new blocking gates from legacy informational reports.

## Mandatory changed-file gates

Changed Python files must pass Ruff. Security-sensitive changed Python files under `backend/stripe_payments`, `ledger`, `scripts`, or `orchestration/enforcement` must pass targeted Bandit. Generated JSON schema validation, ledger verification, and secret scanning are mandatory.

## Legacy informational reports

Repo-wide Ruff and Bandit are reported as legacy debt. They do not block solely because pre-existing counts are nonzero.

## Ratchet rule

The committed baseline in `docs/ci/legacy-ratchet-baseline.json` records current legacy counts. CI fails if the count increases. Counts may decrease without updating the baseline. To intentionally update the baseline after cleanup, run:

```powershell
python scripts/legacy_ratchet.py --update-baseline --json
```

Do not update the baseline to hide newly introduced violations.
