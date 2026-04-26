"""
WebResearcher – Manus-style deep research agent for SintraPrime Operator Mode.

Performs multi-source research, competitive analysis, market research,
fact-checking, and source aggregation with full citation tracking.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .browser_controller import BrowserController, SearchResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes for research outputs
# ---------------------------------------------------------------------------


@dataclass
class Citation:
    """A source citation."""
    url: str
    title: str
    accessed_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%d"))
    relevant_quote: str = ""


@dataclass
class ResearchReport:
    """Structured output of a research task."""
    topic: str
    summary: str
    key_findings: List[str]
    citations: List[Citation]
    sections: Dict[str, str] = field(default_factory=dict)
    raw_data: List[Dict[str, Any]] = field(default_factory=list)
    confidence_score: float = 0.0  # 0.0 – 1.0
    depth_achieved: int = 0

    def to_markdown(self) -> str:
        lines = [f"# Research Report: {self.topic}", ""]
        lines.append(f"**Confidence:** {self.confidence_score:.0%} | **Depth:** {self.depth_achieved}")
        lines.append("")
        lines.append("## Summary")
        lines.append(self.summary)
        lines.append("")
        if self.key_findings:
            lines.append("## Key Findings")
            for i, finding in enumerate(self.key_findings, 1):
                lines.append(f"{i}. {finding}")
            lines.append("")
        for section_name, section_content in self.sections.items():
            lines.append(f"## {section_name}")
            lines.append(section_content)
            lines.append("")
        if self.citations:
            lines.append("## Sources")
            for i, cit in enumerate(self.citations, 1):
                lines.append(f"{i}. [{cit.title}]({cit.url}) – accessed {cit.accessed_at}")
        return "\n".join(lines)

    def to_json(self) -> str:
        return json.dumps({
            "topic": self.topic,
            "summary": self.summary,
            "key_findings": self.key_findings,
            "citations": [
                {"url": c.url, "title": c.title, "accessed_at": c.accessed_at,
                 "relevant_quote": c.relevant_quote}
                for c in self.citations
            ],
            "sections": self.sections,
            "confidence_score": self.confidence_score,
            "depth_achieved": self.depth_achieved,
        }, indent=2)


@dataclass
class CompetitorProfile:
    name: str
    website: str
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    pricing: str = ""
    market_position: str = ""
    notes: str = ""


@dataclass
class CompetitiveMatrix:
    subject: str
    competitors: List[CompetitorProfile]
    summary: str = ""

    def to_markdown(self) -> str:
        lines = [f"# Competitive Analysis: {self.subject}", "", self.summary, ""]
        lines.append("| Company | Website | Strengths | Weaknesses | Pricing |")
        lines.append("|---------|---------|-----------|------------|---------|")
        for c in self.competitors:
            strengths = "; ".join(c.strengths[:2])
            weaknesses = "; ".join(c.weaknesses[:2])
            lines.append(f"| {c.name} | {c.website} | {strengths} | {weaknesses} | {c.pricing} |")
        return "\n".join(lines)


@dataclass
class MarketReport:
    industry: str
    questions: List[str]
    answers: Dict[str, str] = field(default_factory=dict)
    market_size: str = ""
    growth_rate: str = ""
    key_players: List[str] = field(default_factory=list)
    trends: List[str] = field(default_factory=list)
    citations: List[Citation] = field(default_factory=list)

    def to_markdown(self) -> str:
        lines = [f"# Market Research: {self.industry}", ""]
        if self.market_size:
            lines.append(f"**Market Size:** {self.market_size}")
        if self.growth_rate:
            lines.append(f"**Growth Rate:** {self.growth_rate}")
        lines.append("")
        if self.key_players:
            lines.append("## Key Players")
            for p in self.key_players:
                lines.append(f"- {p}")
            lines.append("")
        if self.trends:
            lines.append("## Market Trends")
            for t in self.trends:
                lines.append(f"- {t}")
            lines.append("")
        if self.answers:
            lines.append("## Research Questions & Answers")
            for q, a in self.answers.items():
                lines.append(f"**Q:** {q}")
                lines.append(f"**A:** {a}")
                lines.append("")
        return "\n".join(lines)


@dataclass
class FactCheckResult:
    claim: str
    verdict: str  # "TRUE", "FALSE", "UNVERIFIED", "MIXED"
    confidence: float  # 0.0 – 1.0
    evidence: List[str] = field(default_factory=list)
    sources: List[Citation] = field(default_factory=list)
    explanation: str = ""


@dataclass
class SynthesizedReport:
    urls: List[str]
    synthesis: str
    common_themes: List[str] = field(default_factory=list)
    contradictions: List[str] = field(default_factory=list)
    citations: List[Citation] = field(default_factory=list)


# ---------------------------------------------------------------------------
# WebResearcher
# ---------------------------------------------------------------------------


class WebResearcher:
    """
    Deep research agent inspired by Manus AI.

    Coordinates BrowserController to open multiple sources, extract
    information, cross-reference, deduplicate, and produce structured reports.

    Example:
        researcher = WebResearcher()
        report = researcher.research("top trust attorneys in California", depth=3)
        print(report.to_markdown())
    """

    MIN_SOURCES_FOR_FACT_CHECK = 3

    def __init__(self, browser: Optional[BrowserController] = None):
        self.browser = browser or BrowserController()
        self._owns_browser = browser is None

    def close(self):
        if self._owns_browser:
            self.browser.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # ------------------------------------------------------------------
    # Core Research
    # ------------------------------------------------------------------

    def research(self, topic: str, depth: int = 3) -> ResearchReport:
        """
        Conduct deep research on a topic by browsing multiple sources.

        Args:
            topic: Research topic or question.
            depth: How many levels of sources to traverse (1-5).

        Returns:
            ResearchReport with findings, citations, and structured sections.
        """
        depth = max(1, min(depth, 5))
        logger.info(f"Researching: '{topic}' (depth={depth})")

        # Phase 1: Search
        search_result = self.browser.search_web(topic, max_results=10 * depth)
        search_hits: List[SearchResult] = search_result.data or []

        # Phase 2: Browse sources
        raw_data: List[Dict[str, Any]] = []
        citations: List[Citation] = []
        urls_visited: set = set()

        for hit in search_hits[:5 * depth]:
            if hit.url in urls_visited or not hit.url.startswith("http"):
                continue
            urls_visited.add(hit.url)

            nav = self.browser.navigate(hit.url)
            if not nav:
                continue

            content_result = self.browser.extract_text("body")
            text = content_result.data if content_result else hit.snippet

            raw_data.append({"url": hit.url, "title": hit.title, "text": text or ""})
            citations.append(Citation(url=hit.url, title=hit.title,
                                      relevant_quote=(text or "")[:200]))

            if len(raw_data) >= 5 * depth:
                break

        # Phase 3: Synthesize
        key_findings = self._extract_key_findings(topic, raw_data)
        sections = self._build_sections(topic, raw_data)
        summary = self._build_summary(topic, key_findings)
        confidence = min(len(citations) / (5.0 * depth), 1.0)

        return ResearchReport(
            topic=topic,
            summary=summary,
            key_findings=key_findings,
            citations=citations,
            sections=sections,
            raw_data=raw_data,
            confidence_score=round(confidence, 2),
            depth_achieved=depth,
        )

    # ------------------------------------------------------------------
    # Competitive Analysis
    # ------------------------------------------------------------------

    def competitive_analysis(
        self, subject: str, competitors: List[str]
    ) -> CompetitiveMatrix:
        """
        Research a subject against a list of competitors.

        Args:
            subject: The entity/product/company to analyze.
            competitors: List of competitor names.

        Returns:
            CompetitiveMatrix with profiles for each competitor.
        """
        profiles: List[CompetitorProfile] = []

        for competitor in competitors:
            query = f"{competitor} review strengths weaknesses pricing"
            search = self.browser.search_web(query, max_results=3)
            hits = search.data or []

            strengths: List[str] = []
            weaknesses: List[str] = []
            pricing = ""
            website = ""

            if hits:
                website = hits[0].url
                text = hits[0].snippet.lower()
                # Naive extraction heuristics
                if "strong" in text or "best" in text or "leader" in text:
                    strengths.append("Market leader / strong brand")
                if "expensive" in text or "costly" in text or "pric" in text:
                    weaknesses.append("Higher price point")
                    pricing = "Premium"
                if "free" in text or "affordable" in text:
                    pricing = "Affordable / freemium"
                if "slow" in text or "limit" in text:
                    weaknesses.append("Feature limitations noted")

            profiles.append(CompetitorProfile(
                name=competitor,
                website=website,
                strengths=strengths or ["Data not available"],
                weaknesses=weaknesses or ["Data not available"],
                pricing=pricing or "Unknown",
            ))

        summary = (
            f"Competitive analysis of {subject} against {len(competitors)} competitors. "
            f"Analyzed: {', '.join(competitors)}."
        )
        return CompetitiveMatrix(subject=subject, competitors=profiles, summary=summary)

    # ------------------------------------------------------------------
    # Market Research
    # ------------------------------------------------------------------

    def market_research(
        self, industry: str, questions: List[str]
    ) -> MarketReport:
        """
        Conduct market research for an industry, answering specific questions.

        Args:
            industry: Industry or market segment.
            questions: List of research questions.

        Returns:
            MarketReport with answers, market data, and citations.
        """
        citations: List[Citation] = []
        answers: Dict[str, str] = {}

        # Overall market search
        market_query = f"{industry} market size growth trends 2024"
        search = self.browser.search_web(market_query, max_results=5)
        hits = search.data or []

        market_size = ""
        growth_rate = ""
        key_players: List[str] = []
        trends: List[str] = []

        for hit in hits[:3]:
            if hit.url.startswith("http"):
                citations.append(Citation(url=hit.url, title=hit.title,
                                          relevant_quote=hit.snippet[:200]))
            snippet_lower = hit.snippet.lower()
            if "$" in hit.snippet and not market_size:
                # Extract first dollar figure as market size proxy
                import re
                match = re.search(r"\$[\d,.]+\s*(billion|million|trillion)?", hit.snippet, re.I)
                if match:
                    market_size = match.group(0)
            if "%" in hit.snippet and not growth_rate:
                match = re.search(r"[\d.]+%", hit.snippet)
                if match:
                    growth_rate = match.group(0) + " CAGR"

        # Answer each question
        for question in questions:
            q_search = self.browser.search_web(f"{industry} {question}", max_results=3)
            q_hits = q_search.data or []
            if q_hits:
                answers[question] = q_hits[0].snippet or "No data available."
                if q_hits[0].url.startswith("http"):
                    citations.append(Citation(url=q_hits[0].url, title=q_hits[0].title))
            else:
                answers[question] = "No data available."

        return MarketReport(
            industry=industry,
            questions=questions,
            answers=answers,
            market_size=market_size,
            growth_rate=growth_rate,
            key_players=key_players,
            trends=trends,
            citations=citations,
        )

    # ------------------------------------------------------------------
    # Fact Checking
    # ------------------------------------------------------------------

    def fact_check(self, claim: str) -> FactCheckResult:
        """
        Verify a claim against 3+ independent sources.

        Args:
            claim: The statement to verify.

        Returns:
            FactCheckResult with verdict (TRUE/FALSE/MIXED/UNVERIFIED).
        """
        search = self.browser.search_web(
            f'fact check "{claim}"', max_results=self.MIN_SOURCES_FOR_FACT_CHECK * 2
        )
        hits = search.data or []

        evidence: List[str] = []
        sources: List[Citation] = []
        supports = 0
        contradicts = 0

        for hit in hits[:self.MIN_SOURCES_FOR_FACT_CHECK * 2]:
            snippet_lower = hit.snippet.lower()
            evidence.append(hit.snippet)
            if hit.url.startswith("http"):
                sources.append(Citation(url=hit.url, title=hit.title,
                                        relevant_quote=hit.snippet[:200]))

            # Naive sentiment scoring
            if any(w in snippet_lower for w in ["true", "correct", "confirmed", "accurate", "yes"]):
                supports += 1
            if any(w in snippet_lower for w in ["false", "wrong", "incorrect", "debunked", "myth", "no"]):
                contradicts += 1

        total = supports + contradicts or 1
        confidence = max(supports, contradicts) / (total + len(evidence) * 0.1)
        confidence = min(confidence, 1.0)

        if supports > contradicts and supports >= self.MIN_SOURCES_FOR_FACT_CHECK:
            verdict = "TRUE"
        elif contradicts > supports and contradicts >= self.MIN_SOURCES_FOR_FACT_CHECK:
            verdict = "FALSE"
        elif supports > 0 and contradicts > 0:
            verdict = "MIXED"
        else:
            verdict = "UNVERIFIED"

        explanation = (
            f"Found {len(sources)} sources. {supports} support the claim, "
            f"{contradicts} contradict it."
        )

        return FactCheckResult(
            claim=claim,
            verdict=verdict,
            confidence=round(confidence, 2),
            evidence=evidence[:5],
            sources=sources,
            explanation=explanation,
        )

    # ------------------------------------------------------------------
    # Source Aggregation
    # ------------------------------------------------------------------

    def aggregate_sources(self, urls: List[str]) -> SynthesizedReport:
        """
        Read multiple URLs, synthesize common themes, and note contradictions.

        Args:
            urls: List of URLs to read and aggregate.

        Returns:
            SynthesizedReport with synthesis, themes, and contradictions.
        """
        texts: List[Tuple[str, str, str]] = []  # (url, title, text)
        citations: List[Citation] = []

        for url in urls:
            nav = self.browser.navigate(url)
            if not nav:
                continue
            title = nav.data.get("title", url) if isinstance(nav.data, dict) else url
            content = self.browser.extract_text("body")
            text = (content.data or "")[:3000]
            texts.append((url, title, text))
            citations.append(Citation(url=url, title=title, relevant_quote=text[:200]))

        # Find common themes (naive word frequency)
        all_words: Dict[str, int] = {}
        for _, _, text in texts:
            for word in text.lower().split():
                if len(word) > 5:
                    all_words[word] = all_words.get(word, 0) + 1

        sorted_words = sorted(all_words.items(), key=lambda x: x[1], reverse=True)
        common_themes = [w for w, _ in sorted_words[:10]]

        synthesis = (
            f"Aggregated {len(texts)} sources covering: "
            + ", ".join(common_themes[:5])
            + ". See citations for full details."
        )

        return SynthesizedReport(
            urls=urls,
            synthesis=synthesis,
            common_themes=common_themes,
            contradictions=[],  # Advanced contradiction detection requires LLM
            citations=citations,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _extract_key_findings(
        self, topic: str, raw_data: List[Dict[str, Any]]
    ) -> List[str]:
        """Extract key findings from raw research data (heuristic)."""
        findings: List[str] = []
        topic_words = set(topic.lower().split())

        for item in raw_data[:10]:
            text = item.get("text", "")
            sentences = [s.strip() for s in text.replace("\n", ". ").split(". ") if len(s.strip()) > 30]
            for sentence in sentences[:3]:
                sentence_lower = sentence.lower()
                if any(w in sentence_lower for w in topic_words):
                    findings.append(sentence)
                if len(findings) >= 10:
                    break
            if len(findings) >= 10:
                break

        return findings[:10] if findings else [f"Research on '{topic}' completed. See sources for details."]

    def _build_sections(
        self, topic: str, raw_data: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """Build report sections from raw data."""
        if not raw_data:
            return {}
        sections: Dict[str, str] = {}
        sections["Overview"] = (
            f"This research covers {topic} based on {len(raw_data)} sources. "
            "The following sections summarize key information found."
        )
        if len(raw_data) >= 3:
            sections["Detailed Findings"] = "\n\n".join(
                f"**Source {i+1}: {item['title']}**\n{(item['text'] or '')[:500]}..."
                for i, item in enumerate(raw_data[:3])
            )
        return sections

    def _build_summary(self, topic: str, key_findings: List[str]) -> str:
        """Build a 2-3 sentence summary from key findings."""
        if not key_findings:
            return f"Research on '{topic}' was conducted across multiple sources."
        summary_parts = key_findings[:3]
        return " ".join(summary_parts)
