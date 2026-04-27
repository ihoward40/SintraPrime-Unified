"""Phase 17A — Cross-Stack Integration Tests (60 tests)."""
import pytest
from phase17.integration_tests.cross_stack import (
    IntegrationStatus, IntegrationResult, IntegrationReport,
    IntegrationTestRegistry, build_sintra_integration_suite,
)


# ─────────────────────────────────────────────────────────────
# IntegrationResult tests (10)
# ─────────────────────────────────────────────────────────────
class TestIntegrationResult:
    def test_result_has_test_id(self):
        r = IntegrationResult("t1", "test", IntegrationStatus.PASS, 5.0, "src", "tgt")
        assert r.test_id == "t1"

    def test_result_pass_status(self):
        r = IntegrationResult("t1", "test", IntegrationStatus.PASS, 5.0, "src", "tgt")
        assert r.status == IntegrationStatus.PASS

    def test_result_fail_status(self):
        r = IntegrationResult("t1", "test", IntegrationStatus.FAIL, 5.0, "src", "tgt")
        assert r.status == IntegrationStatus.FAIL

    def test_result_duration(self):
        r = IntegrationResult("t1", "test", IntegrationStatus.PASS, 12.5, "src", "tgt")
        assert r.duration_ms == 12.5

    def test_result_source_module(self):
        r = IntegrationResult("t1", "test", IntegrationStatus.PASS, 5.0, "phase16.moe_router", "parl")
        assert r.source_module == "phase16.moe_router"

    def test_result_target_module(self):
        r = IntegrationResult("t1", "test", IntegrationStatus.PASS, 5.0, "src", "phase16.stripe_billing")
        assert r.target_module == "phase16.stripe_billing"

    def test_result_error_none_on_pass(self):
        r = IntegrationResult("t1", "test", IntegrationStatus.PASS, 5.0, "src", "tgt")
        assert r.error is None

    def test_result_error_on_fail(self):
        r = IntegrationResult("t1", "test", IntegrationStatus.FAIL, 5.0, "src", "tgt",
                              error="Connection refused")
        assert r.error == "Connection refused"

    def test_result_payload(self):
        r = IntegrationResult("t1", "test", IntegrationStatus.PASS, 5.0, "src", "tgt",
                              payload={"key": "value"})
        assert r.payload["key"] == "value"

    def test_result_timestamp_set(self):
        r = IntegrationResult("t1", "test", IntegrationStatus.PASS, 5.0, "src", "tgt")
        assert r.timestamp > 0


# ─────────────────────────────────────────────────────────────
# IntegrationReport tests (15)
# ─────────────────────────────────────────────────────────────
class TestIntegrationReport:
    def _make_report(self, statuses):
        r = IntegrationReport()
        for i, s in enumerate(statuses):
            r.results.append(IntegrationResult(
                f"t{i}", f"test_{i}", s, 1.0, "src", "tgt"
            ))
        return r

    def test_report_id_prefix(self):
        r = IntegrationReport()
        assert r.report_id.startswith("rep_")

    def test_total_count(self):
        r = self._make_report([IntegrationStatus.PASS] * 5)
        assert r.total == 5

    def test_passed_count(self):
        r = self._make_report([IntegrationStatus.PASS, IntegrationStatus.PASS, IntegrationStatus.FAIL])
        assert r.passed == 2

    def test_failed_count(self):
        r = self._make_report([IntegrationStatus.PASS, IntegrationStatus.FAIL, IntegrationStatus.FAIL])
        assert r.failed == 2

    def test_pass_rate_all_pass(self):
        r = self._make_report([IntegrationStatus.PASS] * 4)
        assert r.pass_rate == 1.0

    def test_pass_rate_all_fail(self):
        r = self._make_report([IntegrationStatus.FAIL] * 4)
        assert r.pass_rate == 0.0

    def test_pass_rate_mixed(self):
        r = self._make_report([IntegrationStatus.PASS, IntegrationStatus.FAIL])
        assert r.pass_rate == 0.5

    def test_pass_rate_empty(self):
        r = IntegrationReport()
        assert r.pass_rate == 0.0

    def test_summary_keys(self):
        r = self._make_report([IntegrationStatus.PASS])
        s = r.summary()
        assert "total" in s
        assert "passed" in s
        assert "failed" in s
        assert "pass_rate" in s

    def test_summary_report_id(self):
        r = IntegrationReport()
        s = r.summary()
        assert s["report_id"] == r.report_id

    def test_summary_total_matches(self):
        r = self._make_report([IntegrationStatus.PASS] * 3)
        assert r.summary()["total"] == 3

    def test_summary_passed_matches(self):
        r = self._make_report([IntegrationStatus.PASS, IntegrationStatus.FAIL])
        assert r.summary()["passed"] == 1

    def test_summary_failed_matches(self):
        r = self._make_report([IntegrationStatus.PASS, IntegrationStatus.FAIL])
        assert r.summary()["failed"] == 1

    def test_started_at_set(self):
        r = IntegrationReport()
        assert r.started_at > 0

    def test_finished_at_none_initially(self):
        r = IntegrationReport()
        assert r.finished_at is None


# ─────────────────────────────────────────────────────────────
# IntegrationTestRegistry tests (15)
# ─────────────────────────────────────────────────────────────
class TestIntegrationTestRegistry:
    def test_register_increments_count(self):
        reg = IntegrationTestRegistry()
        reg.register("t1", "src", "tgt", lambda: {})
        assert reg.test_count == 1

    def test_register_multiple(self):
        reg = IntegrationTestRegistry()
        for i in range(5):
            reg.register(f"t{i}", "src", "tgt", lambda: {})
        assert reg.test_count == 5

    def test_run_all_returns_report(self):
        reg = IntegrationTestRegistry()
        reg.register("t1", "src", "tgt", lambda: {"ok": True})
        report = reg.run_all()
        assert isinstance(report, IntegrationReport)

    def test_run_all_pass(self):
        reg = IntegrationTestRegistry()
        reg.register("t1", "src", "tgt", lambda: {"ok": True})
        report = reg.run_all()
        assert report.passed == 1

    def test_run_all_fail_on_exception(self):
        reg = IntegrationTestRegistry()
        def bad():
            raise RuntimeError("connection failed")
        reg.register("t1", "src", "tgt", bad)
        report = reg.run_all()
        assert report.failed == 1

    def test_run_all_fail_stores_error(self):
        reg = IntegrationTestRegistry()
        def bad():
            raise ValueError("bad value")
        reg.register("t1", "src", "tgt", bad)
        report = reg.run_all()
        assert "bad value" in report.results[0].error

    def test_run_all_duration_positive(self):
        reg = IntegrationTestRegistry()
        reg.register("t1", "src", "tgt", lambda: {})
        report = reg.run_all()
        assert report.results[0].duration_ms >= 0

    def test_run_all_finished_at_set(self):
        reg = IntegrationTestRegistry()
        reg.register("t1", "src", "tgt", lambda: {})
        report = reg.run_all()
        assert report.finished_at is not None

    def test_run_all_result_ids_unique(self):
        reg = IntegrationTestRegistry()
        for i in range(5):
            reg.register(f"t{i}", "src", "tgt", lambda: {})
        report = reg.run_all()
        ids = [r.test_id for r in report.results]
        assert len(ids) == len(set(ids))

    def test_run_by_source(self):
        reg = IntegrationTestRegistry()
        reg.register("t1", "module_a", "tgt", lambda: {})
        reg.register("t2", "module_b", "tgt", lambda: {})
        report = reg.run_by_source("module_a")
        assert report.total == 1

    def test_run_by_target(self):
        reg = IntegrationTestRegistry()
        reg.register("t1", "src", "module_x", lambda: {})
        reg.register("t2", "src", "module_y", lambda: {})
        report = reg.run_by_target("module_x")
        assert report.total == 1

    def test_run_by_source_empty(self):
        reg = IntegrationTestRegistry()
        reg.register("t1", "module_a", "tgt", lambda: {})
        report = reg.run_by_source("nonexistent")
        assert report.total == 0

    def test_run_all_payload_stored(self):
        reg = IntegrationTestRegistry()
        reg.register("t1", "src", "tgt", lambda: {"key": "val"})
        report = reg.run_all()
        assert report.results[0].payload.get("key") == "val"

    def test_run_all_source_stored(self):
        reg = IntegrationTestRegistry()
        reg.register("t1", "my_source", "tgt", lambda: {})
        report = reg.run_all()
        assert report.results[0].source_module == "my_source"

    def test_run_all_target_stored(self):
        reg = IntegrationTestRegistry()
        reg.register("t1", "src", "my_target", lambda: {})
        report = reg.run_all()
        assert report.results[0].target_module == "my_target"


# ─────────────────────────────────────────────────────────────
# Full SintraPrime integration suite tests (20)
# ─────────────────────────────────────────────────────────────
class TestSintraIntegrationSuite:
    @pytest.fixture(scope="class")
    def suite(self):
        return build_sintra_integration_suite()

    @pytest.fixture(scope="class")
    def report(self, suite):
        return suite.run_all()

    def test_suite_has_tests(self, suite):
        assert suite.test_count >= 10

    def test_report_total_matches_suite(self, suite, report):
        assert report.total == suite.test_count

    def test_all_tests_pass(self, report):
        failures = [r for r in report.results if r.status == IntegrationStatus.FAIL]
        if failures:
            msgs = [f"{r.name}: {r.error}" for r in failures]
            pytest.fail("Integration failures:\n" + "\n".join(msgs))

    def test_pass_rate_100(self, report):
        assert report.pass_rate == 1.0

    def test_moe_to_parl_present(self, suite):
        names = [t["name"] for t in suite._tests]
        assert "moe_router→parl_orchestrator" in names

    def test_billing_to_tenant_present(self, suite):
        names = [t["name"] for t in suite._tests]
        assert "stripe_billing→multi_tenant" in names

    def test_redline_to_crm_present(self, suite):
        names = [t["name"] for t in suite._tests]
        assert "contract_redline→airtable_crm" in names

    def test_analytics_to_parl_present(self, suite):
        names = [t["name"] for t in suite._tests]
        assert "advanced_analytics→parl_reward" in names

    def test_mobile_to_billing_present(self, suite):
        names = [t["name"] for t in suite._tests]
        assert "mobile_app→stripe_billing" in names

    def test_parl_to_chat_present(self, suite):
        names = [t["name"] for t in suite._tests]
        assert "parl_core→chat_agent" in names

    def test_moe_to_redline_present(self, suite):
        names = [t["name"] for t in suite._tests]
        assert "moe_router→contract_redline" in names

    def test_tenant_to_analytics_present(self, suite):
        names = [t["name"] for t in suite._tests]
        assert "multi_tenant→advanced_analytics" in names

    def test_parl_to_moe_present(self, suite):
        names = [t["name"] for t in suite._tests]
        assert "parl_orchestrator→moe_router" in names

    def test_billing_to_analytics_present(self, suite):
        names = [t["name"] for t in suite._tests]
        assert "stripe_billing→advanced_analytics" in names

    def test_all_results_have_ids(self, report):
        assert all(r.test_id.startswith("int_") for r in report.results)

    def test_all_results_have_duration(self, report):
        assert all(r.duration_ms >= 0 for r in report.results)

    def test_report_finished_at_set(self, report):
        assert report.finished_at is not None

    def test_run_by_source_moe(self, suite):
        sub = suite.run_by_source("phase16.moe_router")
        assert sub.total >= 2

    def test_run_by_target_analytics(self, suite):
        sub = suite.run_by_target("phase16.advanced_analytics")
        assert sub.total >= 2

    def test_summary_pass_rate_1(self, report):
        assert report.summary()["pass_rate"] == 1.0

    def test_summary_total_positive(self, report):
        assert report.summary()["total"] > 0
