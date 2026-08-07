from __future__ import annotations

from dataclasses import dataclass

from governed_inference.contracts import DataClassification, InferenceRequest, receipt_hash


@dataclass(frozen=True)
class RedactionReceipt:
    detected_sensitive_categories: list[str]
    transformations_performed: list[str]
    residual_risk_status: str
    resulting_classification: DataClassification
    policy_decision: str
    redaction_receipt_hash: str


LEGAL_TERMS = {"trust", "estate", "client", "evidence", "deposition", "lawsuit", "attorney"}
FINANCIAL_TERMS = {"bank account", "routing number", "tax return", "ein", "payroll"}
IDENTITY_TERMS = {"ssn", "social security", "passport", "driver license", "date of birth"}


def classify_request_data(request: InferenceRequest) -> DataClassification:
    if request.data_classification != DataClassification.UNKNOWN:
        return request.data_classification
    text = _message_text(request).lower()
    if any(term in text for term in IDENTITY_TERMS):
        return DataClassification.RESTRICTED_IDENTITY
    if any(term in text for term in FINANCIAL_TERMS):
        return DataClassification.RESTRICTED_FINANCIAL
    if any(term in text for term in LEGAL_TERMS):
        return DataClassification.RESTRICTED_LEGAL
    return DataClassification.UNKNOWN


def redact_for_policy(request: InferenceRequest) -> RedactionReceipt:
    classification = classify_request_data(request)
    categories: list[str] = []
    if classification in {
        DataClassification.RESTRICTED_LEGAL,
        DataClassification.RESTRICTED_FINANCIAL,
        DataClassification.RESTRICTED_IDENTITY,
        DataClassification.UNKNOWN,
    }:
        categories.append(classification.value)
    decision = "local_only" if categories else "eligible_for_policy_review"
    receipt_id = receipt_hash(request.request_id, categories, classification.value, decision)
    return RedactionReceipt(
        detected_sensitive_categories=categories,
        transformations_performed=[],
        residual_risk_status="not_redacted",
        resulting_classification=classification,
        policy_decision=decision,
        redaction_receipt_hash=receipt_id,
    )


def _message_text(request: InferenceRequest) -> str:
    return "\n".join(str(message.get("content", "")) for message in request.messages)
