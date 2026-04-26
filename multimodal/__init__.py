"""
multimodal — Multimodal processing layer for SintraPrime-Unified.

Provides:
- document_vision: GPT-4o Vision-based legal document image analysis
- pdf_analyzer: Deep PDF structure parsing (form fields, tables, redactions, Bates numbers)
- audio_transcription: Legal audio transcription with speaker diarization
- legal_analyzer: Unified multimodal case analysis
- multimodal_api: FastAPI router exposing all capabilities
"""

from .document_vision import DocumentVisionEngine, DocumentVisionResult, DocumentType
from .pdf_analyzer import PDFStructureAnalyzer, PDFAnalysisResult, analyze_pdf
from .audio_transcription import LegalAudioTranscriber, TranscriptionResult, transcribe_legal_audio
from .legal_analyzer import MultimodalLegalAnalyzer, CaseSummary, analyze_case

__all__ = [
    "DocumentVisionEngine",
    "DocumentVisionResult",
    "DocumentType",
    "PDFStructureAnalyzer",
    "PDFAnalysisResult",
    "analyze_pdf",
    "LegalAudioTranscriber",
    "TranscriptionResult",
    "transcribe_legal_audio",
    "MultimodalLegalAnalyzer",
    "CaseSummary",
    "analyze_case",
]
