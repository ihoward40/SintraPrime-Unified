"""Tests for Agent Zero — Self-healing autonomous maintenance agent."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# We test in isolation by importing the modules directly
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.zero.zero_agent import (
    ZeroAgent,
    ImportError_,
    TestFailure,
    Patch,
    HealthReport,
    COMMON_IMPORT_FIXES,
)
from agents.zero.health_monitor import (
    HealthMonitor,
    HealthSnapshot,
    Alert,
)


# ── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def tmp_repo(tmp_path):
    """Create a temporary repo structure."""
    (tmp_path / "tests").mkdir()
    (tmp_path / "requirements.txt").write_text("requests\nflask\n")
    # A valid Python file
    (tmp_path / "main.py").write_text("import os\nimport sys\nprint('hello')\n")
    # A file with a broken import
    (tmp_path / "broken.py").write_text("import nonexistent_module_xyz\n")
    return tmp_path


@pytest.fixture
def zero_agent(tmp_repo):
    """Create a ZeroAgent for the temp repo."""
    return ZeroAgent(repo_root=str(tmp_repo))


@pytest.fixture
def health_monitor(tmp_path):
    """Create a HealthMonitor with temp DB."""
    db_path = str(tmp_path / "health.db")
    return HealthMonitor(repo_root=str(tmp_path), db_path=db_path)


# ── ZeroAgent Tests ───────────────────────────────────────────────


class TestZeroAgentInit:
    def test_init_default(self):
        agent = ZeroAgent()
        assert agent.repo_root == Path.cwd()
        assert agent.schedule_interval_hours == 6

    def test_init_custom_root(self, tmp_repo):
        agent = ZeroAgent(repo_root=str(tmp_repo))
        assert agent.repo_root == tmp_repo

    def test_init_with_callback(self, tmp_repo):
        cb = MagicMock()
        agent = ZeroAgent(repo_root=str(tmp_repo), notification_callback=cb)
        assert agent.notification_callback is cb

    def test_init_custom_interval(self, tmp_repo):
        agent = ZeroAgent(repo_root=str(tmp_repo), schedule_interval_hours=12)
        assert agent.schedule_interval_hours == 12


class TestScanImportErrors:
    def test_finds_broken_imports(self, zero_agent):
        errors = zero_agent.scan_import_errors()
        broken = [e for e in errors if "nonexistent_module_xyz" in e.module_name]
        assert len(broken) >= 1

    def test_valid_imports_no_errors(self, tmp_path):
        (tmp_path / "valid.py").write_text("import os\nimport sys\n")
        agent = ZeroAgent(repo_root=str(tmp_path))
        errors = agent.scan_import_errors()
        assert all("os" not in e.module_name for e in errors)

    def test_syntax_error_detection(self, tmp_path):
        (tmp_path / "bad_syntax.py").write_text("def foo(\n")
        agent = ZeroAgent(repo_root=str(tmp_path))
        errors = agent.scan_import_errors()
        syntax_errors = [e for e in errors if e.module_name == "<syntax-error>"]
        assert len(syntax_errors) >= 1

    def test_skips_venv(self, tmp_path):
        venv = tmp_path / ".venv" / "lib"
        venv.mkdir(parents=True)
        (venv / "bad.py").write_text("import totally_fake_pkg\n")
        agent = ZeroAgent(repo_root=str(tmp_path))
        errors = agent.scan_import_errors()
        assert all(".venv" not in e.file_path for e in errors)

    def test_suggested_fix(self, tmp_path):
        (tmp_path / "use_yaml.py").write_text("import yaml\n")
        agent = ZeroAgent(repo_root=str(tmp_path))
        errors = agent.scan_import_errors()
        yaml_errors = [e for e in errors if e.module_name == "yaml"]
        if yaml_errors:
            assert yaml_errors[0].suggested_fix == "pip install pyyaml"


class TestAutoFixImports:
    def test_generates_patches(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("flask\n")
        (tmp_path / "app.py").write_text("import yaml\n")
        agent = ZeroAgent(repo_root=str(tmp_path))
        agent.scan_import_errors()
        patches = agent.auto_fix_imports()
        if any(e.module_name == "yaml" for e in agent._import_errors):
            assert len(patches) >= 1
            assert "pyyaml" in patches[0].patched_content

    def test_no_duplicates(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("pyyaml\n")
        (tmp_path / "app.py").write_text("import yaml\n")
        agent = ZeroAgent(repo_root=str(tmp_path))
        agent.scan_import_errors()
        patches = agent.auto_fix_imports()
        for p in patches:
            assert p.patched_content.count("pyyaml") <= 1

    def test_no_patches_when_clean(self, tmp_path):
        (tmp_path / "app.py").write_text("import os\n")
        agent = ZeroAgent(repo_root=str(tmp_path))
        agent.scan_import_errors()
        patches = agent.auto_fix_imports()
        assert len(patches) == 0


class TestPatchOperations:
    def test_apply_patch(self, tmp_path):
        f = tmp_path / "target.py"
        f.write_text("old content")
        patch = Patch(
            patch_id="test-1", file_path=str(f),
            original_content="old content", patched_content="new content",
            description="test patch",
        )
        agent = ZeroAgent(repo_root=str(tmp_path))
        assert agent.apply_patch(patch) is True
        assert f.read_text() == "new content"
        assert patch.applied is True

    def test_rollback_patch(self, tmp_path):
        f = tmp_path / "target.py"
        f.write_text("new content")
        patch = Patch(
            patch_id="test-2", file_path=str(f),
            original_content="old content", patched_content="new content",
            description="test patch", applied=True,
        )
        agent = ZeroAgent(repo_root=str(tmp_path))
        assert agent.rollback_patch(patch) is True
        assert f.read_text() == "old content"
        assert patch.rolled_back is True

    def test_generate_fix_patch_missing_file(self, tmp_path):
        agent = ZeroAgent(repo_root=str(tmp_path))
        failure = TestFailure(
            test_id="test::missing", file_path="/nonexistent.py",
            error_type="FileNotFoundError", error_message="not found", traceback="",
        )
        assert agent.generate_fix_patch(failure) is None


class TestHealthReport:
    def test_healthy_report(self, tmp_path):
        (tmp_path / "ok.py").write_text("x = 1\n")
        agent = ZeroAgent(repo_root=str(tmp_path))
        report = agent.health_report()
        assert report["overall_status"] == "HEALTHY"
        assert report["import_errors"] == 0

    def test_degraded_report(self, zero_agent):
        zero_agent.scan_import_errors()
        report = zero_agent.health_report()
        if zero_agent._import_errors:
            assert report["overall_status"] == "DEGRADED"

    def test_report_json_serializable(self, zero_agent):
        report = zero_agent.health_report()
        json.dumps(report)  # should not raise


class TestMaintenanceCycle:
    def test_cycle_returns_report(self, tmp_path):
        (tmp_path / "tests").mkdir(exist_ok=True)
        (tmp_path / "ok.py").write_text("x = 1\n")
        agent = ZeroAgent(repo_root=str(tmp_path))
        report = agent.run_maintenance_cycle()
        assert "cycle_id" in report
        assert "elapsed_seconds" in report

    def test_cycle_records_history(self, tmp_path):
        (tmp_path / "tests").mkdir(exist_ok=True)
        agent = ZeroAgent(repo_root=str(tmp_path))
        agent.run_maintenance_cycle()
        assert len(agent.maintenance_history) == 1

    def test_notification_callback_called(self, tmp_path):
        (tmp_path / "tests").mkdir(exist_ok=True)
        cb = MagicMock()
        agent = ZeroAgent(repo_root=str(tmp_path), notification_callback=cb)
        agent.run_maintenance_cycle()
        cb.assert_called_once()


class TestScheduler:
    def test_start_without_apscheduler(self, tmp_path):
        agent = ZeroAgent(repo_root=str(tmp_path))
        # Should not raise even if APScheduler is not installed
        agent.start_scheduler()

    def test_stop_without_start(self, tmp_path):
        agent = ZeroAgent(repo_root=str(tmp_path))
        agent.stop_scheduler()  # should not raise


# ── HealthMonitor Tests ───────────────────────────────────────────


class TestHealthMonitorInit:
    def test_creates_db(self, health_monitor):
        assert os.path.exists(health_monitor.db_path)

    def test_custom_db_path(self, tmp_path):
        db = str(tmp_path / "custom" / "test.db")
        hm = HealthMonitor(db_path=db)
        assert os.path.exists(db)


class TestHealthSnapshot:
    def test_capture_returns_snapshot(self, health_monitor):
        snap = health_monitor.capture_snapshot()
        assert isinstance(snap, HealthSnapshot)
        assert snap.pass_rate >= 0.0

    def test_dashboard_empty(self, health_monitor):
        dash = health_monitor.generate_health_dashboard()
        assert "generated_at" in dash
        assert "trend" in dash


class TestAlerts:
    def test_no_alert_when_healthy(self, health_monitor):
        alert = health_monitor.alert_on_degradation(threshold=0.95)
        # No snapshots yet, so None
        assert alert is None

    def test_acknowledge_nonexistent(self, health_monitor):
        assert health_monitor.acknowledge_alert(9999) is False

    def test_alert_callback(self, tmp_path):
        cb = MagicMock()
        hm = HealthMonitor(db_path=str(tmp_path / "h.db"), alert_callback=cb)
        # Insert a low pass rate snapshot
        conn = hm._connect()
        conn.execute(
            "INSERT INTO health_snapshots (timestamp, total_tests, passed_tests, failed_tests, skipped_tests, pass_rate) VALUES (?,?,?,?,?,?)",
            ("2025-01-01T00:00:00Z", 10, 5, 5, 0, 0.5),
        )
        conn.commit()
        conn.close()
        alert = hm.alert_on_degradation(threshold=0.95)
        assert alert is not None
        assert alert.severity == "HIGH"
        cb.assert_called_once()


class TestDependencyDrift:
    def test_returns_list(self, health_monitor):
        result = health_monitor.check_dependency_drift()
        assert isinstance(result, list)


class TestSecurityVulns:
    def test_returns_list(self, health_monitor):
        result = health_monitor.check_security_vulnerabilities()
        assert isinstance(result, list)
