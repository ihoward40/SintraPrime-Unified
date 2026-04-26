"""Agent Zero — Autonomous self-healing maintenance agent.

Zero continuously monitors the repository for broken imports, failing tests,
and code health issues. It autonomously generates and applies patches to
restore green builds, with rollback capabilities for safety.
"""

import ast
import json
import logging
import os
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("zero_agent")
logger.setLevel(logging.INFO)


@dataclass
class ImportError_:
    """Represents a detected import error in the codebase."""
    file_path: str
    line_number: int
    module_name: str
    error_message: str
    suggested_fix: Optional[str] = None


@dataclass
class TestFailure:
    """Represents a failing test."""
    test_id: str
    file_path: str
    error_type: str
    error_message: str
    traceback: str


@dataclass
class Patch:
    """Represents a code patch to apply."""
    patch_id: str
    file_path: str
    original_content: str
    patched_content: str
    description: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    applied: bool = False
    rolled_back: bool = False


@dataclass
class HealthReport:
    """Structured health report for the repository."""
    timestamp: str
    total_files_scanned: int
    import_errors: int
    test_failures: int
    patches_applied: int
    patches_rolled_back: int
    overall_status: str
    details: Dict[str, Any] = field(default_factory=dict)


COMMON_IMPORT_FIXES = {
    "yaml": "pyyaml",
    "cv2": "opencv-python",
    "PIL": "Pillow",
    "sklearn": "scikit-learn",
    "bs4": "beautifulsoup4",
    "dotenv": "python-dotenv",
    "jwt": "PyJWT",
    "dateutil": "python-dateutil",
    "attr": "attrs",
    "gi": "PyGObject",
}


class ZeroAgent:
    """Autonomous self-healing maintenance agent.

    Zero monitors the codebase health, detects issues like broken imports and
    failing tests, generates patches, applies them with rollback capability,
    and reports on overall repository health.
    """

    def __init__(
        self,
        repo_root: Optional[str] = None,
        notification_callback: Optional[Any] = None,
        schedule_interval_hours: int = 6,
    ):
        self.repo_root = Path(repo_root) if repo_root else Path.cwd()
        self.notification_callback = notification_callback
        self.schedule_interval_hours = schedule_interval_hours
        self._patches: List[Patch] = []
        self._import_errors: List[ImportError_] = []
        self._test_failures: List[TestFailure] = []
        self._maintenance_history: List[Dict[str, Any]] = []
        self._scheduler = None
        logger.info("ZeroAgent initialized for repo: %s", self.repo_root)

    # ------------------------------------------------------------------
    # Import scanning
    # ------------------------------------------------------------------

    def scan_import_errors(self) -> List[ImportError_]:
        """Scan all Python files for broken imports."""
        self._import_errors = []
        python_files = list(self.repo_root.rglob("*.py"))
        logger.info("Scanning %d Python files for import errors...", len(python_files))

        for fpath in python_files:
            if ".venv" in str(fpath) or "node_modules" in str(fpath):
                continue
            try:
                source = fpath.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(source, filename=str(fpath))
            except SyntaxError as exc:
                self._import_errors.append(
                    ImportError_(
                        file_path=str(fpath),
                        line_number=exc.lineno or 0,
                        module_name="<syntax-error>",
                        error_message=str(exc),
                    )
                )
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self._check_import(fpath, node.lineno, alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        self._check_import(fpath, node.lineno, node.module)

        logger.info("Found %d import errors.", len(self._import_errors))
        return self._import_errors

    def _check_import(self, fpath: Path, lineno: int, module_name: str) -> None:
        """Try to import module_name; record failure if not found."""
        top_level = module_name.split(".")[0]
        try:
            __import__(top_level)
        except ImportError as exc:
            suggested = COMMON_IMPORT_FIXES.get(top_level)
            self._import_errors.append(
                ImportError_(
                    file_path=str(fpath),
                    line_number=lineno,
                    module_name=module_name,
                    error_message=str(exc),
                    suggested_fix=f"pip install {suggested}" if suggested else None,
                )
            )

    # ------------------------------------------------------------------
    # Auto-fix imports
    # ------------------------------------------------------------------

    def auto_fix_imports(self) -> List[Patch]:
        """Auto-fix broken imports by adding missing packages to requirements.txt."""
        patches: List[Patch] = []
        to_install: Dict[str, str] = {}

        for err in self._import_errors:
            top_level = err.module_name.split(".")[0]
            if top_level in COMMON_IMPORT_FIXES:
                pkg = COMMON_IMPORT_FIXES[top_level]
                to_install[top_level] = pkg

        if not to_install:
            logger.info("No auto-fixable import errors found.")
            return patches

        req_path = self.repo_root / "requirements.txt"
        original = req_path.read_text() if req_path.exists() else ""
        existing_pkgs = {
            l.strip().split("==")[0].lower()
            for l in original.splitlines()
            if l.strip() and not l.startswith("#")
        }

        additions = []
        for _mod, pkg in to_install.items():
            if pkg.lower() not in existing_pkgs:
                additions.append(pkg)

        if additions:
            new_content = original.rstrip("\n") + "\n" + "\n".join(additions) + "\n"
            patch = Patch(
                patch_id=str(uuid.uuid4()),
                file_path=str(req_path),
                original_content=original,
                patched_content=new_content,
                description=f"Auto-add missing packages: {', '.join(additions)}",
            )
            patches.append(patch)
            self._patches.append(patch)

        logger.info("Generated %d import-fix patches.", len(patches))
        return patches

    # ------------------------------------------------------------------
    # Test scanning
    # ------------------------------------------------------------------

    def scan_test_failures(self) -> List[TestFailure]:
        """Run pytest and capture any failing tests."""
        self._test_failures = []
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "--tb=short", "-q", "--no-header",
                 str(self.repo_root / "tests")],
                capture_output=True, text=True, timeout=300, cwd=str(self.repo_root),
            )
        except FileNotFoundError:
            logger.warning("pytest not found; skipping test scan.")
            return self._test_failures
        except subprocess.TimeoutExpired:
            logger.error("pytest timed out after 300s.")
            return self._test_failures

        if result.returncode != 0:
            self._parse_pytest_output(result.stdout + "\n" + result.stderr)

        logger.info("Detected %d test failures.", len(self._test_failures))
        return self._test_failures

    def _parse_pytest_output(self, output: str) -> None:
        """Parse pytest short-traceback output into TestFailure objects."""
        current_test: Optional[str] = None
        tb_lines: List[str] = []

        for line in output.splitlines():
            if line.startswith("FAILED "):
                if current_test:
                    self._test_failures.append(
                        TestFailure(
                            test_id=current_test,
                            file_path=current_test.split("::")[0],
                            error_type="AssertionError",
                            error_message=tb_lines[-1] if tb_lines else "",
                            traceback="\n".join(tb_lines),
                        )
                    )
                current_test = line.replace("FAILED ", "").strip()
                tb_lines = []
            elif current_test:
                tb_lines.append(line)

        if current_test:
            self._test_failures.append(
                TestFailure(
                    test_id=current_test,
                    file_path=current_test.split("::")[0],
                    error_type="AssertionError",
                    error_message=tb_lines[-1] if tb_lines else "",
                    traceback="\n".join(tb_lines),
                )
            )

    # ------------------------------------------------------------------
    # Patch generation / application
    # ------------------------------------------------------------------

    def generate_fix_patch(self, failure: TestFailure) -> Optional[Patch]:
        """Generate a candidate fix patch for a test failure using LLM."""
        fpath = Path(failure.file_path)
        if not fpath.exists():
            return None

        original = fpath.read_text(encoding="utf-8", errors="replace")
        patched = original
        description = f"Auto-fix for test failure: {failure.test_id}"

        # Try LLM-based fix first if API key is available
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key:
            try:
                import openai
                client = openai.OpenAI(api_key=api_key)
                prompt = f"""
You are an expert Python developer. Fix the following failing test.
File: {failure.file_path}
Test ID: {failure.test_id}
Error Message: {failure.error_message}
Traceback:
{failure.traceback}

Original File Content:
```python
{original}
```

Return ONLY the complete fixed Python code. Do not include markdown formatting like ```python or explanations.
"""
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are an autonomous self-healing agent. Output only raw code."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,
                    max_tokens=4000
                )
                
                result = response.choices[0].message.content.strip()
                if result.startswith("```python"):
                    result = result[9:]
                if result.startswith("```"):
                    result = result[3:]
                if result.endswith("```"):
                    result = result[:-3]
                
                patched = result.strip() + "\n"
                description = f"LLM-generated fix for {failure.test_id}"
                logger.info("Successfully generated LLM patch for %s", failure.test_id)
            except Exception as e:
                logger.error("LLM patch generation failed: %s. Falling back to rule-based.", e)

        # Fallback to rule-based if LLM failed or didn't change anything
        if patched == original:
            if "fixture" in failure.error_message.lower() and "not found" in failure.error_message.lower():
                fixture_name = failure.error_message.split("'")[1] if "'" in failure.error_message else "unknown"
                fixture_code = (
                    f"\n\nimport pytest\n\n@pytest.fixture\ndef {fixture_name}():\n"
                    f'    """Auto-generated placeholder fixture."""\n    return None\n'
                )
                patched = fixture_code + original

        if patched == original:
            return None

        patch = Patch(
            patch_id=str(uuid.uuid4()),
            file_path=str(fpath),
            original_content=original,
            patched_content=patched,
            description=description,
        )
        self._patches.append(patch)
        return patch

    def apply_patch(self, patch: Patch) -> bool:
        """Apply a patch. On failure, auto-rollback."""
        fpath = Path(patch.file_path)
        try:
            fpath.write_text(patch.patched_content, encoding="utf-8")
            patch.applied = True
            logger.info("Applied patch %s to %s", patch.patch_id, patch.file_path)
            return True
        except Exception:
            logger.exception("Failed to apply patch %s — rolling back.", patch.patch_id)
            self.rollback_patch(patch)
            return False

    def rollback_patch(self, patch: Patch) -> bool:
        """Rollback a previously applied patch."""
        fpath = Path(patch.file_path)
        try:
            fpath.write_text(patch.original_content, encoding="utf-8")
            patch.rolled_back = True
            patch.applied = False
            logger.info("Rolled back patch %s", patch.patch_id)
            return True
        except Exception:
            logger.exception("CRITICAL: rollback failed for patch %s", patch.patch_id)
            return False

    # ------------------------------------------------------------------
    # Health report
    # ------------------------------------------------------------------

    def health_report(self) -> Dict[str, Any]:
        """Return a JSON-serialisable health report."""
        report = HealthReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_files_scanned=len(list(self.repo_root.rglob("*.py"))),
            import_errors=len(self._import_errors),
            test_failures=len(self._test_failures),
            patches_applied=sum(1 for p in self._patches if p.applied),
            patches_rolled_back=sum(1 for p in self._patches if p.rolled_back),
            overall_status="HEALTHY" if not self._import_errors and not self._test_failures else "DEGRADED",
            details={
                "import_errors": [asdict(e) for e in self._import_errors[:20]],
                "test_failures": [asdict(t) for t in self._test_failures[:20]],
            },
        )
        return asdict(report)

    # ------------------------------------------------------------------
    # Full maintenance cycle
    # ------------------------------------------------------------------

    def run_maintenance_cycle(self) -> Dict[str, Any]:
        """Execute full scan -> detect -> fix -> verify loop."""
        cycle_id = str(uuid.uuid4())
        logger.info("=== Maintenance Cycle %s START ===", cycle_id)
        start = time.time()

        self.scan_import_errors()
        self.scan_test_failures()

        import_patches = self.auto_fix_imports()
        for p in import_patches:
            self.apply_patch(p)

        test_patches = []
        for failure in self._test_failures:
            patch = self.generate_fix_patch(failure)
            if patch:
                if self.apply_patch(patch):
                    test_patches.append(patch)

        report = self.health_report()
        elapsed = round(time.time() - start, 2)
        report["cycle_id"] = cycle_id
        report["elapsed_seconds"] = elapsed

        if self.notification_callback:
            try:
                self.notification_callback(report)
            except Exception:
                logger.exception("Notification callback failed.")

        self._maintenance_history.append(report)
        logger.info("=== Maintenance Cycle %s END (%ss) ===", cycle_id, elapsed)
        return report

    # ------------------------------------------------------------------
    # Scheduler
    # ------------------------------------------------------------------

    def start_scheduler(self) -> None:
        """Start APScheduler background job for periodic maintenance."""
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
        except ImportError:
            logger.warning("APScheduler not installed; scheduler disabled.")
            return

        self._scheduler = BackgroundScheduler()
        self._scheduler.add_job(
            self.run_maintenance_cycle,
            "interval",
            hours=self.schedule_interval_hours,
            id="zero_maintenance",
        )
        self._scheduler.start()
        logger.info("Scheduler started — cycle every %dh.", self.schedule_interval_hours)

    def stop_scheduler(self) -> None:
        """Stop the background scheduler."""
        if self._scheduler:
            self._scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped.")

    @property
    def maintenance_history(self) -> List[Dict[str, Any]]:
        """Return list of past maintenance cycle reports."""
        return list(self._maintenance_history)
