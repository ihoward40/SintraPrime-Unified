from __future__ import annotations

import pytest

from packages.execution_bridge import ExecutionBridge


def _ucc_metadata() -> dict[str, str]:
    return {
        "debtor_name": "Debtor LLC",
        "secured_party_name": "Secured Inc",
        "collateral": "All assets",
        "jurisdiction": "CA",
    }


def test_validate_success_ucc() -> None:
    result = ExecutionBridge().validate(document="Hello", filing_type="ucc-1", metadata=_ucc_metadata())
    assert result.is_valid is True
    assert result.missing_fields == []


def test_validate_strips_filing_type_whitespace() -> None:
    result = ExecutionBridge().validate(
        document="Hello", filing_type=" ucc-1 ", metadata=_ucc_metadata()
    )
    assert result.is_valid is True


def test_validate_hash_uses_normalized_document() -> None:
    bridge = ExecutionBridge()
    left = bridge.validate(document="  Hello  ", filing_type="ucc-1", metadata=_ucc_metadata())
    right = bridge.validate(document="Hello", filing_type="ucc-1", metadata=_ucc_metadata())
    assert left.document_hash == right.document_hash


def test_validate_missing_fields() -> None:
    result = ExecutionBridge().validate(document="Hello", filing_type="ucc-1", metadata={})
    assert result.is_valid is False
    assert sorted(result.missing_fields) == ["collateral", "debtor_name", "secured_party_name"]


def test_validate_empty_doc_invalid() -> None:
    result = ExecutionBridge().validate(document="   ", filing_type="ucc-1", metadata=_ucc_metadata())
    assert result.is_valid is False
    assert "document is empty" in result.messages


def test_validate_unsupported_type_invalid() -> None:
    result = ExecutionBridge().validate(document="doc", filing_type="other", metadata={})
    assert result.is_valid is False
    assert "unsupported filing type: other" in result.messages


def test_transform_success() -> None:
    payload = ExecutionBridge().transform(document="doc", filing_type="ucc-1", metadata=_ucc_metadata())
    assert payload.filing_type == "ucc-1"
    assert payload.jurisdiction == "CA"
    assert payload.transformed_fields["document_length"] == 3


def test_transform_invalid_raises() -> None:
    with pytest.raises(ValueError, match="cannot transform invalid filing payload"):
        ExecutionBridge().transform(document="", filing_type="ucc-1", metadata={})


def test_estimate_cost_default() -> None:
    assert ExecutionBridge().estimate_cost(filing_type="ucc-1") == 35


def test_estimate_cost_rush() -> None:
    assert ExecutionBridge().estimate_cost(filing_type="court", rush=True) == 225


def test_estimate_cost_strips_filing_type_whitespace() -> None:
    assert ExecutionBridge().estimate_cost(filing_type=" court ") == 150


def test_estimate_cost_unsupported_type_raises() -> None:
    with pytest.raises(ValueError, match="unsupported filing type: other"):
        ExecutionBridge().estimate_cost(filing_type="other")


def test_validate_and_transform_passthrough() -> None:
    payload = ExecutionBridge().validate_and_transform(
        document="doc",
        filing_type="ucc-1",
        metadata=_ucc_metadata(),
    )
    assert payload.filing_type == "ucc-1"


def test_transform_uses_normalized_document_for_length_and_preview() -> None:
    payload = ExecutionBridge().transform(
        document="  abc  ", filing_type="ucc-1", metadata=_ucc_metadata()
    )
    assert payload.transformed_fields["document_length"] == 3
    assert payload.transformed_fields["document_preview"] == "abc"


def test_transform_defaults_jurisdiction_when_null() -> None:
    metadata = _ucc_metadata()
    metadata["jurisdiction"] = None  # type: ignore[assignment]
    payload = ExecutionBridge().transform(document="abc", filing_type="ucc-1", metadata=metadata)
    assert payload.jurisdiction == "unknown"


def test_transform_strips_jurisdiction_whitespace() -> None:
    metadata = _ucc_metadata()
    metadata["jurisdiction"] = " CA "
    payload = ExecutionBridge().transform(document="abc", filing_type="ucc-1", metadata=metadata)
    assert payload.jurisdiction == "CA"


@pytest.mark.parametrize("missing_key", ["case_number", "court_name", "filing_party"])
def test_court_required_fields_enforced(missing_key: str) -> None:
    metadata = {
        "case_number": "123",
        "court_name": "District",
        "filing_party": "Alice",
        "jurisdiction": "NY",
    }
    metadata.pop(missing_key)
    result = ExecutionBridge().validate(document="abc", filing_type="court", metadata=metadata)
    assert result.is_valid is False
    assert missing_key in result.missing_fields
