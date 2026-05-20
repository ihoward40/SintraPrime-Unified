# Bandit Baseline Configuration

## Purpose

The `.bandit-baseline.json` file captures all **pre-existing** security findings in the SintraPrime-Unified codebase. When CI runs bandit with `--baseline .bandit-baseline.json`, it compares current findings against this snapshot and only reports **new** findings — regressions introduced after the baseline was set.

This is a **gate**, not a cleanup. Pre-existing findings are acknowledged and deferred, not hidden.

## Current Baseline Stats

| Metric | Count |
|--------|-------|
| Generated from | main `49fde88c` (2026-05-20) |
| Total findings | 9,265 |
| HIGH severity | 21 |
| MEDIUM severity | 97 |
| LOW severity | 9,147 |
| Files with syntax errors | 1 (`portal/middleware.py`) |
| Lines of code scanned | 225,054 |

## How CI Uses the Baseline

### SintraPrime CI (`ci.yml` — security job)

```bash
bandit -r . -x tests/ -ll --baseline .bandit-baseline.json
```

- `-ll` = report MEDIUM severity and above only
- `--baseline` = suppress findings already in baseline
- Exit code 0 = no new MEDIUM+ findings
- Exit code 1 = new MEDIUM+ findings detected → CI fails

### Sigma Gate (`sigma-gate.yml`)

```bash
python -m bandit -r . \
    --exclude .venv,node_modules,tests \
    --baseline .bandit-baseline.json \
    -f json -o /tmp/bandit.json
```

Then evaluates: any new HIGH findings → fail.

## How New Findings Fail CI

1. Developer adds code with a new security issue (e.g., hardcoded password)
2. Bandit scans and finds it
3. The finding is NOT in `.bandit-baseline.json` → it's reported as new
4. CI exits non-zero → PR blocked

This means:
- ✅ Existing tech debt doesn't block PRs
- ✅ New security issues are caught immediately
- ✅ The baseline shrinks over time as findings are fixed

## How to Regenerate the Baseline

Run from repo root:

```bash
bandit -r . \
    -x tests/,.venv,node_modules \
    -f json -o .bandit-baseline.json
```

**When to regenerate:**
- After intentionally fixing security findings (shrinks the baseline)
- After large refactors that move code (fingerprints change)
- Never to silence new findings — that defeats the purpose

**Verification after regeneration:**

```bash
# Should exit 0 with "No issues identified"
bandit -r . -x tests/ -ll --baseline .bandit-baseline.json
```

## How to Promote Findings into Fixes

1. Review findings by severity:
   ```bash
   bandit -r . -x tests/ -lll  # HIGH only
   bandit -r . -x tests/ -ll   # MEDIUM+
   ```

2. Fix the code (not the baseline)

3. Regenerate baseline to remove the fixed finding:
   ```bash
   bandit -r . -x tests/ -f json -o .bandit-baseline.json
   ```

4. Verify the fix is no longer in the baseline

## Known Issues

| Issue | Detail |
|-------|--------|
| `portal/middleware.py` | Syntax error — bandit skips this file entirely. Fix the syntax to include it in scans. |
| Baseline size | 7.6MB (9,265 findings). Will shrink as findings are fixed. |
| `nosec` comments | 2 findings explicitly suppressed via `#nosec`. These are intentional. |

## Severity Breakdown (as of baseline generation)

### HIGH (21 findings)
These should be prioritized for actual fixes in future PRs. Common patterns:
- Hardcoded passwords/secrets
- Use of `exec()`/`eval()`
- Insecure hash functions (MD5/SHA1 for security)

### MEDIUM (97 findings)
Typical patterns:
- Hardcoded `/tmp` paths (B108)
- SQL string construction (B608)
- Binding to `0.0.0.0` (B104)
- `subprocess` calls without shell=False validation

### LOW (9,147 findings)
Mostly informational:
- `assert` statements (B101) — bulk of findings
- `subprocess` imports
- `try/except/pass` patterns
