"""
BRA — CCS Scorer
================
Constitutional Compliance Score (CCS) engine.

Computes the weighted composite CCS for a knowledge object based on ten dimensions.
Dimension weights are fixed by BGS-01 and may only be changed by CDR.

Governed by: BGS-01, BKGC Art. VIII, BKR-05 (confidence thresholds), BKR-06 (maturity thresholds).

Usage:
    scorer = CCSScorer()
    result = scorer.score(dimensions)
    print(result.total)           # e.g. 84.2
    print(result.confidence_code) # e.g. "CONF-H"
    print(result.maturity_floor)  # e.g. "STG-5"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

# ---------------------------------------------------------------------------
# Dimension weights — BGS-01. Immutable without CDR.
# ---------------------------------------------------------------------------
CCS_WEIGHTS: dict[str, float] = {
    "citation_integrity":      0.20,  # 20% — all claims traceable to authenticated sources
    "provenance_completeness": 0.18,  # 18% — origin and chain of custody documented
    "jurisdiction_accuracy":   0.14,  # 14% — jurisdiction confirmed and correctly coded
    "temporal_accuracy":       0.12,  # 12% — all authorities confirmed current
    "counter_evidence_review": 0.12,  # 12% — counter-evidence systematically identified
    "confidence_calibration":  0.10,  # 10% — confidence level accurately reflects evidence
    "transparency":            0.06,  #  6% — reasoning and methodology explicitly stated
    "auditability":            0.04,  #  4% — all steps reproducible from audit trail
    "reproducibility":         0.02,  #  2% — independent agent can reach same conclusion
    "evidence_preservation":   0.02,  #  2% — all evidence preserved in CEL, none deleted
}

# Verify weights sum to 1.0 (fails loudly at import time if tampered with)
assert abs(sum(CCS_WEIGHTS.values()) - 1.0) < 1e-9, (
    "CCS_WEIGHTS must sum to 1.0. Any change requires a CDR per BGS-01."
)


# ---------------------------------------------------------------------------
# Maturity stage minimum CCS thresholds — BGS-01, BKR-06
# ---------------------------------------------------------------------------
MATURITY_MIN_CCS: dict[str, float | None] = {
    "STG-0": None,  # Idea — not in governance scope
    "STG-1": 40.0,  # Hypothesis
    "STG-2": 55.0,  # Research
    "STG-3": 68.0,  # Corroborated
    "STG-4": 78.0,  # Verified
    "STG-5": 82.0,  # Operational
    "STG-6": 92.0,  # Litigation Ready
    "STG-7": None,  # Historical Archive — immutable, no new scoring
}

# Confidence level thresholds — BKR-05
CONFIDENCE_THRESHOLDS: list[tuple[float, str]] = [
    (78.0, "CONF-H"),  # High Confidence
    (68.0, "CONF-M"),  # Moderate Confidence
    (55.0, "CONF-L"),  # Limited Confidence
    (0.0,  "CONF-P"),  # Preliminary Assessment (below 55 but evidence exists)
]


@dataclass
class CCSResult:
    """Result of a CCS scoring computation."""

    dimensions: dict[str, float]
    weighted_contributions: dict[str, float]
    total: float
    confidence_code: str
    maturity_floor: str
    litigation_ready: bool
    any_dimension_zero: bool
    min_dimension: tuple[str, float]
    max_dimension: tuple[str, float]
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total": round(self.total, 2),
            "confidence_code": self.confidence_code,
            "maturity_floor": self.maturity_floor,
            "litigation_ready": self.litigation_ready,
            "any_dimension_zero": self.any_dimension_zero,
            "min_dimension": {"name": self.min_dimension[0], "score": self.min_dimension[1]},
            "max_dimension": {"name": self.max_dimension[0], "score": self.max_dimension[1]},
            "dimensions": {k: round(v, 2) for k, v in self.dimensions.items()},
            "weighted_contributions": {k: round(v, 4) for k, v in self.weighted_contributions.items()},
            "warnings": self.warnings,
        }


class CCSScorer:
    """
    Compute Constitutional Compliance Scores.

    Weights are fixed by BGS-01. Changing them requires a CDR amendment.
    This class is stateless — instantiate once and call score() repeatedly.
    """

    WEIGHTS: ClassVar[dict[str, float]] = CCS_WEIGHTS

    def score(self, dimensions: dict[str, float]) -> CCSResult:
        """
        Compute the CCS from dimension scores (each 0-100).

        Args:
            dimensions: Dict mapping dimension name to score (0-100).
                        All ten BGS-01 dimensions must be present.

        Returns:
            CCSResult with total, confidence code, maturity floor, and warnings.

        Raises:
            ValueError: If any required dimension is missing or out of range.
        """
        self._validate_inputs(dimensions)

        weighted = {
            dim: dimensions[dim] * weight
            for dim, weight in self.WEIGHTS.items()
        }
        total = sum(weighted.values())

        warnings: list[str] = []
        any_zero = any(v == 0.0 for v in dimensions.values())
        if any_zero:
            zero_dims = [d for d, v in dimensions.items() if v == 0.0]
            warnings.append(
                f"DIMENSION ZERO: {', '.join(zero_dims)}. "
                "A score of 0 on any dimension blocks advancement to Verified (STG-4) per BGS-01."
            )

        # Citation integrity special rules
        ci = dimensions["citation_integrity"]
        if ci < 90 and total >= 82:
            warnings.append(
                "Citation Integrity < 90 blocks Operational (STG-5) advancement per BGS-01, "
                "even though total CCS qualifies."
            )
        if ci < 100 and total >= 92:
            warnings.append(
                "Citation Integrity must be 100 for Litigation Ready (STG-6) per BGS-01."
            )

        # Provenance special rule for Operational
        prov = dimensions["provenance_completeness"]
        if prov < 85 and total >= 82:
            warnings.append(
                "Provenance Completeness < 85 blocks Operational (STG-5) per BGS-01."
            )

        # Litigation Ready: no dimension below 80
        below_80 = {d: v for d, v in dimensions.items() if v < 80}
        if total >= 92 and below_80:
            warnings.append(
                f"Litigation Ready (STG-6) requires all dimensions ≥ 80. "
                f"Below threshold: {below_80}"
            )

        confidence_code = self._assign_confidence(total)
        maturity_floor = self._assign_maturity_floor(total, dimensions)
        litigation_ready = self._is_litigation_ready(total, dimensions)

        dim_items = list(dimensions.items())
        min_dim = min(dim_items, key=lambda x: x[1])
        max_dim = max(dim_items, key=lambda x: x[1])

        return CCSResult(
            dimensions=dict(dimensions),
            weighted_contributions=weighted,
            total=round(total, 2),
            confidence_code=confidence_code,
            maturity_floor=maturity_floor,
            litigation_ready=litigation_ready,
            any_dimension_zero=any_zero,
            min_dimension=min_dim,
            max_dimension=max_dim,
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _validate_inputs(self, dimensions: dict[str, float]) -> None:
        required = set(self.WEIGHTS.keys())
        provided = set(dimensions.keys())
        missing = required - provided
        if missing:
            raise ValueError(f"CCS scoring missing required dimensions: {missing}")
        for dim, score in dimensions.items():
            if not (0.0 <= score <= 100.0):
                raise ValueError(
                    f"Dimension '{dim}' score {score} is out of range [0, 100]."
                )

    def _assign_confidence(self, total: float) -> str:
        for threshold, code in CONFIDENCE_THRESHOLDS:
            if total >= threshold:
                return code
        return "CONF-I"  # Insufficient Evidence (total = 0 or negative — should not occur)

    def _assign_maturity_floor(self, total: float, dims: dict[str, float]) -> str:
        """
        Return the highest maturity stage the CCS total supports,
        subject to dimension-specific gates for STG-5 and STG-6.
        """
        if total >= 92.0 and self._is_litigation_ready(total, dims):
            return "STG-6"
        if total >= 82.0 and self._meets_operational_gates(dims):
            return "STG-5"
        if total >= 78.0 and not any(v == 0.0 for v in dims.values()):
            return "STG-4"
        if total >= 68.0:
            return "STG-3"
        if total >= 55.0:
            return "STG-2"
        if total >= 40.0:
            return "STG-1"
        return "STG-0"

    def _meets_operational_gates(self, dims: dict[str, float]) -> bool:
        return (
            dims.get("citation_integrity", 0) >= 90
            and dims.get("provenance_completeness", 0) >= 85
        )

    def _is_litigation_ready(self, total: float, dims: dict[str, float]) -> bool:
        if total < 92.0:
            return False
        if dims.get("citation_integrity", 0) < 100.0:
            return False
        return not any(v < 80.0 for v in dims.values())

    @staticmethod
    def minimum_ccs_for_stage(stage_code: str) -> float | None:
        """Return the minimum CCS required to enter a maturity stage."""
        return MATURITY_MIN_CCS.get(stage_code)

    @staticmethod
    def dimension_weight(dimension_name: str) -> float:
        """Return the BGS-01 weight for a named dimension."""
        w = CCS_WEIGHTS.get(dimension_name)
        if w is None:
            raise KeyError(f"Unknown CCS dimension: {dimension_name!r}")
        return w
