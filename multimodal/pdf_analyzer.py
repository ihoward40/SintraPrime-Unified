"""
pdf_analyzer.py — Deep PDF structure analysis for legal documents.

Goes far beyond simple text extraction:
- Form field extraction (fillable PDFs)
- Embedded signature detection
- Table extraction (financial tables, court schedules)
- Section/clause detection and labeling
- Bates number detection
- Redaction detection (blacked-out sections)
- Page layout analysis

Uses PyMuPDF (fitz) when available, falls back to pypdf.
"""

from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Backend detection
# ---------------------------------------------------------------------------

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
    logger.info("PyMuPDF (fitz) available — using full backend.")
except ImportError:
    PYMUPDF_AVAILABLE = False
    logger.warning("PyMuPDF not available — falling back to pypdf.")

try:
    from pypdf import PdfReader  # type: ignore
    PYPDF_AVAILABLE = True
except ImportError:
    try:
        from PyPDF2 import PdfReader  # type: ignore
        PYPDF_AVAILABLE = True
    except ImportError:
        PYPDF_AVAILABLE = False
        logger.warning("Neither PyMuPDF nor pypdf is installed.")


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class SectionType(str, Enum):
    RECITAL = "recital"
    DEFINITIONS = "definitions"
    COVENANTS = "covenants"
    CONDITIONS = "conditions"
    SIGNATURES = "signatures"
    EXHIBIT = "exhibit"
    SCHEDULE = "schedule"
    AMENDMENT = "amendment"
    GENERAL = "general"


@dataclass
class FormField:
    name: str
    field_type: str  # text, checkbox, radio, dropdown, signature
    value: Optional[str] = None
    page_number: int = 1
    required: bool = False
    read_only: bool = False


@dataclass
class EmbeddedSignature:
    page_number: int
    signer_name: Optional[str] = None
    signed_at: Optional[str] = None
    certificate_subject: Optional[str] = None
    valid: Optional[bool] = None
    location: Optional[str] = None


@dataclass
class TableData:
    page_number: int
    headers: List[str] = field(default_factory=list)
    rows: List[List[str]] = field(default_factory=list)
    caption: Optional[str] = None
    table_index: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_number": self.page_number,
            "headers": self.headers,
            "rows": self.rows,
            "caption": self.caption,
            "table_index": self.table_index,
        }


@dataclass
class DocumentSection:
    section_type: SectionType
    title: str
    start_page: int
    end_page: int
    content_preview: str = ""
    clause_numbers: List[str] = field(default_factory=list)


@dataclass
class BatesNumber:
    page_number: int
    value: str
    location: str  # "header" | "footer" | "margin"


@dataclass
class RedactedRegion:
    page_number: int
    estimated_char_count: int
    location_description: str
    surrounding_context: str = ""


@dataclass
class PageLayout:
    page_number: int
    width: float
    height: float
    columns: int
    has_header: bool
    has_footer: bool
    has_images: bool
    text_blocks: int
    rotation: int = 0


@dataclass
class PDFAnalysisResult:
    file_path: Optional[str] = None
    total_pages: int = 0
    title: Optional[str] = None
    author: Optional[str] = None
    creator: Optional[str] = None
    creation_date: Optional[str] = None
    modification_date: Optional[str] = None
    is_encrypted: bool = False
    is_linearized: bool = False
    pdf_version: Optional[str] = None
    has_form_fields: bool = False
    form_fields: List[FormField] = field(default_factory=list)
    embedded_signatures: List[EmbeddedSignature] = field(default_factory=list)
    tables: List[TableData] = field(default_factory=list)
    sections: List[DocumentSection] = field(default_factory=list)
    bates_numbers: List[BatesNumber] = field(default_factory=list)
    redacted_regions: List[RedactedRegion] = field(default_factory=list)
    page_layouts: List[PageLayout] = field(default_factory=list)
    full_text: str = ""
    page_texts: List[str] = field(default_factory=list)
    backend_used: str = "none"
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "total_pages": self.total_pages,
            "metadata": {
                "title": self.title,
                "author": self.author,
                "creator": self.creator,
                "creation_date": self.creation_date,
                "modification_date": self.modification_date,
            },
            "security": {
                "is_encrypted": self.is_encrypted,
                "is_linearized": self.is_linearized,
                "pdf_version": self.pdf_version,
            },
            "form_fields": {
                "has_form_fields": self.has_form_fields,
                "count": len(self.form_fields),
                "fields": [
                    {
                        "name": f.name,
                        "type": f.field_type,
                        "value": f.value,
                        "page": f.page_number,
                    }
                    for f in self.form_fields
                ],
            },
            "signatures": {
                "count": len(self.embedded_signatures),
                "items": [
                    {
                        "page": s.page_number,
                        "signer": s.signer_name,
                        "signed_at": s.signed_at,
                        "valid": s.valid,
                    }
                    for s in self.embedded_signatures
                ],
            },
            "tables": [t.to_dict() for t in self.tables],
            "sections": [
                {
                    "type": s.section_type.value,
                    "title": s.title,
                    "pages": f"{s.start_page}-{s.end_page}",
                    "preview": s.content_preview[:200],
                }
                for s in self.sections
            ],
            "bates_numbers": [
                {"page": b.page_number, "value": b.value, "location": b.location}
                for b in self.bates_numbers
            ],
            "redacted_regions": [
                {
                    "page": r.page_number,
                    "estimated_chars": r.estimated_char_count,
                    "location": r.location_description,
                    "context": r.surrounding_context,
                }
                for r in self.redacted_regions
            ],
            "page_layouts": [
                {
                    "page": pl.page_number,
                    "size": f"{pl.width:.0f}x{pl.height:.0f}",
                    "columns": pl.columns,
                    "has_header": pl.has_header,
                    "has_footer": pl.has_footer,
                }
                for pl in self.page_layouts
            ],
            "backend_used": self.backend_used,
            "warnings": self.warnings,
        }


# ---------------------------------------------------------------------------
# PDF Analyzer
# ---------------------------------------------------------------------------

class PDFStructureAnalyzer:
    """
    Deep PDF structure analyzer for legal documents.
    Automatically selects PyMuPDF or pypdf backend.
    """

    BATES_PATTERN = re.compile(r"\b([A-Z]{2,6}[\s_-]?\d{4,10})\b")
    SECTION_MARKERS = {
        SectionType.RECITAL: ["recital", "witnesseth", "whereas"],
        SectionType.DEFINITIONS: ["definitions", "defined terms", "as used herein"],
        SectionType.COVENANTS: ["covenant", "agrees", "obligations"],
        SectionType.CONDITIONS: ["condition", "contingent", "provided that"],
        SectionType.SIGNATURES: ["in witness whereof", "signature page", "signed by", "executed by"],
        SectionType.EXHIBIT: ["exhibit", "attachment", "annex"],
        SectionType.SCHEDULE: ["schedule"],
        SectionType.AMENDMENT: ["amendment", "addendum", "modification"],
    }

    def __init__(self):
        if PYMUPDF_AVAILABLE:
            self.backend = "pymupdf"
        elif PYPDF_AVAILABLE:
            self.backend = "pypdf"
        else:
            self.backend = "none"
            logger.error("No PDF backend available. Install PyMuPDF or pypdf.")

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def analyze(self, source: str | Path | bytes) -> PDFAnalysisResult:
        """
        Analyze a PDF file.
        source can be a file path, Path object, or raw bytes.
        """
        result = PDFAnalysisResult(backend_used=self.backend)

        if isinstance(source, (str, Path)):
            result.file_path = str(source)
            with open(source, "rb") as f:
                pdf_bytes = f.read()
        else:
            pdf_bytes = source

        if self.backend == "pymupdf":
            self._analyze_with_pymupdf(pdf_bytes, result)
        elif self.backend == "pypdf":
            self._analyze_with_pypdf(pdf_bytes, result)
        else:
            result.warnings.append("No PDF backend installed.")

        # Post-processing (backend-agnostic)
        if result.full_text:
            result.sections = self._detect_sections(result.page_texts)
            result.bates_numbers = self._detect_bates_numbers(result.page_texts)

        return result

    # ------------------------------------------------------------------
    # PyMuPDF backend
    # ------------------------------------------------------------------

    def _analyze_with_pymupdf(self, pdf_bytes: bytes, result: PDFAnalysisResult) -> None:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        result.total_pages = doc.page_count
        result.pdf_version = f"1.{doc.pdf_trailer().get('Version', '?')}"
        result.is_encrypted = doc.is_encrypted

        # Metadata
        meta = doc.metadata or {}
        result.title = meta.get("title") or None
        result.author = meta.get("author") or None
        result.creator = meta.get("creator") or None
        result.creation_date = meta.get("creationDate") or None
        result.modification_date = meta.get("modDate") or None

        page_texts: List[str] = []
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text("text")
            page_texts.append(text)

            # Layout analysis
            layout = self._analyze_page_layout_pymupdf(page, page_num)
            result.page_layouts.append(layout)

            # Redaction detection
            redactions = self._detect_redactions_pymupdf(page, page_num, text)
            result.redacted_regions.extend(redactions)

            # Table extraction
            tables = self._extract_tables_pymupdf(page, page_num)
            result.tables.extend(tables)

        result.page_texts = page_texts
        result.full_text = "\n\n".join(page_texts)

        # Form fields
        form_fields = self._extract_form_fields_pymupdf(doc)
        result.form_fields = form_fields
        result.has_form_fields = len(form_fields) > 0

        # Embedded signatures
        result.embedded_signatures = self._detect_embedded_signatures_pymupdf(doc)

        doc.close()

    def _analyze_page_layout_pymupdf(self, page: Any, page_num: int) -> PageLayout:
        rect = page.rect
        blocks = page.get_text("blocks")
        text_blocks = [b for b in blocks if b[6] == 0]  # type 0 = text
        image_blocks = [b for b in blocks if b[6] == 1]  # type 1 = image

        height = rect.height
        header_zone = height * 0.08
        footer_zone = height * 0.92

        has_header = any(b[1] < header_zone for b in text_blocks)
        has_footer = any(b[3] > footer_zone for b in text_blocks)
        has_images = len(image_blocks) > 0

        # Estimate columns by analyzing x-coordinates of text blocks
        if text_blocks:
            x_centers = [(b[0] + b[2]) / 2 for b in text_blocks]
            mid = rect.width / 2
            left_count = sum(1 for x in x_centers if x < mid * 0.75)
            right_count = sum(1 for x in x_centers if x > mid * 1.25)
            columns = 2 if (left_count >= 2 and right_count >= 2) else 1
        else:
            columns = 1

        return PageLayout(
            page_number=page_num,
            width=rect.width,
            height=rect.height,
            columns=columns,
            has_header=has_header,
            has_footer=has_footer,
            has_images=has_images,
            text_blocks=len(text_blocks),
            rotation=page.rotation,
        )

    def _detect_redactions_pymupdf(
        self, page: Any, page_num: int, text: str
    ) -> List[RedactedRegion]:
        regions = []
        # Look for annotation-based redactions
        for annot in page.annots():
            if annot.type[0] == 12:  # Redact annotation type
                rect = annot.rect
                surrounding = self._get_surrounding_text(text, 100)
                regions.append(
                    RedactedRegion(
                        page_number=page_num,
                        estimated_char_count=int(
                            (rect.width * rect.height) / 60
                        ),  # rough estimate
                        location_description=f"x={rect.x0:.0f},y={rect.y0:.0f}",
                        surrounding_context=surrounding,
                    )
                )

        # Heuristic: detect large black rectangles via drawings
        drawings = page.get_drawings()
        for drawing in drawings:
            if drawing.get("fill") == (0, 0, 0) or drawing.get("color") == (0, 0, 0):
                rect = drawing.get("rect")
                if rect and rect.width > 50 and rect.height > 8:
                    regions.append(
                        RedactedRegion(
                            page_number=page_num,
                            estimated_char_count=int(rect.width * rect.height / 60),
                            location_description=f"Black rectangle at x={rect.x0:.0f},y={rect.y0:.0f} w={rect.width:.0f}h={rect.height:.0f}",
                            surrounding_context="",
                        )
                    )
        return regions

    def _extract_tables_pymupdf(self, page: Any, page_num: int) -> List[TableData]:
        tables = []
        try:
            tab_finder = page.find_tables()
            for idx, tab in enumerate(tab_finder.tables):
                df = tab.to_pandas()
                headers = list(df.columns.astype(str))
                rows = [list(row.astype(str)) for _, row in df.iterrows()]
                tables.append(
                    TableData(
                        page_number=page_num,
                        headers=headers,
                        rows=rows,
                        table_index=idx,
                    )
                )
        except Exception as e:
            logger.debug("Table extraction failed on page %d: %s", page_num, e)
        return tables

    def _extract_form_fields_pymupdf(self, doc: Any) -> List[FormField]:
        fields = []
        field_type_map = {
            0: "unknown", 1: "text", 2: "checkbox", 3: "radio",
            4: "text", 5: "dropdown", 6: "listbox", 7: "signature",
        }
        for page_num, page in enumerate(doc, start=1):
            for widget in page.widgets():
                ft = field_type_map.get(widget.field_type, "text")
                value = widget.field_value
                fields.append(
                    FormField(
                        name=widget.field_name or f"field_{len(fields)}",
                        field_type=ft,
                        value=str(value) if value is not None else None,
                        page_number=page_num,
                        required=bool(widget.field_flags & 2),
                        read_only=bool(widget.field_flags & 1),
                    )
                )
        return fields

    def _detect_embedded_signatures_pymupdf(self, doc: Any) -> List[EmbeddedSignature]:
        sigs = []
        for page_num, page in enumerate(doc, start=1):
            for widget in page.widgets():
                if widget.field_type == 7:  # Signature field
                    sigs.append(
                        EmbeddedSignature(
                            page_number=page_num,
                            signer_name=widget.field_name,
                            signed_at=str(widget.field_value) if widget.field_value else None,
                        )
                    )
        return sigs

    # ------------------------------------------------------------------
    # pypdf backend
    # ------------------------------------------------------------------

    def _analyze_with_pypdf(self, pdf_bytes: bytes, result: PDFAnalysisResult) -> None:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        result.total_pages = len(reader.pages)
        result.is_encrypted = reader.is_encrypted

        meta = reader.metadata or {}
        result.title = meta.get("/Title") or None
        result.author = meta.get("/Author") or None
        result.creator = meta.get("/Creator") or None
        result.creation_date = str(meta.get("/CreationDate", "")) or None
        result.modification_date = str(meta.get("/ModDate", "")) or None

        page_texts: List[str] = []
        for page_num, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""
            page_texts.append(text)

            # Simple layout heuristic
            result.page_layouts.append(
                PageLayout(
                    page_number=page_num,
                    width=float(page.mediabox.width),
                    height=float(page.mediabox.height),
                    columns=1,
                    has_header=False,
                    has_footer=False,
                    has_images=False,
                    text_blocks=len(text.split("\n\n")),
                )
            )

            # Redaction heuristic from text
            self._detect_redactions_from_text(text, page_num, result)

        result.page_texts = page_texts
        result.full_text = "\n\n".join(page_texts)

        # Form fields (pypdf AcroForm)
        if "/AcroForm" in (reader.trailer.get("/Root") or {}):
            result.has_form_fields = True
            result.warnings.append(
                "Form field extraction limited with pypdf backend; install PyMuPDF for full support."
            )

    def _detect_redactions_from_text(
        self, text: str, page_num: int, result: PDFAnalysisResult
    ) -> None:
        """Detect redaction placeholders in text (e.g. [REDACTED], ████)."""
        patterns = [r"\[REDACTED\]", r"\[REDACT\]", r"█+", r"▓+", r"<REDACTED>"]
        for pat in patterns:
            for match in re.finditer(pat, text):
                ctx_start = max(0, match.start() - 50)
                ctx_end = min(len(text), match.end() + 50)
                result.redacted_regions.append(
                    RedactedRegion(
                        page_number=page_num,
                        estimated_char_count=len(match.group(0)),
                        location_description="text placeholder",
                        surrounding_context=text[ctx_start:ctx_end],
                    )
                )

    # ------------------------------------------------------------------
    # Post-processing (backend-agnostic)
    # ------------------------------------------------------------------

    def _detect_sections(self, page_texts: List[str]) -> List[DocumentSection]:
        sections: List[DocumentSection] = []
        clause_re = re.compile(r"^\s*(\d+(?:\.\d+)*)\s+([A-Z][^\n]{0,80})", re.MULTILINE)

        for page_num, text in enumerate(page_texts, start=1):
            text_lower = text.lower()
            for section_type, markers in self.SECTION_MARKERS.items():
                for marker in markers:
                    if marker in text_lower:
                        # Find title line
                        idx = text_lower.index(marker)
                        line_start = text.rfind("\n", 0, idx) + 1
                        line_end = text.find("\n", idx)
                        title = text[line_start:line_end].strip() if line_end != -1 else marker
                        clauses = [m.group(0) for m in clause_re.finditer(text)]
                        sections.append(
                            DocumentSection(
                                section_type=section_type,
                                title=title[:120],
                                start_page=page_num,
                                end_page=page_num,
                                content_preview=text[idx : idx + 300].strip(),
                                clause_numbers=[c.split()[0] for c in clauses],
                            )
                        )
                        break  # one match per type per page
        return sections

    def _detect_bates_numbers(self, page_texts: List[str]) -> List[BatesNumber]:
        bates: List[BatesNumber] = []
        for page_num, text in enumerate(page_texts, start=1):
            lines = text.split("\n")
            for line_idx, line in enumerate(lines):
                for match in self.BATES_PATTERN.finditer(line):
                    location = "header" if line_idx < 3 else "footer" if line_idx >= len(lines) - 3 else "body"
                    bates.append(
                        BatesNumber(
                            page_number=page_num,
                            value=match.group(1),
                            location=location,
                        )
                    )
        return bates

    @staticmethod
    def _get_surrounding_text(text: str, chars: int = 100) -> str:
        mid = len(text) // 2
        start = max(0, mid - chars)
        end = min(len(text), mid + chars)
        return text[start:end].strip()


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

def analyze_pdf(source: str | Path | bytes) -> PDFAnalysisResult:
    """Analyze a PDF and return structured results. Convenience function."""
    analyzer = PDFStructureAnalyzer()
    return analyzer.analyze(source)
