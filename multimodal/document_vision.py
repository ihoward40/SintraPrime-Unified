"""
document_vision.py — GPT-4o Vision-based legal document analysis.

Processes images of legal documents: handwritten wills, signed contracts,
court stamps, deeds, IDs, and checks. Extracts text via vision (OCR-style),
detects signatures, stamps, dates, and parties. Provides handwriting
authenticity analysis and document type classification.
"""

from __future__ import annotations

import base64
import json
import logging
import mimetypes
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class DocumentType(str, Enum):
    WILL = "will"
    CONTRACT = "contract"
    DEED = "deed"
    COURT_FILING = "court_filing"
    ID = "identification"
    CHECK = "check"
    UNKNOWN = "unknown"


class HandwritingAuthenticityLevel(str, Enum):
    HIGH = "high"        # likely authentic
    MEDIUM = "medium"    # some concerns
    LOW = "low"          # possible alteration/forgery
    INCONCLUSIVE = "inconclusive"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class SignatureInfo:
    detected: bool = False
    count: int = 0
    locations: List[str] = field(default_factory=list)
    names: List[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class StampInfo:
    detected: bool = False
    count: int = 0
    types: List[str] = field(default_factory=list)
    texts: List[str] = field(default_factory=list)
    locations: List[str] = field(default_factory=list)


@dataclass
class HandwritingAnalysis:
    authenticity: HandwritingAuthenticityLevel = HandwritingAuthenticityLevel.INCONCLUSIVE
    confidence: float = 0.0
    alterations_detected: bool = False
    alteration_regions: List[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class ExtractedParty:
    name: str
    role: str  # e.g. "testator", "witness", "grantor", "grantee"
    address: Optional[str] = None
    signature_present: bool = False


@dataclass
class DocumentVisionResult:
    document_type: DocumentType = DocumentType.UNKNOWN
    raw_text: str = ""
    dates_found: List[str] = field(default_factory=list)
    parties: List[ExtractedParty] = field(default_factory=list)
    signatures: SignatureInfo = field(default_factory=SignatureInfo)
    stamps: StampInfo = field(default_factory=StampInfo)
    handwriting: HandwritingAnalysis = field(default_factory=HandwritingAnalysis)
    key_clauses: List[str] = field(default_factory=list)
    legal_jurisdiction: Optional[str] = None
    notarized: bool = False
    confidence_score: float = 0.0
    warnings: List[str] = field(default_factory=list)
    raw_vision_response: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_type": self.document_type.value,
            "raw_text": self.raw_text,
            "dates_found": self.dates_found,
            "parties": [
                {
                    "name": p.name,
                    "role": p.role,
                    "address": p.address,
                    "signature_present": p.signature_present,
                }
                for p in self.parties
            ],
            "signatures": {
                "detected": self.signatures.detected,
                "count": self.signatures.count,
                "locations": self.signatures.locations,
                "names": self.signatures.names,
                "confidence": self.signatures.confidence,
            },
            "stamps": {
                "detected": self.stamps.detected,
                "count": self.stamps.count,
                "types": self.stamps.types,
                "texts": self.stamps.texts,
                "locations": self.stamps.locations,
            },
            "handwriting": {
                "authenticity": self.handwriting.authenticity.value,
                "confidence": self.handwriting.confidence,
                "alterations_detected": self.handwriting.alterations_detected,
                "alteration_regions": self.handwriting.alteration_regions,
                "notes": self.handwriting.notes,
            },
            "key_clauses": self.key_clauses,
            "legal_jurisdiction": self.legal_jurisdiction,
            "notarized": self.notarized,
            "confidence_score": self.confidence_score,
            "warnings": self.warnings,
        }


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are an expert legal document analyst with decades of experience
in forensic document examination. You analyze images of legal documents and extract
structured information. Always respond with valid JSON. Be precise and thorough.
When uncertain, indicate lower confidence scores."""

ANALYSIS_PROMPT = """Analyze this legal document image and extract the following information
in JSON format:

{
  "document_type": "<will|contract|deed|court_filing|identification|check|unknown>",
  "raw_text": "<full OCR text of the document>",
  "dates_found": ["<date1>", "<date2>"],
  "parties": [
    {"name": "<name>", "role": "<role>", "address": "<address or null>", "signature_present": true/false}
  ],
  "signatures": {
    "detected": true/false,
    "count": <number>,
    "locations": ["<location description>"],
    "names": ["<name if legible>"],
    "confidence": <0.0-1.0>
  },
  "stamps": {
    "detected": true/false,
    "count": <number>,
    "types": ["<notary|court|official|corporate|other>"],
    "texts": ["<stamp text>"],
    "locations": ["<location description>"]
  },
  "handwriting": {
    "authenticity": "<high|medium|low|inconclusive>",
    "confidence": <0.0-1.0>,
    "alterations_detected": true/false,
    "alteration_regions": ["<description of altered region>"],
    "notes": "<analysis notes>"
  },
  "key_clauses": ["<important clause summary>"],
  "legal_jurisdiction": "<state/country or null>",
  "notarized": true/false,
  "confidence_score": <0.0-1.0>,
  "warnings": ["<any concerns or anomalies>"]
}

Focus on:
1. Complete and accurate text extraction
2. Identifying all signatories and their roles
3. Detecting official stamps, seals, notarizations
4. Handwriting consistency and signs of alteration
5. Legal document structure and key provisions
"""


# ---------------------------------------------------------------------------
# Vision engine
# ---------------------------------------------------------------------------

class DocumentVisionEngine:
    """
    GPT-4o Vision-based legal document analyzer.

    Supports:
    - File path input (JPEG, PNG, TIFF, PDF page images, WEBP)
    - Base64 encoded image input
    - URL-based image input
    """

    SUPPORTED_MIME_TYPES = {
        "image/jpeg", "image/png", "image/gif", "image/webp",
        "image/tiff", "image/bmp",
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o",
        max_tokens: int = 4096,
        temperature: float = 0.1,
    ):
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self._client = None

        key = api_key or os.environ.get("OPENAI_API_KEY", "")
        if key:
            try:
                from openai import OpenAI  # type: ignore
                self._client = OpenAI(api_key=key)
                logger.info("DocumentVisionEngine: OpenAI client initialized.")
            except ImportError:
                logger.warning("openai package not installed; vision calls will fail.")
        else:
            logger.warning(
                "OPENAI_API_KEY not set. DocumentVisionEngine running in degraded mode."
            )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def analyze_file(self, file_path: str | Path) -> DocumentVisionResult:
        """Analyze a document image from a file path."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Image file not found: {file_path}")

        mime_type, _ = mimetypes.guess_type(str(path))
        if mime_type not in self.SUPPORTED_MIME_TYPES:
            raise ValueError(
                f"Unsupported file type: {mime_type}. "
                f"Supported: {self.SUPPORTED_MIME_TYPES}"
            )

        with open(path, "rb") as f:
            image_bytes = f.read()

        b64 = base64.b64encode(image_bytes).decode("utf-8")
        return self.analyze_base64(b64, mime_type=mime_type or "image/jpeg")

    def analyze_base64(
        self, b64_data: str, mime_type: str = "image/jpeg"
    ) -> DocumentVisionResult:
        """Analyze a document from base64-encoded image data."""
        if not self._client:
            return self._degraded_result("OpenAI client not configured.")

        image_url = f"data:{mime_type};base64,{b64_data}"
        return self._call_vision_api(image_url)

    def analyze_url(self, image_url: str) -> DocumentVisionResult:
        """Analyze a document image from a public URL."""
        if not self._client:
            return self._degraded_result("OpenAI client not configured.")
        return self._call_vision_api(image_url)

    def classify_document_type(self, text: str) -> DocumentType:
        """Classify document type from extracted text using heuristic rules."""
        text_lower = text.lower()

        patterns: List[Tuple[DocumentType, List[str]]] = [
            (DocumentType.WILL, ["last will and testament", "testator", "bequeath", "bequest", "executor", "revoke all prior wills"]),
            (DocumentType.DEED, ["deed of trust", "grantor", "grantee", "convey and warrant", "quitclaim", "real property", "parcel"]),
            (DocumentType.CONTRACT, ["agreement", "consideration", "party of the first part", "terms and conditions", "whereas", "witnesseth"]),
            (DocumentType.COURT_FILING, ["court of", "plaintiff", "defendant", "case no", "docket", "motion", "order", "judgment", "affidavit"]),
            (DocumentType.ID, ["driver license", "state id", "passport", "date of birth", "expiration date", "identification number"]),
            (DocumentType.CHECK, ["pay to the order of", "memo", "routing number", "bank", "dollars", "void after"]),
        ]

        scores: Dict[DocumentType, int] = {}
        for doc_type, keywords in patterns:
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                scores[doc_type] = score

        if not scores:
            return DocumentType.UNKNOWN

        return max(scores, key=scores.__getitem__)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _call_vision_api(self, image_url: str) -> DocumentVisionResult:
        """Send the image to GPT-4o Vision and parse the response."""
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": image_url, "detail": "high"},
                            },
                            {"type": "text", "text": ANALYSIS_PROMPT},
                        ],
                    },
                ],
            )
            raw_content = response.choices[0].message.content
            return self._parse_vision_response(raw_content)
        except Exception as exc:
            logger.error("Vision API call failed: %s", exc)
            result = self._degraded_result(f"API error: {exc}")
            return result

    def _parse_vision_response(self, raw: str) -> DocumentVisionResult:
        """Parse JSON response from Vision API into DocumentVisionResult."""
        result = DocumentVisionResult(raw_vision_response=raw)

        # Extract JSON block (may be wrapped in markdown code fences)
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find bare JSON object
            json_match = re.search(r"\{.*\}", raw, re.DOTALL)
            json_str = json_match.group(0) if json_match else "{}"

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse vision response JSON: %s", e)
            result.warnings.append(f"JSON parse error: {e}")
            return result

        # Document type
        dt_raw = data.get("document_type", "unknown")
        try:
            result.document_type = DocumentType(dt_raw)
        except ValueError:
            result.document_type = DocumentType.UNKNOWN

        result.raw_text = data.get("raw_text", "")
        result.dates_found = data.get("dates_found", [])
        result.key_clauses = data.get("key_clauses", [])
        result.legal_jurisdiction = data.get("legal_jurisdiction")
        result.notarized = data.get("notarized", False)
        result.confidence_score = float(data.get("confidence_score", 0.0))
        result.warnings = data.get("warnings", [])

        # Parties
        for p in data.get("parties", []):
            result.parties.append(
                ExtractedParty(
                    name=p.get("name", ""),
                    role=p.get("role", ""),
                    address=p.get("address"),
                    signature_present=p.get("signature_present", False),
                )
            )

        # Signatures
        sig = data.get("signatures", {})
        result.signatures = SignatureInfo(
            detected=sig.get("detected", False),
            count=sig.get("count", 0),
            locations=sig.get("locations", []),
            names=sig.get("names", []),
            confidence=float(sig.get("confidence", 0.0)),
        )

        # Stamps
        st = data.get("stamps", {})
        result.stamps = StampInfo(
            detected=st.get("detected", False),
            count=st.get("count", 0),
            types=st.get("types", []),
            texts=st.get("texts", []),
            locations=st.get("locations", []),
        )

        # Handwriting
        hw = data.get("handwriting", {})
        try:
            auth = HandwritingAuthenticityLevel(hw.get("authenticity", "inconclusive"))
        except ValueError:
            auth = HandwritingAuthenticityLevel.INCONCLUSIVE
        result.handwriting = HandwritingAnalysis(
            authenticity=auth,
            confidence=float(hw.get("confidence", 0.0)),
            alterations_detected=hw.get("alterations_detected", False),
            alteration_regions=hw.get("alteration_regions", []),
            notes=hw.get("notes", ""),
        )

        return result

    def _degraded_result(self, warning: str) -> DocumentVisionResult:
        result = DocumentVisionResult()
        result.warnings.append(warning)
        result.document_type = DocumentType.UNKNOWN
        return result


# ---------------------------------------------------------------------------
# Batch processor
# ---------------------------------------------------------------------------

class DocumentBatchProcessor:
    """Process multiple document images concurrently."""

    def __init__(self, engine: DocumentVisionEngine, max_workers: int = 4):
        self.engine = engine
        self.max_workers = max_workers

    def process_files(self, file_paths: List[str | Path]) -> List[DocumentVisionResult]:
        """Process a list of image files and return results in order."""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        results: Dict[int, DocumentVisionResult] = {}
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_idx = {
                executor.submit(self._safe_analyze, path): idx
                for idx, path in enumerate(file_paths)
            }
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    results[idx] = future.result()
                except Exception as e:
                    result = DocumentVisionResult()
                    result.warnings.append(str(e))
                    results[idx] = result

        return [results[i] for i in range(len(file_paths))]

    def _safe_analyze(self, path: str | Path) -> DocumentVisionResult:
        try:
            return self.engine.analyze_file(path)
        except Exception as exc:
            r = DocumentVisionResult()
            r.warnings.append(str(exc))
            return r


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def image_to_base64(file_path: str | Path) -> Tuple[str, str]:
    """
    Convert an image file to base64 string.
    Returns (base64_string, mime_type).
    """
    path = Path(file_path)
    mime_type, _ = mimetypes.guess_type(str(path))
    if not mime_type:
        mime_type = "image/jpeg"
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return b64, mime_type


def summarize_result(result: DocumentVisionResult) -> str:
    """Return a human-readable summary of a DocumentVisionResult."""
    lines = [
        f"Document Type: {result.document_type.value.upper()}",
        f"Confidence: {result.confidence_score:.0%}",
        f"Notarized: {'Yes' if result.notarized else 'No'}",
        f"Dates Found: {', '.join(result.dates_found) if result.dates_found else 'None'}",
        f"Parties ({len(result.parties)}): {', '.join(p.name for p in result.parties)}",
        f"Signatures: {result.signatures.count} detected",
        f"Stamps/Seals: {result.stamps.count} detected",
        f"Handwriting Authenticity: {result.handwriting.authenticity.value}",
    ]
    if result.handwriting.alterations_detected:
        lines.append(f"⚠ ALTERATIONS DETECTED in: {', '.join(result.handwriting.alteration_regions)}")
    if result.warnings:
        lines.append(f"Warnings: {'; '.join(result.warnings)}")
    return "\n".join(lines)
