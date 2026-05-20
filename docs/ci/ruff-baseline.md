# Ruff Baseline Configuration

## Purpose

The ruff baseline configuration uses **directory exclusions** and **per-file-ignores** to suppress pre-existing lint violations while enforcing all rules on new code. This is functionally equivalent to bandit's `--baseline` approach, implemented through ruff's native configuration.

## How It Works

Ruff does not have a built-in baseline file mechanism. Instead, the baseline is encoded in `pyproject.toml` through two layers:

### Layer 1: Directory Exclusions (`exclude`)
Legacy and feature-module directories are excluded from ruff scanning entirely. These directories contain **22,925 of 24,378 total violations (94%)** and are not under active development.

### Layer 2: Per-File-Ignores (`per-file-ignores`)
Active directories (`portal/`, `backend/`, `tests/`, `governance/`, root files) have specific rules suppressed at the subdirectory level. This allows:
- ✅ New violations of *other* rules are caught in those directories
- ✅ New files in *new* directories get full linting (not excluded)
- ⚠️ New files in existing subdirectories inherit that subdirectory's ignores

## Current Baseline Stats

| Metric | Count |
|--------|-------|
| Generated from | main (2026-05-20) |
| Total violations (all dirs) | 24,378 |
| Unique rule codes | 105 |
| Files with violations | 741 |
| Directories excluded | 48 |
| Per-file-ignore entries | 21 |
| **Violations after baseline** | **0** |

### Violations by Category

| Category | Count | % | Strategy |
|----------|-------|---|----------|
| Style/whitespace (W293, W291, W292) | 6,566 | 27% | Exclude + auto-fix later |
| Type modernization (UP006, UP035, UP045, etc.) | 10,225 | 42% | Exclude + auto-fix later |
| Import sorting (I001) | 628 | 3% | Exclude + auto-fix later |
| Unused imports/vars (F401, F841, F541) | 1,669 | 7% | Per-file-ignores |
| Unused arguments (ARG*) | 710 | 3% | Per-file-ignores |
| Datetime timezone (DTZ*) | 722 | 3% | Exclude + per-file-ignores |
| Bugbear (B*) | 595 | 2% | Per-file-ignores |
| Naming (N*) | 213 | 1% | Per-file-ignores |
| Other (RET, SIM, PT, RUF, etc.) | 3,050 | 12% | Mixed |

### Violations by Directory (Top 15)

| Directory | Violations | Status |
|-----------|-----------|--------|
| `core/` | 6,701 | Excluded |
| `integrations/` | 1,721 | Excluded |
| `docket/` | 920 | Excluded |
| `predictive/` | 890 | Excluded |
| `superintelligence/` | 702 | Excluded |
| `backend/` | 572 | Per-file-ignores |
| `esignature/` | 558 | Excluded |
| `federal_agencies/` | 530 | Excluded |
| `phase19/` | 530 | Excluded |
| `portal/` | 522 | Per-file-ignores |
| `voice/` | 508 | Excluded |
| `phase18/` | 487 | Excluded |
| `financial_mastery/` | 475 | Excluded |
| `agents/` | 459 | Excluded |
| `skill_evolution/` | 448 | Excluded |

## CI Command

```yaml
# .github/workflows/ci.yml — lint job
- run: ruff check . --output-format=github
```

Ruff reads `pyproject.toml` automatically. No command-line changes needed.

## How New Violations Fail CI

1. Developer adds code in an active directory (e.g., `portal/routers/new_router.py`)
2. New file inherits `portal/routers/**` per-file-ignores (ARG001, B008, etc.)
3. But any OTHER rule violation (e.g., `F821` undefined name) → ruff reports it → CI fails
4. Developer adds a new module (e.g., `billing/`) — not excluded, full linting applies
5. Developer modifies an excluded directory (e.g., `core/`) — not linted at all

## Cleanup Ladder

### Phase 1: Auto-fixable bulk cleanup (low risk)

Target rules (17,000+ violations, all auto-fixable):
```bash
# Whitespace — safe, no semantic change
ruff check . --select W291,W292,W293 --fix

# Import sorting — safe with isort config
ruff check . --select I001 --fix

# Type annotation modernization — safe for Python 3.11+
ruff check . --select UP006,UP035,UP045 --fix
```

**After fixing:** Remove the fixed rules from `per-file-ignores`, then remove cleaned directories from `exclude`.

### Phase 2: Targeted manual fixes (medium risk)

| Rule | Count | Fix approach |
|------|-------|--------------|
| F401 | 1,187 | Review each — some imports have side effects |
| B008 | 308 | Move default values to function body |
| F841 | 267 | Remove or use the variable |
| B904 | 165 | Add `from` clause to `raise` in `except` |

### Phase 3: Architecture decisions (high effort)

| Rule | Count | Notes |
|------|-------|-------|
| DTZ003/DTZ005 | 671 | Requires timezone-aware datetime migration |
| N999 | 162 | Module naming — may require directory restructuring |
| ARG001/ARG002 | 644 | Some are by design (interface compliance) |

### Phase 4: Directory re-inclusion

As directories are cleaned up:
1. Run `ruff check <directory>/` to verify zero violations
2. Remove the directory from `exclude` in `pyproject.toml`
3. Add `per-file-ignores` if any residual violations remain
4. Commit — CI now enforces rules on that directory

Suggested order (by violation count, ascending):
1. `scripts/` (already in per-file-ignores)
2. `governance/` (already in per-file-ignores)
3. `security/` (low count)
4. `observability/` (low count)
5. `scheduler/` (low count)
6. `predictive/` (low count)
7. Work outward from active directories

## Known Issues

| Issue | Detail |
|-------|--------|
| `portal/middleware.py` | Python syntax error — excluded from ruff entirely. Fix the syntax first. |
| `PHASE_11_14_INTEGRATION_ORCHESTRATOR.py` | Root-level legacy file. Excluded. |
| Per-file-ignores scope | New files in existing subdirectories inherit that subdirectory's ignores. This is a known ruff limitation — baseline files would be better but don't exist in ruff. |

## Rollback Plan

Revert `pyproject.toml` to previous version. The original config had the same `select` and `ignore` rules but no `exclude` or `per-file-ignores` — ruff will report all 24,378 violations again, and CI lint will fail (same as before this PR).

## Configuration Reference

The baseline lives entirely in `pyproject.toml` under:
- `[tool.ruff]` → `exclude` list
- `[tool.ruff.lint.per-file-ignores]` → directory-level suppressions

No separate baseline file. No workflow changes.
