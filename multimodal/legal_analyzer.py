"""
legal_analyzer.py — Multimodal legal case analyzer.

Combines vision (document images), text (PDF parsing), and audio (transcription)
to produce a unified case analysis:
- Cross-references information across media types
- Constructs a unified timeline
- Scores evidence strength
- Generates a multimedia case summary
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .document_vision import DocumentVisionResult, DocumentType
from .pdf_analyzer import PDFAnalysisResult
from .audio_transcription import TranscriptionResult, LegalRecordingType

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class EvidenceStrength(str, Enum):
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    INSUFFICIENT = "insufficient"


class InconsistencyType(str, Enum):
    DATE_MISMATCH = "date_mismatch"
    PARTY_MISMATCH = "party_mismatch"
    SIGNATURE_MISSING = "signature_missing"
    DOCUMENT_ALTERED = "document_altered"
    AUDIO_TEXT_CONFLICT = "audio_text_conflict"
    TIMELINE_GAP = "timeline_gap"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class TimelineEvent:
    date_str: str
    description: str
    source: str  # "vision", "pdf", "audio", "inferred"
    confidence: float = 1.0
    page_or_timestamp: Optional[str] = None
    parsed_date: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date_str,
            "description": self.description,
            "source": self.source,
            "confidence": self.confidence,
            "location": self.page_or_timestamp,
        }


@dataclass
class Inconsistency:
    inconsistency_type: InconsistencyType
    description: str
    sources: List[str]
    severity: str = "medium"  # low, medium, high

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.inconsistency_type.value,
            "description": self.description,
            "sources": self.sources,
            "severity": self.severity,
        }


@dataclass
class EvidenceItem:
    source_type: str  # "document_image", "pdf", "audio"
    description: str
    weight: float  # 0.0-1.0
    corroborated: bool = False
    corroboration_sources: List[str] = field(default_factory=list)


@dataclass
class CaseSummary:
    case_id: Optional[str] = None
    summary_text: str = ""
    key_parties: List[str] = field(default_factory=list)
    key_dates: List[str] = field(default_factory=list)
    timeline: List[TimelineEvent] = field(default_factory=list)
    inconsistencies: List[Inconsistency] = field(default_factory=list)
    evidence_items: List[EvidenceItem] = field(default_factory=list)
    evidence_strength: EvidenceStrength = EvidenceStrength.INSUFFICIENT
    evidence_score: float = 0.0
    document_types_found: List[str] = field(default_factory=list)
    cross_references: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "summary": self.summary_text,
            "key_parties": self.key_parties,
            "key_dates": self.key_dates,
            "timeline": [e.to_dict() for e in self.timeline],
            "inconsistencies": [i.to_dict() for i in self.inconsistencies],
            "evidence_strength": self.evidence_strength.value,
            "evidence_score": self.evidence_score,
            "document_types_found": self.document_types_found,
            "cross_references": self.cross_references,
            "recommendations": self.recommendations,
            "warnings": self.warnings,
            "evidence_items": [
                {
                    "source": e.source_type,
                    "description": e.description,
                    "weight": e.weight,
                    "corroborated": e.corroborated,
                }
                for e in self.evidence_items
            ],
        }


# ---------------------------------------------------------------------------
# Date parsing utilities
# ---------------------------------------------------------------------------

DATE_PATTERNS = [
    re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b"),
    re.compile(r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})\b", re.IGNORECASE),
    re.compile(r"\b(\d{4})[/-](\d{2})[/-](\d{2})\b"),
]

MONTH_MAP = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}


def parse_date_fuzzy(date_str: str) -> Optional[datetime]:
    """Attempt to parse a date string into a datetime object."""
    for pat in DATE_PATTERNS:
        m = pat.search(date_str)
        if not m:
            continue
        try:
            groups = m.groups()
            if len(groups) == 3:
                if groups[0].isdigit() and groups[1].isdigit() and groups[2].isdigit():
                    g0, g1, g2 = int(groups[0]), int(groups[1]), int(groups[2])
                    if len(groups[2]) == 4:
                        # M/D/YYYY or YYYY-MM-DD (year in last position)
                        if g0 > 31:
                            return datetime(g0, g1, g2)
                        else:
                            return datetime(g2, g0, g1)
                    elif g0 > 31:
                        # YYYY-MM-DD where year is in first position, day is 2-digit
                        return datetime(g0, g1, g2)
                    else:
                        yr = g2
                        yr = yr + 2000 if yr < 50 else yr + 1900
                        return datetime(yr, g0, g1)
                else:
                    # Month name
                    month = MONTH_MAP.get(str(groups[0]).lower())
                    if month:
                        return datetime(int(groups[2]), month, int(groups[1]))
        except (ValueError, IndexError):
            continue
    return None


# ---------------------------------------------------------------------------
# Multimodal Legal Analyzer
# ---------------------------------------------------------------------------

class MultimodalLegalAnalyzer:
    """
    Integrates vision, PDF, and audio analysis results into a unified
    legal case analysis.
    """

    def __init__(self, case_id: Optional[str] = None):
        self.case_id = case_id

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def analyze(
        self,
        vision_results: Optional[List[DocumentVisionResult]] = None,
        pdf_results: Optional[List[PDFAnalysisResult]] = None,
        audio_results: Optional[List[TranscriptionResult]] = None,
    ) -> CaseSummary:
        """
        Perform unified multimodal analysis.

        At least one of vision_results, pdf_results, or audio_results must be provided.
        """
        summary = CaseSummary(case_id=self.case_id)

        vision_results = vision_results or []
        pdf_results = pdf_results or []
        audio_results = audio_results or []

        if not any([vision_results, pdf_results, audio_results]):
            summary.warnings.append("No analysis inputs provided.")
            return summary

        # Step 1: Collect evidence items
        self._collect_evidence(summary, vision_results, pdf_results, audio_results)

        # Step 2: Build timeline
        self._build_timeline(summary, vision_results, pdf_results, audio_results)

        # Step 3: Extract key parties
        self._extract_parties(summary, vision_results, pdf_results, audio_results)

        # Step 4: Cross-reference
        self._cross_reference(summary, vision_results, pdf_results, audio_results)

        # Step 5: Detect inconsistencies
        self._detect_inconsistencies(summary, vision_results, pdf_results, audio_results)

        # Step 6: Score evidence
        self._score_evidence(summary)

        # Step 7: Generate recommendations
        self._generate_recommendations(summary, vision_results, pdf_results, audio_results)

        # Step 8: Generate summary text
        summary.summary_text = self._generate_summary_text(summary, vision_results, pdf_results, audio_results)

        return summary

    # ------------------------------------------------------------------
    # Evidence collection
    # ------------------------------------------------------------------

    def _collect_evidence(
        self,
        summary: CaseSummary,
        vision: List[DocumentVisionResult],
        pdfs: List[PDFAnalysisResult],
        audio: List[TranscriptionResult],
    ) -> None:
        for vr in vision:
            weight = vr.confidence_score * 0.9
            if vr.handwriting.alterations_detected:
                weight *= 0.5
                summary.warnings.append("Document alterations detected — evidence weight reduced.")
            summary.evidence_items.append(
                EvidenceItem(
                    source_type="document_image",
                    description=f"{vr.document_type.value} document with {len(vr.parties)} parties",
                    weight=weight,
                )
            )
            summary.document_types_found.append(vr.document_type.value)

        for pr in pdfs:
            weight = 0.85
            if pr.redacted_regions:
                weight *= 0.8
                summary.warnings.append(f"{len(pr.redacted_regions)} redacted region(s) in PDF.")
            summary.evidence_items.append(
                EvidenceItem(
                    source_type="pdf",
                    description=f"PDF: {pr.total_pages} pages, {len(pr.sections)} sections",
                    weight=weight,
                )
            )

        for ar in audio:
            weight = ar.confidence_avg * 0.8
            summary.evidence_items.append(
                EvidenceItem(
                    source_type="audio",
                    description=f"{ar.recording_type.value} recording, {len(ar.segments)} segments",
                    weight=weight,
                )
            )

    # ------------------------------------------------------------------
    # Timeline construction
    # ------------------------------------------------------------------

    def _build_timeline(
        self,
        summary: CaseSummary,
        vision: List[DocumentVisionResult],
        pdfs: List[PDFAnalysisResult],
        audio: List[TranscriptionResult],
    ) -> None:
        events: List[TimelineEvent] = []

        for vr in vision:
            for date_str in vr.dates_found:
                events.append(
                    TimelineEvent(
                        date_str=date_str,
                        description=f"Date found in {vr.document_type.value} document",
                        source="vision",
                        confidence=vr.confidence_score,
                        parsed_date=parse_date_fuzzy(date_str),
                    )
                )

        for pr in pdfs:
            if pr.creation_date:
                events.append(
                    TimelineEvent(
                        date_str=str(pr.creation_date),
                        description="PDF creation date",
                        source="pdf",
                        confidence=1.0,
                        parsed_date=parse_date_fuzzy(str(pr.creation_date)),
                    )
                )
            if pr.modification_date and pr.modification_date != pr.creation_date:
                events.append(
                    TimelineEvent(
                        date_str=str(pr.modification_date),
                        description="PDF last modified",
                        source="pdf",
                        confidence=1.0,
                        parsed_date=parse_date_fuzzy(str(pr.modification_date)),
                    )
                )
            # Dates from text
            date_re = re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b")
            for date_str in date_re.findall(pr.full_text)[:20]:
                events.append(
                    TimelineEvent(
                        date_str=date_str,
                        description="Date found in PDF text",
                        source="pdf",
                        confidence=0.7,
                        parsed_date=parse_date_fuzzy(date_str),
                    )
                )

        # Deduplicate and sort
        seen = set()
        unique_events = []
        for ev in events:
            key = (ev.date_str, ev.source)
            if key not in seen:
                seen.add(key)
                unique_events.append(ev)

        unique_events.sort(
            key=lambda e: e.parsed_date or datetime(9999, 12, 31)
        )
        summary.timeline = unique_events
        summary.key_dates = list({e.date_str for e in unique_events[:10]})

    # ------------------------------------------------------------------
    # Party extraction
    # ------------------------------------------------------------------

    def _extract_parties(
        self,
        summary: CaseSummary,
        vision: List[DocumentVisionResult],
        pdfs: List[PDFAnalysisResult],
        audio: List[TranscriptionResult],
    ) -> None:
        parties: set = set()

        for vr in vision:
            for party in vr.parties:
                if party.name:
                    parties.add(party.name)

        for ar in audio:
            for speaker in ar.speakers:
                if speaker.identified_name:
                    parties.add(speaker.identified_name)
                elif speaker.label:
                    parties.add(speaker.label)

        summary.key_parties = sorted(parties)

    # ------------------------------------------------------------------
    # Cross-referencing
    # ------------------------------------------------------------------

    def _cross_reference(
        self,
        summary: CaseSummary,
        vision: List[DocumentVisionResult],
        pdfs: List[PDFAnalysisResult],
        audio: List[TranscriptionResult],
    ) -> None:
        refs = []

        # Cross-ref parties between vision and audio
        vision_names = set()
        for vr in vision:
            for p in vr.parties:
                vision_names.add(p.name.lower())

        audio_names = set()
        for ar in audio:
            for sp in ar.speakers:
                if sp.identified_name:
                    audio_names.add(sp.identified_name.lower())

        overlap = vision_names & audio_names
        if overlap:
            refs.append({
                "type": "party_confirmed",
                "description": f"Party names confirmed across document and audio: {', '.join(overlap)}",
                "confidence": 0.9,
            })
            for ei in summary.evidence_items:
                ei.corroborated = True
                if "document_image" in ei.source_type or "audio" in ei.source_type:
                    ei.corroboration_sources.append("cross_reference")

        # Cross-ref dates between PDF and vision
        pdf_dates = set()
        for pr in pdfs:
            date_re = re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b")
            for d in date_re.findall(pr.full_text)[:20]:
                pdf_dates.add(d)

        vision_dates = set()
        for vr in vision:
            vision_dates.update(vr.dates_found)

        date_overlap = pdf_dates & vision_dates
        if date_overlap:
            refs.append({
                "type": "date_confirmed",
                "description": f"Dates confirmed across PDF and image: {', '.join(list(date_overlap)[:5])}",
                "confidence": 0.85,
            })

        summary.cross_references = refs

    # ------------------------------------------------------------------
    # Inconsistency detection
    # ------------------------------------------------------------------

    def _detect_inconsistencies(
        self,
        summary: CaseSummary,
        vision: List[DocumentVisionResult],
        pdfs: List[PDFAnalysisResult],
        audio: List[TranscriptionResult],
    ) -> None:
        for vr in vision:
            if vr.handwriting.alterations_detected:
                summary.inconsistencies.append(
                    Inconsistency(
                        inconsistency_type=InconsistencyType.DOCUMENT_ALTERED,
                        description=f"Handwriting alterations detected in {vr.document_type.value}: {', '.join(vr.handwriting.alteration_regions)}",
                        sources=["vision"],
                        severity="high",
                    )
                )

            # Check signatures vs parties
            if vr.parties and not vr.signatures.detected:
                summary.inconsistencies.append(
                    Inconsistency(
                        inconsistency_type=InconsistencyType.SIGNATURE_MISSING,
                        description=f"Parties listed but no signatures detected in {vr.document_type.value}.",
                        sources=["vision"],
                        severity="medium",
                    )
                )

        # Timeline gap detection
        if len(summary.timeline) >= 2:
            sorted_events = [e for e in summary.timeline if e.parsed_date]
            for i in range(len(sorted_events) - 1):
                delta = sorted_events[i + 1].parsed_date - sorted_events[i].parsed_date
                if delta.days > 365:
                    summary.inconsistencies.append(
                        Inconsistency(
                            inconsistency_type=InconsistencyType.TIMELINE_GAP,
                            description=f"Large timeline gap ({delta.days} days) between {sorted_events[i].date_str} and {sorted_events[i+1].date_str}.",
                            sources=["timeline"],
                            severity="low",
                        )
                    )

    # ------------------------------------------------------------------
    # Evidence scoring
    # ------------------------------------------------------------------

    def _score_evidence(self, summary: CaseSummary) -> None:
        if not summary.evidence_items:
            summary.evidence_score = 0.0
            summary.evidence_strength = EvidenceStrength.INSUFFICIENT
            return

        base_score = sum(ei.weight for ei in summary.evidence_items) / len(summary.evidence_items)

        # Bonuses
        corroborated = sum(1 for ei in summary.evidence_items if ei.corroborated)
        corroboration_bonus = min(0.2, corroborated * 0.05)

        # Penalties for inconsistencies
        high_severity = sum(1 for i in summary.inconsistencies if i.severity == "high")
        med_severity = sum(1 for i in summary.inconsistencies if i.severity == "medium")
        penalty = high_severity * 0.15 + med_severity * 0.05

        final = min(1.0, max(0.0, base_score + corroboration_bonus - penalty))
        summary.evidence_score = round(final, 3)

        if final >= 0.75:
            summary.evidence_strength = EvidenceStrength.STRONG
        elif final >= 0.55:
            summary.evidence_strength = EvidenceStrength.MODERATE
        elif final >= 0.30:
            summary.evidence_strength = EvidenceStrength.WEAK
        else:
            summary.evidence_strength = EvidenceStrength.INSUFFICIENT

    # ------------------------------------------------------------------
    # Recommendations
    # ------------------------------------------------------------------

    def _generate_recommendations(
        self,
        summary: CaseSummary,
        vision: List[DocumentVisionResult],
        pdfs: List[PDFAnalysisResult],
        audio: List[TranscriptionResult],
    ) -> None:
        recs = []

        if any(i.inconsistency_type == InconsistencyType.DOCUMENT_ALTERED for i in summary.inconsistencies):
            recs.append("Retain forensic document examiner to analyze suspected alterations.")

        if any(i.inconsistency_type == InconsistencyType.SIGNATURE_MISSING for i in summary.inconsistencies):
            recs.append("Obtain original signed copies or verify execution of unsigned documents.")

        if summary.evidence_strength in (EvidenceStrength.WEAK, EvidenceStrength.INSUFFICIENT):
            recs.append("Gather additional corroborating evidence to strengthen the case.")

        for pr in pdfs:
            if pr.redacted_regions:
                recs.append(f"Seek unredacted copies of PDF ({len(pr.redacted_regions)} redaction(s) found).")

        if any(i.inconsistency_type == InconsistencyType.TIMELINE_GAP for i in summary.inconsistencies):
            recs.append("Investigate timeline gaps with additional documents or witness statements.")

        for ar in audio:
            if ar.objections:
                recs.append(f"Review {len(ar.objections)} objection(s) raised during recorded proceedings.")

        summary.recommendations = recs

    # ------------------------------------------------------------------
    # Summary text
    # ------------------------------------------------------------------

    def _generate_summary_text(
        self,
        summary: CaseSummary,
        vision: List[DocumentVisionResult],
        pdfs: List[PDFAnalysisResult],
        audio: List[TranscriptionResult],
    ) -> str:
        lines = []
        case_label = f"Case {self.case_id}" if self.case_id else "Case Analysis"
        lines.append(f"=== {case_label} — Multimodal Legal Analysis ===\n")

        lines.append(f"Evidence Strength: {summary.evidence_strength.value.upper()} (score: {summary.evidence_score:.0%})")
        lines.append(f"Media analyzed: {len(vision)} image(s), {len(pdfs)} PDF(s), {len(audio)} audio recording(s)")

        if summary.key_parties:
            lines.append(f"\nKey Parties ({len(summary.key_parties)}): {', '.join(summary.key_parties[:10])}")

        if summary.key_dates:
            lines.append(f"Key Dates: {', '.join(summary.key_dates[:5])}")

        if summary.timeline:
            lines.append(f"\nTimeline: {len(summary.timeline)} event(s) identified.")
            for ev in summary.timeline[:5]:
                lines.append(f"  • [{ev.date_str}] {ev.description} (via {ev.source})")

        if summary.cross_references:
            lines.append(f"\nCross-References ({len(summary.cross_references)}):")
            for ref in summary.cross_references:
                lines.append(f"  • {ref['description']}")

        if summary.inconsistencies:
            lines.append(f"\n⚠ Inconsistencies ({len(summary.inconsistencies)}):")
            for inc in summary.inconsistencies:
                lines.append(f"  • [{inc.severity.upper()}] {inc.description}")

        if summary.recommendations:
            lines.append(f"\nRecommendations ({len(summary.recommendations)}):")
            for rec in summary.recommendations:
                lines.append(f"  → {rec}")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

def analyze_case(
    vision_results: Optional[List[DocumentVisionResult]] = None,
    pdf_results: Optional[List[PDFAnalysisResult]] = None,
    audio_results: Optional[List[TranscriptionResult]] = None,
    case_id: Optional[str] = None,
) -> CaseSummary:
    """Perform a full multimodal legal case analysis. Convenience function."""
    analyzer = MultimodalLegalAnalyzer(case_id=case_id)
    return analyzer.analyze(
        vision_results=vision_results,
        pdf_results=pdf_results,
        audio_results=audio_results,
    )
