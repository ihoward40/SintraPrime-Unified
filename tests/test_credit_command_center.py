"""Tests for the Credit Command Center v1 scaffold.

Covers models, scorecard math, folder naming, receipt creation, and fixture loading.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from packages.credit_command_center import (
    ActionReceipt,
    Bureau,
    CaseStatus,
    ClientCase,
    ConfidenceLevel,
    CreditAccount,
    EvidenceItem,
    Finding,
    FindingCategory,
    Scorecard,
    ScorecardRating,
    ServiceTier,
    build_case_folder_path,
    build_evidence_folder_path,
    create_receipt,
    normalize_client_name,
    rate_scorecard,
)

FIXTURE_DIR = Path(__file__).resolve().parent.parent / "packages" / "credit_command_center" / "fixtures"


# ── Model Creation ───────────────────────────────────────────────────────────


class TestClientCase:
    def test_create_minimal(self):
        case = ClientCase(case_id="C-0001", client_name="Test User", email="test@example.com")
        assert case.case_id == "C-0001"
        assert case.client_name == "Test User"
        assert case.tier == ServiceTier.AUDIT
        assert case.status == CaseStatus.INTAKE
        assert case.scorecard_total is None

    def test_create_full(self):
        case = ClientCase(
            case_id="C-0002",
            client_name="Jane Doe",
            email="jane@example.com",
            tier=ServiceTier.BLUEPRINT,
            status=CaseStatus.ANALYSIS,
            scorecard_total=45,
            scorecard_rating=ScorecardRating.MODERATE,
        )
        assert case.scorecard_total == 45
        assert case.scorecard_rating == ScorecardRating.MODERATE

    def test_invalid_case_id(self):
        with pytest.raises(ValueError, match="case_id must start with 'C-'"):
            ClientCase(case_id="X-0001", client_name="Bad", email="bad@example.com")

    def test_invalid_scorecard_total_too_high(self):
        with pytest.raises(Exception, match="less than or equal to 70"):
            ClientCase(
                case_id="C-0003",
                client_name="Bad",
                email="bad@example.com",
                scorecard_total=99,
            )

    def test_invalid_scorecard_total_negative(self):
        with pytest.raises(Exception, match="greater than or equal to 0"):
            ClientCase(
                case_id="C-0004",
                client_name="Bad",
                email="bad@example.com",
                scorecard_total=-5,
            )


class TestCreditAccount:
    def test_create_minimal(self):
        acct = CreditAccount(
            creditor_name="Test Bank",
            account_number="****5678",
            account_type="credit card",
            bureau=Bureau.EQUIFAX,
        )
        assert acct.creditor_name == "Test Bank"
        assert acct.bureau == Bureau.EQUIFAX
        assert acct.status.value == "open"

    def test_create_full(self):
        acct = CreditAccount(
            creditor_name="UACC",
            account_number="****1234",
            account_type="auto loan",
            bureau=Bureau.TRANSUNION,
            balance=12517.55,
            status="collections",
            date_opened="2021-03-15",
            remarks="CFPB complaint filed",
        )
        assert acct.balance == 12517.55
        assert acct.status.value == "collections"


class TestEvidenceItem:
    def test_create_minimal(self):
        item = EvidenceItem(file_name="doc.pdf", file_path="/clients/test/")
        assert item.file_name == "doc.pdf"
        assert item.belongs_in_report is True
        assert item.confidence == ConfidenceLevel.MEDIUM

    def test_create_with_ocr(self):
        item = EvidenceItem(
            file_name="scan.png",
            file_path="/clients/test/",
            confidence=ConfidenceLevel.PENDING_OCR,
        )
        assert item.confidence == ConfidenceLevel.PENDING_OCR


class TestFinding:
    def test_create_valid(self):
        finding = Finding(
            finding_number=1,
            category=FindingCategory.CREDIT,
            what_is_wrong="Account in collections incorrectly",
            evidence_support="Credit report shows $5k balance, account was paid",
            next_step="File dispute with bureau",
        )
        assert finding.finding_number == 1
        assert finding.category == FindingCategory.CREDIT

    def test_invalid_finding_number_zero(self):
        with pytest.raises(ValueError):
            Finding(
                finding_number=0,
                category=FindingCategory.CREDIT,
                what_is_wrong="x",
                evidence_support="y",
                next_step="z",
            )


class TestActionReceipt:
    def test_create_minimal(self):
        receipt = ActionReceipt(
            receipt_id="R-0001",
            case_id="C-0001",
            actor="Hermes",
            action="intake_received",
        )
        assert receipt.receipt_id == "R-0001"
        assert receipt.actor == "Hermes"
        assert receipt.details == {}

    def test_create_with_details(self):
        receipt = ActionReceipt(
            receipt_id="R-0002",
            case_id="C-0001",
            actor="Isiah",
            action="document_cataloged",
            details={"file_count": 5, "source": "email"},
            file_path="/clients/isiah-howard/intake/",
        )
        assert receipt.details["file_count"] == 5
        assert receipt.file_path is not None


# ── Scorecard ────────────────────────────────────────────────────────────────


class TestScorecard:
    def test_total_calculation(self):
        sc = Scorecard(
            credit=8,
            collection_defense=7,
            housing=6,
            employment=9,
            documentation=5,
            evidence=4,
            follow_up=3,
        )
        assert sc.total == 42

    def test_rating_strong(self):
        sc = Scorecard(credit=9, collection_defense=9, housing=9, employment=9, documentation=8, evidence=8, follow_up=8)
        assert sc.total == 60
        assert sc.rating == ScorecardRating.STRONG

    def test_rating_moderate(self):
        sc = Scorecard(credit=6, collection_defense=6, housing=6, employment=6, documentation=6, evidence=5, follow_up=5)
        assert sc.total == 40
        assert sc.rating == ScorecardRating.MODERATE

    def test_rating_weak(self):
        sc = Scorecard(credit=3, collection_defense=3, housing=3, employment=3, documentation=3, evidence=3, follow_up=2)
        assert sc.total == 20
        assert sc.rating == ScorecardRating.WEAK

    def test_rating_high_risk(self):
        sc = Scorecard(credit=2, collection_defense=2, housing=2, employment=2, documentation=2, evidence=2, follow_up=2)
        assert sc.total == 14
        assert sc.rating == ScorecardRating.HIGH_RISK

    def test_all_zero(self):
        sc = Scorecard(credit=0, collection_defense=0, housing=0, employment=0, documentation=0, evidence=0, follow_up=0)
        assert sc.total == 0
        assert sc.rating == ScorecardRating.HIGH_RISK

    def test_all_max(self):
        sc = Scorecard(credit=10, collection_defense=10, housing=10, employment=10, documentation=10, evidence=10, follow_up=10)
        assert sc.total == 70
        assert sc.rating == ScorecardRating.STRONG

    def test_category_scores(self):
        sc = Scorecard(credit=5, collection_defense=4, housing=7, employment=8, documentation=6, evidence=5, follow_up=3)
        cats = sc.category_scores()
        assert cats["credit"] == 5
        assert cats["follow_up"] == 3
        assert len(cats) == 7

    def test_invalid_score_too_low(self):
        with pytest.raises(ValueError):
            Scorecard(credit=-1, collection_defense=5, housing=5, employment=5, documentation=5, evidence=5, follow_up=5)

    def test_invalid_score_too_high(self):
        with pytest.raises(ValueError):
            Scorecard(credit=11, collection_defense=5, housing=5, employment=5, documentation=5, evidence=5, follow_up=5)


# ── Helpers ──────────────────────────────────────────────────────────────────


class TestNormalizeClientName:
    def test_simple(self):
        assert normalize_client_name("Isiah Howard") == "isiah-howard"

    def test_extra_spaces(self):
        assert normalize_client_name("  John   Doe  ") == "john-doe"

    def test_hyphenated(self):
        assert normalize_client_name("Alice-Bob Smith") == "alice-bob-smith"

    def test_special_chars(self):
        assert normalize_client_name("O'Brien") == "obrien"

    def test_already_slug(self):
        assert normalize_client_name("jane-doe") == "jane-doe"


class TestBuildCaseFolderPath:
    def test_simple(self):
        path = build_case_folder_path("clients", "Isiah Howard")
        assert path == "clients/isiah-howard"

    def test_custom_base(self):
        path = build_case_folder_path("/data/cases", "Jane Doe")
        assert path == "/data/cases/jane-doe"


class TestBuildEvidenceFolderPath:
    def test_intake(self):
        path = build_evidence_folder_path("clients", "Isiah Howard", "intake")
        assert path == "clients/isiah-howard/intake"

    def test_credit_reports(self):
        path = build_evidence_folder_path("clients", "Isiah Howard", "credit-reports")
        assert path == "clients/isiah-howard/credit-reports"

    def test_output(self):
        path = build_evidence_folder_path("/data", "Jane Doe", "output")
        assert path == "/data/jane-doe/output"


class TestRateScorecard:
    def test_delegates_to_model(self):
        sc = Scorecard(credit=9, collection_defense=9, housing=9, employment=9, documentation=8, evidence=8, follow_up=8)
        assert rate_scorecard(sc) == ScorecardRating.STRONG

    def test_high_risk(self):
        sc = Scorecard(credit=2, collection_defense=2, housing=2, employment=2, documentation=2, evidence=2, follow_up=2)
        assert rate_scorecard(sc) == ScorecardRating.HIGH_RISK


class TestCreateReceipt:
    def test_auto_generates_id(self):
        receipt = create_receipt(case_id="C-0001", actor="Hermes", action="intake_received")
        assert receipt.receipt_id.startswith("R-")
        assert receipt.case_id == "C-0001"
        assert receipt.actor == "Hermes"

    def test_with_explicit_id(self):
        receipt = create_receipt(
            case_id="C-0001",
            actor="Isiah",
            action="document_cataloged",
            receipt_id="R-EXPLICIT-001",
        )
        assert receipt.receipt_id == "R-EXPLICIT-001"

    def test_with_details_and_file_path(self):
        receipt = create_receipt(
            case_id="C-0001",
            actor="System",
            action="evidence_scanned",
            details={"files_found": 12, "ocr_needed": 3},
            file_path="/clients/isiah-howard/evidence/",
        )
        assert receipt.details["files_found"] == 12
        assert receipt.file_path == "/clients/isiah-howard/evidence/"


# ── Fixture Loading ──────────────────────────────────────────────────────────


class TestClient0001Fixture:
    """Validate that the Client #0 fixture loads correctly."""

    @pytest.fixture
    def fixture_data(self):
        path = FIXTURE_DIR / "client_0001.json"
        assert path.exists(), f"Fixture not found: {path}"
        with open(path) as f:
            return json.load(f)

    def test_fixture_exists(self):
        assert FIXTURE_DIR.exists()

    def test_case_loaded(self, fixture_data):
        case_data = fixture_data["case"]
        case = ClientCase(**case_data)
        assert case.case_id == "C-0001"
        assert case.client_name == "Isiah Howard"
        assert case.tier == ServiceTier.AUDIT

    def test_credit_accounts_loaded(self, fixture_data):
        accounts = [CreditAccount(**a) for a in fixture_data["credit_accounts"]]
        assert len(accounts) == 3
        assert all(a.creditor_name == "UACC" for a in accounts)
        bureaus = {a.bureau for a in accounts}
        assert bureaus == {Bureau.EQUIFAX, Bureau.TRANSUNION, Bureau.EXPERIAN}

    def test_evidence_items_loaded(self, fixture_data):
        items = [EvidenceItem(**e) for e in fixture_data["evidence_items"]]
        assert len(items) == 1
        assert items[0].sender == "UACC Compliance Department"
        assert items[0].confidence == ConfidenceLevel.HIGH

    def test_findings_loaded(self, fixture_data):
        findings = [Finding(**f) for f in fixture_data["findings"]]
        assert len(findings) == 1
        assert findings[0].category == FindingCategory.CREDIT
        assert findings[0].confidence == ConfidenceLevel.HIGH

    def test_scorecard_loaded(self, fixture_data):
        sc = Scorecard(**fixture_data["scorecard"])
        assert sc.total == 38
        assert sc.rating == ScorecardRating.WEAK
        assert sc.credit == 5
        assert sc.follow_up == 3
