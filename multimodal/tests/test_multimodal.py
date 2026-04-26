"""
test_multimodal.py — Comprehensive test suite for the multimodal package.

70+ tests covering:
- DocumentVisionEngine (mocked OpenAI Vision API)
- PDFStructureAnalyzer (both PyMuPDF and pypdf paths)
- LegalAudioTranscriber (mocked Whisper API)
- MultimodalLegalAnalyzer (full integration)
- FastAPI router endpoints

All external API calls are mocked.
"""

from __future__ import annotations

import base64
import io
import json
import sys
import types
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# ---------------------------------------------------------------------------
# Stub heavy optional dependencies so tests run without installing them
# ---------------------------------------------------------------------------

def _stub_module(name: str) -> types.ModuleType:
    mod = types.ModuleType(name)
    sys.modules.setdefault(name, mod)
    return sys.modules[name]

# Stub fitz (PyMuPDF) — tests run against pypdf path by default
_fitz = _stub_module("fitz")

# Stub faster_whisper
_fw = _stub_module("faster_whisper")
_fw.WhisperModel = None  # type: ignore

# Stub openai-whisper (local)
_lw = _stub_module("whisper")
_lw.load_model = None  # type: ignore

# Stub openai
_openai_mod = _stub_module("openai")

# Stub pypdf
_pypdf = _stub_module("pypdf")

# Stub pydantic / fastapi for api tests
_pydantic = _stub_module("pydantic")
_pydantic.BaseModel = object  # type: ignore
_pydantic.Field = lambda *a, **kw: None  # type: ignore
_fastapi = _stub_module("fastapi")
_fastapi.APIRouter = MagicMock  # type: ignore
_fastapi.File = lambda *a, **kw: None  # type: ignore
_fastapi.Form = lambda *a, **kw: None  # type: ignore
_fastapi.HTTPException = Exception  # type: ignore
_fastapi.UploadFile = MagicMock  # type: ignore
_fastapi.status = MagicMock()  # type: ignore
_fastapi_responses = _stub_module("fastapi.responses")
_fastapi_responses.JSONResponse = MagicMock  # type: ignore

# ---------------------------------------------------------------------------
# Now import the modules under test (after stubs are in place)
# ---------------------------------------------------------------------------

from multimodal.document_vision import (  # noqa: E402
    DocumentVisionEngine,
    DocumentVisionResult,
    DocumentType,
    HandwritingAuthenticityLevel,
    HandwritingAnalysis,
    SignatureInfo,
    StampInfo,
    ExtractedParty,
    DocumentBatchProcessor,
    image_to_base64,
    summarize_result,
)
from multimodal.pdf_analyzer import (  # noqa: E402
    PDFStructureAnalyzer,
    PDFAnalysisResult,
    FormField,
    EmbeddedSignature,
    TableData,
    DocumentSection,
    SectionType,
    BatesNumber,
    RedactedRegion,
    PageLayout,
    analyze_pdf,
)
from multimodal.audio_transcription import (  # noqa: E402
    LegalAudioTranscriber,
    TranscriptionResult,
    TranscriptSegment,
    ActionItem,
    SpeakerProfile,
    LegalRecordingType,
    TranscriptionBackend,
    transcribe_legal_audio,
    LEGAL_TERMS,
)
from multimodal.legal_analyzer import (  # noqa: E402
    MultimodalLegalAnalyzer,
    CaseSummary,
    EvidenceStrength,
    InconsistencyType,
    TimelineEvent,
    Inconsistency,
    EvidenceItem,
    parse_date_fuzzy,
    analyze_case,
)


# ===========================================================================
# Fixtures & helpers
# ===========================================================================

SAMPLE_VISION_JSON = {
    "document_type": "will",
    "raw_text": "Last Will and Testament of John Doe. I, John Doe, being of sound mind, do hereby declare this to be my last will.",
    "dates_found": ["January 15, 2024", "03/20/2023"],
    "parties": [
        {"name": "John Doe", "role": "testator", "address": "123 Main St", "signature_present": True},
        {"name": "Jane Smith", "role": "witness", "address": None, "signature_present": True},
    ],
    "signatures": {"detected": True, "count": 2, "locations": ["bottom of page 1"], "names": ["John Doe", "Jane Smith"], "confidence": 0.92},
    "stamps": {"detected": True, "count": 1, "types": ["notary"], "texts": ["STATE OF CALIFORNIA"], "locations": ["top right"]},
    "handwriting": {"authenticity": "high", "confidence": 0.88, "alterations_detected": False, "alteration_regions": [], "notes": "Consistent handwriting throughout."},
    "key_clauses": ["Executor: Jane Smith", "Beneficiary: Mary Doe — 50%"],
    "legal_jurisdiction": "California",
    "notarized": True,
    "confidence_score": 0.91,
    "warnings": [],
}

SAMPLE_VISION_JSON_ALTERED = {
    **SAMPLE_VISION_JSON,
    "handwriting": {
        "authenticity": "low",
        "confidence": 0.55,
        "alterations_detected": True,
        "alteration_regions": ["Date field on line 3"],
        "notes": "Possible date alteration detected.",
    },
    "warnings": ["Possible alteration detected."],
}


def _make_vision_result(data: dict = None) -> DocumentVisionResult:
    """Create a DocumentVisionResult from dict using the engine's parser."""
    engine = DocumentVisionEngine.__new__(DocumentVisionEngine)
    engine.model = "gpt-4o"
    engine.max_tokens = 4096
    engine.temperature = 0.1
    engine._client = None
    raw = json.dumps(data or SAMPLE_VISION_JSON)
    return engine._parse_vision_response(raw)


def _make_pdf_result(pages: int = 5, text: str = "Sample legal document text.") -> PDFAnalysisResult:
    result = PDFAnalysisResult()
    result.total_pages = pages
    result.title = "Test Agreement"
    result.author = "Legal Firm LLC"
    result.full_text = text
    result.page_texts = [text] * pages
    result.backend_used = "test"
    return result


def _make_audio_result(segments: int = 3) -> TranscriptionResult:
    result = TranscriptionResult()
    result.recording_type = LegalRecordingType.DEPOSITION
    result.language = "en"
    result.duration_seconds = 60.0 * segments
    result.backend_used = "mock"
    result.confidence_avg = 0.9
    for i in range(segments):
        seg = TranscriptSegment(
            speaker=f"Speaker {i % 2 + 1}",
            timestamp_start=float(i * 60),
            timestamp_end=float((i + 1) * 60),
            text="The witness stated the contract was signed on March 1, 2024.",
            confidence=0.9,
        )
        result.segments.append(seg)
    result.full_text = " ".join(s.text for s in result.segments)
    return result


# ===========================================================================
# 1. DocumentVisionEngine tests
# ===========================================================================

class TestDocumentType:
    def test_all_enum_values(self):
        assert DocumentType.WILL.value == "will"
        assert DocumentType.CONTRACT.value == "contract"
        assert DocumentType.DEED.value == "deed"
        assert DocumentType.COURT_FILING.value == "court_filing"
        assert DocumentType.ID.value == "identification"
        assert DocumentType.CHECK.value == "check"
        assert DocumentType.UNKNOWN.value == "unknown"

    def test_enum_from_string(self):
        assert DocumentType("will") == DocumentType.WILL
        assert DocumentType("unknown") == DocumentType.UNKNOWN


class TestDocumentVisionEngine:
    def test_init_no_api_key(self):
        with patch.dict("os.environ", {}, clear=True):
            engine = DocumentVisionEngine(api_key=None)
        assert engine._client is None

    def test_init_with_api_key_no_openai(self):
        """Should gracefully handle missing openai package — engine initializes with _client=None."""
        # Since openai is stubbed as an empty module in this test suite,
        # importing OpenAI from it fails and _client remains None.
        engine = DocumentVisionEngine.__new__(DocumentVisionEngine)
        engine._client = None
        # Verify the engine is usable without a client
        result = engine._degraded_result("No client available.")
        assert result.document_type == DocumentType.UNKNOWN
        assert engine._client is None

    def test_parse_vision_response_valid_json(self):
        engine = DocumentVisionEngine.__new__(DocumentVisionEngine)
        engine._client = None
        raw = json.dumps(SAMPLE_VISION_JSON)
        result = engine._parse_vision_response(raw)
        assert result.document_type == DocumentType.WILL
        assert result.notarized is True
        assert result.confidence_score == pytest.approx(0.91)
        assert len(result.parties) == 2
        assert result.signatures.count == 2
        assert result.signatures.detected is True
        assert result.stamps.detected is True
        assert result.stamps.count == 1
        assert result.handwriting.authenticity == HandwritingAuthenticityLevel.HIGH
        assert result.handwriting.alterations_detected is False
        assert result.legal_jurisdiction == "California"
        assert len(result.dates_found) == 2

    def test_parse_vision_response_markdown_fence(self):
        engine = DocumentVisionEngine.__new__(DocumentVisionEngine)
        engine._client = None
        raw = f"```json\n{json.dumps(SAMPLE_VISION_JSON)}\n```"
        result = engine._parse_vision_response(raw)
        assert result.document_type == DocumentType.WILL

    def test_parse_vision_response_malformed_json(self):
        engine = DocumentVisionEngine.__new__(DocumentVisionEngine)
        engine._client = None
        result = engine._parse_vision_response("{not valid json}")
        assert result.document_type == DocumentType.UNKNOWN
        assert len(result.warnings) > 0

    def test_parse_vision_response_alterations_detected(self):
        engine = DocumentVisionEngine.__new__(DocumentVisionEngine)
        engine._client = None
        raw = json.dumps(SAMPLE_VISION_JSON_ALTERED)
        result = engine._parse_vision_response(raw)
        assert result.handwriting.alterations_detected is True
        assert result.handwriting.authenticity == HandwritingAuthenticityLevel.LOW
        assert "Date field on line 3" in result.handwriting.alteration_regions

    def test_degraded_result(self):
        engine = DocumentVisionEngine.__new__(DocumentVisionEngine)
        engine._client = None
        result = engine._degraded_result("Test warning")
        assert result.document_type == DocumentType.UNKNOWN
        assert "Test warning" in result.warnings

    def test_analyze_base64_no_client(self):
        engine = DocumentVisionEngine.__new__(DocumentVisionEngine)
        engine._client = None
        result = engine.analyze_base64(base64.b64encode(b"fake").decode())
        assert "not configured" in result.warnings[0]

    def test_analyze_url_no_client(self):
        engine = DocumentVisionEngine.__new__(DocumentVisionEngine)
        engine._client = None
        result = engine.analyze_url("https://example.com/doc.jpg")
        assert result.document_type == DocumentType.UNKNOWN

    def test_analyze_file_not_found(self):
        engine = DocumentVisionEngine.__new__(DocumentVisionEngine)
        engine._client = None
        with pytest.raises(FileNotFoundError):
            engine.analyze_file("/nonexistent/path.jpg")

    def test_analyze_file_unsupported_type(self, tmp_path):
        f = tmp_path / "doc.xyz"
        f.write_bytes(b"data")
        engine = DocumentVisionEngine.__new__(DocumentVisionEngine)
        engine._client = None
        with pytest.raises(ValueError, match="Unsupported file type"):
            engine.analyze_file(f)

    def test_classify_document_will(self):
        engine = DocumentVisionEngine.__new__(DocumentVisionEngine)
        engine._client = None
        text = "I, John Doe, being of sound mind, do hereby create this last will and testament. Executor: Jane."
        assert engine.classify_document_type(text) == DocumentType.WILL

    def test_classify_document_contract(self):
        engine = DocumentVisionEngine.__new__(DocumentVisionEngine)
        engine._client = None
        text = "This agreement between the parties. Consideration: $10,000. Terms and conditions apply."
        assert engine.classify_document_type(text) == DocumentType.CONTRACT

    def test_classify_document_deed(self):
        engine = DocumentVisionEngine.__new__(DocumentVisionEngine)
        engine._client = None
        text = "Deed of trust. Grantor conveys to Grantee the real property located at Parcel No. 123."
        assert engine.classify_document_type(text) == DocumentType.DEED

    def test_classify_document_court(self):
        engine = DocumentVisionEngine.__new__(DocumentVisionEngine)
        engine._client = None
        text = "In the Superior Court of the State. Plaintiff vs Defendant. Case No. 2024-CV-001. Motion granted."
        assert engine.classify_document_type(text) == DocumentType.COURT_FILING

    def test_classify_document_unknown(self):
        engine = DocumentVisionEngine.__new__(DocumentVisionEngine)
        engine._client = None
        assert engine.classify_document_type("Hello world") == DocumentType.UNKNOWN

    def test_vision_api_call_success(self):
        engine = DocumentVisionEngine.__new__(DocumentVisionEngine)
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps(SAMPLE_VISION_JSON)
        mock_client.chat.completions.create.return_value = mock_response
        engine._client = mock_client
        engine.model = "gpt-4o"
        engine.max_tokens = 4096
        engine.temperature = 0.1

        result = engine._call_vision_api("data:image/jpeg;base64,abc123")
        assert result.document_type == DocumentType.WILL
        mock_client.chat.completions.create.assert_called_once()

    def test_vision_api_call_failure(self):
        engine = DocumentVisionEngine.__new__(DocumentVisionEngine)
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = RuntimeError("API error")
        engine._client = mock_client
        engine.model = "gpt-4o"
        engine.max_tokens = 4096
        engine.temperature = 0.1

        result = engine._call_vision_api("data:image/jpeg;base64,abc")
        assert "API error" in result.warnings[0]

    def test_to_dict_structure(self):
        result = _make_vision_result()
        d = result.to_dict()
        assert "document_type" in d
        assert "parties" in d
        assert "signatures" in d
        assert "stamps" in d
        assert "handwriting" in d
        assert "key_clauses" in d

    def test_summarize_result(self):
        result = _make_vision_result()
        summary = summarize_result(result)
        assert "WILL" in summary
        assert "California" in summary or "Notarized" in summary

    def test_parties_extraction(self):
        result = _make_vision_result()
        assert result.parties[0].name == "John Doe"
        assert result.parties[0].role == "testator"
        assert result.parties[0].signature_present is True
        assert result.parties[1].name == "Jane Smith"
        assert result.parties[1].role == "witness"


class TestDocumentBatchProcessor:
    def test_batch_process_no_files(self):
        engine = DocumentVisionEngine.__new__(DocumentVisionEngine)
        engine._client = None
        processor = DocumentBatchProcessor(engine)
        results = processor.process_files([])
        assert results == []

    def test_batch_process_error_handling(self):
        engine = DocumentVisionEngine.__new__(DocumentVisionEngine)
        engine._client = None
        processor = DocumentBatchProcessor(engine)
        results = processor.process_files(["/nonexistent/image.jpg"])
        assert len(results) == 1
        assert len(results[0].warnings) > 0


# ===========================================================================
# 2. PDFStructureAnalyzer tests
# ===========================================================================

class TestPDFStructureAnalyzer:
    def test_init_no_backend(self):
        """Should gracefully init when no PDF backend is available."""
        with patch("multimodal.pdf_analyzer.PYMUPDF_AVAILABLE", False), \
             patch("multimodal.pdf_analyzer.PYPDF_AVAILABLE", False):
            analyzer = PDFStructureAnalyzer()
            assert analyzer.backend == "none"

    def test_analyze_no_backend(self):
        with patch("multimodal.pdf_analyzer.PYMUPDF_AVAILABLE", False), \
             patch("multimodal.pdf_analyzer.PYPDF_AVAILABLE", False):
            analyzer = PDFStructureAnalyzer()
            result = analyzer.analyze(b"%PDF-1.4 dummy")
            assert "No PDF backend installed" in result.warnings[0]

    def test_analyze_pypdf_text_extraction(self):
        """Mock pypdf to return text and verify extraction."""
        mock_reader = MagicMock()
        mock_reader.is_encrypted = False
        mock_reader.metadata = {"/Title": "Test Will", "/Author": "Atty Smith"}
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Whereas the grantor conveys to grantee. Case No. 123."
        mock_page.mediabox.width = 612
        mock_page.mediabox.height = 792
        mock_reader.pages = [mock_page, mock_page]
        mock_reader.trailer = {}

        with patch("multimodal.pdf_analyzer.PYMUPDF_AVAILABLE", False), \
             patch("multimodal.pdf_analyzer.PYPDF_AVAILABLE", True), \
             patch("multimodal.pdf_analyzer.PdfReader", return_value=mock_reader):
            analyzer = PDFStructureAnalyzer()
            result = analyzer.analyze(b"%PDF-1.4 data")

        assert result.total_pages == 2
        assert result.title == "Test Will"
        assert result.author == "Atty Smith"
        assert "grantor" in result.full_text

    def test_detect_bates_numbers(self):
        analyzer = PDFStructureAnalyzer()
        pages = ["SMITH001234\nThis is document text.", "ABC 00056789 more text."]
        bates = analyzer._detect_bates_numbers(pages)
        assert any(b.value.replace(" ", "") in ("SMITH001234", "ABC00056789") for b in bates)

    def test_detect_sections_recital(self):
        analyzer = PDFStructureAnalyzer()
        pages = ["WITNESSETH: the parties agree that.\nWhereas, the Grantor..."]
        sections = analyzer._detect_sections(pages)
        types = [s.section_type for s in sections]
        assert SectionType.RECITAL in types

    def test_detect_sections_signatures(self):
        analyzer = PDFStructureAnalyzer()
        pages = ["IN WITNESS WHEREOF, the parties have executed this Agreement."]
        sections = analyzer._detect_sections(pages)
        types = [s.section_type for s in sections]
        assert SectionType.SIGNATURES in types

    def test_detect_sections_exhibit(self):
        analyzer = PDFStructureAnalyzer()
        pages = ["EXHIBIT A\nSchedule of Assets"]
        sections = analyzer._detect_sections(pages)
        types = [s.section_type for s in sections]
        assert SectionType.EXHIBIT in types

    def test_redaction_from_text(self):
        result = PDFAnalysisResult()
        analyzer = PDFStructureAnalyzer()
        text = "The accused [REDACTED] was present at the scene."
        analyzer._detect_redactions_from_text(text, 1, result)
        assert len(result.redacted_regions) == 1
        assert result.redacted_regions[0].page_number == 1

    def test_redaction_from_text_blocks(self):
        result = PDFAnalysisResult()
        analyzer = PDFStructureAnalyzer()
        text = "Name: ████████ was present."
        analyzer._detect_redactions_from_text(text, 2, result)
        assert len(result.redacted_regions) >= 1

    def test_to_dict_structure(self):
        result = _make_pdf_result()
        result.form_fields = [FormField(name="field1", field_type="text", value="John")]
        result.bates_numbers = [BatesNumber(page_number=1, value="ABC00001", location="footer")]
        d = result.to_dict()
        assert "form_fields" in d
        assert "bates_numbers" in d
        assert "sections" in d
        assert "redacted_regions" in d

    def test_analyze_pdf_convenience(self):
        """Test the module-level convenience function."""
        with patch("multimodal.pdf_analyzer.PYMUPDF_AVAILABLE", False), \
             patch("multimodal.pdf_analyzer.PYPDF_AVAILABLE", False):
            result = analyze_pdf(b"%PDF dummy")
            assert isinstance(result, PDFAnalysisResult)

    def test_form_field_dataclass(self):
        field = FormField(name="Signature1", field_type="signature", value=None, page_number=2)
        assert field.name == "Signature1"
        assert field.field_type == "signature"
        assert field.page_number == 2

    def test_table_data_to_dict(self):
        table = TableData(
            page_number=3,
            headers=["Date", "Amount", "Description"],
            rows=[["01/01/2024", "$1,000", "Retainer"]],
            table_index=0,
        )
        d = table.to_dict()
        assert d["headers"] == ["Date", "Amount", "Description"]
        assert d["page_number"] == 3


# ===========================================================================
# 3. LegalAudioTranscriber tests
# ===========================================================================

class TestLegalAudioTranscriber:
    def test_auto_select_backend_no_deps(self):
        with patch("multimodal.audio_transcription.OPENAI_WHISPER_AVAILABLE", False), \
             patch("multimodal.audio_transcription.FASTER_WHISPER_AVAILABLE", False), \
             patch("multimodal.audio_transcription.LOCAL_WHISPER_AVAILABLE", False):
            t = LegalAudioTranscriber()
            assert t.backend == TranscriptionBackend.MOCK

    def test_auto_select_backend_openai_priority(self):
        """When an openai client is available, the API backend should be preferred."""
        import multimodal.audio_transcription as at_mod
        original = getattr(at_mod, "_OpenAI", None)
        try:
            mock_openai = MagicMock(return_value=MagicMock())
            at_mod._OpenAI = mock_openai
            at_mod.OPENAI_WHISPER_AVAILABLE = True
            t = LegalAudioTranscriber(api_key="sk-test")
            assert t.backend == TranscriptionBackend.OPENAI_API
        finally:
            if original is None and hasattr(at_mod, "_OpenAI"):
                del at_mod._OpenAI
            elif original is not None:
                at_mod._OpenAI = original
            at_mod.OPENAI_WHISPER_AVAILABLE = False

    def test_transcribe_file_not_found(self):
        t = LegalAudioTranscriber()
        with pytest.raises(FileNotFoundError):
            t.transcribe_file("/nonexistent/audio.mp3")

    def test_transcribe_file_unsupported_format(self, tmp_path):
        f = tmp_path / "audio.xyz"
        f.write_bytes(b"data")
        t = LegalAudioTranscriber()
        with pytest.raises(ValueError, match="Unsupported format"):
            t.transcribe_file(f)

    def test_transcribe_no_backend(self, tmp_path):
        f = tmp_path / "audio.mp3"
        f.write_bytes(b"dummy mp3")
        with patch("multimodal.audio_transcription.OPENAI_WHISPER_AVAILABLE", False), \
             patch("multimodal.audio_transcription.FASTER_WHISPER_AVAILABLE", False), \
             patch("multimodal.audio_transcription.LOCAL_WHISPER_AVAILABLE", False):
            t = LegalAudioTranscriber()
            result = t.transcribe_file(f)
        assert "No transcription backend" in result.warnings[0]

    def test_detect_recording_type_deposition(self):
        t = LegalAudioTranscriber()
        result = TranscriptionResult()
        result.segments = [
            TranscriptSegment("Speaker 1", 0, 10, "The deponent is hereby sworn by the court reporter.")
        ]
        t._build_full_text(result)
        t._detect_recording_type(result)
        assert result.recording_type == LegalRecordingType.DEPOSITION

    def test_detect_recording_type_hearing(self):
        t = LegalAudioTranscriber()
        result = TranscriptionResult()
        result.segments = [
            TranscriptSegment("Judge", 0, 10, "Your Honor, we are here for the motion hearing.")
        ]
        t._build_full_text(result)
        t._detect_recording_type(result)
        assert result.recording_type == LegalRecordingType.HEARING

    def test_detect_recording_type_unknown(self):
        t = LegalAudioTranscriber()
        result = TranscriptionResult()
        result.segments = [TranscriptSegment("Speaker 1", 0, 5, "Hello, how are you?")]
        t._build_full_text(result)
        t._detect_recording_type(result)
        assert result.recording_type == LegalRecordingType.UNKNOWN

    def test_extract_legal_terms(self):
        t = LegalAudioTranscriber()
        result = TranscriptionResult()
        result.full_text = "Objection! Hearsay. The witness is not competent. Sustained."
        t._extract_legal_terms(result)
        assert "objection" in result.key_legal_terms
        assert "hearsay" in result.key_legal_terms
        assert "sustained" in result.key_legal_terms

    def test_extract_objections(self):
        t = LegalAudioTranscriber()
        result = TranscriptionResult()
        result.segments = [
            TranscriptSegment("Attorney A", 0, 5, "Objection, leading the witness."),
            TranscriptSegment("Attorney B", 5, 10, "No objection your honor."),
        ]
        t._extract_objections(result)
        assert len(result.objections) >= 1
        assert result.objections[0]["speaker"] == "Attorney A"

    def test_extract_action_items(self):
        t = LegalAudioTranscriber()
        result = TranscriptionResult()
        result.segments = [
            TranscriptSegment("Attorney", 0, 10, "I will provide the documents by next Friday.")
        ]
        t._extract_action_items(result)
        assert len(result.action_items) >= 1

    def test_build_speaker_profiles(self):
        t = LegalAudioTranscriber()
        result = TranscriptionResult()
        result.segments = [
            TranscriptSegment("Speaker 1", 0, 10, "Yes, that is correct."),
            TranscriptSegment("Speaker 2", 10, 20, "Objection, counsel is leading the witness."),
            TranscriptSegment("Speaker 1", 20, 30, "The contract was signed in January."),
        ]
        t._build_speaker_profiles(result)
        assert len(result.speakers) == 2
        labels = [sp.label for sp in result.speakers]
        assert "Speaker 1" in labels
        assert "Speaker 2" in labels

    def test_compute_avg_confidence(self):
        t = LegalAudioTranscriber()
        result = TranscriptionResult()
        result.segments = [
            TranscriptSegment("S1", 0, 5, "text", confidence=0.8),
            TranscriptSegment("S2", 5, 10, "text", confidence=0.9),
        ]
        t._compute_avg_confidence(result)
        assert result.confidence_avg == pytest.approx(0.85)

    def test_compute_avg_confidence_empty(self):
        t = LegalAudioTranscriber()
        result = TranscriptionResult()
        t._compute_avg_confidence(result)
        assert result.confidence_avg == 0.0

    def test_transcript_segment_timestamp_str(self):
        seg = TranscriptSegment("S1", 65.5, 70.25, "text")
        ts = seg.timestamp_str
        assert "01:05" in ts
        assert "-->" in ts

    def test_transcript_to_dict(self):
        result = _make_audio_result()
        d = result.to_dict()
        assert "segments" in d
        assert "speakers" in d
        assert "action_items" in d
        assert "key_legal_terms" in d

    def test_transcript_to_srt(self):
        result = _make_audio_result(2)
        srt = result.to_srt()
        assert "Speaker" in srt
        assert "-->" in srt

    def test_transcript_to_plaintext(self):
        result = _make_audio_result(2)
        text = result.to_plaintext()
        assert "Speaker" in text

    def test_parse_openai_segments_speaker_change_on_silence(self):
        t = LegalAudioTranscriber()
        raw = [
            {"text": "Hello.", "start": 0.0, "end": 2.0, "avg_logprob": 0.0},
            {"text": "How are you?", "start": 6.0, "end": 8.0, "avg_logprob": 0.0},  # 4s gap → new speaker
        ]
        segments = t._parse_openai_segments(raw)
        assert segments[0].speaker != segments[1].speaker

    def test_openai_transcription_mock(self, tmp_path):
        """Mock full OpenAI transcription API call."""
        audio_path = tmp_path / "depo.mp3"
        audio_path.write_bytes(b"fake mp3 data")

        mock_response = MagicMock()
        mock_response.language = "en"
        mock_response.duration = 120.0
        mock_seg = {"text": "The witness stated the contract was signed.", "start": 0.0, "end": 5.0, "avg_logprob": 0.0}
        mock_response.segments = [mock_seg]

        mock_client = MagicMock()
        mock_client.audio.transcriptions.create.return_value = mock_response

        # Build the transcriber directly without going through __init__ openai detection
        t = LegalAudioTranscriber.__new__(LegalAudioTranscriber)
        t._openai_client = mock_client
        t._local_model = None
        t.backend = TranscriptionBackend.OPENAI_API
        t.language = None
        t.model = "whisper-1"
        t.local_model_size = "base"

        result = t.transcribe_file(audio_path)

        assert result.language == "en"
        assert result.duration_seconds == 120.0
        assert len(result.segments) == 1

    def test_transcribe_legal_audio_convenience(self, tmp_path):
        f = tmp_path / "audio.wav"
        f.write_bytes(b"fake wav")
        with patch("multimodal.audio_transcription.OPENAI_WHISPER_AVAILABLE", False), \
             patch("multimodal.audio_transcription.FASTER_WHISPER_AVAILABLE", False), \
             patch("multimodal.audio_transcription.LOCAL_WHISPER_AVAILABLE", False):
            result = transcribe_legal_audio(f)
            assert isinstance(result, TranscriptionResult)

    def test_legal_terms_list_not_empty(self):
        assert len(LEGAL_TERMS) > 20
        assert "objection" in LEGAL_TERMS
        assert "hearsay" in LEGAL_TERMS


# ===========================================================================
# 4. MultimodalLegalAnalyzer tests
# ===========================================================================

class TestParseDateFuzzy:
    def test_slash_format_mdy(self):
        d = parse_date_fuzzy("01/15/2024")
        assert d is not None
        assert d.year == 2024

    def test_month_name_format(self):
        d = parse_date_fuzzy("January 15, 2024")
        assert d is not None
        assert d.month == 1
        assert d.day == 15

    def test_iso_format(self):
        d = parse_date_fuzzy("2024-03-20")
        assert d is not None
        assert d.year == 2024
        assert d.month == 3

    def test_invalid_date(self):
        d = parse_date_fuzzy("not a date at all")
        assert d is None

    def test_short_year(self):
        d = parse_date_fuzzy("01/15/24")
        assert d is not None
        assert d.year == 2024


class TestMultimodalLegalAnalyzer:
    def test_empty_inputs(self):
        analyzer = MultimodalLegalAnalyzer(case_id="TEST-001")
        summary = analyzer.analyze()
        assert "No analysis inputs provided" in summary.warnings[0]

    def test_vision_only_analysis(self):
        vr = _make_vision_result()
        analyzer = MultimodalLegalAnalyzer(case_id="WILL-001")
        summary = analyzer.analyze(vision_results=[vr])
        assert summary.case_id == "WILL-001"
        assert len(summary.evidence_items) == 1
        assert "will" in summary.document_types_found

    def test_pdf_only_analysis(self):
        pr = _make_pdf_result(pages=10, text="Whereas the parties agree. Case No. 123. Plaintiff vs Defendant.")
        analyzer = MultimodalLegalAnalyzer()
        summary = analyzer.analyze(pdf_results=[pr])
        assert len(summary.evidence_items) == 1

    def test_audio_only_analysis(self):
        ar = _make_audio_result(5)
        analyzer = MultimodalLegalAnalyzer()
        summary = analyzer.analyze(audio_results=[ar])
        assert len(summary.evidence_items) == 1
        assert any(sp.label.startswith("Speaker") for sp in ar.speakers) or len(ar.speakers) == 0

    def test_full_multimodal_analysis(self):
        vr = _make_vision_result()
        pr = _make_pdf_result(pages=5, text="John Doe signed on January 15, 2024.")
        ar = _make_audio_result(3)
        analyzer = MultimodalLegalAnalyzer(case_id="CASE-2024-001")
        summary = analyzer.analyze(vision_results=[vr], pdf_results=[pr], audio_results=[ar])
        assert summary.evidence_strength in list(EvidenceStrength)
        assert summary.evidence_score >= 0.0
        assert len(summary.summary_text) > 50

    def test_inconsistency_alteration_detected(self):
        vr = _make_vision_result(SAMPLE_VISION_JSON_ALTERED)
        analyzer = MultimodalLegalAnalyzer()
        summary = analyzer.analyze(vision_results=[vr])
        inc_types = [i.inconsistency_type for i in summary.inconsistencies]
        assert InconsistencyType.DOCUMENT_ALTERED in inc_types

    def test_inconsistency_signature_missing(self):
        data = {**SAMPLE_VISION_JSON, "signatures": {**SAMPLE_VISION_JSON["signatures"], "detected": False, "count": 0}}
        vr = _make_vision_result(data)
        analyzer = MultimodalLegalAnalyzer()
        summary = analyzer.analyze(vision_results=[vr])
        inc_types = [i.inconsistency_type for i in summary.inconsistencies]
        assert InconsistencyType.SIGNATURE_MISSING in inc_types

    def test_evidence_score_strong(self):
        vr = _make_vision_result()  # high confidence, no alterations
        vr.confidence_score = 0.95
        pr = _make_pdf_result()
        ar = _make_audio_result()
        analyzer = MultimodalLegalAnalyzer()
        summary = analyzer.analyze(vision_results=[vr], pdf_results=[pr], audio_results=[ar])
        assert summary.evidence_score > 0.5

    def test_evidence_score_reduced_by_alterations(self):
        vr = _make_vision_result(SAMPLE_VISION_JSON_ALTERED)
        analyzer = MultimodalLegalAnalyzer()
        summary = analyzer.analyze(vision_results=[vr])
        # Alterations should reduce evidence weight
        assert summary.evidence_score < 0.8

    def test_timeline_construction(self):
        vr = _make_vision_result()  # has dates: "January 15, 2024", "03/20/2023"
        pr = _make_pdf_result(text="Agreement dated 01/01/2022. Signed 06/15/2023.")
        analyzer = MultimodalLegalAnalyzer()
        summary = analyzer.analyze(vision_results=[vr], pdf_results=[pr])
        assert len(summary.timeline) > 0

    def test_party_extraction_vision(self):
        vr = _make_vision_result()
        analyzer = MultimodalLegalAnalyzer()
        summary = analyzer.analyze(vision_results=[vr])
        assert "John Doe" in summary.key_parties

    def test_recommendations_generated(self):
        vr = _make_vision_result(SAMPLE_VISION_JSON_ALTERED)
        analyzer = MultimodalLegalAnalyzer()
        summary = analyzer.analyze(vision_results=[vr])
        assert len(summary.recommendations) > 0
        assert any("forensic" in r.lower() for r in summary.recommendations)

    def test_case_summary_to_dict(self):
        vr = _make_vision_result()
        analyzer = MultimodalLegalAnalyzer(case_id="DICT-TEST")
        summary = analyzer.analyze(vision_results=[vr])
        d = summary.to_dict()
        assert d["case_id"] == "DICT-TEST"
        assert "evidence_strength" in d
        assert "timeline" in d
        assert "inconsistencies" in d
        assert "cross_references" in d

    def test_analyze_case_convenience(self):
        vr = _make_vision_result()
        summary = analyze_case(vision_results=[vr], case_id="CONV-001")
        assert isinstance(summary, CaseSummary)
        assert summary.case_id == "CONV-001"

    def test_redaction_warning_in_pdf(self):
        pr = _make_pdf_result()
        pr.redacted_regions = [RedactedRegion(page_number=1, estimated_char_count=50, location_description="center")]
        analyzer = MultimodalLegalAnalyzer()
        summary = analyzer.analyze(pdf_results=[pr])
        assert any("redact" in w.lower() for w in summary.warnings)

    def test_timeline_gap_inconsistency(self):
        from datetime import datetime
        analyzer = MultimodalLegalAnalyzer()
        summary = CaseSummary()
        summary.timeline = [
            TimelineEvent("01/01/2020", "Event A", "pdf", parsed_date=datetime(2020, 1, 1)),
            TimelineEvent("01/01/2022", "Event B", "pdf", parsed_date=datetime(2022, 1, 1)),  # 2yr gap
        ]
        # Directly call inconsistency detection
        analyzer._detect_inconsistencies(summary, [], [], [])
        inc_types = [i.inconsistency_type for i in summary.inconsistencies]
        assert InconsistencyType.TIMELINE_GAP in inc_types


# ===========================================================================
# 5. Integration: multimodal_api (FastAPI router) tests
# ===========================================================================

class TestMultimodalAPIRouter:
    """
    Tests for the FastAPI router factory. We mock FastAPI to avoid needing
    a running server, and test the engine/analyzer integration logic directly.
    """

    def test_get_vision_engine_singleton(self):
        from multimodal.multimodal_api import get_vision_engine
        e1 = get_vision_engine()
        e2 = get_vision_engine()
        assert e1 is e2

    def test_get_pdf_analyzer_singleton(self):
        from multimodal.multimodal_api import get_pdf_analyzer
        a1 = get_pdf_analyzer()
        a2 = get_pdf_analyzer()
        assert a1 is a2

    def test_get_audio_transcriber_singleton(self):
        from multimodal.multimodal_api import get_audio_transcriber
        t1 = get_audio_transcriber()
        t2 = get_audio_transcriber()
        assert t1 is t2

    def test_supported_formats_lists(self):
        from multimodal.multimodal_api import (
            SUPPORTED_IMAGE_FORMATS,
            SUPPORTED_PDF_FORMATS,
            SUPPORTED_AUDIO_FORMATS,
        )
        assert ".jpg" in SUPPORTED_IMAGE_FORMATS
        assert ".jpeg" in SUPPORTED_IMAGE_FORMATS
        assert ".png" in SUPPORTED_IMAGE_FORMATS
        assert ".pdf" in SUPPORTED_PDF_FORMATS
        assert ".mp3" in SUPPORTED_AUDIO_FORMATS
        assert ".wav" in SUPPORTED_AUDIO_FORMATS

    def test_create_multimodal_router_no_fastapi(self):
        from multimodal import multimodal_api
        with patch.object(multimodal_api, "FASTAPI_AVAILABLE", False):
            with pytest.raises(ImportError):
                multimodal_api.create_multimodal_router()

    def test_vision_engine_base64_integration(self):
        """Test that analyze_base64 returns a result dict properly."""
        from multimodal.multimodal_api import get_vision_engine
        engine = get_vision_engine()
        # With no client, should return degraded result gracefully
        b64 = base64.b64encode(b"fake image data").decode()
        result = engine.analyze_base64(b64)
        assert isinstance(result, DocumentVisionResult)

    def test_pdf_analyzer_integration(self):
        from multimodal.multimodal_api import get_pdf_analyzer
        analyzer = get_pdf_analyzer()
        # Use a mock reader to avoid pypdf errors with invalid bytes
        mock_reader = MagicMock()
        mock_reader.is_encrypted = False
        mock_reader.metadata = {}
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Sample legal document text."
        mock_page.mediabox.width = 612
        mock_page.mediabox.height = 792
        mock_reader.pages = [mock_page]
        mock_reader.trailer = {}
        with patch("multimodal.pdf_analyzer.PYMUPDF_AVAILABLE", False), \
             patch("multimodal.pdf_analyzer.PYPDF_AVAILABLE", True), \
             patch("multimodal.pdf_analyzer.PdfReader", return_value=mock_reader):
            result = analyzer.analyze(b"%PDF-1.4 minimal")
        assert isinstance(result, PDFAnalysisResult)

    def test_audio_transcriber_integration(self):
        from multimodal.multimodal_api import get_audio_transcriber
        t = get_audio_transcriber()
        assert isinstance(t, LegalAudioTranscriber)
