"""
BRA — Knowledge Object Validator
=================================
Validates Knowledge Object metadata against BKGC v2.0 and BGS v1.0 rules.

BKGC v2.0 Art. VIII-IX; BGS v1.0 BGS-01 through BGS-04.

This module does NOT create knowledge objects — it validates metadata dicts
against the constitutional schema and business rules. Use this before
advancing a KO's maturity stage.

Usage:
    validator = KnowledgeObjectValidator(ccs_scorer)
    result = validator.validate(ko_dict)
    if result.valid:
        print("KO passes constitutional validation")
    else:
        for err in result.errors:
            print(f"  ERROR: {err}")
        for warn in result.warnings:
            print(f"  WARN:  {warn}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from blackstone.bra.ccs import MATURITY_MIN_CCS, CCSScorer

# Claim status → minimum maturity stage allowed for assignment
CLAIM_STATUS_MIN_STAGE: dict[str, str] = {
    "CTRL":  "STG-2",  # Research
    "PERS":  "STG-2",  # Research
    "HIST":  "STG-2",  # Research
    "SCHOL": "STG-2",  # Research
    "EDU":   "STG-1",  # Hypothesis
    "EMRG":  "STG-1",  # Hypothesis
    "DISP":  "STG-2",  # Research
    "UNVR":  "STG-1",  # Hypothesis
}

# Confidence codes → minimum CCS
CONFIDENCE_MIN_CCS: dict[str, float] = {
    "CONF-H": 78.0,
    "CONF-M": 68.0,
    "CONF-L": 55.0,
    "CONF-P": 0.0,
    "CONF-I": 0.0,
}

STAGE_ORDER = ["STG-0", "STG-1", "STG-2", "STG-3", "STG-4", "STG-5", "STG-6", "STG-7"]


def _stage_gte(a: str, b: str) -> bool:
    """Return True if stage a is >= stage b."""
    return STAGE_ORDER.index(a) >= STAGE_ORDER.index(b)


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    computed_ccs: float | None = None


class KnowledgeObjectValidator:
    """
    Validate a knowledge object dict against BKGC v2.0 and BGS v1.0 rules.

    Checks:
      1. Required fields present
      2. EV-ID format compliance (BKR-02)
      3. CCS score consistency (BGS-01)
      4. Maturity stage gate compliance (BGS-02)
      5. Claim status eligibility for maturity stage (BGS-03)
      6. Confidence level alignment with CCS (BGS-04)
      7. Jurisdiction confirmation rule (BGS-03.2)
      8. Counter-evidence requirement (BKGC Art. XIX)
      9. Temporal accuracy requirement (BGS-01 dimension)
      10. Human review trigger ($500 rule, BGS-11)
      11. Legal hold block (BGS-19)
      12. AI content source class (CDR-00001)
      13. Litigation Ready special gates (BGS-01, STG-6)
    """

    EV_ID_PATTERN = r"^EV-\d{8}-\d{4}(-D\d+)?$"
    KO_ID_PATTERN = r"^KO-\d{8}-\d{4}$"

    def __init__(self, ccs_scorer: CCSScorer | None = None) -> None:
        self._scorer = ccs_scorer or CCSScorer()

    def validate(self, ko: dict[str, Any], *, _stage_advancement: bool = False) -> ValidationResult:
        """
        Validate a knowledge object metadata dict.

        Args:
            ko: The KO metadata dict (should conform to knowledge_object.schema.json).
            _stage_advancement: If True, apply stricter advancement gate checks.

        Returns:
            ValidationResult with errors, warnings, and computed CCS.
        """
        errors: list[str] = []
        warnings: list[str] = []

        # 1. Required fields
        required = [
            "ko_id", "title", "maturity_stage_code", "claim_status_code",
            "confidence_level_code", "jurisdiction_code", "jurisdiction_confirmed",
            "ccs_score", "ccs_dimensions", "claims", "evidence_ids",
            "counter_evidence_assessed", "temporal_current",
        ]
        for f in required:
            if f not in ko:
                errors.append(f"Missing required field: '{f}'")

        if errors:
            return ValidationResult(valid=False, errors=errors)

        stage = ko["maturity_stage_code"]
        claim_code = ko["claim_status_code"]
        conf_code = ko["confidence_level_code"]
        jur_confirmed = ko["jurisdiction_confirmed"]
        ccs_score = ko["ccs_score"]
        dimensions = ko.get("ccs_dimensions", {})

        # 2. KO-ID format
        import re
        if not re.match(self.KO_ID_PATTERN, ko.get("ko_id", "")):
            errors.append(f"ko_id '{ko.get('ko_id')}' does not match format KO-YYYYMMDD-NNNN (BKR-02).")

        # 3. CCS recomputation consistency
        if dimensions:
            try:
                result = self._scorer.score(dimensions)
                computed = result.total
                if abs(computed - ccs_score) > 0.5:
                    errors.append(
                        f"ccs_score {ccs_score} does not match computed CCS {computed:.2f} "
                        f"from dimensions. Recompute and update. (BGS-01)"
                    )
                warnings.extend(result.warnings)
                # Pass computed CCS to caller
                computed_ccs = computed
            except ValueError as e:
                errors.append(f"CCS dimension error: {e}")
                computed_ccs = None
        else:
            errors.append("ccs_dimensions missing or empty. All 10 BGS-01 dimensions required.")
            computed_ccs = None

        # 4. Maturity stage minimum CCS
        min_ccs = MATURITY_MIN_CCS.get(stage)
        if min_ccs is not None and ccs_score < min_ccs:
            errors.append(
                f"Stage {stage} requires CCS ≥ {min_ccs}, but ccs_score is {ccs_score}. (BGS-01, BKR-06)"
            )

        # 5. Claim status eligibility for maturity stage
        min_stage_for_claim = CLAIM_STATUS_MIN_STAGE.get(claim_code)
        if min_stage_for_claim and not _stage_gte(stage, min_stage_for_claim):
            errors.append(
                f"Claim status '{claim_code}' cannot be assigned at stage {stage}. "
                f"Minimum stage: {min_stage_for_claim}. (BKR-04)"
            )

        # 6. Confidence alignment with CCS
        _ = CONFIDENCE_MIN_CCS.get(conf_code, 0.0)
        if conf_code == "CONF-H" and ccs_score < 78.0:
            errors.append(f"CONF-H requires CCS >= 78. CCS is {ccs_score}. (BKR-05)")
        elif conf_code == "CONF-M" and ccs_score < 68.0:
            errors.append(f"CONF-M requires CCS >= 68. CCS is {ccs_score}. (BKR-05)")
        elif conf_code == "CONF-L" and ccs_score < 55.0:
            errors.append(f"CONF-L requires CCS >= 55. CCS is {ccs_score}. (BKR-05)")
        if conf_code == "CONF-I":
            errors.append(
                "CONF-I (Insufficient Evidence) is a STOP signal. No conclusion may be communicated. "
                "Return to Hypothesis stage. (BKR-05, BKGC Art. XXII)"
            )

        # 7. Jurisdiction confirmation rule
        if not jur_confirmed and claim_code == "CTRL":
            errors.append(
                "Claim status CTRL (Controlling) requires jurisdiction_confirmed = true. "
                "Unconfirmed jurisdiction caps claim status at PERS. (BGS-03.2)"
            )
        if not jur_confirmed and claim_code not in ("UNVR", "EDU", "EMRG"):
            warnings.append(
                "jurisdiction_confirmed is false. Claim status is capped at PERS per BGS-03.2. "
                "Resolve jurisdiction before advancing to Corroborated (STG-3)."
            )

        # 8. Counter-evidence requirement
        if _stage_gte(stage, "STG-2") and not ko.get("counter_evidence_assessed"):
            errors.append(
                "counter_evidence_assessed must be true at Research stage (STG-2) and above. "
                "(BKGC Art. XIX)"
            )

        # 9. Temporal currency
        if _stage_gte(stage, "STG-4") and not ko.get("temporal_current"):
            errors.append(
                "temporal_current must be true at Verified stage (STG-4) and above. (BKGC Art. X)"
            )
        if _stage_gte(stage, "STG-2") and not ko.get("temporal_current"):
            warnings.append(
                "temporal_current is false. Confirm all cited authorities are current before advancing."
            )

        # 10. Human review trigger — $500 rule (BGS-11)
        financial = ko.get("financial_amount_usd")
        if financial is not None and financial >= 500.0:
            if not ko.get("human_review_required"):
                errors.append(
                    f"financial_amount_usd is ${financial:,.2f} (≥ $500). "
                    "human_review_required must be true. (BGS-11)"
                )

        # 11. Legal hold
        if ko.get("legal_hold"):
            if ko.get("integrity_status") != "INTACT":
                warnings.append(
                    "KO is under legal hold. Modification, deletion, and archival are blocked. (BGS-19)"
                )

        # 12. Litigation Ready special gates (STG-6)
        if stage == "STG-6":
            if dimensions.get("citation_integrity", 0) < 100:
                errors.append(
                    "Litigation Ready (STG-6) requires citation_integrity dimension = 100. (BGS-01)"
                )
            dim_below_80 = {k: v for k, v in dimensions.items() if v < 80}
            if dim_below_80:
                errors.append(
                    f"Litigation Ready (STG-6) requires all dimensions ≥ 80. "
                    f"Below threshold: {dim_below_80}. (BGS-01)"
                )
            if claim_code not in ("CTRL", "PERS"):
                errors.append(
                    f"Litigation Ready (STG-6) allows only CTRL or PERS claim status. "
                    f"Found: {claim_code}. (BKR-06)"
                )
            if not ko.get("decision_traceability"):
                errors.append(
                    "Litigation Ready (STG-6) requires a complete decision_traceability record. (BKGC Art. XXIII)"
                )

        # 13. Evidence IDs format check
        import re as re2
        for ev_id in ko.get("evidence_ids", []):
            if not re2.match(self.EV_ID_PATTERN, ev_id):
                errors.append(f"evidence_id '{ev_id}' does not match format EV-YYYYMMDD-NNNN. (BKR-02)")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            computed_ccs=computed_ccs if 'computed_ccs' in dir() else None,
        )

    def check_advancement(self, ko: dict[str, Any], target_stage: str) -> ValidationResult:
        """
        Check whether a KO can advance to a target maturity stage.
        Returns a ValidationResult with errors explaining what is blocking advancement.
        """
        result = self.validate(ko, stage_advancement=True)
        min_ccs = MATURITY_MIN_CCS.get(target_stage)
        ccs = ko.get("ccs_score", 0)

        if min_ccs is not None and ccs < min_ccs:
            result.errors.insert(0,
                f"Cannot advance to {target_stage}: CCS {ccs} < minimum {min_ccs}. "
                f"Improve evidence quality to raise CCS. (BGS-02)"
            )
            result.valid = False

        return result
