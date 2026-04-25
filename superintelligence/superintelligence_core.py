"""
superintelligence_core.py — Unified orchestrator connecting all SI layers.

Integrates Memory, Reasoning, Self-Audit, Learning, and Parliament.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# Import all superintelligence modules
try:
    from memory_system import UnifiedMemory
    from distributed_reasoning import ReasoningEngine, ReasoningPath, ReasoningResult
    from self_audit import SelfAuditEngine, AuditResult
    from learning_engine import LearningEngine, PatternRecognizer, PerformanceTracker
    from agent_parliament import AgentParliament
except ImportError:
    from superintelligence.memory_system import UnifiedMemory
    from superintelligence.distributed_reasoning import (
        ReasoningEngine, ReasoningPath, ReasoningResult
    )
    from superintelligence.self_audit import SelfAuditEngine, AuditResult
    from superintelligence.learning_engine import (
        LearningEngine, PatternRecognizer, PerformanceTracker
    )
    from superintelligence.agent_parliament import AgentParliament


def _now_ts() -> float:
    return time.time()


# ---------------------------------------------------------------------------
# ProcessingResult — structured output of the full pipeline
# ---------------------------------------------------------------------------

@dataclass
class ProcessingResult:
    query_id: str
    query: str
    response: str
    confidence: float
    reasoning_chain: List[str]
    audit_result: Optional[AuditResult]
    memory_hits: int
    parliament_used: bool
    duration_ms: float
    fixed: bool = False

    def __repr__(self) -> str:
        return (f"ProcessingResult(id={self.query_id[:8]}, "
                f"confidence={self.confidence:.2f}, "
                f"fixed={self.fixed})")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query_id": self.query_id,
            "query": self.query[:200],
            "response": self.response[:500],
            "confidence": self.confidence,
            "reasoning_chain": self.reasoning_chain[:10],
            "audit_passed": self.audit_result.passed if self.audit_result else None,
            "audit_score": self.audit_result.overall_score if self.audit_result else None,
            "memory_hits": self.memory_hits,
            "parliament_used": self.parliament_used,
            "duration_ms": self.duration_ms,
            "fixed": self.fixed,
        }


# ---------------------------------------------------------------------------
# SuperIntelligenceCore
# ---------------------------------------------------------------------------

class SuperIntelligenceCore:
    """
    The unified superintelligence orchestrator for SintraPrime.

    Connects:
      - UnifiedMemory          (3-tier memory)
      - ReasoningEngine        (4-path parallel reasoning)
      - SelfAuditEngine        (10-rule self-audit)
      - LearningEngine         (lesson extraction & application)
      - PatternRecognizer      (event pattern detection)
      - PerformanceTracker     (task performance metrics)
      - AgentParliament        (multi-agent debate & voting)
    """

    CRITICAL_KEYWORDS = {
        "delete", "destroy", "irreversible", "shutdown", "security",
        "ethics", "harm", "critical", "deploy", "production"
    }

    def __init__(self):
        self.memory      = UnifiedMemory()
        self.reasoner    = ReasoningEngine(memory_system=self.memory)
        self.auditor     = SelfAuditEngine()
        self.learner     = LearningEngine()
        self.patterns    = PatternRecognizer()
        self.tracker     = PerformanceTracker()
        self.parliament  = AgentParliament()
        self._last_result: Optional[ProcessingResult] = None
        self._session_history: List[ProcessingResult] = []

    def _is_critical(self, query: str) -> bool:
        """Check if query requires parliamentary debate."""
        q_lower = query.lower()
        return any(kw in q_lower for kw in self.CRITICAL_KEYWORDS)

    def _build_response_from_reasoning(
        self, query: str,
        results: List[ReasoningResult],
        memory_context: str
    ) -> Tuple[str, float, List[str]]:
        """Synthesize a response from parallel reasoning results."""
        if not results:
            return (f"Unable to reason about: {query}", 0.1, [])

        winner, consensus_score = self.reasoner.vote(results)
        chain: List[str] = []

        # Collect reasoning chains from all paths
        for r in results:
            chain.extend(r.reasoning_chain[:3])

        chain.append(f"Voting winner: {winner.path_type.value} "
                     f"(confidence={winner.confidence:.2f})")
        chain.append(f"Consensus score: {consensus_score:.2f}")

        # Build response
        response_parts = [winner.answer]

        # Add supporting paths if they agree
        supporting = [
            r for r in results
            if r.path_type != winner.path_type and r.confidence > 0.4
        ]
        if supporting:
            response_parts.append(
                f"\n[Corroborated by {len(supporting)} other reasoning path(s)]"
            )

        # Add memory context if relevant
        if memory_context:
            response_parts.append(f"\n[Memory context: {memory_context[:100]}]")

        # Adjust confidence by consensus
        final_confidence = winner.confidence * (0.7 + 0.3 * consensus_score)
        return "\n".join(response_parts), final_confidence, chain

    async def process(
        self,
        query: str,
        context: str = "",
        criticality: str = "normal"
    ) -> ProcessingResult:
        """
        Full processing pipeline:
        1. Search memory for relevant context
        2. Apply lessons from past experience
        3. Run distributed reasoning (4 paths)
        4. Self-audit the response
        5. Auto-fix any issues
        6. Learn from the interaction
        7. If critical: run parliament debate
        """
        start = _now_ts()
        query_id = str(uuid.uuid4())

        # --- Step 1: Memory search ---
        memory_results = self.memory.recall_all(query, n_each=3)
        memory_context = ""
        if memory_results:
            top = memory_results[0]
            memory_context = str(top.get("content", top.get("value", "")))[:200]

        # Enhanced context for reasoning
        full_context = context
        if memory_context:
            full_context = f"{context}\n[Memory: {memory_context}]".strip()

        # --- Step 2: Apply past lessons ---
        lessons = self.learner.apply_lessons(query)
        lesson_insights = []
        if lessons:
            lesson_insights = [l.insight[:80] for _, l in lessons[:2]]
            full_context += "\n[Lessons: " + " | ".join(lesson_insights) + "]"

        # --- Step 3: Distributed reasoning ---
        reasoning_results = self.reasoner.reason(query, context=full_context)

        # --- Step 4: Build response ---
        response, confidence, chain = self._build_response_from_reasoning(
            query, reasoning_results, memory_context
        )

        # --- Step 5: Parliament debate (if critical) ---
        parliament_used = False
        is_critical = criticality == "critical" or self._is_critical(query)
        if is_critical:
            try:
                debate_rounds = self.parliament.debate(query, rounds=2)
                chain.append(f"Parliament debate: {len(debate_rounds)} rounds")
                decision = self.parliament.record_decision(
                    query, response[:100], reasoning="distributed reasoning result"
                )
                chain.append(f"Parliament decision ID: {decision.decision_id[:8]}")
                parliament_used = True
            except Exception as e:
                chain.append(f"Parliament error: {e}")

        # --- Step 6: Self-audit ---
        audit_result = self.auditor.audit(response, context=full_context)
        fixed = False
        if not audit_result.passed:
            response = self.auditor.fix(response, audit_result)
            fixed = True
            chain.append(f"Audit fixed {len(audit_result.issues)} issue(s)")

        # --- Step 7: Learn from interaction ---
        outcome = "success" if audit_result.passed else "needs_improvement"
        lesson = self.learner.learn_from_outcome(
            action=f"process_query: {query[:80]}",
            outcome=outcome,
            context=full_context[:200],
        )
        chain.append(f"Lesson recorded: {lesson.lesson_id[:8]}")

        # Track performance
        self.patterns.observe(f"query:{query[:30]}")
        self.tracker.record_task(
            task_type="query_processing",
            success=audit_result.passed,
            duration=(_now_ts() - start) * 1000,
            quality_score=confidence,
        )

        # Store in episodic memory
        self.memory.episodic.record(
            event_type="query_processing",
            content=query,
            context=full_context[:200],
            outcome=f"{outcome} (confidence={confidence:.2f})",
        )

        duration_ms = (_now_ts() - start) * 1000

        result = ProcessingResult(
            query_id=query_id,
            query=query,
            response=response,
            confidence=confidence,
            reasoning_chain=chain,
            audit_result=audit_result,
            memory_hits=len(memory_results),
            parliament_used=parliament_used,
            duration_ms=duration_ms,
            fixed=fixed,
        )
        self._last_result = result
        self._session_history.append(result)
        return result

    async def learn_from_session(self, session_history: Optional[List[Any]] = None) -> Dict[str, Any]:
        """Extract lessons from completed session."""
        history = session_history or self._session_history
        lessons_extracted = 0
        for item in history:
            if isinstance(item, ProcessingResult):
                outcome = "success" if (item.audit_result and item.audit_result.passed) else "failure"
                lesson = self.learner.learn_from_outcome(
                    action=f"session_item: {item.query[:60]}",
                    outcome=outcome,
                    context=f"confidence={item.confidence:.2f}",
                )
                lessons_extracted += 1
        # Detect patterns
        patterns = self.patterns.detect_patterns(min_occurrences=2)
        return {
            "session_items": len(history),
            "lessons_extracted": lessons_extracted,
            "patterns_found": len(patterns),
            "patterns": [p.name for p in patterns[:5]],
        }

    async def introspect(self) -> Dict[str, Any]:
        """Self-reflection: how am I performing?"""
        memory_stats = self.memory.stats()
        perf_summary = self.tracker.summary()
        focus_areas = self.tracker.suggest_focus_areas()
        audit_stats = self.auditor.logger.stats()
        lesson_count = self.learner.count()
        parliament_stats = self.parliament.stats()
        patterns = self.patterns.detect_patterns(min_occurrences=2)

        # Compute overall health score
        health_factors = []
        if audit_stats.get("total_audits", 0) > 0:
            health_factors.append(audit_stats.get("pass_rate", 0.5))
        if perf_summary.get("total_tasks", 0) > 0:
            overall_success = sum(
                v["success_rate"] for v in perf_summary.get("per_type", {}).values()
            ) / max(len(perf_summary.get("per_type", {})), 1)
            health_factors.append(overall_success)
        health_score = sum(health_factors) / max(len(health_factors), 1) if health_factors else 0.5

        return {
            "health_score": round(health_score, 3),
            "memory": memory_stats,
            "performance": perf_summary,
            "focus_areas": focus_areas,
            "audit_stats": audit_stats,
            "lessons_learned": lesson_count,
            "parliament": parliament_stats,
            "patterns_detected": len(patterns),
            "session_queries": len(self._session_history),
            "reasoning_cache_size": self.reasoner.cache.size(),
        }

    def explain_last_response(self) -> str:
        """Full transparency: show all reasoning steps."""
        if self._last_result is None:
            return "No response has been generated yet in this session."

        r = self._last_result
        lines = [
            "=" * 60,
            "FULL REASONING TRANSPARENCY REPORT",
            "=" * 60,
            f"Query ID: {r.query_id}",
            f"Query: {r.query[:200]}",
            f"",
            f"RESPONSE:",
            r.response[:500],
            f"",
            f"METADATA:",
            f"  Confidence:      {r.confidence:.3f}",
            f"  Duration:        {r.duration_ms:.1f}ms",
            f"  Memory hits:     {r.memory_hits}",
            f"  Parliament used: {r.parliament_used}",
            f"  Fixed by audit:  {r.fixed}",
            f"",
            f"REASONING CHAIN:",
        ]
        for i, step in enumerate(r.reasoning_chain, 1):
            lines.append(f"  {i:2}. {step}")

        if r.audit_result:
            lines += [
                f"",
                f"AUDIT RESULT:",
                f"  Passed: {r.audit_result.passed}",
                f"  Score:  {r.audit_result.overall_score:.3f}",
                f"  Issues: {len(r.audit_result.issues)}",
            ]
            for issue in r.audit_result.issues:
                lines.append(f"    - [{issue.severity}] {issue.rule_name}: {issue.description[:80]}")

        lines.append("=" * 60)
        return "\n".join(lines)

    def __repr__(self) -> str:
        return (
            f"SuperIntelligenceCore("
            f"memory={self.memory}, "
            f"reasoner={self.reasoner}, "
            f"auditor={self.auditor})"
        )
