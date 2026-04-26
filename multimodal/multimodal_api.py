"""
multimodal_api.py — FastAPI router for multimodal legal analysis endpoints.

Routes:
  POST /multimodal/analyze-image    — analyze a document image via GPT-4o Vision
  POST /multimodal/analyze-pdf      — deep PDF structure analysis
  POST /multimodal/transcribe       — audio to legal transcript
  POST /multimodal/full-analysis    — all three combined
  GET  /multimodal/supported-formats — list supported file types
"""

from __future__ import annotations

import base64
import io
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel, Field
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    logger.error("FastAPI not installed. Install with: pip install fastapi")

from .document_vision import DocumentVisionEngine, DocumentVisionResult
from .pdf_analyzer import PDFStructureAnalyzer, PDFAnalysisResult
from .audio_transcription import LegalAudioTranscriber, TranscriptionResult
from .legal_analyzer import MultimodalLegalAnalyzer, CaseSummary


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

if FASTAPI_AVAILABLE:
    class ImageAnalysisRequest(BaseModel):
        """Request body for image analysis via base64."""
        image_base64: str = Field(..., description="Base64-encoded image data.")
        mime_type: str = Field("image/jpeg", description="MIME type of the image.")
        case_id: Optional[str] = Field(None, description="Optional case identifier.")

    class ImageAnalysisResponse(BaseModel):
        success: bool
        case_id: Optional[str]
        result: Dict[str, Any]
        warnings: List[str] = []

    class PDFAnalysisResponse(BaseModel):
        success: bool
        filename: str
        result: Dict[str, Any]
        warnings: List[str] = []

    class TranscriptionResponse(BaseModel):
        success: bool
        filename: str
        result: Dict[str, Any]
        warnings: List[str] = []

    class FullAnalysisResponse(BaseModel):
        success: bool
        case_id: Optional[str]
        image_result: Optional[Dict[str, Any]]
        pdf_result: Optional[Dict[str, Any]]
        audio_result: Optional[Dict[str, Any]]
        case_summary: Dict[str, Any]
        warnings: List[str] = []

    class SupportedFormatsResponse(BaseModel):
        image_formats: List[str]
        pdf_formats: List[str]
        audio_formats: List[str]


# ---------------------------------------------------------------------------
# Supported formats
# ---------------------------------------------------------------------------

SUPPORTED_IMAGE_FORMATS = [".jpg", ".jpeg", ".png", ".gif", ".webp", ".tiff", ".bmp"]
SUPPORTED_PDF_FORMATS = [".pdf"]
SUPPORTED_AUDIO_FORMATS = [".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm", ".ogg", ".flac"]


# ---------------------------------------------------------------------------
# Dependency: shared engine instances
# ---------------------------------------------------------------------------

_vision_engine: Optional[DocumentVisionEngine] = None
_pdf_analyzer: Optional[PDFStructureAnalyzer] = None
_audio_transcriber: Optional[LegalAudioTranscriber] = None


def get_vision_engine() -> DocumentVisionEngine:
    global _vision_engine
    if _vision_engine is None:
        _vision_engine = DocumentVisionEngine()
    return _vision_engine


def get_pdf_analyzer() -> PDFStructureAnalyzer:
    global _pdf_analyzer
    if _pdf_analyzer is None:
        _pdf_analyzer = PDFStructureAnalyzer()
    return _pdf_analyzer


def get_audio_transcriber() -> LegalAudioTranscriber:
    global _audio_transcriber
    if _audio_transcriber is None:
        _audio_transcriber = LegalAudioTranscriber()
    return _audio_transcriber


# ---------------------------------------------------------------------------
# Router factory
# ---------------------------------------------------------------------------

def create_multimodal_router(prefix: str = "/multimodal") -> Any:
    """
    Create and return the multimodal FastAPI router.
    Raises ImportError if FastAPI is not installed.
    """
    if not FASTAPI_AVAILABLE:
        raise ImportError("FastAPI is required. Install with: pip install fastapi")

    router = APIRouter(prefix=prefix, tags=["Multimodal Legal Analysis"])

    # -----------------------------------------------------------------------
    # GET /multimodal/supported-formats
    # -----------------------------------------------------------------------
    @router.get(
        "/supported-formats",
        response_model=SupportedFormatsResponse,
        summary="List supported file formats",
    )
    async def supported_formats() -> SupportedFormatsResponse:
        """Return lists of supported file extensions for each media type."""
        return SupportedFormatsResponse(
            image_formats=SUPPORTED_IMAGE_FORMATS,
            pdf_formats=SUPPORTED_PDF_FORMATS,
            audio_formats=SUPPORTED_AUDIO_FORMATS,
        )

    # -----------------------------------------------------------------------
    # POST /multimodal/analyze-image
    # -----------------------------------------------------------------------
    @router.post(
        "/analyze-image",
        response_model=ImageAnalysisResponse,
        summary="Analyze a legal document image via GPT-4o Vision",
    )
    async def analyze_image(
        image_file: Optional[UploadFile] = File(None, description="Image file upload."),
        image_base64: Optional[str] = Form(None, description="Base64-encoded image."),
        mime_type: str = Form("image/jpeg", description="MIME type."),
        case_id: Optional[str] = Form(None, description="Optional case ID."),
    ) -> ImageAnalysisResponse:
        """
        Analyze a legal document image.
        Provide either `image_file` (multipart upload) or `image_base64` (form field).
        """
        engine = get_vision_engine()

        if image_file is not None:
            contents = await image_file.read()
            b64 = base64.b64encode(contents).decode("utf-8")
            ct = image_file.content_type or mime_type
        elif image_base64:
            b64 = image_base64
            ct = mime_type
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Provide either image_file or image_base64.",
            )

        try:
            result: DocumentVisionResult = engine.analyze_base64(b64, mime_type=ct)
            return ImageAnalysisResponse(
                success=True,
                case_id=case_id,
                result=result.to_dict(),
                warnings=result.warnings,
            )
        except Exception as exc:
            logger.error("Image analysis failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(exc),
            )

    # -----------------------------------------------------------------------
    # POST /multimodal/analyze-pdf
    # -----------------------------------------------------------------------
    @router.post(
        "/analyze-pdf",
        response_model=PDFAnalysisResponse,
        summary="Deep structural analysis of a PDF legal document",
    )
    async def analyze_pdf(
        pdf_file: UploadFile = File(..., description="PDF file to analyze."),
    ) -> PDFAnalysisResponse:
        """
        Perform deep structural analysis of a PDF:
        form fields, signatures, tables, sections, Bates numbers, redactions.
        """
        if not pdf_file.filename or not pdf_file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Only PDF files are supported.",
            )

        analyzer = get_pdf_analyzer()
        contents = await pdf_file.read()

        try:
            result: PDFAnalysisResult = analyzer.analyze(contents)
            return PDFAnalysisResponse(
                success=True,
                filename=pdf_file.filename,
                result=result.to_dict(),
                warnings=result.warnings,
            )
        except Exception as exc:
            logger.error("PDF analysis failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(exc),
            )

    # -----------------------------------------------------------------------
    # POST /multimodal/transcribe
    # -----------------------------------------------------------------------
    @router.post(
        "/transcribe",
        response_model=TranscriptionResponse,
        summary="Transcribe a legal audio recording",
    )
    async def transcribe_audio(
        audio_file: UploadFile = File(..., description="Audio file to transcribe."),
    ) -> TranscriptionResponse:
        """
        Transcribe a legal audio recording with speaker diarization.
        Returns structured segments with timestamps, speaker labels, and action items.
        """
        filename = audio_file.filename or "audio.mp3"
        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ".mp3"
        if ext not in SUPPORTED_AUDIO_FORMATS:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported audio format: {ext}. Supported: {SUPPORTED_AUDIO_FORMATS}",
            )

        transcriber = get_audio_transcriber()
        contents = await audio_file.read()

        try:
            result: TranscriptionResult = transcriber.transcribe_bytes(contents, filename=filename)
            return TranscriptionResponse(
                success=True,
                filename=filename,
                result=result.to_dict(),
                warnings=result.warnings,
            )
        except Exception as exc:
            logger.error("Transcription failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(exc),
            )

    # -----------------------------------------------------------------------
    # POST /multimodal/full-analysis
    # -----------------------------------------------------------------------
    @router.post(
        "/full-analysis",
        response_model=FullAnalysisResponse,
        summary="Combined multimodal analysis: image + PDF + audio",
    )
    async def full_analysis(
        case_id: Optional[str] = Form(None, description="Optional case identifier."),
        image_file: Optional[UploadFile] = File(None, description="Optional document image."),
        pdf_file: Optional[UploadFile] = File(None, description="Optional PDF document."),
        audio_file: Optional[UploadFile] = File(None, description="Optional audio recording."),
    ) -> FullAnalysisResponse:
        """
        Perform a complete multimodal legal analysis combining:
        - GPT-4o Vision analysis of document images
        - Deep PDF structural analysis
        - Legal audio transcription with speaker diarization
        - Cross-reference and unified case summary
        """
        if not any([image_file, pdf_file, audio_file]):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Provide at least one of: image_file, pdf_file, audio_file.",
            )

        vision_results = []
        pdf_results = []
        audio_results = []
        warnings: List[str] = []

        image_dict = None
        pdf_dict = None
        audio_dict = None

        # Vision
        if image_file:
            try:
                engine = get_vision_engine()
                contents = await image_file.read()
                b64 = base64.b64encode(contents).decode("utf-8")
                ct = image_file.content_type or "image/jpeg"
                vr = engine.analyze_base64(b64, mime_type=ct)
                vision_results.append(vr)
                image_dict = vr.to_dict()
                warnings.extend(vr.warnings)
            except Exception as exc:
                warnings.append(f"Image analysis error: {exc}")

        # PDF
        if pdf_file:
            try:
                analyzer = get_pdf_analyzer()
                contents = await pdf_file.read()
                pr = analyzer.analyze(contents)
                pdf_results.append(pr)
                pdf_dict = pr.to_dict()
                warnings.extend(pr.warnings)
            except Exception as exc:
                warnings.append(f"PDF analysis error: {exc}")

        # Audio
        if audio_file:
            try:
                transcriber = get_audio_transcriber()
                filename = audio_file.filename or "audio.mp3"
                contents = await audio_file.read()
                ar = transcriber.transcribe_bytes(contents, filename=filename)
                audio_results.append(ar)
                audio_dict = ar.to_dict()
                warnings.extend(ar.warnings)
            except Exception as exc:
                warnings.append(f"Audio transcription error: {exc}")

        # Unified analysis
        legal_analyzer = MultimodalLegalAnalyzer(case_id=case_id)
        case_summary: CaseSummary = legal_analyzer.analyze(
            vision_results=vision_results or None,
            pdf_results=pdf_results or None,
            audio_results=audio_results or None,
        )
        warnings.extend(case_summary.warnings)

        return FullAnalysisResponse(
            success=True,
            case_id=case_id,
            image_result=image_dict,
            pdf_result=pdf_dict,
            audio_result=audio_dict,
            case_summary=case_summary.to_dict(),
            warnings=warnings,
        )

    return router


# ---------------------------------------------------------------------------
# App factory (standalone usage)
# ---------------------------------------------------------------------------

def create_app():
    """Create a standalone FastAPI app with the multimodal router mounted."""
    if not FASTAPI_AVAILABLE:
        raise ImportError("FastAPI is required.")

    from fastapi import FastAPI

    app = FastAPI(
        title="SintraPrime Multimodal Legal Analysis API",
        description="GPT-4o Vision, PDF parsing, and Whisper transcription for legal documents.",
        version="1.0.0",
    )
    router = create_multimodal_router()
    app.include_router(router)
    return app
