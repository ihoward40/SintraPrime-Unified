"""CI Enforcer — Pre-commit hooks and GitHub Actions workflow generation.

Generates git hooks and CI workflow files that call Sigma for every
commit and pull request.
"""

import json
import logging
import os
import stat
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ci_enforcer")
logger.setLevel(logging.INFO)

SIGMA_GATE_WORKFLOW = textwrap.dedent("""\
name: "Sigma Gate"

on:
  pull_request:
    branches: [ main, develop ]
  push:
    branches: [ main ]

permissions:
  contents: read
  pull-requests: write
  statuses: write

jobs:
  sigma-gate:
    name: "Sigma Quality Gate"
    runs-on: ubuntu-latest
    timeout-minutes: 15

    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-cov bandit mypy

      - name: Run tests with coverage
        run: |
          python -m pytest tests/ --tb=short --cov=. --cov-report=term-missing

      - name: Security scan (bandit)
        run: |
          python -m bandit -r . --exclude .venv,node_modules,tests -ll || true

      - name: Post gate status
        if: always()
        run: echo "Sigma gate completed"
""")


PRE_COMMIT_HOOK = textwrap.dedent("""\
#!/usr/bin/env bash
# Sigma pre-commit hook
set -euo pipefail

echo "Sigma pre-commit gate..."

if command -v python3 &>/dev/null; then
    echo "  Running tests..."
    python3 -m pytest tests/ -x -q --tb=line --no-header 2>/dev/null || {
        echo "Tests failed — commit blocked."
        exit 1
    }
    echo "  Tests passed."

    STAGED=$(git diff --cached --name-only --diff-filter=ACMR -- '*.py')
    if [ -n "$STAGED" ]; then
        echo "  Running security scan on staged files..."
        echo "$STAGED" | xargs python3 -m bandit -q 2>/dev/null || {
            echo "  Security warnings found (non-blocking)."
        }
    fi
else
    echo "  Python3 not found — skipping checks."
fi

echo "Sigma gate passed — commit allowed."
""")


PRE_PUSH_HOOK = textwrap.dedent("""\
#!/usr/bin/env bash
# Sigma pre-push hook
set -euo pipefail

echo "Sigma pre-push gate..."

if command -v python3 &>/dev/null; then
    python3 -m pytest tests/ --tb=short -q --no-header || {
        echo "Tests failed — push blocked."
        exit 1
    }
    echo "All tests passed — push allowed."
fi
""")


class CIEnforcer:
    """Manages CI/CD enforcement: git hooks and GitHub Actions workflows.

    Generates and installs pre-commit/pre-push hooks that invoke Sigma
    checks, and produces GitHub Actions workflow files.
    """

    def __init__(self, repo_root: Optional[str] = None):
        self.repo_root = Path(repo_root) if repo_root else Path.cwd()
        logger.info("CIEnforcer initialized for %s", self.repo_root)

    def install_hooks(self) -> Dict[str, bool]:
        """Install Sigma git hooks (pre-commit, pre-push)."""
        hooks_dir = self.repo_root / ".git" / "hooks"
        results: Dict[str, bool] = {}

        if not hooks_dir.parent.exists():
            logger.warning(".git directory not found — creating hooks dir anyway.")

        hooks_dir.mkdir(parents=True, exist_ok=True)

        for name, content in [("pre-commit", PRE_COMMIT_HOOK), ("pre-push", PRE_PUSH_HOOK)]:
            hook_path = hooks_dir / name
            try:
                hook_path.write_text(content)
                hook_path.chmod(hook_path.stat().st_mode | stat.S_IEXEC)
                results[name] = True
                logger.info("Installed %s hook at %s", name, hook_path)
            except OSError as exc:
                logger.error("Failed to install %s hook: %s", name, exc)
                results[name] = False

        return results

    def uninstall_hooks(self) -> Dict[str, bool]:
        """Remove Sigma git hooks."""
        hooks_dir = self.repo_root / ".git" / "hooks"
        results: Dict[str, bool] = {}
        for name in ("pre-commit", "pre-push"):
            hook_path = hooks_dir / name
            try:
                if hook_path.exists():
                    hook_path.unlink()
                results[name] = True
            except OSError as exc:
                logger.error("Failed to remove %s hook: %s", name, exc)
                results[name] = False
        return results

    def generate_github_actions_workflow(self) -> str:
        """Return the full YAML content for the Sigma gate workflow."""
        return SIGMA_GATE_WORKFLOW

    def write_github_actions_workflow(self) -> Path:
        """Write the workflow YAML to .github/workflows/sigma-gate.yml."""
        wf_dir = self.repo_root / ".github" / "workflows"
        wf_dir.mkdir(parents=True, exist_ok=True)
        wf_path = wf_dir / "sigma-gate.yml"
        wf_path.write_text(SIGMA_GATE_WORKFLOW)
        logger.info("Wrote workflow to %s", wf_path)
        return wf_path

    def validate_pr_checklist(self, pr_body: str) -> Dict[str, Any]:
        """Validate that a PR body contains required checklist items."""
        required_items = [
            ("description", ["## description", "## summary", "## what"]),
            ("test_evidence", ["## test", "test result", "pytest", "coverage"]),
            ("changelog", ["## changelog", "## changes", "### changed"]),
        ]

        results: Dict[str, Any] = {"passed": True, "missing": [], "found": []}
        body_lower = pr_body.lower() if pr_body else ""

        for item_name, keywords in required_items:
            found = any(kw in body_lower for kw in keywords)
            if found:
                results["found"].append(item_name)
            else:
                results["missing"].append(item_name)
                results["passed"] = False

        return results

    def enforcement_status(self) -> Dict[str, Any]:
        """Return current enforcement status."""
        hooks_dir = self.repo_root / ".git" / "hooks"
        wf_path = self.repo_root / ".github" / "workflows" / "sigma-gate.yml"

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pre_commit_installed": (hooks_dir / "pre-commit").exists(),
            "pre_push_installed": (hooks_dir / "pre-push").exists(),
            "github_actions_workflow": wf_path.exists(),
            "repo_root": str(self.repo_root),
        }
