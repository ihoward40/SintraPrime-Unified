# Sigma Gate Policy — PR #102

## Change

Added `if: always()` to the Bandit security scan step in `.github/workflows/sigma-gate.yml`.

## Why

Before this change, the Sigma Gate workflow had a cascading-skip problem:

```
Step 1: Run tests with coverage     → ✅ passes
Step 2: Enforce coverage threshold   → ❌ fails (63% < 80%)
Step 3: Security scan (bandit)       → ⏭️ SKIPPED (because Step 2 failed)
Step 4: Post gate status             → ✅ runs (has if: always())
```

Security scanning should run regardless of whether coverage meets its threshold.
The bandit step is independent — it scans for new security findings, not coverage.

## After

```
Step 1: Run tests with coverage     → ✅ passes
Step 2: Enforce coverage threshold   → ❌ fails (63% < 80%)
Step 3: Security scan (bandit)       → ✅ RUNS (if: always())
Step 4: Post gate status             → ✅ runs (if: always())
```

## Coverage Threshold Decision (deferred)

Current state: 63.0% measured, 80% threshold.

| Option | Description | Trade-off |
|--------|-------------|-----------|
| A | Keep 80%, write tests | Sigma Gate stays red until scheduler coverage improves |
| B | Lower to 60%, ratchet | Sigma Gate goes green now, ratchet upward over time |

This PR does NOT change the threshold. That is a separate policy decision.

## Coverage Baseline

As of PR #101 merge:
- agents/nova: 88%
- agents/sigma: 74%
- agents/zero: 73%
- scheduler: 32%
- TOTAL: 63%

Gap to 80%: ~351 lines (primarily scheduler at 32%).

## Rollback

Remove `if: always()` from the bandit step. Security scan will revert to being skipped
when coverage threshold fails.
