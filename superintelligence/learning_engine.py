"""
learning_engine.py — Adaptive learning engine for SintraPrime.

SintraPrime gets smarter from every interaction.
"""

from __future__ import annotations

import json
import os
import re
import time
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

LESSONS_PATH = Path(os.environ.get("SINTRA_DATA_DIR", str(Path.home() / ".sintra")) + "/lessons.json")


def _now_ts() -> float:
    return time.time()


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z0-9]+", text.lower())


def _similarity(a: str, b: str) -> float:
    """Simple Jaccard similarity between two strings."""
    ta = set(_tokenize(a))
    tb = set(_tokenize(b))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


# ---------------------------------------------------------------------------
# Lesson dataclass
# ---------------------------------------------------------------------------

@dataclass
class Lesson:
    lesson_id: str
    timestamp: float
    trigger_event: str
    insight: str
    confidence: float
    domain: str
    applied_count: int = 0
    reinforcement_count: int = 0
    deprecation_count: int = 0
    generalized_from: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict) -> "Lesson":
        return cls(**d)

    def __repr__(self) -> str:
        return (f"Lesson(id={self.lesson_id[:8]}, domain={self.domain!r}, "
                f"confidence={self.confidence:.2f}, applied={self.applied_count})")


# ---------------------------------------------------------------------------
# LearningEngine
# ---------------------------------------------------------------------------

class LearningEngine:
    """Extracts and applies lessons from interactions."""

    def __init__(self, path: Path = LESSONS_PATH):
        self.path = path
        self._lessons: Dict[str, Lesson] = {}
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                with open(self.path, "r") as f:
                    data = json.load(f)
                for lid, ldata in data.items():
                    self._lessons[lid] = Lesson.from_dict(ldata)
            except Exception:
                self._lessons = {}

    def _save(self):
        data = {lid: l.to_dict() for lid, l in self._lessons.items()}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w") as f:
            json.dump(data, f, indent=2)

    def _detect_domain(self, action: str, context: str) -> str:
        """Heuristically detect domain from action/context."""
        text = (action + " " + context).lower()
        domain_keywords = {
            "math": ["calculate", "number", "equation", "formula", "sum", "math"],
            "coding": ["code", "function", "bug", "program", "script", "error", "python", "api"],
            "reasoning": ["logic", "argue", "conclude", "reason", "infer", "deduce"],
            "writing": ["write", "draft", "essay", "article", "text", "document"],
            "research": ["research", "search", "find", "investigate", "study", "analyze"],
            "planning": ["plan", "schedule", "organize", "task", "project", "goal"],
        }
        scores: Dict[str, int] = defaultdict(int)
        for domain, keywords in domain_keywords.items():
            for kw in keywords:
                if kw in text:
                    scores[domain] += 1
        if scores:
            return max(scores, key=lambda d: scores[d])
        return "general"

    def _extract_insight(self, action: str, outcome: str) -> str:
        """Extract a generalizable lesson from action + outcome."""
        outcome_lower = outcome.lower()
        success_words = {"success", "completed", "solved", "correct", "done", "good", "great", "improved"}
        failure_words = {"fail", "error", "wrong", "incorrect", "bad", "broken", "mistake"}

        is_success = any(w in outcome_lower for w in success_words)
        is_failure = any(w in outcome_lower for w in failure_words)

        # Trim action to key part
        action_short = action[:100].strip()

        if is_success:
            return f"When performing '{action_short}', the approach led to success: {outcome[:80]}"
        elif is_failure:
            return f"When performing '{action_short}', this approach failed: {outcome[:80]}. Avoid or adjust."
        else:
            return f"Observation from '{action_short}': {outcome[:80]}"

    def learn_from_outcome(self, action: str, outcome: str,
                            context: str = "") -> Lesson:
        """Extract lessons from what worked/failed."""
        insight = self._extract_insight(action, outcome)
        domain = self._detect_domain(action, context)
        outcome_lower = outcome.lower()
        success_words = {"success", "completed", "solved", "correct", "good"}
        confidence = 0.65 if any(w in outcome_lower for w in success_words) else 0.45

        lesson = Lesson(
            lesson_id=str(uuid.uuid4()),
            timestamp=_now_ts(),
            trigger_event=action[:200],
            insight=insight,
            confidence=confidence,
            domain=domain,
        )
        self._lessons[lesson.lesson_id] = lesson
        self._save()
        return lesson

    def apply_lessons(self, situation: str) -> List[Tuple[float, Lesson]]:
        """Find and apply relevant past lessons."""
        scored: List[Tuple[float, Lesson]] = []
        for lesson in self._lessons.values():
            sim = _similarity(situation, lesson.trigger_event + " " + lesson.insight)
            weighted = sim * lesson.confidence
            if weighted > 0.05:
                scored.append((weighted, lesson))
        scored.sort(key=lambda x: x[0], reverse=True)
        # Mark applied
        for _, lesson in scored[:5]:
            lesson.applied_count += 1
        if scored:
            self._save()
        return scored[:10]

    def reinforce(self, lesson_id: str, delta: float = 0.05) -> Optional[Lesson]:
        """Increase confidence in a lesson (it worked again)."""
        if lesson_id not in self._lessons:
            return None
        lesson = self._lessons[lesson_id]
        lesson.confidence = min(1.0, lesson.confidence + delta)
        lesson.reinforcement_count += 1
        self._save()
        return lesson

    def deprecate(self, lesson_id: str, delta: float = 0.1) -> Optional[Lesson]:
        """Decrease confidence in a lesson (it failed)."""
        if lesson_id not in self._lessons:
            return None
        lesson = self._lessons[lesson_id]
        lesson.confidence = max(0.0, lesson.confidence - delta)
        lesson.deprecation_count += 1
        # Auto-remove if confidence very low
        if lesson.confidence < 0.05:
            del self._lessons[lesson_id]
            self._save()
            return None
        self._save()
        return lesson

    def generalize(self, lesson_ids: List[str]) -> Optional[Lesson]:
        """Combine specific lessons into general principles."""
        lessons = [self._lessons[lid] for lid in lesson_ids if lid in self._lessons]
        if len(lessons) < 2:
            return None
        # Combine insights
        combined_insight = "General principle from multiple lessons: " + " | ".join(
            l.insight[:60] for l in lessons
        )
        avg_confidence = sum(l.confidence for l in lessons) / len(lessons)
        # Find common domain
        domain_counts = Counter(l.domain for l in lessons)
        common_domain = domain_counts.most_common(1)[0][0]

        general_lesson = Lesson(
            lesson_id=str(uuid.uuid4()),
            timestamp=_now_ts(),
            trigger_event="generalized from " + str(len(lessons)) + " lessons",
            insight=combined_insight,
            confidence=avg_confidence * 0.9,  # slight discount for generalization
            domain=common_domain,
            generalized_from=lesson_ids,
        )
        self._lessons[general_lesson.lesson_id] = general_lesson
        self._save()
        return general_lesson

    def transfer(self, source_domain: str, target_domain: str) -> List[Lesson]:
        """Apply lessons across domains."""
        source_lessons = [l for l in self._lessons.values() if l.domain == source_domain]
        transferred = []
        for lesson in source_lessons:
            new_lesson = Lesson(
                lesson_id=str(uuid.uuid4()),
                timestamp=_now_ts(),
                trigger_event=f"[Transferred from {source_domain}] " + lesson.trigger_event[:100],
                insight=f"[Adapted to {target_domain}] " + lesson.insight[:200],
                confidence=lesson.confidence * 0.7,  # discount for domain transfer
                domain=target_domain,
                generalized_from=[lesson.lesson_id],
            )
            self._lessons[new_lesson.lesson_id] = new_lesson
            transferred.append(new_lesson)
        if transferred:
            self._save()
        return transferred

    def all_lessons(self) -> Dict[str, Lesson]:
        return dict(self._lessons)

    def count(self) -> int:
        return len(self._lessons)

    def __repr__(self) -> str:
        return f"LearningEngine(lessons={len(self._lessons)}, path={self.path})"


# ---------------------------------------------------------------------------
# PatternRecognizer
# ---------------------------------------------------------------------------

@dataclass
class Pattern:
    name: str
    sequence: List[str]
    occurrences: int
    first_seen: float
    last_seen: float
    callbacks: List[Callable] = field(default_factory=list, repr=False)

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "sequence": self.sequence,
            "occurrences": self.occurrences,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
        }

    def __repr__(self) -> str:
        return f"Pattern(name={self.name!r}, occurrences={self.occurrences})"


class PatternRecognizer:
    """Records events and detects repeating patterns."""

    def __init__(self, window_size: int = 50):
        self.window_size = window_size
        self._events: List[Tuple[float, str]] = []
        self._patterns: Dict[str, Pattern] = {}
        self._alert_patterns: Dict[str, List[Callable]] = defaultdict(list)

    def observe(self, event: str):
        """Record an event."""
        self._events.append((_now_ts(), event))
        if len(self._events) > self.window_size * 2:
            self._events = self._events[-self.window_size:]
        # Check existing patterns
        for name, pattern in self._patterns.items():
            callbacks = self._alert_patterns.get(name, [])
            if self._check_pattern_match(pattern):
                for cb in callbacks:
                    try:
                        cb(name, event)
                    except Exception:
                        pass

    def _check_pattern_match(self, pattern: Pattern) -> bool:
        """Check if the recent events match a known pattern."""
        recent = [e for _, e in self._events[-len(pattern.sequence):]]
        if len(recent) < len(pattern.sequence):
            return False
        return [_tokenize(e)[0] if _tokenize(e) else e for e in recent] == \
               [_tokenize(e)[0] if _tokenize(e) else e for e in pattern.sequence]

    def detect_patterns(self, min_occurrences: int = 3) -> List[Pattern]:
        """Find repeating sub-sequences in the event stream."""
        events = [e for _, e in self._events]
        if len(events) < min_occurrences * 2:
            return []

        # Find repeating bigrams and trigrams
        new_patterns: Dict[str, int] = defaultdict(int)
        for n in (2, 3):
            for i in range(len(events) - n + 1):
                key = tuple(events[i:i+n])
                new_patterns[key] += 1

        detected = []
        for seq_tuple, count in new_patterns.items():
            if count >= min_occurrences:
                seq = list(seq_tuple)
                name = "+".join(s[:10] for s in seq)
                if name not in self._patterns:
                    p = Pattern(
                        name=name,
                        sequence=seq,
                        occurrences=count,
                        first_seen=_now_ts(),
                        last_seen=_now_ts(),
                    )
                    self._patterns[name] = p
                else:
                    self._patterns[name].occurrences = count
                    self._patterns[name].last_seen = _now_ts()
                detected.append(self._patterns[name])

        return sorted(detected, key=lambda p: p.occurrences, reverse=True)

    def predict_next(self, recent_events: List[str]) -> Optional[str]:
        """Predict what happens next based on patterns."""
        best_match: Optional[Tuple[int, str]] = None
        for name, pattern in self._patterns.items():
            seq = pattern.sequence
            # Check if recent events end with the start of this pattern
            for length in range(1, len(seq)):
                if len(recent_events) >= length:
                    tail = recent_events[-length:]
                    pattern_prefix = seq[:length]
                    # Simple token-level match
                    match = all(
                        _similarity(t, p) > 0.5
                        for t, p in zip(tail, pattern_prefix)
                    )
                    if match and len(seq) > length:
                        candidate = seq[length]
                        score = pattern.occurrences * length
                        if best_match is None or score > best_match[0]:
                            best_match = (score, candidate)

        return best_match[1] if best_match else None

    def alert_on_pattern(self, pattern_name: str, callback: Callable):
        """Fire callback when pattern detected."""
        self._alert_patterns[pattern_name].append(callback)

    def all_patterns(self) -> List[Pattern]:
        return list(self._patterns.values())

    def __repr__(self) -> str:
        return f"PatternRecognizer(events={len(self._events)}, patterns={len(self._patterns)})"


# ---------------------------------------------------------------------------
# PerformanceTracker
# ---------------------------------------------------------------------------

@dataclass
class TaskRecord:
    task_type: str
    success: bool
    duration: float
    quality_score: float
    timestamp: float

    def to_dict(self) -> Dict:
        return asdict(self)


class PerformanceTracker:
    """Tracks success/failure rates per task type."""

    def __init__(self):
        self._records: List[TaskRecord] = []

    def record_task(self, task_type: str, success: bool,
                    duration: float = 0.0, quality_score: float = 0.5):
        """Record a task outcome."""
        rec = TaskRecord(
            task_type=task_type,
            success=success,
            duration=duration,
            quality_score=max(0.0, min(1.0, quality_score)),
            timestamp=_now_ts(),
        )
        self._records.append(rec)

    def _by_type(self, task_type: str) -> List[TaskRecord]:
        return [r for r in self._records if r.task_type == task_type]

    def success_rate(self, task_type: str) -> float:
        records = self._by_type(task_type)
        if not records:
            return 0.0
        return sum(1 for r in records if r.success) / len(records)

    def worst_performing(self, top_n: int = 5) -> List[Tuple[str, float]]:
        """Find where agent struggles most."""
        types = set(r.task_type for r in self._records)
        rates = [(t, self.success_rate(t)) for t in types]
        rates.sort(key=lambda x: x[1])
        return rates[:top_n]

    def improvement_over_time(self, task_type: str, window: int = 10) -> List[float]:
        """Show learning curve as windowed success rates."""
        records = self._by_type(task_type)
        if len(records) < window:
            return [self.success_rate(task_type)]
        curve = []
        for i in range(window, len(records) + 1):
            window_recs = records[i - window:i]
            rate = sum(1 for r in window_recs if r.success) / window
            curve.append(rate)
        return curve

    def suggest_focus_areas(self) -> List[str]:
        """Suggest what the agent should practice."""
        worst = self.worst_performing(top_n=3)
        suggestions = []
        for task_type, rate in worst:
            if rate < 0.5:
                suggestions.append(
                    f"Focus on '{task_type}' (success rate: {rate:.0%})"
                )
            elif rate < 0.75:
                suggestions.append(
                    f"Improve '{task_type}' (success rate: {rate:.0%})"
                )
        return suggestions or ["Performance looks good across all tracked task types!"]

    def summary(self) -> Dict[str, Any]:
        types = set(r.task_type for r in self._records)
        return {
            "total_tasks": len(self._records),
            "task_types": len(types),
            "per_type": {t: {
                "count": len(self._by_type(t)),
                "success_rate": round(self.success_rate(t), 3),
                "avg_quality": round(
                    sum(r.quality_score for r in self._by_type(t)) / max(len(self._by_type(t)), 1), 3
                ),
                "avg_duration": round(
                    sum(r.duration for r in self._by_type(t)) / max(len(self._by_type(t)), 1), 3
                ),
            } for t in types},
        }

    def __repr__(self) -> str:
        types = set(r.task_type for r in self._records)
        return f"PerformanceTracker(records={len(self._records)}, task_types={len(types)})"
