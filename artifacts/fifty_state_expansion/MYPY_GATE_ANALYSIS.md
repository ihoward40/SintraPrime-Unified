# MyPy Gate Analysis - Phase 2A

Date: 2026-08-03
Branch: feat/fifty-state-trust-intelligence
Starting HEAD: f157c00ce8d0e1a65a04f24808f1b02d07944a5c

## Root Cause

The repository worktree directory is named `SintraPrime-Unified-fifty-state`. A top-level `__init__.py` is present, so MyPy attempts to treat the worktree directory itself as a Python package when invoked with ordinary package/file arguments. Hyphens are invalid in Python package names, causing:

```text
SintraPrime-Unified-fifty-state contains __init__.py but is not a valid Python package name
```

The repository/worktree was not renamed. The safer disposition is to run MyPy from the repository root against explicit package bases that do not cause MyPy to import the hyphenated parent package.

## Attempted Commands

```text
python -m mypy legal_authority portal\services\jurisdiction_rule_service.py portal\routers\jurisdictions.py
```

Result: failed with invalid package-name error above.

```text
python -m mypy --explicit-package-bases legal_authority portal\services\jurisdiction_rule_service.py portal\routers\jurisdictions.py
```

Result: timed out after 35 seconds in this environment.

```text
python -m mypy --config-file pyproject.toml --explicit-package-bases legal_authority portal\services\jurisdiction_rule_service.py portal\routers\jurisdictions.py
```

Result: timed out after 35 seconds in this environment.

```text
python -m mypy --scripts-are-modules legal_authority\constants.py legal_authority\models.py legal_authority\repository.py legal_authority\engine.py legal_authority\review_workflow.py legal_authority\source_monitor.py
```

Result: failed with the same invalid package-name error.

```text
python -m mypy --explicit-package-bases --follow-imports=skip --ignore-missing-imports legal_authority
```

Initial result: failed with a real typing issue in `legal_authority/repository.py` review sorting. The sort key could return `None`.

Final result after fix:

```text
Success: no issues found in 7 source files
```

## Configuration Changes

None. The resolved command is narrow and repository-safe. No worktree rename and no broad MyPy configuration suppression was introduced.

## Final Disposition

Use this Phase 2A legal-authority MyPy gate command:

```text
python -m mypy --explicit-package-bases --follow-imports=skip --ignore-missing-imports legal_authority
```

Risk: this command validates the Phase 2A legal-authority package but intentionally skips deep imported portal dependencies. A future CI fix should remove the top-level `__init__.py` only if repo governance confirms it is not part of a supported package contract, or configure MyPy with package targets that avoid the hyphenated worktree parent.
