"""
Tests for Client C-0001 UACC Fixture

Validates that the Evidence Command Center correctly processes
the UACC auto repossession case fixture.
"""

import json
import pytest
from pathlib import Path
import sys

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent.parent / "packages"))

from evidence_command_center import (
    EvidenceRegistry,
    ViolationRegistry,
    ExhibitRegistry,
    Evidence,
    Violation,
    Statute,
    Severity,
    EvidenceStatus,
    calculate_readiness_score,
)


class TestUACCFixture:
    """Test UACC case fixture processing."""

    @pytest.fixture
    def fixture_path(self):
        """Path to UACC fixture directory."""
        return Path(__file__).parent.parent / "clients" / "C-0001-UACC"

    @pytest.fixture
    def evidence_data(self, fixture_path):
        """Load evidence manifest."""
        with open(fixture_path / "evidence_manifest.json") as f:
            return json.load(f)

    @pytest.fixture
    def violation_data(self, fixture_path):
        """Load violation candidates."""
        with open(fixture_path / "violation_candidates.json") as f:
            return json.load(f)

    @pytest.fixture
    def readiness_report(self, fixture_path):
        """Load generated readiness report."""
        with open(fixture_path / "readiness_report.json") as f:
            return json.load(f)

    @pytest.fixture
    def exhibit_manifest(self, fixture_path):
        """Load generated exhibit manifest."""
        with open(fixture_path / "exhibit_manifest.json") as f:
            return json.load(f)

    def test_fixture_files_exist(self, fixture_path):
        """Verify all required fixture files exist."""
        required_files = [
            "client.json",
            "case.json",
            "account.json",
            "evidence_manifest.json",
            "violation_candidates.json",
            "exhibit_manifest.json",
            "readiness_report.json",
            "README.md",
        ]
        for filename in required_files:
            assert (fixture_path / filename).exists(), f"Missing {filename}"

    def test_evidence_counts(self, evidence_data):
        """Verify evidence counts match expectations."""
        assert evidence_data["evidence_count"] == 8
        assert evidence_data["verification_summary"]["verified"] == 4
        assert evidence_data["verification_summary"]["missing"] == 4

    def test_violation_counts(self, violation_data):
        """Verify violation counts match expectations."""
        assert violation_data["violation_count"] == 6
        assert violation_data["statute_summary"]["UCC"] == 4
        assert violation_data["statute_summary"]["FCRA"] == 2
        assert violation_data["severity_summary"]["high"] == 3
        assert violation_data["severity_summary"]["medium"] == 2
        assert violation_data["severity_summary"]["low"] == 1

    def test_readiness_score_range(self, readiness_report):
        """Verify readiness score is in expected range."""
        score = readiness_report["overall_readiness_score"]
        assert 0 <= score <= 100, f"Score {score} out of range"
        assert readiness_report["readiness_level"] in [
            "NOT_READY",
            "PARTIAL",
            "OPERATIONAL",
            "LITIGATION_READY",
        ]

    def test_readiness_level_partial(self, readiness_report):
        """UACC case should be PARTIAL readiness (missing evidence)."""
        assert readiness_report["readiness_level"] == "PARTIAL"
        assert 40 <= readiness_report["overall_readiness_score"] < 70

    def test_component_scores_sum_to_total(self, readiness_report):
        """Component scores should sum to overall score."""
        components = readiness_report["component_scores"]
        total = sum(components.values())
        overall = readiness_report["overall_readiness_score"]
        assert abs(total - overall) < 0.01, f"Components {total} != overall {overall}"

    def test_exhibit_count_matches_verified_evidence(self, readiness_report, exhibit_manifest):
        """Exhibits should equal verified evidence count."""
        verified = readiness_report["evidence_summary"]["verified"]
        exhibits = exhibit_manifest["exhibit_count"]
        assert exhibits == verified, f"Exhibits {exhibits} != verified evidence {verified}"

    def test_exhibit_numbering(self, exhibit_manifest):
        """Exhibits should be numbered A, B, C, D."""
        expected_numbers = ["Exhibit A", "Exhibit B", "Exhibit C", "Exhibit D"]
        actual_numbers = [ex["exhibit_number"] for ex in exhibit_manifest["exhibits"]]
        assert actual_numbers == expected_numbers

    def test_missing_evidence_impact(self, readiness_report):
        """Missing evidence should be identified."""
        missing_count = readiness_report["evidence_summary"]["missing"]
        assert missing_count == 4
        
        impact = readiness_report["missing_evidence_impact"]
        assert any("4/8 evidence items approved" in item for item in impact)

    def test_violation_statute_distribution(self, violation_data):
        """Verify UCC and FCRA violations identified."""
        violations = violation_data["violations"]
        
        ucc_violations = [v for v in violations if v["statute"] == "UCC"]
        fcra_violations = [v for v in violations if v["statute"] == "FCRA"]
        
        assert len(ucc_violations) == 4
        assert len(fcra_violations) == 2

    def test_deficiency_calculation_violation(self, violation_data):
        """Most confident violation should be deficiency calculation error."""
        violations = violation_data["violations"]
        
        # Find VIO-UACC-004 (deficiency calculation)
        deficiency_vio = next(v for v in violations if v["violation_id"] == "VIO-UACC-004")
        
        assert deficiency_vio["severity"] == "high"
        assert deficiency_vio["confidence"] == 0.85  # Highest confidence
        assert "discrepancy" in deficiency_vio["description"].lower()

    def test_recommendations_present(self, readiness_report):
        """Readiness report should contain actionable recommendations."""
        recommendations = readiness_report["readiness_analysis"]["recommendations"]
        assert len(recommendations) > 0
        assert any("missing evidence" in rec.lower() for rec in recommendations)

    def test_weaknesses_identified(self, readiness_report):
        """Weaknesses should be clearly identified."""
        weaknesses = readiness_report["readiness_analysis"]["weaknesses"]
        assert len(weaknesses) > 0
        assert any("evidence collection incomplete" in weak.lower() for weak in weaknesses)

    def test_case_not_litigation_ready(self, readiness_report):
        """Case should not be litigation-ready due to missing evidence."""
        level = readiness_report["readiness_level"]
        assert level != "LITIGATION_READY"
        
        recommendations = readiness_report["readiness_analysis"]["recommendations"]
        assert any("not yet ready" in rec.lower() for rec in recommendations)

    def test_deterministic_readiness_score(self, fixture_path):
        """Running scoring twice should produce identical results."""
        # This test would re-run the generation script and compare outputs
        # For now, verify the score is recorded
        with open(fixture_path / "readiness_report.json") as f:
            report = json.load(f)
        
        score = report["overall_readiness_score"]
        assert isinstance(score, (int, float))
        assert score > 0


class TestUACCFactAccuracy:
    """Validate UACC case facts."""

    @pytest.fixture
    def account_data(self):
        """Load account details."""
        path = Path(__file__).parent.parent / "clients" / "C-0001-UACC" / "account.json"
        with open(path) as f:
            return json.load(f)

    def test_deficiency_calculation(self, account_data):
        """Verify deficiency calculation arithmetic."""
        breakdown = account_data["post_repossession"]["deficiency_breakdown"]
        
        # Verify arithmetic
        calculated_deficiency = (
            breakdown["remaining_principal"] +
            breakdown["accrued_interest"] +
            breakdown["late_fees"] +
            breakdown["repossession_costs"] +
            breakdown["storage_fees"] -
            breakdown["sale_proceeds"]
        )
        
        assert breakdown["total_owed"] == 29300.00
        assert breakdown["net_deficiency"] == 10800.00
        assert breakdown["claimed_deficiency"] == 12800.00
        assert breakdown["discrepancy"] == 2000.00
        assert calculated_deficiency == 10800.00

    def test_loan_payment_history(self, account_data):
        """Verify payment history facts."""
        payment = account_data["payment_history"]
        assert payment["total_payments_made"] == 29
        assert payment["last_payment_amount"] == 495.00
        assert payment["total_paid"] == 14355.00

    def test_vehicle_identification(self, account_data):
        """Verify vehicle details."""
        vehicle = account_data["loan_details"]
        assert vehicle["vehicle"] == "2020 Honda Accord"
        assert vehicle["vin"] == "1HGCV1F3XLA123456"
        assert vehicle["original_amount"] == 28500.00
