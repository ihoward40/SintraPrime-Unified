from __future__ import annotations

import pytest

from packages.browser_automation import FilingEngine, FilingRequest, FilingTarget


def _request(filing_type: str) -> FilingRequest:
    return FilingRequest(
        filing_type=filing_type,
        jurisdiction="CA",
        payload={"doc": "alpha", "amount": 1},
        signer_name="Alex",
    )


def test_capture_signature_is_deterministic() -> None:
    engine = FilingEngine()
    a = engine.capture_signature("Alex", {"a": 1})
    b = engine.capture_signature("Alex", {"a": 1})
    assert a == b


def test_capture_signature_changes_for_payload() -> None:
    engine = FilingEngine()
    assert engine.capture_signature("Alex", {"a": 1}) != engine.capture_signature("Alex", {"a": 2})


def test_capture_signature_is_stable_across_dict_order() -> None:
    engine = FilingEngine()
    assert engine.capture_signature("Alex", {"a": 1, "b": 2}) == engine.capture_signature(
        "Alex", {"b": 2, "a": 1}
    )


@pytest.mark.parametrize(
    ("filing_type", "target"),
    [("ucc-1", FilingTarget.UCC), ("court-motion", FilingTarget.COURT)],
)
def test_file_routes_to_expected_target(filing_type: str, target: FilingTarget) -> None:
    result = FilingEngine().file(_request(filing_type))
    assert result.target is target


def test_file_generates_receipt_reference() -> None:
    result = FilingEngine().file(_request("ucc-1"))
    assert result.receipt_reference.startswith("receipt-ca-")


def test_screenshot_trail_has_expected_steps() -> None:
    result = FilingEngine().file(_request("ucc-1"))
    assert len(result.screenshots) == 4
    assert result.screenshots[0].endswith("01-start.png")
    assert result.screenshots[-1].endswith("04-submitted.png")


def test_browser_log_order() -> None:
    result = FilingEngine().file(_request("court-order"))
    assert result.browser_log[0] == "open:court:CA"
    assert result.browser_log[1].startswith("sign:sig-")
    assert result.browser_log[2] == "submit:ok"


@pytest.mark.parametrize("filing_type", ["UCC-1", "ucc-amendment", "court", "Court-Order"])
def test_file_submits_supported_variants(filing_type: str) -> None:
    result = FilingEngine().file(_request(filing_type))
    assert result.status == "submitted"


def test_custom_audit_root_is_used() -> None:
    result = FilingEngine(screenshot_root="screens").file(_request("ucc-1"))
    assert all(path.startswith("screens/") for path in result.screenshots)


def test_blank_screenshot_root_rejected() -> None:
    with pytest.raises(ValueError, match="screenshot_root must not be empty"):
        FilingEngine(screenshot_root="   ")


def test_absolute_screenshot_root_preserved() -> None:
    result = FilingEngine(screenshot_root="/var/audit").file(_request("ucc-1"))
    assert all(path.startswith("/var/audit/") for path in result.screenshots)


def test_unsupported_filing_type_rejected() -> None:
    with pytest.raises(ValueError, match="unsupported filing type: other"):
        FilingEngine().file(_request("other"))


def test_receipt_reference_normalizes_jurisdiction_whitespace() -> None:
    request = _request("court")
    request.jurisdiction = " CA "
    result = FilingEngine().file(request)
    assert result.receipt_reference.startswith("receipt-ca-")
    assert result.browser_log[0] == "open:court:CA"
