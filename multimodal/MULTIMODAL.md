# SintraPrime Multimodal Processing Layer

The `multimodal/` package provides a complete multimodal processing layer for **SintraPrime-Unified**, enabling legal AI workflows that combine document images, PDF structure analysis, and audio transcription into unified case analyses.

---

## Modules

### 1. `document_vision.py` — Document Vision Engine
GPT-4o Vision integration for analyzing images of legal documents.

**Features:**
- Full OCR-style text extraction via vision API
- Signature detection (count, location, signer names)
- Stamp/seal detection (notary, court, official seals)
- Date extraction from handwritten and typed text
- Party identification with roles (testator, witness, grantor, etc.)
- Handwriting authenticity analysis with alteration detection
- Document type classification: `will`, `contract`, `deed`, `court_filing`, `identification`, `check`
- Batch processing with concurrent execution
- Graceful degradation when API key not configured

**Usage:**
```python
from multimodal.document_vision import DocumentVisionEngine

engine = DocumentVisionEngine()  # reads OPENAI_API_KEY from env

# From file path
result = engine.analyze_file("signed_will.jpg")

# From base64
result = engine.analyze_base64(b64_string, mime_type="image/png")

# From URL
result = engine.analyze_url("https://example.com/contract.jpg")

print(result.document_type)          # DocumentType.WILL
print(result.parties)                # [ExtractedParty(name="John Doe", role="testator", ...)]
print(result.handwriting.alterations_detected)  # False
print(result.to_dict())              # full structured output
```

---

### 2. `pdf_analyzer.py` — PDF Structure Analyzer
Deep PDF parsing beyond simple text extraction.

**Features:**
- Form field extraction (fillable PDFs) — type, value, required status
- Embedded digital signature detection
- Table extraction (court schedules, financial tables) — uses PyMuPDF `find_tables()`
- Section/clause detection: recitals, definitions, covenants, conditions, signature blocks, exhibits
- Bates number detection with position (header/footer/body)
- Redaction detection — annotation-based (PyMuPDF) and text placeholder-based
- Full page layout analysis (columns, headers, footers, images, rotation)
- Automatic backend selection: **PyMuPDF (fitz)** → **pypdf** fallback

**Usage:**
```python
from multimodal.pdf_analyzer import analyze_pdf

# From file path
result = analyze_pdf("deposition_exhibit.pdf")

# From bytes
with open("contract.pdf", "rb") as f:
    result = analyze_pdf(f.read())

print(result.total_pages)
print(result.form_fields)
print(result.tables)
print(result.bates_numbers)
print(result.redacted_regions)
print(result.to_dict())
```

**Install PyMuPDF for best results:**
```bash
pip install pymupdf
```

---

### 3. `audio_transcription.py` — Legal Audio Transcription
Transcription with speaker diarization and legal-context awareness.

**Features:**
- OpenAI Whisper API integration (cloud, best accuracy)
- faster-whisper local backend (efficient GPU/CPU inference)
- openai-whisper local backend (original OpenAI model)
- Speaker diarization via silence gap heuristics
- Legal terminology detection (objection, hearsay, sustained, etc.)
- Objection extraction with timestamps
- Action item extraction from transcripts
- Speaker profiling (role identification, speaking time, word count)
- Output formats: structured dict, SRT subtitles, plain text

**Supported audio formats:** `.mp3`, `.mp4`, `.mpeg`, `.mpga`, `.m4a`, `.wav`, `.webm`, `.ogg`, `.flac`

**Usage:**
```python
from multimodal.audio_transcription import LegalAudioTranscriber

transcriber = LegalAudioTranscriber()  # auto-selects best available backend

result = transcriber.transcribe_file("deposition_smith_2024.mp3")

print(result.recording_type)         # LegalRecordingType.DEPOSITION
print(result.speakers)               # [SpeakerProfile(label="Speaker 1", role="attorney", ...)]
print(result.objections)             # [{"speaker": ..., "timestamp": ..., "text": ...}]
print(result.action_items)           # [ActionItem(description=..., assigned_to=...)]
print(result.to_srt())               # SRT subtitle export
print(result.to_plaintext())         # readable transcript
```

---

### 4. `legal_analyzer.py` — Multimodal Legal Analyzer
Unifies vision, PDF, and audio results into a complete case analysis.

**Features:**
- Cross-references parties and dates across all media types
- Timeline construction from all sources (sorted by parsed date)
- Inconsistency detection: alterations, missing signatures, timeline gaps, party mismatches
- Evidence strength scoring (0.0–1.0) with corroboration bonuses and inconsistency penalties
- Case summary generation with recommendations
- Evidence strength classification: `strong`, `moderate`, `weak`, `insufficient`

**Usage:**
```python
from multimodal.legal_analyzer import analyze_case

summary = analyze_case(
    vision_results=[vision_result],
    pdf_results=[pdf_result],
    audio_results=[audio_result],
    case_id="CASE-2024-001",
)

print(summary.evidence_strength)     # EvidenceStrength.STRONG
print(summary.evidence_score)        # 0.847
print(summary.inconsistencies)       # list of detected inconsistencies
print(summary.recommendations)       # legal action recommendations
print(summary.summary_text)          # human-readable case summary
print(summary.to_dict())             # full structured output
```

---

### 5. `multimodal_api.py` — FastAPI Router
REST API exposing all multimodal capabilities.

**Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/multimodal/analyze-image` | Analyze document image (upload or base64) |
| `POST` | `/multimodal/analyze-pdf` | Deep PDF structure analysis |
| `POST` | `/multimodal/transcribe` | Audio to legal transcript |
| `POST` | `/multimodal/full-analysis` | All three combined + case summary |
| `GET` | `/multimodal/supported-formats` | List supported file types |

**Mount in your FastAPI app:**
```python
from fastapi import FastAPI
from multimodal.multimodal_api import create_multimodal_router

app = FastAPI()
app.include_router(create_multimodal_router())
```

**Standalone:**
```python
from multimodal.multimodal_api import create_app
import uvicorn

app = create_app()
uvicorn.run(app, host="0.0.0.0", port=8080)
```

---

## Installation

```bash
# Required
pip install openai fastapi pydantic

# Recommended for PDF (full feature set)
pip install pymupdf

# Fallback PDF
pip install pypdf

# Local audio transcription (optional)
pip install faster-whisper
# or
pip install openai-whisper
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | Required for GPT-4o Vision and Whisper API |

---

## Running Tests

```bash
# From the SintraPrime-Unified root
python -m pytest multimodal/tests/ -v

# With coverage
python -m pytest multimodal/tests/ -v --cov=multimodal --cov-report=term-missing
```

Tests mock all external API calls (OpenAI Vision, Whisper) and work without any API keys or network access.

---

## Architecture

```
multimodal/
├── __init__.py               # Package exports
├── document_vision.py        # GPT-4o Vision engine (~400 lines)
├── pdf_analyzer.py           # PDF structure analyzer (~400 lines)
├── audio_transcription.py    # Legal audio transcriber (~380 lines)
├── legal_analyzer.py         # Unified case analyzer (~350 lines)
├── multimodal_api.py         # FastAPI router (~230 lines)
├── MULTIMODAL.md             # This file
└── tests/
    ├── __init__.py
    └── test_multimodal.py    # 70+ tests
```

---

## Supported Document Types

| Type | Detection Keywords |
|------|--------------------|
| Will | last will, testator, bequeath, executor |
| Contract | agreement, consideration, witnesseth |
| Deed | grantor, grantee, convey and warrant, parcel |
| Court Filing | plaintiff, defendant, case no, motion, judgment |
| Identification | driver license, passport, date of birth |
| Check | pay to the order of, routing number |

---

## Supported Recording Types

- Depositions
- Court Hearings
- Client Calls
- Mediation Sessions
- Arbitration Proceedings
- Telephone Conferences

---

*Part of SintraPrime-Unified — The smartest AI agent system.*
