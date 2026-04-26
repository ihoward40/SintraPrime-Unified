"""
Comprehensive test suite for legal_integrations package.

All external API calls are mocked — no real credentials required.
Run with:
    python -m pytest legal_integrations/tests/ -v
"""

from __future__ import annotations

import io
import json
import os
import sys
from typing import Any, Dict
from unittest.mock import MagicMock, Mock, patch

import pytest

# ---------------------------------------------------------------------------
# Ensure the package root is on the path when running from repo root
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Set dummy env vars before importing modules that read them at import time
os.environ.setdefault("NETDOCUMENTS_CLIENT_ID", "nd_client_id")
os.environ.setdefault("NETDOCUMENTS_CLIENT_SECRET", "nd_secret")
os.environ.setdefault("NETDOCUMENTS_CABINET_ID", "nd_cabinet")
os.environ.setdefault("IMANAGE_CLIENT_ID", "im_client")
os.environ.setdefault("IMANAGE_CLIENT_SECRET", "im_secret")
os.environ.setdefault("IMANAGE_SERVER_URL", "https://imanage.example.com")
os.environ.setdefault("IMANAGE_CUSTOMER_ID", "cust123")
os.environ.setdefault("IMANAGE_LIBRARY", "lib1")
os.environ.setdefault("WORLDOX_API_URL", "https://worldox.example.com")
os.environ.setdefault("WORLDOX_API_KEY", "wx_key")
os.environ.setdefault("WORLDOX_USERNAME", "wx_user")
os.environ.setdefault("WORLDOX_PASSWORD", "wx_pass")
os.environ.setdefault("CLIO_CLIENT_ID", "clio_id")
os.environ.setdefault("CLIO_CLIENT_SECRET", "clio_secret")
os.environ.setdefault("CLIO_REFRESH_TOKEN", "clio_refresh")
os.environ.setdefault("MYCASE_API_KEY", "mc_key")
os.environ.setdefault("PRACTICEPANTHER_ACCESS_TOKEN", "pp_token")
os.environ.setdefault("PACER_USERNAME", "pacer_user")
os.environ.setdefault("PACER_PASSWORD", "pacer_pass")
os.environ.setdefault("TYLER_CLIENT_TOKEN", "tyler_token")
os.environ.setdefault("TYLER_SERVER_URL", "https://tyler.example.com")
os.environ.setdefault("TYLER_FIRM_ID", "firm123")
os.environ.setdefault("FSX_USERNAME", "fsx_user")
os.environ.setdefault("FSX_PASSWORD", "fsx_pass")
os.environ.setdefault("ODYSSEY_API_KEY", "ody_key")
os.environ.setdefault("ODYSSEY_BASE_URL", "https://odyssey.example.com")
os.environ.setdefault("ODYSSEY_JURISDICTION", "IL")
os.environ.setdefault("WESTLAW_CLIENT_ID", "wl_id")
os.environ.setdefault("WESTLAW_CLIENT_SECRET", "wl_secret")
os.environ.setdefault("LEXISNEXIS_CLIENT_ID", "ln_id")
os.environ.setdefault("LEXISNEXIS_CLIENT_SECRET", "ln_secret")
os.environ.setdefault("FASTCASE_API_KEY", "fc_key")
os.environ.setdefault("COURTLISTENER_API_TOKEN", "cl_token")
os.environ.setdefault("PLAID_CLIENT_ID", "plaid_id")
os.environ.setdefault("PLAID_SECRET", "plaid_secret")
os.environ.setdefault("YODLEE_CLIENT_ID", "y_id")
os.environ.setdefault("YODLEE_SECRET", "y_secret")
os.environ.setdefault("FINICITY_PARTNER_ID", "fin_id")
os.environ.setdefault("FINICITY_PARTNER_SECRET", "fin_secret")
os.environ.setdefault("FINICITY_APP_KEY", "fin_app_key")
os.environ.setdefault("BLOOMBERG_LAW_API_KEY", "bb_key")

from legal_integrations.court_efiling import (
    AcceptedDocument,
    FilingConfirmation,
    FilingDocument,
    FilingRequest,
    FilingStatus,
    FilingStatusResult,
    OdysseyEFileConnector,
    PACERFilingConnector,
    FileServeXpressConnector,
    TylerTechConnector,
    calculate_filing_fee,
    get_efiling_system,
    validate_document_format,
    validate_filing_request,
)
from legal_integrations.dms_connectors import (
    ClioConnector,
    DMSDocument,
    DMSMatter,
    IManageConnector,
    MyCaseConnector,
    NetDocumentsConnector,
    PracticePantherConnector,
    SearchResult,
    WorldoxConnector,
    get_dms_connector,
)
from legal_integrations.financial_connectors import (
    Account,
    AssetReport,
    BankruptcyCase,
    BloombergLawConnector,
    EDGARConnector,
    FinicityConnector,
    PACERBankruptcyConnector,
    PlaidConnector,
    SECFiling,
    YodleeConnector,
)
from legal_integrations.legal_research import (
    CitatorResult,
    CourtListenerConnector,
    FastcaseConnector,
    GoogleScholarLegalConnector,
    LexisNexisConnector,
    ResearchResult,
    UnifiedLegalSearch,
    UnifiedSearchResult,
    WestlawEdgeConnector,
    build_unified_search,
    get_research_connector,
    parse_citation,
    validate_citation,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_response(json_data: Any = None, status_code: int = 200, content: bytes = b"") -> Mock:
    """Build a mock requests.Response."""
    mock = Mock()
    mock.status_code = status_code
    mock.json.return_value = json_data or {}
    mock.content = content or json.dumps(json_data or {}).encode()
    mock.text = (content or json.dumps(json_data or {}).encode()).decode()
    mock.headers = {}
    mock.raise_for_status = Mock()
    return mock


def _pdf_bytes() -> bytes:
    return b"%PDF-1.4 test document content"


# ===========================================================================
# DMS CONNECTOR TESTS
# ===========================================================================


class TestNetDocumentsConnector:
    def _connector(self) -> NetDocumentsConnector:
        c = NetDocumentsConnector()
        c._session = MagicMock()
        return c

    def test_authenticate_sets_token(self):
        c = self._connector()
        c._session.post.return_value = _mock_response({"access_token": "tok123"})
        c.authenticate()
        assert c._access_token == "tok123"
        c._session.headers.update.assert_called()

    def test_upload_document(self):
        c = self._connector()
        c._access_token = "tok"
        c._session.headers = MagicMock()
        c._session.post.return_value = _mock_response(
            {"docId": "doc1", "name": "test.pdf", "version": "1"}
        )
        doc = c.upload_document("m1", "test.pdf", io.BytesIO(b"content"))
        assert doc.doc_id == "doc1"
        assert doc.matter_id == "m1"

    def test_download_document(self):
        c = self._connector()
        c._session.get.return_value = _mock_response(content=b"pdfbytes")
        result = c.download_document("doc1")
        assert result == b"pdfbytes"

    def test_search(self):
        c = self._connector()
        c._session.get.return_value = _mock_response(
            {"results": [{"docId": "d1", "name": "Motion.pdf", "score": 0.9}]}
        )
        results = c.search("motion to dismiss")
        assert len(results) == 1
        assert results[0].doc_id == "d1"
        assert results[0].score == 0.9

    def test_create_matter(self):
        c = self._connector()
        c._session.post.return_value = _mock_response({"matterId": "m99", "name": "Smith v. Jones"})
        matter = c.create_matter("Smith v. Jones", "John Smith")
        assert matter.matter_id == "m99"

    def test_list_matters(self):
        c = self._connector()
        c._session.get.return_value = _mock_response(
            {"matters": [{"matterId": "m1", "name": "Case1", "status": "open"}]}
        )
        matters = c.list_matters()
        assert len(matters) == 1
        assert matters[0].matter_id == "m1"


class TestIManageConnector:
    def _connector(self) -> IManageConnector:
        c = IManageConnector()
        c._session = MagicMock()
        return c

    def test_authenticate(self):
        c = self._connector()
        c._session.post.return_value = _mock_response({"access_token": "im_tok"})
        c.authenticate()
        assert c._access_token == "im_tok"

    def test_upload_document(self):
        c = self._connector()
        c._access_token = "tok"
        c._session.headers = MagicMock()
        c._session.post.return_value = _mock_response({"data": {"id": "im_doc1", "name": "contract.pdf"}})
        doc = c.upload_document("matter1", "contract.pdf", io.BytesIO(b"data"))
        assert doc.doc_id == "im_doc1"

    def test_search(self):
        c = self._connector()
        c._session.get.return_value = _mock_response(
            {"data": {"results": [{"id": "r1", "name": "Brief.pdf"}]}}
        )
        results = c.search("brief")
        assert results[0].doc_id == "r1"

    def test_list_matters(self):
        c = self._connector()
        c._session.get.return_value = _mock_response(
            {"data": {"workspaces": [{"id": "ws1", "name": "Matter A"}]}}
        )
        matters = c.list_matters()
        assert matters[0].matter_id == "ws1"


class TestWorldoxConnector:
    def _connector(self) -> WorldoxConnector:
        c = WorldoxConnector()
        c._session = MagicMock()
        return c

    def test_authenticate(self):
        c = self._connector()
        c._session.post.return_value = _mock_response({"token": "wx_tok"})
        c.authenticate()
        assert c._token == "wx_tok"

    def test_upload_document(self):
        c = self._connector()
        c._token = "tok"
        c._session.headers = MagicMock()
        c._session.post.return_value = _mock_response({"docId": "wx1"})
        doc = c.upload_document("m1", "file.pdf", io.BytesIO(b"data"))
        assert doc.doc_id == "wx1"

    def test_search(self):
        c = self._connector()
        c._session.get.return_value = _mock_response({"documents": [{"docId": "d1", "name": "X.pdf"}]})
        results = c.search("query")
        assert len(results) == 1


class TestClioConnector:
    def _connector(self) -> ClioConnector:
        c = ClioConnector()
        c._session = MagicMock()
        return c

    def test_authenticate(self):
        c = self._connector()
        c._session.post.return_value = _mock_response({"access_token": "clio_tok"})
        c.authenticate()
        assert c._access_token == "clio_tok"

    def test_upload_document(self):
        c = self._connector()
        c._access_token = "tok"
        c._session.headers = MagicMock()
        c._session.post.return_value = _mock_response(
            {"data": {"id": 42, "name": "doc.pdf", "latest_document_version": {"id": 1, "uuid": "u1", "put_url": ""}}}
        )
        c._session.patch.return_value = _mock_response({})
        doc = c.upload_document("100", "doc.pdf", io.BytesIO(b"data"))
        assert doc.doc_id == "42"

    def test_list_matters(self):
        c = self._connector()
        c._session.get.return_value = _mock_response(
            {"data": [{"id": 1, "description": "Case A", "status": "open", "client": {"name": "Alice"}}]}
        )
        matters = c.list_matters()
        assert matters[0].name == "Case A"

    def test_create_matter(self):
        c = self._connector()
        c._session.post.return_value = _mock_response({"data": {"id": 99, "description": "New Case"}})
        matter = c.create_matter("New Case", "Bob")
        assert matter.matter_id == "99"


class TestMyCaseConnector:
    def _connector(self) -> MyCaseConnector:
        c = MyCaseConnector()
        c._session = MagicMock()
        return c

    def test_authenticate_sets_headers(self):
        c = self._connector()
        c._session.headers = MagicMock()
        c.authenticate()
        assert c._session.headers.update.called

    def test_upload_document(self):
        c = self._connector()
        c._session.post.return_value = _mock_response({"id": 77, "filename": "x.pdf"})
        doc = c.upload_document("case1", "x.pdf", io.BytesIO(b"data"))
        assert doc.doc_id == "77"

    def test_search(self):
        c = self._connector()
        c._session.get.return_value = _mock_response({"documents": [{"id": 1, "filename": "y.pdf"}]})
        results = c.search("contract")
        assert results[0].doc_id == "1"


class TestPracticePantherConnector:
    def _connector(self) -> PracticePantherConnector:
        c = PracticePantherConnector()
        c._session = MagicMock()
        return c

    def test_authenticate(self):
        c = self._connector()
        c._session.headers = MagicMock()
        c.authenticate()
        assert c._session.headers.update.called

    def test_upload_document(self):
        c = self._connector()
        c._session.post.return_value = _mock_response({"id": 55, "name": "filing.pdf"})
        doc = c.upload_document("m1", "filing.pdf", io.BytesIO(b"data"))
        assert doc.doc_id == "55"

    def test_list_matters(self):
        c = self._connector()
        c._session.get.return_value = _mock_response({"data": [{"id": 1, "name": "Matter X"}]})
        matters = c.list_matters()
        assert len(matters) == 1


class TestDMSFactory:
    def test_get_dms_connector_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown DMS platform"):
            get_dms_connector("unknown_dms")

    @patch("legal_integrations.dms_connectors.ClioConnector.authenticate")
    def test_get_dms_connector_clio(self, mock_auth):
        connector = get_dms_connector("clio")
        assert connector.name == "clio"
        mock_auth.assert_called_once()

    @patch("legal_integrations.dms_connectors.NetDocumentsConnector.authenticate")
    def test_get_dms_connector_netdocuments(self, mock_auth):
        connector = get_dms_connector("netdocuments")
        assert connector.name == "netdocuments"


# ===========================================================================
# COURT E-FILING TESTS
# ===========================================================================


class TestFilingHelpers:
    def test_validate_document_format_valid_pdf(self):
        doc = FilingDocument(filename="x.pdf", content=_pdf_bytes(), content_type="application/pdf")
        validate_document_format(doc)  # no exception

    def test_validate_document_format_invalid_type(self):
        doc = FilingDocument(filename="x.zip", content=b"data", content_type="application/zip")
        with pytest.raises(ValueError, match="Unsupported content type"):
            validate_document_format(doc)

    def test_validate_document_format_empty_content(self):
        doc = FilingDocument(filename="x.pdf", content=b"", content_type="application/pdf")
        with pytest.raises(ValueError, match="no content"):
            validate_document_format(doc)

    def test_validate_document_format_bad_pdf_magic(self):
        doc = FilingDocument(filename="x.pdf", content=b"not a pdf", content_type="application/pdf")
        with pytest.raises(ValueError, match="valid PDF"):
            validate_document_format(doc)

    def test_validate_filing_request_valid(self):
        req = FilingRequest(
            case_number="21-cv-1234",
            court_id="nysd",
            filing_type="civil_motion",
            documents=[FilingDocument(filename="m.pdf", content=_pdf_bytes(), content_type="application/pdf")],
        )
        errors = validate_filing_request(req)
        assert errors == []

    def test_validate_filing_request_missing_fields(self):
        req = FilingRequest(case_number="", court_id="", filing_type="x", documents=[])
        errors = validate_filing_request(req)
        assert any("case_number" in e for e in errors)
        assert any("court_id" in e for e in errors)
        assert any("document" in e for e in errors)

    def test_calculate_filing_fee_civil_complaint(self):
        fee = calculate_filing_fee("civil_complaint")
        assert fee == 402.00

    def test_calculate_filing_fee_multi_doc(self):
        fee = calculate_filing_fee("civil_complaint", document_count=3)
        assert fee == 403.00

    def test_calculate_filing_fee_default(self):
        fee = calculate_filing_fee("unknown_type")
        assert fee == 50.00


class TestPACERFilingConnector:
    def _connector(self) -> PACERFilingConnector:
        c = PACERFilingConnector()
        c._session = MagicMock()
        return c

    def test_authenticate(self):
        c = self._connector()
        c._session.post.return_value = _mock_response({"nextGenCSO": "pacer_tok"})
        c.authenticate()
        assert c._token == "pacer_tok"

    def test_file_document(self):
        c = self._connector()
        c._token = "tok"
        c._session.headers = MagicMock()
        c._session.post.return_value = _mock_response(
            {"filingId": "f123", "status": "pending", "confirmationNumber": "CNF001"}
        )
        req = FilingRequest(
            case_number="21-cv-1",
            court_id="nysd",
            filing_type="civil_motion",
            documents=[FilingDocument(filename="m.pdf", content=_pdf_bytes())],
        )
        result = c.file_document(req)
        assert result.filing_id == "f123"
        assert result.status == FilingStatus.PENDING

    def test_check_filing_status(self):
        c = self._connector()
        c._session.get.return_value = _mock_response({"status": "accepted", "message": "OK"})
        result = c.check_filing_status("f123")
        assert result.status == FilingStatus.ACCEPTED

    def test_get_confirmation(self):
        c = self._connector()
        c._session.get.return_value = _mock_response(
            {"caseNumber": "21-cv-1", "status": "accepted", "fee": 402.0, "documentsAccepted": ["m.pdf"]}
        )
        conf = c.get_confirmation("f123")
        assert conf.fee_charged == 402.0

    def test_list_accepted_docs(self):
        c = self._connector()
        c._session.get.return_value = _mock_response(
            {"documents": [{"code": "MOT", "description": "Motion", "fee": 0.0}]}
        )
        docs = c.list_accepted_docs("nysd")
        assert docs[0].code == "MOT"

    def test_file_document_invalid_raises(self):
        c = self._connector()
        req = FilingRequest(case_number="", court_id="", filing_type="x", documents=[])
        with pytest.raises(ValueError):
            c.file_document(req)


class TestTylerTechConnector:
    def _connector(self) -> TylerTechConnector:
        c = TylerTechConnector()
        c._session = MagicMock()
        return c

    def test_authenticate(self):
        c = self._connector()
        c._session.headers = MagicMock()
        c.authenticate()
        assert c._session.headers.update.called

    def test_file_document(self):
        c = self._connector()
        c._session.headers = MagicMock()
        # create envelope
        c._session.post.side_effect = [
            _mock_response({"EnvelopeID": "env001"}),
            _mock_response({}),  # attach doc
            _mock_response({"status": "pending", "confirmationNumber": "C001"}),  # submit
        ]
        req = FilingRequest(
            case_number="2024-CIV-001",
            court_id="cook_county",
            filing_type="civil_complaint",
            documents=[FilingDocument(filename="complaint.pdf", content=_pdf_bytes())],
        )
        conf = c.file_document(req)
        assert conf.filing_id == "env001"

    def test_check_filing_status(self):
        c = self._connector()
        c._session.get.return_value = _mock_response({"FilingStatus": "Accepted", "StatusDescription": "Filed"})
        result = c.check_filing_status("env001")
        assert result.status == FilingStatus.ACCEPTED


class TestFileServeXpressConnector:
    def _connector(self) -> FileServeXpressConnector:
        c = FileServeXpressConnector()
        c._session = MagicMock()
        return c

    def test_authenticate(self):
        c = self._connector()
        c._session.post.return_value = _mock_response({"authToken": "fsx_tok"})
        c.authenticate()
        assert c._session_token == "fsx_tok"

    def test_file_document(self):
        c = self._connector()
        c._session_token = "tok"
        c._session.headers = MagicMock()
        c._session.post.return_value = _mock_response({"filingId": "fsx1", "status": "pending", "transactionId": "T1"})
        req = FilingRequest(
            case_number="CA-2024-0001",
            court_id="lasc",
            filing_type="civil_motion",
            documents=[FilingDocument(filename="motion.pdf", content=_pdf_bytes())],
        )
        conf = c.file_document(req)
        assert conf.filing_id == "fsx1"


class TestOdysseyEFileConnector:
    def _connector(self) -> OdysseyEFileConnector:
        c = OdysseyEFileConnector()
        c._session = MagicMock()
        return c

    def test_authenticate(self):
        c = self._connector()
        c._session.headers = MagicMock()
        c.authenticate()
        assert c._session.headers.update.called

    def test_file_document(self):
        c = self._connector()
        c._session.headers = MagicMock()
        c._session.post.return_value = _mock_response(
            {"submissionId": "ody1", "status": "pending", "confirmationCode": "ODY-001"}
        )
        req = FilingRequest(
            case_number="IL-2024-0001",
            court_id="cook",
            filing_type="civil_complaint",
            documents=[FilingDocument(filename="complaint.pdf", content=_pdf_bytes())],
        )
        conf = c.file_document(req)
        assert conf.filing_id == "ody1"


class TestEFilingFactory:
    def test_unknown_system_raises(self):
        with pytest.raises(ValueError, match="Unknown e-filing system"):
            get_efiling_system("unknown_court")

    @patch("legal_integrations.court_efiling.PACERFilingConnector.authenticate")
    def test_get_pacer(self, mock_auth):
        system = get_efiling_system("pacer")
        assert system.name == "pacer"
        mock_auth.assert_called_once()


# ===========================================================================
# LEGAL RESEARCH TESTS
# ===========================================================================


class TestCitationParser:
    def test_parse_standard_citation(self):
        c = parse_citation("410 U.S. 113 (1973)")
        assert c.volume == "410"
        assert c.reporter == "U.S."
        assert c.page == "113"
        assert c.year == "1973"

    def test_parse_federal_circuit(self):
        c = parse_citation("999 F.3d 100 (9th Cir. 2020)")
        assert c.volume == "999"
        assert c.page == "100"

    def test_parse_invalid(self):
        c = parse_citation("not a citation")
        assert not c.is_valid

    def test_validate_citation_valid(self):
        is_valid, parsed = validate_citation("410 U.S. 113 (1973)")
        assert is_valid
        assert parsed.volume == "410"

    def test_validate_citation_invalid(self):
        is_valid, parsed = validate_citation("garbage text")
        assert not is_valid

    def test_citation_is_valid_property(self):
        from legal_integrations.legal_research import LegalCitation
        c = LegalCitation(raw="x", reporter="U.S.", page="100")
        assert c.is_valid
        c2 = LegalCitation(raw="x")
        assert not c2.is_valid


class TestWestlawConnector:
    def _connector(self) -> WestlawEdgeConnector:
        c = WestlawEdgeConnector()
        c._session = MagicMock()
        return c

    def test_authenticate(self):
        c = self._connector()
        c._session.post.return_value = _mock_response({"access_token": "wl_tok"})
        c.authenticate()
        assert c._access_token == "wl_tok"

    def test_search(self):
        c = self._connector()
        c._session.get.return_value = _mock_response(
            {"Results": [{"ID": "wl1", "Title": "Roe v. Wade", "Citation": "410 U.S. 113", "Relevance": 0.99}]}
        )
        results = c.search("abortion rights")
        assert results[0].source == "westlaw"
        assert results[0].citation == "410 U.S. 113"

    def test_get_document(self):
        c = self._connector()
        c._session.get.return_value = _mock_response({"fullText": "...", "ID": "wl1"})
        doc = c.get_document("wl1")
        assert doc.get("ID") == "wl1"

    def test_cite(self):
        c = self._connector()
        c._session.get.return_value = _mock_response(
            {"CitingReferences": [{"ID": "x1", "Title": "Case A"}], "TreatmentFlag": "Positive"}
        )
        result = c.cite("410 U.S. 113")
        assert result.treatment == "positive"
        assert len(result.citing_cases) == 1


class TestLexisNexisConnector:
    def _connector(self) -> LexisNexisConnector:
        c = LexisNexisConnector()
        c._session = MagicMock()
        return c

    def test_authenticate(self):
        c = self._connector()
        c._session.post.return_value = _mock_response({"access_token": "ln_tok"})
        c.authenticate()
        assert c._access_token == "ln_tok"

    def test_search(self):
        c = self._connector()
        c._session.get.return_value = _mock_response(
            {"value": [{"id": "ln1", "name": "Smith v. Jones", "citation": "100 F.3d 200"}]}
        )
        results = c.search("breach of contract")
        assert results[0].source == "lexisnexis"

    def test_cite(self):
        c = self._connector()
        c._session.get.return_value = _mock_response({"citingDocuments": [], "treatment": "neutral"})
        result = c.cite("100 F.3d 200")
        assert result.treatment == "neutral"


class TestFastcaseConnector:
    def _connector(self) -> FastcaseConnector:
        c = FastcaseConnector()
        c._session = MagicMock()
        return c

    def test_authenticate(self):
        c = self._connector()
        c._session.headers = MagicMock()
        c.authenticate()
        assert c._session.headers.update.called

    def test_search(self):
        c = self._connector()
        c._session.get.return_value = _mock_response(
            {"cases": [{"caseId": "fc1", "caseName": "Alpha v. Beta", "relevanceScore": 0.8}]}
        )
        results = c.search("negligence")
        assert results[0].result_id == "fc1"
        assert results[0].score == 0.8


class TestCourtListenerConnector:
    def _connector(self) -> CourtListenerConnector:
        c = CourtListenerConnector()
        c._session = MagicMock()
        return c

    def test_authenticate(self):
        c = self._connector()
        c._session.headers = MagicMock()
        c.authenticate()
        assert c._session.headers.update.called

    def test_search(self):
        c = self._connector()
        c._session.get.return_value = _mock_response(
            {"results": [{"id": 99, "caseName": "US v. Doe", "citation": ["99 F.3d 1"], "score": 1.5}]}
        )
        results = c.search("criminal procedure")
        assert results[0].result_id == "99"

    def test_cite(self):
        c = self._connector()
        c._session.get.side_effect = [
            _mock_response({"results": [{"id": 1}]}),
            _mock_response({"results": [{"id": 2, "case_name": "Citing Case"}]}),
        ]
        result = c.cite("410 U.S. 113")
        assert len(result.citing_cases) == 1


class TestGoogleScholarConnector:
    def _connector(self) -> GoogleScholarLegalConnector:
        c = GoogleScholarLegalConnector(request_delay=0)
        c._session = MagicMock()
        return c

    def test_authenticate_no_op(self):
        c = self._connector()
        c.authenticate()  # should not raise

    def test_search_no_beautifulsoup(self):
        c = self._connector()
        # Without beautifulsoup4, returns empty list
        import importlib
        with patch.dict("sys.modules", {"bs4": None}):
            results = c.search("constitutional law")
            assert results == []

    def test_get_document(self):
        c = self._connector()
        c._session.get.return_value = _mock_response(content=b"<html>case text</html>")
        result = c.get_document("123456")
        assert "url" in result


class TestUnifiedLegalSearch:
    def test_search_empty_connectors(self):
        unified = UnifiedLegalSearch()
        result = unified.search("test query")
        assert result.total_found == 0
        assert result.results == []

    def test_search_aggregates_results(self):
        mock_connector = MagicMock()
        mock_connector.name = "mock_source"
        mock_connector.search.return_value = [
            ResearchResult(source="mock_source", result_id="1", title="Case A", score=0.9),
            ResearchResult(source="mock_source", result_id="2", title="Case B", score=0.5),
        ]
        unified = UnifiedLegalSearch(connectors=[mock_connector])
        result = unified.search("test")
        assert result.total_found == 2
        assert result.results[0].score >= result.results[1].score  # sorted

    def test_search_handles_connector_error(self):
        mock_connector = MagicMock()
        mock_connector.name = "failing_source"
        mock_connector.search.side_effect = Exception("API error")
        unified = UnifiedLegalSearch(connectors=[mock_connector])
        result = unified.search("test")
        assert "failing_source" in result.errors
        assert result.total_found == 0

    def test_cite_all(self):
        mock_connector = MagicMock()
        mock_connector.name = "src1"
        mock_connector.cite.return_value = CitatorResult(source_citation="410 U.S. 113")
        unified = UnifiedLegalSearch(connectors=[mock_connector])
        results = unified.cite_all("410 U.S. 113")
        assert "src1" in results

    def test_add_connector(self):
        unified = UnifiedLegalSearch()
        mock_connector = MagicMock()
        mock_connector.name = "new_source"
        unified.add_connector(mock_connector)
        assert len(unified._connectors) == 1

    @patch("legal_integrations.legal_research.get_research_connector")
    def test_build_unified_search(self, mock_get):
        mock_get.return_value = MagicMock(name="mock")
        unified = build_unified_search(sources=["westlaw"])
        assert isinstance(unified, UnifiedLegalSearch)

    def test_research_factory_unknown(self):
        with pytest.raises(ValueError):
            get_research_connector("unknown_source")


# ===========================================================================
# FINANCIAL CONNECTOR TESTS
# ===========================================================================


class TestPlaidConnector:
    def _connector(self) -> PlaidConnector:
        c = PlaidConnector()
        c._session = MagicMock()
        return c

    def test_get_accounts(self):
        c = self._connector()
        c._session.post.return_value = _mock_response(
            {
                "accounts": [
                    {"account_id": "acc1", "name": "Checking", "type": "depository", "balances": {"current": 1000.0, "available": 900.0, "iso_currency_code": "USD"}},
                ],
                "item": {"institution_id": "chase"},
            }
        )
        accounts = c.get_accounts("access_token_xyz")
        assert accounts[0].account_id == "acc1"
        assert accounts[0].balance_current == 1000.0

    def test_create_asset_report(self):
        c = self._connector()
        c._session.post.return_value = _mock_response({"asset_report_token": "assets_token_123"})
        token = c.create_asset_report(["access_token_xyz"])
        assert token == "assets_token_123"

    def test_get_asset_report(self):
        c = self._connector()
        c._session.post.return_value = _mock_response(
            {
                "report": {
                    "report_id": "rpt1",
                    "items": [
                        {
                            "accounts": [
                                {"account_id": "a1", "name": "Savings", "type": "depository", "balances": {"current": 5000.0, "iso_currency_code": "USD"}},
                            ]
                        }
                    ],
                }
            }
        )
        report = c.get_asset_report("tok123")
        assert report.report_id == "rpt1"
        assert report.total_assets == 5000.0

    def test_get_transactions(self):
        c = self._connector()
        c._session.post.return_value = _mock_response({"transactions": [{"id": "txn1", "amount": 50.0}]})
        txns = c.get_transactions("access_token", "2024-01-01", "2024-12-31")
        assert len(txns) == 1


class TestYodleeConnector:
    def _connector(self) -> YodleeConnector:
        c = YodleeConnector()
        c._session = MagicMock()
        return c

    def test_authenticate(self):
        c = self._connector()
        c._session.post.return_value = _mock_response({"token": {"accessToken": "y_tok"}})
        c.authenticate()
        assert c._access_token == "y_tok"

    def test_get_accounts(self):
        c = self._connector()
        c._session.headers = MagicMock()
        c._session.get.return_value = _mock_response(
            {"account": [{"id": 1, "accountName": "Bank A", "balance": {"amount": 200.0, "currency": "USD"}}]}
        )
        accounts = c.get_accounts("user_session_tok")
        assert accounts[0].account_id == "1"


class TestFinicityConnector:
    def _connector(self) -> FinicityConnector:
        c = FinicityConnector()
        c._session = MagicMock()
        return c

    def test_authenticate(self):
        c = self._connector()
        c._session.headers = MagicMock()
        c._session.post.return_value = _mock_response({"token": "fin_tok"})
        c.authenticate()
        assert c._access_token == "fin_tok"

    def test_get_accounts(self):
        c = self._connector()
        c._session.get.return_value = _mock_response(
            {"accounts": [{"id": 1001, "name": "Checking", "type": "checking", "balance": 750.0}]}
        )
        accounts = c.get_accounts("cust123")
        assert accounts[0].account_id == "1001"


class TestEDGARConnector:
    def _connector(self) -> EDGARConnector:
        c = EDGARConnector()
        c._session = MagicMock()
        return c

    def test_get_company_cik(self):
        c = self._connector()
        c._session.get.return_value = _mock_response(
            {"hits": {"hits": [{"_source": {"entity_id": "0000320193"}}]}}
        )
        cik = c.get_company_cik("Apple Inc.")
        assert cik == "0000320193"

    def test_get_company_cik_not_found(self):
        c = self._connector()
        c._session.get.return_value = _mock_response({"hits": {"hits": []}})
        cik = c.get_company_cik("NonExistentCorp")
        assert cik is None

    def test_get_submissions(self):
        c = self._connector()
        c._session.get.return_value = _mock_response({"name": "Apple Inc.", "cik": "0000320193"})
        result = c.get_submissions("0000320193")
        assert result["name"] == "Apple Inc."

    def test_search_filings(self):
        c = self._connector()
        # Mock get_company_cik
        c._session.get.side_effect = [
            _mock_response({"hits": {"hits": [{"_source": {"entity_id": "0000320193"}}]}}),
            _mock_response({
                "name": "Apple Inc.",
                "filings": {
                    "recent": {
                        "form": ["10-K", "10-Q"],
                        "accessionNumber": ["0000320193-24-000001", "0000320193-24-000002"],
                        "filingDate": ["2024-10-31", "2024-07-31"],
                    }
                },
            }),
        ]
        filings = c.search_filings(company_name="Apple Inc.", form_type="10-K")
        assert len(filings) == 1
        assert filings[0].form_type == "10-K"

    def test_get_company_facts(self):
        c = self._connector()
        c._session.get.return_value = _mock_response({"facts": {"us-gaap": {}}})
        facts = c.get_company_facts("0000320193")
        assert "facts" in facts


class TestBloombergLawConnector:
    def _connector(self) -> BloombergLawConnector:
        c = BloombergLawConnector()
        c._session = MagicMock()
        return c

    def test_authenticate(self):
        c = self._connector()
        c._session.headers = MagicMock()
        c.authenticate()
        assert c._session.headers.update.called

    def test_get_company_financials(self):
        c = self._connector()
        c._session.get.return_value = _mock_response({"ticker": "AAPL", "revenue": 394e9})
        data = c.get_company_financials("AAPL")
        assert data.get("ticker") == "AAPL"

    def test_get_dockets(self):
        c = self._connector()
        c._session.get.return_value = _mock_response({"dockets": [{"id": "d1"}]})
        dockets = c.get_dockets("Apple")
        assert len(dockets) == 1


class TestPACERBankruptcyConnector:
    def _connector(self) -> PACERBankruptcyConnector:
        c = PACERBankruptcyConnector()
        c._session = MagicMock()
        return c

    def test_authenticate(self):
        c = self._connector()
        c._session.post.return_value = _mock_response({"nextGenCSO": "pacer_bk_tok"})
        c.authenticate()
        assert c._token == "pacer_bk_tok"

    def test_search_cases(self):
        c = self._connector()
        c._session.get.return_value = _mock_response(
            {"content": [{"caseId": "bk1", "partyName": "John Doe", "chapter": "7", "dateFiled": "2024-01-15"}]}
        )
        cases = c.search_cases(debtor_name="John Doe")
        assert cases[0].debtor_name == "John Doe"
        assert cases[0].chapter == "7"

    def test_get_case_detail(self):
        c = self._connector()
        c._session.get.return_value = _mock_response({"caseId": "bk1", "status": "discharged"})
        detail = c.get_case_detail("bk1")
        assert detail["status"] == "discharged"

    def test_get_case_docket(self):
        c = self._connector()
        c._session.get.return_value = _mock_response(
            {"docketEntries": [{"entryNumber": 1, "description": "Petition filed"}]}
        )
        docket = c.get_case_docket("bk1")
        assert len(docket) == 1

    def test_search_assets(self):
        c = self._connector()
        c._session.get.return_value = _mock_response(
            {"assets": [{"assetId": "a1", "description": "Real estate", "value": 150000.0}]}
        )
        assets = c.search_assets("bk1")
        assert assets[0]["description"] == "Real estate"


# ===========================================================================
# INTEGRATIONS API TESTS
# ===========================================================================


class TestIntegrationsAPI:
    """Tests for the FastAPI router — uses TestClient if available."""

    @pytest.fixture(autouse=True)
    def _check_fastapi(self):
        pytest.importorskip("fastapi", reason="fastapi not installed")
        pytest.importorskip("httpx", reason="httpx not installed")

    @pytest.fixture
    def client(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from legal_integrations.integrations_api import router
        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    def test_dms_connect_unknown_platform(self, client):
        resp = client.post("/integrations/dms/connect", json={"platform": "unknown_platform"})
        assert resp.status_code == 400

    @patch("legal_integrations.integrations_api.get_dms_connector")
    def test_dms_connect_success(self, mock_factory, client):
        mock_connector = MagicMock()
        mock_connector.name = "clio"
        mock_factory.return_value = mock_connector
        resp = client.post("/integrations/dms/connect", json={"platform": "clio"})
        assert resp.status_code == 200
        assert resp.json()["connected"] is True

    def test_research_search_empty_query(self, client):
        resp = client.post("/integrations/research/search", json={"query": ""})
        assert resp.status_code == 422  # Pydantic validation error

    @patch("legal_integrations.integrations_api.build_unified_search")
    def test_research_search_success(self, mock_build, client):
        mock_unified = MagicMock()
        mock_unified.search.return_value = UnifiedSearchResult(
            query="negligence", total_found=1,
            results=[ResearchResult(source="fastcase", result_id="1", title="Case A")],
        )
        mock_build.return_value = mock_unified
        resp = client.post("/integrations/research/search", json={"query": "negligence"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_found"] == 1

    def test_citation_validate_valid(self, client):
        resp = client.post(
            "/integrations/research/cite/validate",
            json={"citation": "410 U.S. 113 (1973)"},
        )
        assert resp.status_code == 200
        assert resp.json()["is_valid"] is True

    def test_citation_validate_invalid(self, client):
        resp = client.post(
            "/integrations/research/cite/validate",
            json={"citation": "not a real citation"},
        )
        assert resp.status_code == 200
        assert resp.json()["is_valid"] is False

    def test_court_status_missing_system(self, client):
        """Should try to create system connector; fails gracefully."""
        resp = client.get("/integrations/court/status/filing123?system=unknown_sys")
        assert resp.status_code in (400, 503)

    @patch("legal_integrations.integrations_api.EDGARConnector")
    def test_edgar_filings_no_params(self, mock_edgar, client):
        resp = client.get("/integrations/financial/edgar/filings")
        assert resp.status_code == 400

    @patch("legal_integrations.integrations_api.EDGARConnector")
    def test_edgar_filings_with_company(self, mock_edgar_cls, client):
        mock_edgar = MagicMock()
        mock_edgar.search_filings.return_value = [
            SECFiling(accession_number="001", company_name="Apple", cik="320193", form_type="10-K")
        ]
        mock_edgar_cls.return_value = mock_edgar
        resp = client.get("/integrations/financial/edgar/filings?company_name=Apple")
        assert resp.status_code == 200
        assert resp.json()["count"] == 1
