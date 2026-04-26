"""
Document Ingester — Ingest legal documents into the RAG knowledge base.
Supports: Python/Markdown source files, PDFs, plain text, CourtListener JSON.
"""

import hashlib
import re
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class LegalDocument:
    """A single legal document with content, metadata, and optional embedding."""
    id: str
    content: str
    metadata: dict          # source, category, jurisdiction, date, etc.
    embedding: Optional[list[float]] = None
    chunks: list[str] = field(default_factory=list)


class DocumentIngester:
    """
    Ingests legal knowledge from:
    1. SintraPrime's trust_law/ module
    2. SintraPrime's legal_intelligence/ module
    3. SintraPrime's federal_agencies/ module
    4. SintraPrime's case_law/ module
    5. External legal documents (PDF, TXT, DOCX)
    6. Court decisions (JSON from CourtListener)
    """

    CHUNK_SIZE = 512       # approximate token target (chars / 4)
    CHUNK_OVERLAP = 64     # overlap in approximate tokens

    # Jurisdiction keyword mapping
    JURISDICTION_PATTERNS = {
        "federal": re.compile(
            r"\b(federal|U\.S\.|United States|USC|CFR|IRS|SEC|FDIC|OCC|FRB|CFPB|FHFA)\b",
            re.IGNORECASE,
        ),
        "california": re.compile(r"\b(California|Cal\.|CA)\b", re.IGNORECASE),
        "new_york": re.compile(r"\b(New York|N\.Y\.|NY)\b", re.IGNORECASE),
        "texas": re.compile(r"\b(Texas|Tex\.|TX)\b", re.IGNORECASE),
        "delaware": re.compile(r"\b(Delaware|Del\.|DE)\b", re.IGNORECASE),
        "florida": re.compile(r"\b(Florida|Fla\.|FL)\b", re.IGNORECASE),
    }

    STATUTE_PATTERN = re.compile(
        r"\b(\d+\s+U\.S\.C\.?\s+§?\s*\d+[\w\-]*"
        r"|\d+\s+C\.F\.R\.?\s+§?\s*\d+[\w\-\.]*"
        r"|§\s*\d+[\w\-\.]*"
        r"|Rule\s+\d+[\w\-\.]*)\b",
        re.IGNORECASE,
    )

    DATE_PATTERN = re.compile(
        r"\b(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}"
        r"|\b(?:January|February|March|April|May|June|July|August|September"
        r"|October|November|December)\s+\d{1,2},?\s+\d{4})\b",
        re.IGNORECASE,
    )

    PARTY_PATTERN = re.compile(
        r"\b([A-Z][A-Za-z\s&\.,]+)\s+v\.?\s+([A-Z][A-Za-z\s&\.,]+)\b"
    )

    CASE_TYPE_PATTERNS = {
        "trust_law": re.compile(
            r"\b(trust|trustee|beneficiary|settlor|grantor|fiduciary|estate|probate)\b",
            re.IGNORECASE,
        ),
        "contract": re.compile(
            r"\b(contract|agreement|breach|consideration|offer|acceptance)\b",
            re.IGNORECASE,
        ),
        "regulatory": re.compile(
            r"\b(regulation|compliance|agency|rulemaking|administrative)\b",
            re.IGNORECASE,
        ),
        "securities": re.compile(
            r"\b(securities|SEC|stock|shareholder|investment|fraud)\b",
            re.IGNORECASE,
        ),
        "constitutional": re.compile(
            r"\b(constitutional|amendment|due process|equal protection|First Amendment)\b",
            re.IGNORECASE,
        ),
    }

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def ingest_directory(self, path: str, category: str) -> list[LegalDocument]:
        """
        Recursively ingest all .py, .md, and .txt files from a directory.

        Args:
            path:     Filesystem path to the directory.
            category: Logical category label (e.g. 'trust_law').

        Returns:
            List of LegalDocument objects (one per file).
        """
        root = Path(path)
        if not root.exists():
            return []

        documents: list[LegalDocument] = []
        extensions = {".py", ".md", ".txt", ".rst"}

        for file_path in sorted(root.rglob("*")):
            if file_path.is_file() and file_path.suffix.lower() in extensions:
                try:
                    content = file_path.read_text(encoding="utf-8", errors="replace")
                    if not content.strip():
                        continue

                    doc_id = self._make_id(str(file_path))
                    metadata = self.extract_legal_metadata(content)
                    metadata.update(
                        {
                            "source": str(file_path),
                            "category": category,
                            "file_type": file_path.suffix.lstrip("."),
                            "file_name": file_path.name,
                        }
                    )

                    chunks = self.chunk_text(content, doc_id)

                    doc = LegalDocument(
                        id=doc_id,
                        content=content,
                        metadata=metadata,
                        chunks=chunks,
                    )
                    documents.append(doc)

                except Exception as exc:  # noqa: BLE001
                    # Log but do not crash on individual file errors
                    print(f"[DocumentIngester] Warning: could not read {file_path}: {exc}")

        return documents

    def ingest_pdf(self, path: str) -> list[LegalDocument]:
        """
        Ingest a legal PDF document.
        Attempts pdfplumber → PyPDF2 → pdfminer → raw extraction in that order.

        Args:
            path: Filesystem path to the PDF file.

        Returns:
            List with one LegalDocument per logical section (or one per page
            when no clear section boundaries are detected).
        """
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"PDF not found: {path}")

        text = self._extract_pdf_text(file_path)
        if not text.strip():
            return []

        doc_id = self._make_id(str(file_path))
        metadata = self.extract_legal_metadata(text)
        metadata.update(
            {
                "source": str(file_path),
                "category": "pdf_document",
                "file_type": "pdf",
                "file_name": file_path.name,
            }
        )

        chunks = self.chunk_text(text, doc_id)

        return [
            LegalDocument(
                id=doc_id,
                content=text,
                metadata=metadata,
                chunks=chunks,
            )
        ]

    def ingest_case_json(self, data: dict) -> LegalDocument:
        """
        Ingest a court case from CourtListener JSON format.

        Handles top-level fields:
        - id, case_name, date_filed, court, jurisdiction_type,
          plain_text / html_with_citations / opinions[].text
        """
        case_id = str(data.get("id", self._make_id(json.dumps(data)[:256])))
        case_name = data.get("case_name", "Unknown v. Unknown")
        date_filed = data.get("date_filed", "")
        court = data.get("court", "")
        jurisdiction_type = data.get("jurisdiction_type", "")
        docket_number = data.get("docket_number", "")

        # Extract opinion text
        text_parts: list[str] = []
        if data.get("plain_text"):
            text_parts.append(data["plain_text"])
        if data.get("html_with_citations"):
            # Strip basic HTML tags
            raw = re.sub(r"<[^>]+>", " ", data["html_with_citations"])
            text_parts.append(raw)
        for opinion in data.get("opinions", []):
            for key in ("text", "plain_text", "html"):
                if opinion.get(key):
                    text_parts.append(
                        re.sub(r"<[^>]+>", " ", opinion[key])
                    )
                    break

        content = f"{case_name}\n\n" + "\n\n".join(text_parts)
        content = re.sub(r"\s{3,}", "\n\n", content).strip()

        doc_id = f"case_{case_id}"
        metadata = self.extract_legal_metadata(content)
        metadata.update(
            {
                "source": f"CourtListener:{case_id}",
                "category": "case_law",
                "case_name": case_name,
                "date_filed": date_filed,
                "court": court,
                "jurisdiction_type": jurisdiction_type,
                "docket_number": docket_number,
            }
        )

        chunks = self.chunk_text(content, doc_id)

        return LegalDocument(
            id=doc_id,
            content=content,
            metadata=metadata,
            chunks=chunks,
        )

    def chunk_text(self, text: str, doc_id: str) -> list[str]:
        """
        Split text into overlapping token-sized chunks for embedding.

        Uses character-level approximation: 1 token ≈ 4 characters.
        Respects paragraph and sentence boundaries when possible.
        """
        char_size = self.CHUNK_SIZE * 4
        char_overlap = self.CHUNK_OVERLAP * 4

        if not text:
            return []

        # Normalise whitespace
        text = re.sub(r"\r\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Try to split on paragraph boundaries first
        paragraphs = text.split("\n\n")
        chunks: list[str] = []
        current = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(current) + len(para) + 2 <= char_size:
                current = (current + "\n\n" + para).strip()
            else:
                if current:
                    chunks.append(current)
                    # Start next chunk with overlap from the end of current
                    overlap_start = max(0, len(current) - char_overlap)
                    current = current[overlap_start:].strip() + "\n\n" + para
                    current = current.strip()
                else:
                    # Single paragraph larger than chunk size — split by sentence
                    sentences = re.split(r"(?<=[.!?])\s+", para)
                    for sent in sentences:
                        if len(current) + len(sent) + 1 <= char_size:
                            current = (current + " " + sent).strip()
                        else:
                            if current:
                                chunks.append(current)
                                overlap_start = max(0, len(current) - char_overlap)
                                current = current[overlap_start:].strip() + " " + sent
                            else:
                                # Sentence itself exceeds chunk size — hard split
                                for i in range(0, len(sent), char_size - char_overlap):
                                    chunks.append(sent[i: i + char_size])
                                current = ""

        if current.strip():
            chunks.append(current.strip())

        # Assign chunk IDs (embedded in chunk header for traceability)
        labelled = []
        for idx, chunk in enumerate(chunks):
            labelled.append(f"[{doc_id}::chunk{idx}]\n{chunk}")

        return labelled

    def extract_legal_metadata(self, content: str) -> dict:
        """
        Extract structured metadata from legal text via regex patterns.

        Returns dict with: jurisdiction, case_type, parties, dates, statutes_cited
        """
        # Jurisdiction
        jurisdiction = "unknown"
        best_count = 0
        for jname, pattern in self.JURISDICTION_PATTERNS.items():
            matches = pattern.findall(content)
            if len(matches) > best_count:
                best_count = len(matches)
                jurisdiction = jname

        # Case type — pick all that match, primary is highest-match
        case_types: dict[str, int] = {}
        for ctype, pattern in self.CASE_TYPE_PATTERNS.items():
            count = len(pattern.findall(content))
            if count > 0:
                case_types[ctype] = count
        primary_case_type = (
            max(case_types, key=lambda k: case_types[k]) if case_types else "general"
        )

        # Parties (v. pattern)
        parties_raw = self.PARTY_PATTERN.findall(content[:4000])  # First 4k chars
        parties = [f"{p[0].strip()} v. {p[1].strip()}" for p in parties_raw[:5]]

        # Dates
        dates = list(dict.fromkeys(self.DATE_PATTERN.findall(content)))[:10]

        # Statutes cited
        statutes = list(dict.fromkeys(self.STATUTE_PATTERN.findall(content)))[:20]

        return {
            "jurisdiction": jurisdiction,
            "case_type": primary_case_type,
            "case_types_detected": list(case_types.keys()),
            "parties": parties,
            "dates": dates,
            "statutes_cited": statutes,
        }

    # ------------------------------------------------------------------ #
    #  Private helpers                                                     #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _make_id(source: str) -> str:
        return hashlib.sha1(source.encode()).hexdigest()[:12]

    @staticmethod
    def _extract_pdf_text(file_path: Path) -> str:
        """Try multiple PDF extraction libraries, fall back gracefully."""
        # 1. pdfplumber
        try:
            import pdfplumber  # type: ignore

            with pdfplumber.open(str(file_path)) as pdf:
                pages = [p.extract_text() or "" for p in pdf.pages]
            return "\n\n".join(pages)
        except ImportError:
            pass
        except Exception:
            pass

        # 2. PyPDF2
        try:
            from PyPDF2 import PdfReader  # type: ignore

            reader = PdfReader(str(file_path))
            pages = [
                (page.extract_text() or "") for page in reader.pages
            ]
            return "\n\n".join(pages)
        except ImportError:
            pass
        except Exception:
            pass

        # 3. pdfminer
        try:
            from pdfminer.high_level import extract_text  # type: ignore

            return extract_text(str(file_path))
        except ImportError:
            pass
        except Exception:
            pass

        # 4. poppler (system tool)
        import subprocess

        result = subprocess.run(
            ["pdftotext", str(file_path), "-"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return result.stdout

        raise RuntimeError(
            f"Could not extract text from PDF: {file_path}. "
            "Install pdfplumber, PyPDF2, pdfminer, or poppler-utils."
        )
