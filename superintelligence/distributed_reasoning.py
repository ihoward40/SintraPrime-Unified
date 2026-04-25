"""
distributed_reasoning.py — Four parallel reasoning paths with voting.

Provides DeductiveReasoner, InductiveReasoner, AbductiveReasoner,
AnalogicalReasoner, ReasoningEngine, and ReasoningCache.
"""

from __future__ import annotations

import hashlib
import math
import re
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    from memory_system import UnifiedMemory, _tf_idf_similarity
except ImportError:
    try:
        from superintelligence.memory_system import UnifiedMemory, _tf_idf_similarity
    except ImportError:
        UnifiedMemory = None  # type: ignore

        def _tf_idf_similarity(a: str, b: str) -> float:  # type: ignore
            import re, math
            from collections import defaultdict
            def tok(t): return re.findall(r"[a-zA-Z0-9]+", t.lower())
            q, d = tok(a), tok(b)
            if not q or not d: return 0.0
            vocab = set(q) | set(d)
            qf: Dict[str, int] = defaultdict(int)
            df: Dict[str, int] = defaultdict(int)
            for t in q: qf[t] += 1
            for t in d: df[t] += 1
            dot = sum(qf[t] * df[t] for t in vocab)
            mq = math.sqrt(sum(v*v for v in qf.values()))
            md = math.sqrt(sum(v*v for v in df.values()))
            return dot / (mq * md) if mq and md else 0.0


# ---------------------------------------------------------------------------
# Enums & Dataclasses
# ---------------------------------------------------------------------------

class ReasoningPath(Enum):
    DEDUCTIVE   = "deductive"
    INDUCTIVE   = "inductive"
    ABDUCTIVE   = "abductive"
    ANALOGICAL  = "analogical"


@dataclass
class ReasoningResult:
    path_type: ReasoningPath
    answer: str
    confidence: float          # 0.0 – 1.0
    reasoning_chain: List[str]
    duration_ms: float = 0.0
    error: Optional[str] = None

    def __repr__(self) -> str:
        return (f"ReasoningResult(path={self.path_type.value}, "
                f"confidence={self.confidence:.2f}, "
                f"answer={self.answer[:60]!r})")


@dataclass
class DebateRound:
    round_num: int
    speaker: ReasoningPath
    statement: str
    counter_arguments: List[str] = field(default_factory=list)
    support_score: float = 0.5

    def __repr__(self) -> str:
        return f"DebateRound(round={self.round_num}, speaker={self.speaker.value})"


# ---------------------------------------------------------------------------
# Individual Reasoners
# ---------------------------------------------------------------------------

class DeductiveReasoner:
    """Applies formal logic rules: modus ponens, modus tollens, syllogism."""

    # Simple rule patterns: (antecedent pattern, consequent template)
    _RULES = [
        (r"if (.+) then (.+)", "modus_ponens"),
        (r"all (.+) are (.+)", "syllogism"),
        (r"no (.+) are (.+)", "syllogism_neg"),
        (r"(.+) implies (.+)", "implication"),
    ]

    def reason(self, question: str, premises: List[str]) -> ReasoningResult:
        start = time.time()
        chain: List[str] = []
        conclusions: List[str] = []
        confidence = 0.5

        chain.append(f"Deductive reasoning on: {question!r}")
        chain.append(f"Premises: {premises}")

        # Parse premises into IF-THEN rules
        rules: List[Tuple[str, str]] = []
        for premise in premises:
            p_lower = premise.lower().strip()
            for pattern, rule_type in self._RULES:
                m = re.search(pattern, p_lower)
                if m:
                    if rule_type == "modus_ponens":
                        antecedent, consequent = m.group(1).strip(), m.group(2).strip()
                        rules.append((antecedent, consequent))
                        chain.append(f"  Rule ({rule_type}): if '{antecedent}' → '{consequent}'")
                    elif rule_type == "syllogism":
                        subj, pred = m.group(1).strip(), m.group(2).strip()
                        rules.append((subj, pred))
                        chain.append(f"  Syllogism: all '{subj}' are '{pred}'")

        q_lower = question.lower()
        for antecedent, consequent in rules:
            if antecedent in q_lower or any(antecedent in p.lower() for p in premises):
                conclusions.append(f"Therefore: {consequent}")
                confidence = min(confidence + 0.15, 0.95)
                chain.append(f"  Applying rule: {antecedent} → {consequent}")

        if conclusions:
            answer = " | ".join(conclusions)
        else:
            # Attempt direct extraction from premises
            answer = (
                f"Based on deductive analysis of {len(premises)} premise(s), "
                f"the most logical conclusion regarding '{question}' requires additional premises. "
                f"Available inference: {premises[0] if premises else 'none'}"
            )
            confidence = 0.3
            chain.append("  No direct deductive conclusion — insufficient premises")

        duration = (time.time() - start) * 1000
        return ReasoningResult(
            path_type=ReasoningPath.DEDUCTIVE,
            answer=answer,
            confidence=confidence,
            reasoning_chain=chain,
            duration_ms=duration,
        )


class InductiveReasoner:
    """Identifies patterns from examples and generalizes to rules."""

    def reason(self, question: str, examples: List[str]) -> ReasoningResult:
        start = time.time()
        chain: List[str] = []
        confidence = 0.4

        chain.append(f"Inductive reasoning on: {question!r}")
        chain.append(f"Analyzing {len(examples)} examples")

        if not examples:
            return ReasoningResult(
                path_type=ReasoningPath.INDUCTIVE,
                answer="Insufficient examples for inductive reasoning.",
                confidence=0.1,
                reasoning_chain=chain,
                duration_ms=(time.time() - start) * 1000,
            )

        # Find common tokens across examples
        from collections import Counter
        all_tokens: List[str] = []
        for ex in examples:
            all_tokens.extend(re.findall(r"[a-zA-Z]+", ex.lower()))
        token_counts = Counter(all_tokens)
        common = [t for t, c in token_counts.most_common(10) if c > 1 and len(t) > 3]

        chain.append(f"  Common elements found: {common[:5]}")

        # Check for numeric patterns
        numbers = []
        for ex in examples:
            nums = re.findall(r"\d+(?:\.\d+)?", ex)
            numbers.extend(float(n) for n in nums)
        numeric_pattern = ""
        if len(numbers) >= 2:
            diffs = [numbers[i+1] - numbers[i] for i in range(len(numbers)-1)]
            if len(set(round(d, 2) for d in diffs)) == 1:
                numeric_pattern = f" arithmetic pattern with diff={diffs[0]}"
                confidence += 0.2

        # Build generalized conclusion
        if common:
            pattern_desc = f"Pattern detected: '{', '.join(common[:3])}' appear consistently"
            confidence += min(len(common) * 0.05, 0.25)
        else:
            pattern_desc = "No strong common pattern found across examples"

        answer = (
            f"Inductive generalization from {len(examples)} examples: "
            f"{pattern_desc}{numeric_pattern}. "
            f"Regarding '{question}': this pattern suggests a general rule holds "
            f"with {len(examples)}-example support."
        )
        confidence = min(confidence + len(examples) * 0.02, 0.9)
        chain.append(f"  Generalized rule: {pattern_desc}")
        chain.append(f"  Confidence scaled by example count: {confidence:.2f}")

        duration = (time.time() - start) * 1000
        return ReasoningResult(
            path_type=ReasoningPath.INDUCTIVE,
            answer=answer,
            confidence=confidence,
            reasoning_chain=chain,
            duration_ms=duration,
        )


class AbductiveReasoner:
    """Finds the best explanation for an observation (Occam's razor + fit)."""

    def reason(self, observation: str,
               possible_explanations: List[str]) -> ReasoningResult:
        start = time.time()
        chain: List[str] = []
        confidence = 0.5

        chain.append(f"Abductive reasoning on observation: {observation!r}")

        if not possible_explanations:
            return ReasoningResult(
                path_type=ReasoningPath.ABDUCTIVE,
                answer=f"No explanations provided for: {observation}",
                confidence=0.1,
                reasoning_chain=chain,
                duration_ms=(time.time() - start) * 1000,
            )

        scored: List[Tuple[float, str]] = []
        for exp in possible_explanations:
            # Simplicity score: shorter explanations preferred (Occam's razor)
            simplicity = 1.0 / (1.0 + len(exp.split()) / 10.0)
            # Fit score: how well does the explanation match the observation?
            fit = _tf_idf_similarity(observation, exp)
            total = 0.6 * fit + 0.4 * simplicity
            scored.append((total, exp))
            chain.append(f"  Explanation: {exp[:60]!r} → score={total:.3f} "
                         f"(fit={fit:.3f}, simplicity={simplicity:.3f})")

        scored.sort(key=lambda x: x[0], reverse=True)
        best_score, best_exp = scored[0]

        # Confidence based on how much better the best is vs second best
        if len(scored) > 1:
            gap = scored[0][0] - scored[1][0]
            confidence = 0.5 + min(gap * 2, 0.4)
        else:
            confidence = 0.7

        chain.append(f"  Best explanation selected: {best_exp[:60]!r}")
        answer = (
            f"Best explanation (abductive): {best_exp} "
            f"[ranked 1/{len(possible_explanations)}, score={best_score:.3f}]"
        )

        duration = (time.time() - start) * 1000
        return ReasoningResult(
            path_type=ReasoningPath.ABDUCTIVE,
            answer=answer,
            confidence=confidence,
            reasoning_chain=chain,
            duration_ms=duration,
        )


class AnalogicalReasoner:
    """Finds analogous past problems and maps their solutions."""

    def reason(self, problem: str,
               memory_system: Optional[Any] = None,
               analogies: Optional[List[Dict[str, str]]] = None) -> ReasoningResult:
        start = time.time()
        chain: List[str] = []
        confidence = 0.3

        chain.append(f"Analogical reasoning on: {problem!r}")

        past_problems: List[Tuple[float, str, str]] = []  # (sim, problem, solution)

        # Search memory system if available
        if memory_system is not None:
            try:
                recalls = memory_system.recall_all(problem, n_each=5)
                for item in recalls:
                    sim = item["score"]
                    content = item.get("content", item.get("value", ""))
                    outcome = item.get("outcome", "")
                    if sim > 0.05:
                        past_problems.append((sim, str(content), str(outcome)))
                        chain.append(f"  Memory match (sim={sim:.3f}): {str(content)[:60]!r}")
            except Exception as e:
                chain.append(f"  Memory search error: {e}")

        # Use provided analogies if available
        if analogies:
            for a in analogies:
                sim = _tf_idf_similarity(problem, a.get("problem", ""))
                past_problems.append((sim, a.get("problem", ""), a.get("solution", "")))

        if not past_problems:
            answer = (
                f"No analogous problems found in memory for: {problem!r}. "
                f"Cannot apply analogical reasoning without prior examples."
            )
            confidence = 0.15
            chain.append("  No analogies found")
        else:
            past_problems.sort(key=lambda x: x[0], reverse=True)
            best_sim, best_problem, best_solution = past_problems[0]
            confidence = min(best_sim * 0.8 + 0.2, 0.85)
            chain.append(f"  Best analogy (sim={best_sim:.3f}): {best_problem[:60]!r}")
            chain.append(f"  Mapped solution: {best_solution[:60]!r}")
            answer = (
                f"Analogical solution: By analogy to '{best_problem[:80]}' "
                f"(structural similarity={best_sim:.2f}), the solution to '{problem}' "
                f"is likely: {best_solution or 'similar approach as past problem'}"
            )

        duration = (time.time() - start) * 1000
        return ReasoningResult(
            path_type=ReasoningPath.ANALOGICAL,
            answer=answer,
            confidence=confidence,
            reasoning_chain=chain,
            duration_ms=duration,
        )


# ---------------------------------------------------------------------------
# ReasoningCache — LRU cache with semantic similarity
# ---------------------------------------------------------------------------

class ReasoningCache:
    """LRU cache for reasoning results with semantic similarity lookup."""

    def __init__(self, capacity: int = 256, similarity_threshold: float = 0.85):
        self.capacity = capacity
        self.threshold = similarity_threshold
        self._cache: OrderedDict[str, Tuple[str, List[ReasoningResult]]] = OrderedDict()

    def _key(self, question: str) -> str:
        return hashlib.md5(question.lower().strip().encode()).hexdigest()

    def get(self, question: str) -> Optional[List[ReasoningResult]]:
        """Return cached results if question is semantically similar to a cached one."""
        for cached_q, results in self._cache.items():
            raw_q, result_list = results
            sim = _tf_idf_similarity(question, raw_q)
            if sim >= self.threshold:
                # Move to end (LRU)
                self._cache.move_to_end(cached_q)
                return result_list
        return None

    def put(self, question: str, results: List[ReasoningResult]):
        """Cache reasoning results."""
        key = self._key(question)
        self._cache[key] = (question, results)
        self._cache.move_to_end(key)
        if len(self._cache) > self.capacity:
            self._cache.popitem(last=False)

    def size(self) -> int:
        return len(self._cache)

    def __repr__(self) -> str:
        return f"ReasoningCache(size={len(self._cache)}/{self.capacity})"


# ---------------------------------------------------------------------------
# ReasoningEngine — Main orchestrator
# ---------------------------------------------------------------------------

class ReasoningEngine:
    """Runs all 4 reasoning paths in parallel and votes on the best answer."""

    def __init__(self, memory_system: Optional[Any] = None):
        self.memory = memory_system
        self.deductive = DeductiveReasoner()
        self.inductive = InductiveReasoner()
        self.abductive = AbductiveReasoner()
        self.analogical = AnalogicalReasoner()
        self.cache = ReasoningCache()
        self._lock = threading.Lock()

    def _run_deductive(self, question: str, context: str) -> ReasoningResult:
        premises = [s.strip() for s in context.split(".") if s.strip()]
        return self.deductive.reason(question, premises)

    def _run_inductive(self, question: str, context: str) -> ReasoningResult:
        examples = [s.strip() for s in context.split(";") if s.strip()]
        if not examples:
            examples = [s.strip() for s in context.split(".") if s.strip()]
        return self.inductive.reason(question, examples)

    def _run_abductive(self, question: str, context: str) -> ReasoningResult:
        explanations = [s.strip() for s in context.split("|") if s.strip()]
        if not explanations:
            explanations = [s.strip() for s in context.split(".") if s.strip() and len(s) > 10]
        return self.abductive.reason(question, explanations)

    def _run_analogical(self, question: str, context: str) -> ReasoningResult:
        return self.analogical.reason(question, memory_system=self.memory)

    def reason(self, question: str, context: str = "",
               paths: Optional[List[ReasoningPath]] = None) -> List[ReasoningResult]:
        """Run all (or specified) reasoning paths in parallel."""
        # Check cache first
        cached = self.cache.get(question)
        if cached is not None:
            return cached

        selected_paths = paths or list(ReasoningPath)
        results: List[Optional[ReasoningResult]] = [None] * len(selected_paths)
        errors: List[Optional[Exception]] = [None] * len(selected_paths)

        path_fns = {
            ReasoningPath.DEDUCTIVE:  self._run_deductive,
            ReasoningPath.INDUCTIVE:  self._run_inductive,
            ReasoningPath.ABDUCTIVE:  self._run_abductive,
            ReasoningPath.ANALOGICAL: self._run_analogical,
        }

        def run_path(idx: int, path: ReasoningPath):
            try:
                results[idx] = path_fns[path](question, context)
            except Exception as e:
                results[idx] = ReasoningResult(
                    path_type=path,
                    answer=f"Error in {path.value} reasoning: {e}",
                    confidence=0.0,
                    reasoning_chain=[str(e)],
                    error=str(e),
                )

        threads = []
        for i, path in enumerate(selected_paths):
            t = threading.Thread(target=run_path, args=(i, path))
            threads.append(t)
            t.start()
        for t in threads:
            t.join(timeout=10)

        final = [r for r in results if r is not None]
        self.cache.put(question, final)
        return final

    def vote(self, path_results: List[ReasoningResult]) -> Tuple[ReasoningResult, float]:
        """Weighted voting by confidence to select best answer."""
        if not path_results:
            raise ValueError("No reasoning results to vote on")
        total_weight = sum(r.confidence for r in path_results)
        if total_weight == 0:
            return path_results[0], 0.0
        # Winner = highest confidence
        winner = max(path_results, key=lambda r: r.confidence)
        # Consensus score = weighted agreement
        consensus = sum(
            r.confidence / total_weight
            for r in path_results
            if _tf_idf_similarity(winner.answer, r.answer) > 0.3
        )
        return winner, min(consensus, 1.0)

    def consensus(self, path_results: List[ReasoningResult]) -> float:
        """Check if paths agree (consensus_score 0-1)."""
        if len(path_results) < 2:
            return 1.0
        pairs = []
        for i in range(len(path_results)):
            for j in range(i + 1, len(path_results)):
                sim = _tf_idf_similarity(path_results[i].answer, path_results[j].answer)
                pairs.append(sim)
        return sum(pairs) / len(pairs) if pairs else 0.0

    def debate(self, question: str, rounds: int = 3) -> List[DebateRound]:
        """Paths challenge each other's answers over multiple rounds."""
        all_rounds: List[DebateRound] = []
        # Initial reasoning
        results = self.reason(question, context="")
        if not results:
            return all_rounds

        current_statements: Dict[ReasoningPath, str] = {
            r.path_type: r.answer for r in results
        }

        for round_num in range(1, rounds + 1):
            for r in results:
                counters = []
                for other in results:
                    if other.path_type != r.path_type:
                        sim = _tf_idf_similarity(r.answer, other.answer)
                        if sim < 0.4:
                            counters.append(
                                f"{other.path_type.value} disagrees "
                                f"(sim={sim:.2f}): {other.answer[:80]}"
                            )
                support = sum(
                    _tf_idf_similarity(r.answer, other.answer)
                    for other in results if other.path_type != r.path_type
                ) / max(len(results) - 1, 1)
                dr = DebateRound(
                    round_num=round_num,
                    speaker=r.path_type,
                    statement=r.answer[:200],
                    counter_arguments=counters,
                    support_score=support,
                )
                all_rounds.append(dr)

        return all_rounds

    def explain(self, answer: str, path_results: List[ReasoningResult]) -> str:
        """Generate human-readable explanation of how the answer was reached."""
        lines = [
            f"=== Reasoning Explanation ===",
            f"Final Answer: {answer[:200]}",
            f"",
            f"Reasoning Paths Used: {len(path_results)}",
        ]
        for r in path_results:
            lines.append(f"\n[{r.path_type.value.upper()} — confidence={r.confidence:.2f}]")
            for step in r.reasoning_chain[:5]:
                lines.append(f"  {step}")
            lines.append(f"  → Conclusion: {r.answer[:100]}")

        winner, cons_score = self.vote(path_results)
        lines.append(f"\nVoting Winner: {winner.path_type.value} (confidence={winner.confidence:.2f})")
        lines.append(f"Consensus Score: {cons_score:.2f}")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"ReasoningEngine(cache={self.cache.size()}, memory={'yes' if self.memory else 'no'})"
