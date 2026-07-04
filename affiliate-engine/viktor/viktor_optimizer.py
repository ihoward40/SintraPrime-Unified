"""
Viktor Optimizer — SintraPrime Affiliate Engine
================================================
Scoring engine for all content produced by Tasklet.
Evaluates each piece across 5 dimensions, returns a
structured score + improvement patches before publish.

Usage:
    from viktor_optimizer import ViktorOptimizer
    optimizer = ViktorOptimizer()
    report = optimizer.evaluate(content_type="tiktok_script", content=raw_text, topic="shopify seo tips")
    print(report.to_markdown())

Or run standalone:
    uv run python viktor_optimizer.py --file content.md --type tiktok_script
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

# ─────────────────────────────────────────────────────────────
# CONFIG — Isiah Howard / IKE Solutions brand context
# Update this section as the brand evolves.
# ─────────────────────────────────────────────────────────────

BRAND_CONFIG = {
    "name": "IKE Solutions",
    "founder": "Isiah Howard",
    "handle": "@isiahh.americannational",
    "niches": [
        "secured party creditor",
        "trust education",
        "consumer law",
        "credit repair",
        "ecommerce / Shopify",
        "AI automation",
        "digital products",
    ],
    "affiliate_primary": "Shopify",
    "affiliate_secondary": ["AI tools", "email platforms", "legal software"],
    "audience": "entrepreneurs, credit-challenged adults, trust/law learners, small business owners",
    "cta_goal": "Shopify affiliate signup or lead magnet download",
    "brand_voice": "direct, educational, empowering, lawful-professional tone",
}

# Keywords that signal strong purchase intent for this brand
HIGH_INTENT_KEYWORDS = [
    "how to start", "best shopify", "shopify free trial", "build an online store",
    "make money online", "passive income", "sell digital products", "ecommerce",
    "ai tools for business", "credit repair", "dispute", "trust", "consumer rights",
    "affiliate marketing", "lead generation", "start a business", "dropshipping",
]

# Brand differentiator signals (words that make this content unique vs generic)
DIFFERENTIATOR_SIGNALS = [
    "secured party", "trust", "consumer law", "dispute", "credit bureau",
    "irrevocable", "IKE Solutions", "lawful", "creditor", "UCC",
    "american national", "consumer advocacy",
]

# Weak CTA patterns (need improvement)
WEAK_CTA_PATTERNS = [
    r"click here", r"learn more", r"check it out", r"follow me", r"like and subscribe",
    r"visit the link", r"link in bio",
]

# Strong CTA patterns (desirable)
STRONG_CTA_PATTERNS = [
    r"start.*free", r"get.*free", r"download.*free", r"grab.*free",
    r"sign up.*today", r"join.*today", r"claim.*now", r"get started",
    r"free trial", r"no cost", r"zero.*cost", r"instantly",
]

# Platform-specific hook benchmarks (seconds to hook)
PLATFORM_HOOKS = {
    "tiktok_script": {"hook_window": 3, "ideal_length_words": (150, 350)},
    "youtube_script": {"hook_window": 30, "ideal_length_words": (800, 2500)},
    "shorts_script": {"hook_window": 3, "ideal_length_words": (80, 200)},
    "instagram_caption": {"hook_window": None, "ideal_length_words": (50, 150)},
    "facebook_post": {"hook_window": None, "ideal_length_words": (50, 300)},
    "x_thread": {"hook_window": None, "ideal_length_words": (20, 80)},
    "pinterest_description": {"hook_window": None, "ideal_length_words": (20, 100)},
    "blog_article": {"hook_window": None, "ideal_length_words": (800, 2500)},
    "email_subject": {"hook_window": None, "ideal_length_words": (5, 12)},
    "email_body": {"hook_window": None, "ideal_length_words": (150, 600)},
    "lead_magnet": {"hook_window": None, "ideal_length_words": (300, 5000)},
}


# ─────────────────────────────────────────────────────────────
# WEIGHTED SCORING FORMULA
# Viktor's rubric — Tasklet receives this as standing instructions
# ─────────────────────────────────────────────────────────────

DIMENSION_WEIGHTS = {
    "hook":         0.25,   # First impression — stops scroll / earns the click
    "cta":          0.25,   # Drives affiliate conversion — highest revenue impact
    "seo":          0.20,   # Long-term organic reach
    "platform_fit": 0.15,   # Format, length, tone match for the channel
    "brand_signal": 0.15,   # Differentiators vs generic content
}

# Minimum publish threshold (0-10 scale)
MIN_PUBLISH_SCORE = 6.5


# ─────────────────────────────────────────────────────────────
# DATA MODELS
# ─────────────────────────────────────────────────────────────

class ContentType(StrEnum):
    TIKTOK_SCRIPT = "tiktok_script"
    YOUTUBE_SCRIPT = "youtube_script"
    SHORTS_SCRIPT = "shorts_script"
    INSTAGRAM_CAPTION = "instagram_caption"
    FACEBOOK_POST = "facebook_post"
    X_THREAD = "x_thread"
    PINTEREST_DESCRIPTION = "pinterest_description"
    BLOG_ARTICLE = "blog_article"
    EMAIL_SUBJECT = "email_subject"
    EMAIL_BODY = "email_body"
    LEAD_MAGNET = "lead_magnet"


@dataclass
class DimensionScore:
    name: str
    raw_score: float        # 0-10
    weight: float
    weighted_score: float
    issues: list[str] = field(default_factory=list)
    patches: list[str] = field(default_factory=list)


@dataclass
class ViktorReport:
    content_type: str
    topic: str
    evaluated_at: str
    word_count: int

    # Scores
    hook_score: DimensionScore
    cta_score: DimensionScore
    seo_score: DimensionScore
    platform_fit_score: DimensionScore
    brand_signal_score: DimensionScore

    overall_score: float            # 0-10 weighted
    publish_gate: str               # APPROVED / HOLD / REJECTED
    priority_fix: str               # Single most important improvement

    # Predictions
    predicted_traffic_tier: str     # LOW / MEDIUM / HIGH / VIRAL
    predicted_ctr_tier: str         # LOW / AVERAGE / STRONG
    predicted_conversion_tier: str  # LOW / AVERAGE / STRONG

    # Improved content
    improved_content: str

    def to_markdown(self) -> str:
        gate_emoji = {"APPROVED": "✅", "HOLD": "⚠️", "REJECTED": "🔴"}.get(self.publish_gate, "❓")
        lines = [
            "# Viktor Optimization Report",
            f"**Topic:** {self.topic}  |  **Type:** {self.content_type}  |  **Words:** {self.word_count}",
            f"**Evaluated:** {self.evaluated_at}",
            "",
            f"## Overall Score: {self.overall_score:.1f}/10 — {gate_emoji} {self.publish_gate}",
            "",
            "## Dimension Breakdown",
            "| Dimension | Raw | Weight | Weighted |",
            "|-----------|-----|--------|----------|",
        ]
        for dim in [self.hook_score, self.cta_score, self.seo_score,
                    self.platform_fit_score, self.brand_signal_score]:
            lines.append(f"| {dim.name} | {dim.raw_score:.1f} | {dim.weight:.0%} | {dim.weighted_score:.2f} |")

        lines += ["", "## Issues & Patches"]
        for dim in [self.hook_score, self.cta_score, self.seo_score,
                    self.platform_fit_score, self.brand_signal_score]:
            if dim.issues:
                lines.append(f"\n### {dim.name}")
                for issue in dim.issues:
                    lines.append(f"- ⚠️ {issue}")
                for patch in dim.patches:
                    lines.append(f"- 🔧 {patch}")

        lines += [
            "",
            "## Priority Fix",
            f"**{self.priority_fix}**",
            "",
            "## Predictions",
            f"- **Traffic Tier:** {self.predicted_traffic_tier}",
            f"- **CTR Tier:** {self.predicted_ctr_tier}",
            f"- **Conversion Tier:** {self.predicted_conversion_tier}",
            "",
            "## Improved Version",
            "```",
            self.improved_content,
            "```",
        ]
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "content_type": self.content_type,
            "topic": self.topic,
            "evaluated_at": self.evaluated_at,
            "word_count": self.word_count,
            "overall_score": round(self.overall_score, 2),
            "publish_gate": self.publish_gate,
            "priority_fix": self.priority_fix,
            "scores": {
                "hook": {"raw": self.hook_score.raw_score, "weighted": self.hook_score.weighted_score},
                "cta": {"raw": self.cta_score.raw_score, "weighted": self.cta_score.weighted_score},
                "seo": {"raw": self.seo_score.raw_score, "weighted": self.seo_score.weighted_score},
                "platform_fit": {"raw": self.platform_fit_score.raw_score, "weighted": self.platform_fit_score.weighted_score},
                "brand_signal": {"raw": self.brand_signal_score.raw_score, "weighted": self.brand_signal_score.weighted_score},
            },
            "predictions": {
                "traffic": self.predicted_traffic_tier,
                "ctr": self.predicted_ctr_tier,
                "conversion": self.predicted_conversion_tier,
            },
        }


# ─────────────────────────────────────────────────────────────
# SCORING ENGINE
# ─────────────────────────────────────────────────────────────

class ViktorOptimizer:
    """Viktor — Growth Hacker. Scores and improves Tasklet content before publish."""

    def evaluate(
        self,
        content: str,
        content_type: str,
        topic: str = "",
        target_keyword: str = "",
    ) -> ViktorReport:
        ct = content_type.lower().replace(" ", "_").replace("-", "_")
        words = content.split()
        word_count = len(words)
        content_lower = content.lower()

        hook = self._score_hook(content, ct, words)
        cta = self._score_cta(content_lower, ct)
        seo = self._score_seo(content_lower, topic, target_keyword)
        platform = self._score_platform_fit(ct, word_count, content_lower)
        brand = self._score_brand_signal(content_lower)

        overall = (
            hook.weighted_score
            + cta.weighted_score
            + seo.weighted_score
            + platform.weighted_score
            + brand.weighted_score
        )

        publish_gate = (
            "APPROVED" if overall >= MIN_PUBLISH_SCORE
            else "HOLD" if overall >= 4.5
            else "REJECTED"
        )

        # Determine single priority fix
        dims = sorted(
            [hook, cta, seo, platform, brand],
            key=lambda d: d.raw_score / (d.weight * 10)  # worst weighted performer first
        )
        priority_fix = dims[0].patches[0] if dims[0].patches else f"Improve {dims[0].name} score ({dims[0].raw_score:.1f}/10)"

        # Predictions
        traffic_tier = self._predict_traffic(seo.raw_score, brand.raw_score, topic)
        ctr_tier = self._predict_ctr(hook.raw_score, platform.raw_score)
        conversion_tier = self._predict_conversion(cta.raw_score, brand.raw_score)

        improved = self._generate_improved(content, hook, cta, seo, platform, brand, ct, topic)

        return ViktorReport(
            content_type=ct,
            topic=topic or "(unspecified)",
            evaluated_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M"),
            word_count=word_count,
            hook_score=hook,
            cta_score=cta,
            seo_score=seo,
            platform_fit_score=platform,
            brand_signal_score=brand,
            overall_score=round(overall, 2),
            publish_gate=publish_gate,
            priority_fix=priority_fix,
            predicted_traffic_tier=traffic_tier,
            predicted_ctr_tier=ctr_tier,
            predicted_conversion_tier=conversion_tier,
            improved_content=improved,
        )

    # ── Hook Scoring ──────────────────────────────────────────
    def _score_hook(self, content: str, ct: str, words: list[str]) -> DimensionScore:
        score = 10.0
        issues, patches = [], []
        config = PLATFORM_HOOKS.get(ct, {})
        hook_window = config.get("hook_window")
        content_lower = content.lower()

        # For video content: score the first 3 seconds (approx first 20 words)
        if hook_window:
            opening = " ".join(words[:20]).lower()

            # Check for question hook
            has_question = "?" in opening
            # Check for number hook
            has_number = bool(re.search(r'\b\d+\b', opening))
            # Check for bold claim
            has_bold_claim = any(w in opening for w in [
                "never", "always", "secret", "mistake", "truth", "nobody tells",
                "stop", "don't", "warning", "exposed", "real reason",
                "i made", "i earned", "i lost", "changed my",
            ])
            # Check for pattern interrupt
            has_pattern_interrupt = any(w in opening for w in [
                "wait", "before you", "listen", "real talk", "hear me out",
                "most people", "everybody thinks", "hot take",
            ])

            hook_signals = sum([has_question, has_number, has_bold_claim, has_pattern_interrupt])

            if hook_signals == 0:
                score -= 3.0
                issues.append("Opening 20 words have no scroll-stopper signal (question, number, bold claim, or pattern interrupt)")
                patches.append("Open with a question or bold stat: 'Did you know 90% of Shopify stores fail in year one — here's the one thing survivors do differently.'")
            elif hook_signals == 1:
                score -= 1.0
                patches.append("Strengthen hook by adding a number or tension element to the opening line")

            # Penalize weak openers
            weak_openers = ["in this video", "today i want to", "hey guys", "hello everyone", "welcome back"]
            if any(opener in content_lower[:100] for opener in weak_openers):
                score -= 2.0
                issues.append("Weak opener detected (generic greeting or 'in this video...')")
                patches.append("Delete the intro greeting. Start with the hook immediately. First word should create curiosity or tension.")

        else:
            # Non-video: score first sentence
            first_sentence = content.split(".")[0] if "." in content else content[:100]
            if len(first_sentence.split()) < 5:
                score -= 2.0
                issues.append("First sentence too short to create engagement")
                patches.append("Expand first sentence into a complete hook — state the problem or outcome upfront")

        score = max(0.0, min(10.0, score))
        return DimensionScore(
            name="Hook",
            raw_score=score,
            weight=DIMENSION_WEIGHTS["hook"],
            weighted_score=round(score * DIMENSION_WEIGHTS["hook"], 3),
            issues=issues,
            patches=patches,
        )

    # ── CTA Scoring ───────────────────────────────────────────
    def _score_cta(self, content_lower: str, ct: str) -> DimensionScore:
        score = 10.0
        issues, patches = [], []

        # Check for any CTA at all
        has_any_cta = any(
            re.search(p, content_lower) for p in STRONG_CTA_PATTERNS + WEAK_CTA_PATTERNS
        )
        if not has_any_cta:
            score -= 4.0
            issues.append("No call-to-action found")
            patches.append("Add CTA near the end: 'Start your free Shopify trial at the link in my bio — no credit card needed, cancel anytime.'")

        # Check CTA quality
        has_strong = any(re.search(p, content_lower) for p in STRONG_CTA_PATTERNS)
        has_weak = any(re.search(p, content_lower) for p in WEAK_CTA_PATTERNS)

        if has_weak and not has_strong:
            score -= 2.5
            issues.append("CTA present but weak — 'link in bio' or 'click here' without benefit framing")
            patches.append("Replace weak CTA with benefit-driven version: 'Grab the free Shopify Launch Checklist — link in bio. It's the same system I'd use to build from zero.'")

        # Check CTA placement
        content_thirds = len(content_lower) // 3
        last_third = content_lower[2 * content_thirds:]
        if has_any_cta and not any(re.search(p, last_third) for p in STRONG_CTA_PATTERNS + WEAK_CTA_PATTERNS):
            score -= 1.5
            issues.append("CTA appears early but not in final third — readers who finish don't get a conversion opportunity")
            patches.append("Add a second CTA in the final paragraph/closing. Reinforce the offer after delivering value.")

        # Check for urgency / specificity
        has_urgency = any(w in content_lower for w in ["now", "today", "limited", "only", "expires", "free trial"])
        if not has_urgency and has_any_cta:
            score -= 1.0
            patches.append("Add urgency or specificity to CTA: 'Start your free 3-day trial today' outperforms 'click to learn more'")

        score = max(0.0, min(10.0, score))
        return DimensionScore(
            name="CTA",
            raw_score=score,
            weight=DIMENSION_WEIGHTS["cta"],
            weighted_score=round(score * DIMENSION_WEIGHTS["cta"], 3),
            issues=issues,
            patches=patches,
        )

    # ── SEO Scoring ───────────────────────────────────────────
    def _score_seo(self, content_lower: str, topic: str, target_keyword: str) -> DimensionScore:
        score = 10.0
        issues, patches = [], []

        # Keyword presence
        kw = (target_keyword or topic or "").lower()
        if kw:
            kw_count = content_lower.count(kw)
            word_count = len(content_lower.split())
            if kw_count == 0:
                score -= 3.0
                issues.append(f"Target keyword '{kw}' not found in content")
                patches.append(f"Include '{kw}' naturally in the first 100 words, at least once in the middle, and near the end")
            elif word_count > 200 and kw_count < 2:
                score -= 1.5
                issues.append(f"Target keyword '{kw}' appears only once in a long piece — insufficient density")
                patches.append(f"Add 1-2 more natural mentions of '{kw}' for long-form content")

        # High-intent keyword presence
        intent_hits = sum(1 for kw in HIGH_INTENT_KEYWORDS if kw in content_lower)
        if intent_hits == 0:
            score -= 2.0
            issues.append("No high-purchase-intent keywords detected")
            patches.append(f"Weave in intent signals: {', '.join(HIGH_INTENT_KEYWORDS[:4])}")
        elif intent_hits < 2:
            score -= 1.0
            patches.append("Add 1-2 more purchase-intent keywords for stronger organic signal")

        # Title/headline for blog/email (first line should contain keyword)
        if content_lower.startswith("#") or "\n" in content_lower[:50]:
            first_line = content_lower.split("\n")[0].strip("#").strip()
            if kw and kw not in first_line:
                score -= 1.5
                issues.append("Target keyword missing from headline/title")
                patches.append(f"Start title with or include '{kw}' — e.g., '{kw.title()}: [Benefit Statement]'")

        score = max(0.0, min(10.0, score))
        return DimensionScore(
            name="SEO",
            raw_score=score,
            weight=DIMENSION_WEIGHTS["seo"],
            weighted_score=round(score * DIMENSION_WEIGHTS["seo"], 3),
            issues=issues,
            patches=patches,
        )

    # ── Platform Fit Scoring ──────────────────────────────────
    def _score_platform_fit(self, ct: str, word_count: int, content_lower: str) -> DimensionScore:
        score = 10.0
        issues, patches = [], []
        config = PLATFORM_HOOKS.get(ct, {})
        ideal_min, ideal_max = config.get("ideal_length_words", (0, 99999))

        if word_count < ideal_min:
            deficit = ideal_min - word_count
            score -= min(4.0, deficit / ideal_min * 8)
            issues.append(f"Content too short for {ct}: {word_count} words (ideal: {ideal_min}-{ideal_max})")
            patches.append(f"Expand by ~{deficit} words — add more specific steps, examples, or social proof")

        elif word_count > ideal_max:
            excess = word_count - ideal_max
            score -= min(3.0, excess / ideal_max * 6)
            issues.append(f"Content too long for {ct}: {word_count} words (ideal: {ideal_min}-{ideal_max})")
            patches.append(f"Trim ~{excess} words — cut filler phrases, consolidate repetitive points")

        # Platform-specific checks
        if ct in ["tiktok_script", "shorts_script", "youtube_script"]:
            if "action" not in content_lower and "show" not in content_lower and "screen" not in content_lower:
                score -= 1.0
                patches.append("Add visual direction cues: describe what appears on screen or what action is performed")

        if ct in ["instagram_caption", "facebook_post", "x_thread"]:
            if "\n" not in content_lower and word_count > 50:
                score -= 1.5
                issues.append("No line breaks in social copy — hard to read on mobile")
                patches.append("Add line breaks every 1-2 sentences for mobile readability. White space = engagement.")

        if ct == "email_subject":
            if word_count > 12:
                score -= 2.0
                issues.append("Email subject too long — will be cut off on mobile (>50 chars)")
                patches.append("Trim to 6-10 words. Front-load the benefit or curiosity element.")
            if content_lower.startswith("re:") or content_lower.startswith("fwd:"):
                score -= 1.0

        score = max(0.0, min(10.0, score))
        return DimensionScore(
            name="Platform Fit",
            raw_score=score,
            weight=DIMENSION_WEIGHTS["platform_fit"],
            weighted_score=round(score * DIMENSION_WEIGHTS["platform_fit"], 3),
            issues=issues,
            patches=patches,
        )

    # ── Brand Signal Scoring ──────────────────────────────────
    def _score_brand_signal(self, content_lower: str) -> DimensionScore:
        score = 10.0
        issues, patches = [], []

        # Check for brand differentiators
        diff_hits = sum(1 for sig in DIFFERENTIATOR_SIGNALS if sig in content_lower)
        if diff_hits == 0:
            score -= 4.0
            issues.append("Zero brand differentiators — content is generic and indistinguishable from competitors")
            patches.append(
                "Add at least one brand anchor: reference trust law, consumer rights, credit disputes, or secured-party creditor perspective. "
                "Example: 'I built my Shopify store while disputing $74K with the IRS and rebuilding my credit. Here's what actually works.'"
            )
        elif diff_hits == 1:
            score -= 1.5
            patches.append("Strengthen brand voice — add a second differentiator signal (trust, consumer law, or personal proof story)")

        # Check for personal authority / social proof
        authority_signals = ["i", "my", "we", "our", "when i", "i built", "i made", "i learned"]
        has_authority = any(sig in content_lower for sig in authority_signals)
        if not has_authority:
            score -= 2.0
            issues.append("No first-person authority signal — reads like generic copywriting, not a trusted voice")
            patches.append("Add a first-person proof point: 'I personally used this to...' or 'My clients at IKE Solutions...'")

        # Check for generic filler that dilutes brand
        generic_phrases = ["game changer", "revolutionary", "amazing", "incredible", "best ever", "life changing"]
        generic_hits = sum(1 for p in generic_phrases if p in content_lower)
        if generic_hits >= 2:
            score -= 1.5
            issues.append(f"Overuse of generic hype phrases ({generic_hits} found) — weakens credibility")
            patches.append("Replace hype words with specific facts: instead of 'amazing results', say 'increased conversion by X%' or 'paid off $X in 90 days'")

        score = max(0.0, min(10.0, score))
        return DimensionScore(
            name="Brand Signal",
            raw_score=score,
            weight=DIMENSION_WEIGHTS["brand_signal"],
            weighted_score=round(score * DIMENSION_WEIGHTS["brand_signal"], 3),
            issues=issues,
            patches=patches,
        )

    # ── Predictions ───────────────────────────────────────────
    def _predict_traffic(self, seo_score: float, brand_score: float, topic: str) -> str:
        combined = (seo_score * 0.6 + brand_score * 0.4)
        topic_lower = topic.lower()
        # Boost for high-volume topics
        if any(kw in topic_lower for kw in ["shopify", "ai tools", "make money", "passive income"]):
            combined += 1.0
        if combined >= 8: return "HIGH"
        if combined >= 6: return "MEDIUM"
        if combined >= 4: return "LOW"
        return "MINIMAL"

    def _predict_ctr(self, hook_score: float, platform_score: float) -> str:
        combined = (hook_score * 0.7 + platform_score * 0.3)
        if combined >= 8: return "STRONG (>5%)"
        if combined >= 6: return "AVERAGE (2-5%)"
        return "LOW (<2%)"

    def _predict_conversion(self, cta_score: float, brand_score: float) -> str:
        combined = (cta_score * 0.6 + brand_score * 0.4)
        if combined >= 8: return "STRONG (>3%)"
        if combined >= 6: return "AVERAGE (1-3%)"
        return "LOW (<1%)"

    # ── Improvement Generator ─────────────────────────────────
    def _generate_improved(
        self,
        content: str,
        hook: DimensionScore,
        cta: DimensionScore,
        seo: DimensionScore,
        platform: DimensionScore,
        brand: DimensionScore,
        ct: str,
        topic: str,
    ) -> str:
        """
        Generates inline improvement notes embedded in the content.
        For full AI rewrite, pass content to your LLM with the patches as instructions.
        """

        # Add improvement header with patches as inline comments
        all_patches = hook.patches + cta.patches + seo.patches + platform.patches + brand.patches
        if not all_patches:
            return content + "\n\n<!-- Viktor: No changes needed. Approved as-is. -->"

        patch_block = "\n".join(f"<!-- PATCH {i+1}: {p} -->" for i, p in enumerate(all_patches))
        return f"{content}\n\n{patch_block}\n\n<!-- Viktor: Apply patches above before publishing. -->"


# ─────────────────────────────────────────────────────────────
# WEEKLY REPORT GENERATOR
# ─────────────────────────────────────────────────────────────

class WeeklyViktorReport:
    """Aggregate multiple ViktorReports into a weekly summary for Hermes feedback loop."""

    def __init__(self, reports: list[ViktorReport]):
        self.reports = reports

    def summary(self) -> dict:
        if not self.reports:
            return {}

        approved = [r for r in self.reports if r.publish_gate == "APPROVED"]
        held = [r for r in self.reports if r.publish_gate == "HOLD"]
        rejected = [r for r in self.reports if r.publish_gate == "REJECTED"]

        avg_score = sum(r.overall_score for r in self.reports) / len(self.reports)

        # Most common issues
        all_issues = []
        for r in self.reports:
            for dim in [r.hook_score, r.cta_score, r.seo_score, r.platform_fit_score, r.brand_signal_score]:
                all_issues.extend(dim.issues)

        from collections import Counter
        top_issues = Counter(all_issues).most_common(3)

        # Hermes learning directives
        hermes_directives = []
        if avg_score < 6.5:
            hermes_directives.append("Overall quality below threshold — Tasklet needs tighter briefs with explicit keyword, hook, and CTA requirements")
        if len(rejected) > len(approved):
            hermes_directives.append("More rejections than approvals — reduce research breadth, focus on 3-5 high-intent topics only")
        if any("brand" in issue.lower() for issue in all_issues):
            hermes_directives.append("Brand signal weak across content — include IKE Solutions differentiators in every Tasklet brief")
        if any("cta" in issue.lower() for issue in all_issues):
            hermes_directives.append("CTA failures recurring — mandate explicit CTA template in every Tasklet output")

        return {
            "week_ending": datetime.now(UTC).strftime("%Y-%m-%d"),
            "total_pieces": len(self.reports),
            "approved": len(approved),
            "held": len(held),
            "rejected": len(rejected),
            "approval_rate": f"{len(approved)/len(self.reports)*100:.0f}%",
            "avg_score": round(avg_score, 2),
            "top_issues": [issue for issue, _ in top_issues],
            "hermes_directives_for_next_week": hermes_directives,
        }

    def to_markdown(self) -> str:
        s = self.summary()
        lines = [
            "# Viktor Weekly Summary",
            f"**Week Ending:** {s.get('week_ending')}",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Total Pieces | {s.get('total_pieces')} |",
            f"| Approved | {s.get('approved')} ✅ |",
            f"| Hold | {s.get('held')} ⚠️ |",
            f"| Rejected | {s.get('rejected')} 🔴 |",
            f"| Approval Rate | {s.get('approval_rate')} |",
            f"| Avg Score | {s.get('avg_score')}/10 |",
            "",
            "## Top Recurring Issues",
        ]
        for issue in s.get("top_issues", []):
            lines.append(f"- {issue}")

        lines += ["", "## Hermes Directives for Next Cycle"]
        for directive in s.get("hermes_directives_for_next_week", []):
            lines.append(f"- 🔁 {directive}")

        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# CLI ENTRYPOINT
# ─────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Viktor Optimizer — SintraPrime Affiliate Engine")
    parser.add_argument("--file", help="Path to content file (.md or .txt)")
    parser.add_argument("--content", help="Content text directly (use quotes)")
    parser.add_argument("--type", required=True, help="Content type: tiktok_script, blog_article, email_body, etc.")
    parser.add_argument("--topic", default="", help="Topic/title of the content")
    parser.add_argument("--keyword", default="", help="Primary target keyword")
    parser.add_argument("--output", choices=["markdown", "json"], default="markdown")
    args = parser.parse_args()

    if args.file:
        content = Path(args.file).read_text()
    elif args.content:
        content = args.content
    else:
        print("Error: provide --file or --content")
        sys.exit(1)

    optimizer = ViktorOptimizer()
    report = optimizer.evaluate(
        content=content,
        content_type=args.type,
        topic=args.topic,
        target_keyword=args.keyword,
    )

    if args.output == "json":
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(report.to_markdown())


if __name__ == "__main__":
    main()
