"""
Tests for BRA CCS Scorer — BGS-01 compliance.
"""
import pytest

from blackstone.bra.ccs import CCS_WEIGHTS, CCSScorer


@pytest.fixture
def scorer():
    return CCSScorer()


def _dims(**overrides) -> dict:
    """Build a valid full dimension set with a given base value, with overrides."""
    base = overrides.pop("_base", 80.0)
    dims = dict.fromkeys(CCS_WEIGHTS, base)
    dims.update(overrides)
    return dims


class TestWeights:
    def test_weights_sum_to_one(self):
        total = sum(CCS_WEIGHTS.values())
        assert abs(total - 1.0) < 1e-9

    def test_citation_integrity_is_heaviest(self):
        assert CCS_WEIGHTS["citation_integrity"] == 0.20

    def test_provenance_is_second(self):
        assert CCS_WEIGHTS["provenance_completeness"] == 0.18


class TestScoring:
    def test_all_hundred_gives_hundred(self, scorer):
        dims = _dims(_base=100.0)
        result = scorer.score(dims)
        assert result.total == 100.0

    def test_all_zero_gives_zero(self, scorer):
        dims = _dims(_base=0.0)
        result = scorer.score(dims)
        assert result.total == 0.0

    def test_weights_applied_correctly(self, scorer):
        # Only citation_integrity = 100, rest = 0 → should equal weight 0.20 * 100 = 20.0
        dims = _dims(_base=0.0, citation_integrity=100.0)
        result = scorer.score(dims)
        assert abs(result.total - 20.0) < 0.01

    def test_typical_operational_score(self, scorer):
        dims = _dims(_base=85.0, citation_integrity=92.0, provenance_completeness=88.0)
        result = scorer.score(dims)
        assert result.total >= 82.0
        assert result.maturity_floor == "STG-5"

    def test_missing_dimension_raises(self, scorer):
        dims = dict.fromkeys(list(CCS_WEIGHTS.keys())[:-1], 80.0)  # missing last
        with pytest.raises(ValueError, match="missing required dimensions"):
            scorer.score(dims)

    def test_out_of_range_raises(self, scorer):
        dims = _dims(_base=80.0, citation_integrity=101.0)
        with pytest.raises(ValueError, match="out of range"):
            scorer.score(dims)


class TestConfidenceCodes:
    def test_high_confidence_at_78(self, scorer):
        dims = _dims(_base=78.0)
        result = scorer.score(dims)
        assert result.confidence_code == "CONF-H"

    def test_moderate_at_68(self, scorer):
        dims = _dims(_base=68.0)
        result = scorer.score(dims)
        assert result.confidence_code == "CONF-M"

    def test_limited_at_55(self, scorer):
        dims = _dims(_base=55.0)
        result = scorer.score(dims)
        assert result.confidence_code == "CONF-L"

    def test_preliminary_below_55(self, scorer):
        dims = _dims(_base=40.0)
        result = scorer.score(dims)
        assert result.confidence_code == "CONF-P"


class TestMaturityFloor:
    def test_litigation_ready_at_92_with_gates(self, scorer):
        dims = _dims(_base=95.0, citation_integrity=100.0)
        result = scorer.score(dims)
        assert result.maturity_floor == "STG-6"
        assert result.litigation_ready is True

    def test_lit_ready_blocked_by_ci_below_100(self, scorer):
        dims = _dims(_base=93.0, citation_integrity=99.0)
        result = scorer.score(dims)
        assert result.litigation_ready is False

    def test_operational_gate_ci_90(self, scorer):
        dims = _dims(_base=85.0, citation_integrity=89.0, provenance_completeness=86.0)
        result = scorer.score(dims)
        assert result.maturity_floor in ("STG-3", "STG-4")  # blocked from STG-5
        assert any("Citation Integrity" in w for w in result.warnings)

    def test_zero_dimension_blocks_verified(self, scorer):
        dims = _dims(_base=80.0, reproducibility=0.0)
        result = scorer.score(dims)
        assert result.any_dimension_zero is True
        assert result.maturity_floor in ("STG-3",)  # can't reach STG-4


class TestMaturityThresholds:
    @pytest.mark.parametrize(("stage", "min_ccs"), [
        ("STG-1", 40.0), ("STG-2", 55.0), ("STG-3", 68.0),
        ("STG-4", 78.0), ("STG-5", 82.0), ("STG-6", 92.0),
    ])
    def test_minimum_ccs(self, stage, min_ccs):
        assert CCSScorer.minimum_ccs_for_stage(stage) == min_ccs
