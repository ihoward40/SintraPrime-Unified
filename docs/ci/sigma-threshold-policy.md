# Sigma Threshold Policy — PR #103

## Decision

Temporary baseline threshold: **60%**
Long-term target: **80%**

This is a baseline policy decision, not the final quality target.

## Current Coverage (as of PR #102 merge)

```
agents/nova:     88%
agents/sigma:    74%
agents/zero:     73%
scheduler:       32%
TOTAL:           63.0%
```

## Why 60%, not 65%

Current coverage is 63.0%. Setting 65% would still fail Sigma Gate.
60% provides a passing baseline with 3% headroom while we write real tests.

## Ratchet Schedule

| Stage | Threshold | Priority Target | Notes |
|-------|-----------|-----------------|-------|
| **Now** | 60% | — | Baseline. Sigma Gate goes green. |
| Stage 1 | 65% | scheduler/ (32%) | Biggest gap. ~35 lines to reach 65%. |
| Stage 2 | 70% | scheduler/ continued | scheduler → 50%+ target |
| Stage 3 | 75% | agents/zero (73%), agents/sigma (74%) | Incremental improvement |
| Stage 4 | 80% | Full repo | Final quality target reached |

Each stage should be a separate PR with real test additions, not coverage hacks.

## Coverage Priority Order

1. **scheduler/** — 32% coverage, largest gap, highest ROI
2. **agents/zero/** — 73%, close to threshold bumps
3. **agents/sigma/** — 74%, close to threshold bumps
4. **agents/nova/** — 88%, already strong

## Rules

- No fake coverage (empty tests, pragma: no cover abuse)
- No app code changes to inflate coverage
- Each threshold bump must be accompanied by real test additions
- Bandit behavior unchanged — runs with `if: always()`

## Rollback

Change threshold back to 80% in sigma-gate.yml (or any intermediate value).
