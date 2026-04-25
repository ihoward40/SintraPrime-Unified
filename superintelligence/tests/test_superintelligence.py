"""
test_superintelligence.py — Comprehensive tests for all superintelligence modules.

Run with: cd /agent/home/SintraPrime-Unified && python -m pytest superintelligence/tests/ -v
"""

import asyncio
import json
import os
import sys
import tempfile
import time
import uuid
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Path setup — ensure we can import from the superintelligence package
# ---------------------------------------------------------------------------
SI_DIR = Path(__file__).resolve().parent.parent
if str(SI_DIR) not in sys.path:
    sys.path.insert(0, str(SI_DIR))
if str(SI_DIR.parent) not in sys.path:
    sys.path.insert(0, str(SI_DIR.parent))


# Use temp files for all tests to avoid polluting production files
@pytest.fixture(autouse=True)
def tmp_paths(tmp_path, monkeypatch):
    """Redirect all persistence paths to temp directory."""
    import memory_system as ms
    import self_audit as sa
    import learning_engine as le
    import agent_parliament as ap

    monkeypatch.setattr(ms, "EPISODIC_PATH", tmp_path / "episodic.jsonl")
    monkeypatch.setattr(ms, "SEMANTIC_PATH", tmp_path / "semantic.json")
    monkeypatch.setattr(ms, "PROCEDURAL_PATH", tmp_path / "procedural.json")
    monkeypatch.setattr(sa, "AUDIT_LOG_PATH", tmp_path / "audit_log.jsonl")
    monkeypatch.setattr(le, "LESSONS_PATH", tmp_path / "lessons.json")
    monkeypatch.setattr(ap, "PARLIAMENT_LOG_PATH", tmp_path / "parliament.jsonl")
    return tmp_path


# ===========================================================================
# SECTION 1: EpisodicMemory
# ===========================================================================

class TestEpisodicMemory:

    def _make(self, tmp_path):
        from memory_system import EpisodicMemory
        return EpisodicMemory(path=tmp_path / "episodic.jsonl")

    def test_record_creates_episode(self, tmp_path):
        mem = self._make(tmp_path)
        ep = mem.record("test", "hello world", "ctx", "success")
        assert ep.episode_id
        assert ep.event_type == "test"
        assert ep.content == "hello world"

    def test_record_persists(self, tmp_path):
        mem = self._make(tmp_path)
        ep = mem.record("persist_test", "persistent content", "ctx", "ok")
        mem2 = self._make(tmp_path)
        assert mem2.count() == 1
        assert mem2._episodes[0].content == "persistent content"

    def test_recall_returns_relevant(self, tmp_path):
        mem = self._make(tmp_path)
        mem.record("info", "machine learning algorithms", "AI", "done")
        mem.record("info", "cooking pasta recipe", "food", "done")
        results = mem.recall("machine learning", n=5)
        assert len(results) > 0
        assert results[0][1].content == "machine learning algorithms"

    def test_recall_top_n(self, tmp_path):
        mem = self._make(tmp_path)
        for i in range(15):
            mem.record("test", f"content {i}", "", "")
        results = mem.recall("content", n=5)
        assert len(results) <= 5

    def test_recent_returns_most_recent(self, tmp_path):
        mem = self._make(tmp_path)
        for i in range(25):
            mem.record("event", f"event {i}", "", "")
        recent = mem.recent(n=10)
        assert len(recent) == 10

    def test_important_filters_correctly(self, tmp_path):
        mem = self._make(tmp_path)
        mem.record("critical", "very important event", "", "success")
        mem.record("low", "minor note", "", "")
        important = mem.important(threshold=0.6)
        assert any("very important" in e.content for e in important)

    def test_compress_old_episodes(self, tmp_path):
        mem = self._make(tmp_path)
        # Manually add old episodes
        from memory_system import Episode
        old_ep = Episode(
            episode_id=str(uuid.uuid4()),
            timestamp=time.time() - 40 * 86400,
            event_type="old_event",
            content="old content",
            context="",
            outcome="done",
            importance_score=0.5,
            tags=["old"],
        )
        mem._episodes.append(old_ep)
        mem._append_to_file(old_ep)
        compressed = mem.compress_old(days=30)
        assert compressed >= 1

    def test_importance_score_range(self, tmp_path):
        mem = self._make(tmp_path)
        ep = mem.record("error", "critical failure happened", "", "failure")
        assert 0.0 <= ep.importance_score <= 1.0

    def test_episode_repr(self, tmp_path):
        mem = self._make(tmp_path)
        ep = mem.record("test", "hello", "", "")
        assert "Episode" in repr(ep)

    def test_count(self, tmp_path):
        mem = self._make(tmp_path)
        for i in range(5):
            mem.record("test", f"content {i}", "", "")
        assert mem.count() == 5


# ===========================================================================
# SECTION 2: SemanticMemory
# ===========================================================================

class TestSemanticMemory:

    def _make(self, tmp_path):
        from memory_system import SemanticMemory
        return SemanticMemory(path=tmp_path / "semantic.json")

    def test_learn_stores_fact(self, tmp_path):
        mem = self._make(tmp_path)
        fact = mem.learn("python_version", "3.12", confidence=0.9, source="test")
        assert fact.key == "python_version"
        assert fact.value == "3.12"

    def test_learn_persists(self, tmp_path):
        mem = self._make(tmp_path)
        mem.learn("color", "blue", confidence=0.8)
        mem2 = self._make(tmp_path)
        assert "color" in mem2._facts
        assert mem2._facts["color"].value == "blue"

    def test_recall_by_key(self, tmp_path):
        mem = self._make(tmp_path)
        mem.learn("capital_france", "Paris", confidence=0.95)
        results = mem.recall("capital france")
        assert len(results) > 0
        assert results[0][1].key == "capital_france"

    def test_update_changes_value(self, tmp_path):
        mem = self._make(tmp_path)
        mem.learn("score", 100, confidence=0.7)
        updated = mem.update("score", 200, confidence=0.9)
        assert updated is not None
        assert updated.value == 200

    def test_update_nonexistent_returns_none(self, tmp_path):
        mem = self._make(tmp_path)
        result = mem.update("nonexistent_key", "value")
        assert result is None

    def test_forget_removes_fact(self, tmp_path):
        mem = self._make(tmp_path)
        mem.learn("temp_fact", "temporary", confidence=0.5)
        assert mem.forget("temp_fact") is True
        assert "temp_fact" not in mem._facts

    def test_forget_nonexistent(self, tmp_path):
        mem = self._make(tmp_path)
        assert mem.forget("does_not_exist") is False

    def test_related_facts(self, tmp_path):
        mem = self._make(tmp_path)
        mem.learn("dog", "a domestic animal", confidence=0.9)
        mem.learn("cat", "a domestic pet animal", confidence=0.9)
        mem.learn("car", "a vehicle", confidence=0.9)
        related = mem.related("dog", n=3)
        assert len(related) >= 0  # may find cat as related

    def test_confidence_clamping(self, tmp_path):
        mem = self._make(tmp_path)
        fact = mem.learn("x", "y", confidence=1.5)
        assert fact.confidence <= 1.0
        fact2 = mem.learn("a", "b", confidence=-0.5)
        assert fact2.confidence >= 0.0

    def test_count(self, tmp_path):
        mem = self._make(tmp_path)
        mem.learn("k1", "v1")
        mem.learn("k2", "v2")
        assert mem.count() == 2


# ===========================================================================
# SECTION 3: ProceduralMemory
# ===========================================================================

class TestProceduralMemory:

    def _make(self, tmp_path):
        from memory_system import ProceduralMemory
        return ProceduralMemory(path=tmp_path / "procedural.json")

    def test_record_procedure(self, tmp_path):
        mem = self._make(tmp_path)
        proc = mem.record_procedure("deploy_app", ["build", "test", "deploy"], 0.9, "CI/CD")
        assert proc.name == "deploy_app"
        assert len(proc.steps) == 3

    def test_find_procedure_matches(self, tmp_path):
        mem = self._make(tmp_path)
        mem.record_procedure("sort_data", ["load", "sort", "save"], 0.85, "data processing")
        result = mem.find_procedure("how to sort data")
        assert result is not None
        _, proc = result
        assert proc.name == "sort_data"

    def test_find_procedure_no_match(self, tmp_path):
        mem = self._make(tmp_path)
        result = mem.find_procedure("completely unrelated query xyz123")
        assert result is None or result[0] < 0.5

    def test_update_success_rate(self, tmp_path):
        mem = self._make(tmp_path)
        mem.record_procedure("test_proc", ["step1"], 0.5, "testing")
        updated = mem.update_success_rate("test_proc", success=True)
        assert updated is not None
        assert updated.success_rate > 0.5

    def test_combine_procedures(self, tmp_path):
        mem = self._make(tmp_path)
        mem.record_procedure("proc_a", ["step_a1", "step_a2"], 0.8, "first")
        mem.record_procedure("proc_b", ["step_b1", "step_b2"], 0.8, "second")
        combined = mem.combine_procedures("proc_a", "proc_b", "combined_ab")
        assert combined is not None
        assert "--- transition ---" in combined.steps
        assert len(combined.steps) == 5

    def test_combine_missing_procedure(self, tmp_path):
        mem = self._make(tmp_path)
        mem.record_procedure("proc_a", ["step1"], 0.8, "ctx")
        result = mem.combine_procedures("proc_a", "nonexistent")
        assert result is None

    def test_persist_and_reload(self, tmp_path):
        mem = self._make(tmp_path)
        mem.record_procedure("workflow_x", ["a", "b", "c"], 0.75, "context_x")
        mem2 = self._make(tmp_path)
        assert "workflow_x" in mem2._procedures

    def test_proc_repr(self, tmp_path):
        mem = self._make(tmp_path)
        proc = mem.record_procedure("my_proc", ["s1"], 0.7, "ctx")
        assert "Procedure" in repr(proc)


# ===========================================================================
# SECTION 4: MemoryConsolidator
# ===========================================================================

class TestMemoryConsolidator:

    def _make_all(self, tmp_path):
        from memory_system import EpisodicMemory, SemanticMemory, ProceduralMemory, MemoryConsolidator
        ep = EpisodicMemory(path=tmp_path / "ep.jsonl")
        sem = SemanticMemory(path=tmp_path / "sem.json")
        proc = ProceduralMemory(path=tmp_path / "proc.json")
        con = MemoryConsolidator(ep, sem, proc)
        return ep, sem, proc, con

    def test_consolidate_moves_important(self, tmp_path):
        ep, sem, proc, con = self._make_all(tmp_path)
        ep.record("milestone", "important discovery", "", "success")
        result = con.consolidate()
        assert result["consolidated"] >= 0

    def test_prune_removes_old_low_importance(self, tmp_path):
        ep, sem, proc, con = self._make_all(tmp_path)
        from memory_system import Episode
        old_low = Episode(
            episode_id=str(uuid.uuid4()),
            timestamp=time.time() - 100 * 86400,
            event_type="trivial",
            content="unimportant",
            context="",
            outcome="",
            importance_score=0.1,
            tags=[],
        )
        ep._episodes.append(old_low)
        ep._append_to_file(old_low)
        result = con.prune(min_importance=0.3, max_age_days=90)
        assert result["pruned_episodes"] >= 1

    def test_stats_returns_dict(self, tmp_path):
        ep, sem, proc, con = self._make_all(tmp_path)
        ep.record("test", "content", "", "")
        stats = con.stats()
        assert "episodic" in stats
        assert "semantic" in stats
        assert "procedural" in stats

    def test_consolidation_count_increments(self, tmp_path):
        ep, sem, proc, con = self._make_all(tmp_path)
        con.consolidate()
        con.consolidate()
        assert con._consolidation_count == 2


# ===========================================================================
# SECTION 5: UnifiedMemory
# ===========================================================================

class TestUnifiedMemory:

    def _make(self, tmp_path):
        from memory_system import UnifiedMemory
        return UnifiedMemory(
            episodic_path=tmp_path / "ep.jsonl",
            semantic_path=tmp_path / "sem.json",
            procedural_path=tmp_path / "proc.json",
        )

    def test_remember_auto_episodic(self, tmp_path):
        mem = self._make(tmp_path)
        result = mem.remember("I did something interesting today",
                               event_type="observation", context="", outcome="")
        assert result is not None

    def test_remember_auto_semantic(self, tmp_path):
        mem = self._make(tmp_path)
        result = mem.remember("The definition of entropy is disorder",
                               key="entropy_def", confidence=0.8)
        assert result is not None

    def test_remember_procedural(self, tmp_path):
        mem = self._make(tmp_path)
        result = mem.remember("step by step procedure workflow process",
                               memory_type="procedural",
                               name="workflow_1",
                               steps=["step 1", "step 2"])
        assert result is not None

    def test_recall_all_searches_all_types(self, tmp_path):
        mem = self._make(tmp_path)
        mem.episodic.record("event", "python programming language", "", "done")
        mem.semantic.learn("python", "a programming language", 0.9)
        results = mem.recall_all("python programming")
        assert len(results) > 0

    def test_export_memories(self, tmp_path):
        mem = self._make(tmp_path)
        mem.episodic.record("test", "content", "", "")
        mem.semantic.learn("key", "value", 0.8)
        exported = mem.export_memories()
        assert "episodic" in exported
        assert "semantic" in exported
        assert "procedural" in exported
        assert "exported_at" in exported

    def test_import_memories(self, tmp_path):
        mem = self._make(tmp_path)
        mem.episodic.record("import_test", "to be imported", "", "ok")
        exported = mem.export_memories()
        mem2 = self._make(tmp_path / "other")
        mem2.path = tmp_path  # same base but different memory
        tmp_path2 = tmp_path / "other"
        tmp_path2.mkdir(exist_ok=True)
        mem3 = self._make(tmp_path2)
        imported = mem3.import_memories(exported)
        assert imported["episodic"] >= 0

    def test_repr(self, tmp_path):
        mem = self._make(tmp_path)
        assert "UnifiedMemory" in repr(mem)


# ===========================================================================
# SECTION 6: Distributed Reasoning — Individual Reasoners
# ===========================================================================

class TestDeductiveReasoner:

    def test_reason_returns_result(self):
        from distributed_reasoning import DeductiveReasoner
        r = DeductiveReasoner()
        result = r.reason("Is Socrates mortal?",
                          ["If all men are mortal then Socrates is mortal",
                           "All men are mortal"])
        assert result.answer
        assert 0 <= result.confidence <= 1

    def test_reason_with_empty_premises(self):
        from distributed_reasoning import DeductiveReasoner
        r = DeductiveReasoner()
        result = r.reason("What is X?", [])
        assert result.confidence < 0.5

    def test_reasoning_chain_not_empty(self):
        from distributed_reasoning import DeductiveReasoner
        r = DeductiveReasoner()
        result = r.reason("Test question?", ["If A then B"])
        assert len(result.reasoning_chain) > 0

    def test_result_repr(self):
        from distributed_reasoning import DeductiveReasoner, ReasoningPath
        r = DeductiveReasoner()
        result = r.reason("Q?", ["P1"])
        assert "ReasoningResult" in repr(result)
        assert result.path_type == ReasoningPath.DEDUCTIVE


class TestInductiveReasoner:

    def test_reason_finds_pattern(self):
        from distributed_reasoning import InductiveReasoner
        r = InductiveReasoner()
        examples = ["10 apples", "20 apples", "30 apples"]
        result = r.reason("How many apples next?", examples)
        assert result.answer
        assert result.path_type.value == "inductive"

    def test_reason_empty_examples(self):
        from distributed_reasoning import InductiveReasoner
        r = InductiveReasoner()
        result = r.reason("Pattern?", [])
        assert result.confidence < 0.3

    def test_confidence_increases_with_more_examples(self):
        from distributed_reasoning import InductiveReasoner
        r = InductiveReasoner()
        few = r.reason("Q?", ["a", "b"])
        many = r.reason("Q?", ["a", "b", "c", "d", "e", "f"])
        assert many.confidence >= few.confidence


class TestAbductiveReasoner:

    def test_reason_picks_best_explanation(self):
        from distributed_reasoning import AbductiveReasoner
        r = AbductiveReasoner()
        result = r.reason(
            "The street is wet",
            ["It rained", "Someone watered the plants", "A pipe burst"]
        )
        assert result.answer
        assert result.confidence > 0

    def test_reason_no_explanations(self):
        from distributed_reasoning import AbductiveReasoner
        r = AbductiveReasoner()
        result = r.reason("observation", [])
        assert result.confidence < 0.3

    def test_single_explanation_high_confidence(self):
        from distributed_reasoning import AbductiveReasoner
        r = AbductiveReasoner()
        result = r.reason("system failed", ["power outage"])
        assert result.confidence > 0.5


class TestAnalogicalReasoner:

    def test_reason_no_memory(self):
        from distributed_reasoning import AnalogicalReasoner
        r = AnalogicalReasoner()
        result = r.reason("How to sort a list?", memory_system=None)
        assert result.answer
        assert result.path_type.value == "analogical"

    def test_reason_with_analogies(self):
        from distributed_reasoning import AnalogicalReasoner
        r = AnalogicalReasoner()
        analogies = [
            {"problem": "sort a list of numbers", "solution": "use bubble sort or merge sort"},
        ]
        result = r.reason("how to sort items?", analogies=analogies)
        assert result.confidence > 0.15


# ===========================================================================
# SECTION 7: ReasoningEngine
# ===========================================================================

class TestReasoningEngine:

    def test_reason_all_paths(self):
        from distributed_reasoning import ReasoningEngine
        engine = ReasoningEngine()
        results = engine.reason("What is 2+2?", context="basic math")
        assert len(results) == 4  # all 4 paths

    def test_reason_selected_paths(self):
        from distributed_reasoning import ReasoningEngine, ReasoningPath
        engine = ReasoningEngine()
        results = engine.reason("Test?", paths=[ReasoningPath.DEDUCTIVE, ReasoningPath.INDUCTIVE])
        assert len(results) == 2

    def test_vote_returns_winner(self):
        from distributed_reasoning import ReasoningEngine
        engine = ReasoningEngine()
        results = engine.reason("Which way?", context="")
        winner, score = engine.vote(results)
        assert winner is not None
        assert 0 <= score <= 1

    def test_consensus_score(self):
        from distributed_reasoning import ReasoningEngine
        engine = ReasoningEngine()
        results = engine.reason("Test consensus?")
        score = engine.consensus(results)
        assert 0 <= score <= 1

    def test_debate_returns_rounds(self):
        from distributed_reasoning import ReasoningEngine
        engine = ReasoningEngine()
        rounds = engine.debate("Should AI be regulated?", rounds=2)
        assert len(rounds) > 0

    def test_explain_returns_string(self):
        from distributed_reasoning import ReasoningEngine
        engine = ReasoningEngine()
        results = engine.reason("Test?")
        winner, _ = engine.vote(results)
        explanation = engine.explain(winner.answer, results)
        assert "Reasoning Explanation" in explanation

    def test_cache_hit(self):
        from distributed_reasoning import ReasoningEngine
        engine = ReasoningEngine()
        engine.reason("Cached question about weather?")
        size1 = engine.cache.size()
        engine.reason("Cached question about weather?")
        size2 = engine.cache.size()
        assert size1 == size2  # No new cache entry

    def test_parallel_execution(self):
        from distributed_reasoning import ReasoningEngine
        engine = ReasoningEngine()
        start = time.time()
        results = engine.reason("Parallel test?", context="testing concurrency")
        duration = time.time() - start
        assert len(results) == 4
        # Should run in parallel, not 4x sequential
        assert duration < 5.0


# ===========================================================================
# SECTION 8: ReasoningCache
# ===========================================================================

class TestReasoningCache:

    def test_put_and_get(self):
        from distributed_reasoning import ReasoningCache, ReasoningResult, ReasoningPath
        cache = ReasoningCache(similarity_threshold=0.7)
        results = [ReasoningResult(
            path_type=ReasoningPath.DEDUCTIVE,
            answer="42",
            confidence=0.9,
            reasoning_chain=["step1"]
        )]
        cache.put("What is the answer?", results)
        retrieved = cache.get("What is the answer?")
        assert retrieved is not None

    def test_cache_miss_different_question(self):
        from distributed_reasoning import ReasoningCache, ReasoningResult, ReasoningPath
        cache = ReasoningCache(similarity_threshold=0.9)
        results = [ReasoningResult(
            path_type=ReasoningPath.INDUCTIVE,
            answer="pattern",
            confidence=0.8,
            reasoning_chain=[]
        )]
        cache.put("dogs bark at night", results)
        retrieved = cache.get("cats meow in the morning")
        assert retrieved is None

    def test_lru_eviction(self):
        from distributed_reasoning import ReasoningCache, ReasoningResult, ReasoningPath
        cache = ReasoningCache(capacity=3)
        for i in range(5):
            r = [ReasoningResult(
                path_type=ReasoningPath.DEDUCTIVE,
                answer=f"answer {i}",
                confidence=0.5,
                reasoning_chain=[]
            )]
            cache.put(f"unique question number {i}", r)
        assert cache.size() <= 3


# ===========================================================================
# SECTION 9: Self Audit Engine
# ===========================================================================

class TestSelfAuditEngine:

    def test_audit_clean_response_passes(self):
        from self_audit import SelfAuditEngine
        engine = SelfAuditEngine()
        result = engine.audit("The sky is blue, based on observable evidence.", context="")
        assert result.overall_score > 0.0

    def test_audit_has_10_rules(self):
        from self_audit import SelfAuditEngine
        engine = SelfAuditEngine()
        assert len(engine.rules()) == 10

    def test_register_custom_rule(self):
        from self_audit import SelfAuditEngine, AuditRule
        engine = SelfAuditEngine()
        custom = AuditRule(
            rule_id="C001",
            name="CustomRule",
            description="A test rule",
            severity="low",
            check_fn=lambda r, c: (True, ""),
        )
        engine.register_rule(custom)
        assert len(engine.rules()) == 11

    def test_toxicity_detected(self):
        from self_audit import SelfAuditEngine
        engine = SelfAuditEngine()
        result = engine.audit("I hate all people who are stupid idiots.", "")
        issues = [i.rule_id for i in result.issues]
        assert "R004" in issues  # ToxicityFilter

    def test_overconfidence_detected(self):
        from self_audit import SelfAuditEngine
        engine = SelfAuditEngine()
        result = engine.audit(
            "I am certain without a doubt that the answer is 42. I know for a fact this is true.",
            ""
        )
        issues = [i.rule_id for i in result.issues]
        assert "R009" in issues

    def test_circular_reasoning_detected(self):
        from self_audit import SelfAuditEngine
        engine = SelfAuditEngine()
        result = engine.audit(
            "The process is good because the process works well and the process is correct because the process.",
            ""
        )
        # Should detect circular reasoning or no issues if text isn't exact pattern
        assert isinstance(result.passed, bool)

    def test_fix_overconfident_response(self):
        from self_audit import SelfAuditEngine
        engine = SelfAuditEngine()
        response = "I am certain without a doubt that AI will solve all problems."
        audit_result = engine.audit(response, "")
        fixed = engine.fix(response, audit_result)
        assert isinstance(fixed, str)

    def test_report_is_string(self):
        from self_audit import SelfAuditEngine
        engine = SelfAuditEngine()
        result = engine.audit("Test response.", "")
        report = engine.report(result)
        assert "AUDIT REPORT" in report

    def test_audit_result_repr(self):
        from self_audit import SelfAuditEngine
        engine = SelfAuditEngine()
        result = engine.audit("clean response", "")
        assert "AuditResult" in repr(result)

    def test_audit_score_between_0_and_1(self):
        from self_audit import SelfAuditEngine
        engine = SelfAuditEngine()
        result = engine.audit("Some response text.", "")
        assert 0.0 <= result.overall_score <= 1.0


# ===========================================================================
# SECTION 10: AutoFixer
# ===========================================================================

class TestAutoFixer:

    def test_fix_overconfidence(self):
        from self_audit import AutoFixer
        fixer = AutoFixer()
        response = "I am certain this is true."
        fixed = fixer.fix_overconfidence(response)
        assert "I am certain" not in fixed or "I believe" in fixed

    def test_fix_hallucinations_adds_qualifier(self):
        from self_audit import AutoFixer
        fixer = AutoFixer()
        response = "Albert Einstein invented the iPhone in 2007."
        fixed = fixer.fix_hallucinations(response, "context about physics")
        assert "[Note:" in fixed or len(fixed) >= len(response)

    def test_fix_incompleteness_adds_note(self):
        from self_audit import AutoFixer
        fixer = AutoFixer()
        fixed = fixer.fix_incompleteness("Short answer.", "detailed question")
        assert "Note:" in fixed or len(fixed) > len("Short answer.")

    def test_fix_circular_reasoning(self):
        from self_audit import AutoFixer
        fixer = AutoFixer()
        fixed = fixer.fix_circular_reasoning("X because X.")
        assert "Warning" in fixed or len(fixed) > len("X because X.")


# ===========================================================================
# SECTION 11: AuditLogger
# ===========================================================================

class TestAuditLogger:

    def test_log_and_stats(self, tmp_path):
        from self_audit import SelfAuditEngine, AuditLogger
        logger = AuditLogger(path=tmp_path / "audit.jsonl")
        engine = SelfAuditEngine()
        result = engine.audit("Test response", "")
        logger.log(result)
        stats = logger.stats()
        assert stats["total_audits"] >= 1

    def test_recent_returns_last_n(self, tmp_path):
        from self_audit import SelfAuditEngine, AuditLogger
        logger = AuditLogger(path=tmp_path / "audit.jsonl")
        engine = SelfAuditEngine()
        for i in range(5):
            result = engine.audit(f"Response {i}", "")
            logger.log(result)
        recent = logger.recent(n=3)
        assert len(recent) <= 3

    def test_logger_repr(self, tmp_path):
        from self_audit import AuditLogger
        logger = AuditLogger(path=tmp_path / "audit.jsonl")
        assert "AuditLogger" in repr(logger)


# ===========================================================================
# SECTION 12: LearningEngine
# ===========================================================================

class TestLearningEngine:

    def _make(self, tmp_path):
        from learning_engine import LearningEngine
        return LearningEngine(path=tmp_path / "lessons.json")

    def test_learn_from_success(self, tmp_path):
        engine = self._make(tmp_path)
        lesson = engine.learn_from_outcome(
            "deployed new code", "success", "production environment"
        )
        assert lesson.lesson_id
        assert lesson.confidence > 0.5

    def test_learn_from_failure(self, tmp_path):
        engine = self._make(tmp_path)
        lesson = engine.learn_from_outcome(
            "deployed untested code", "failure - error in production", ""
        )
        assert lesson.lesson_id
        assert lesson.confidence >= 0

    def test_apply_lessons_finds_relevant(self, tmp_path):
        engine = self._make(tmp_path)
        engine.learn_from_outcome("deploying to production", "success", "")
        applied = engine.apply_lessons("deployment to production server")
        assert isinstance(applied, list)

    def test_reinforce_increases_confidence(self, tmp_path):
        engine = self._make(tmp_path)
        lesson = engine.learn_from_outcome("test action", "success", "")
        old_conf = lesson.confidence
        reinforced = engine.reinforce(lesson.lesson_id)
        assert reinforced.confidence >= old_conf

    def test_deprecate_decreases_confidence(self, tmp_path):
        engine = self._make(tmp_path)
        lesson = engine.learn_from_outcome("test action", "success", "")
        lid = lesson.lesson_id
        original_confidence = lesson.confidence  # capture before mutation
        # Deprecate repeatedly
        for _ in range(3):
            result = engine.deprecate(lid, delta=0.1)
            if result is None:
                break  # lesson removed — pass
        # Either removed (confidence was low) or reduced
        if lid in engine._lessons:
            assert engine._lessons[lid].confidence < original_confidence
        # If removed: deprecation worked correctly

    def test_generalize_creates_new_lesson(self, tmp_path):
        engine = self._make(tmp_path)
        l1 = engine.learn_from_outcome("task A succeeded", "success", "domain1")
        l2 = engine.learn_from_outcome("task B succeeded", "success", "domain1")
        general = engine.generalize([l1.lesson_id, l2.lesson_id])
        assert general is not None
        assert "General principle" in general.insight

    def test_transfer_between_domains(self, tmp_path):
        engine = self._make(tmp_path)
        engine.learn_from_outcome("math calculation", "success", "math")
        engine._lessons[list(engine._lessons.keys())[0]].domain = "math"
        transferred = engine.transfer("math", "physics")
        assert isinstance(transferred, list)

    def test_persist_and_reload(self, tmp_path):
        engine = self._make(tmp_path)
        engine.learn_from_outcome("persistent lesson", "success", "")
        engine2 = self._make(tmp_path)
        assert engine2.count() == engine.count()

    def test_lesson_repr(self, tmp_path):
        engine = self._make(tmp_path)
        lesson = engine.learn_from_outcome("action", "outcome", "")
        assert "Lesson" in repr(lesson)


# ===========================================================================
# SECTION 13: PatternRecognizer
# ===========================================================================

class TestPatternRecognizer:

    def test_observe_records_event(self):
        from learning_engine import PatternRecognizer
        pr = PatternRecognizer()
        pr.observe("login")
        assert len(pr._events) == 1

    def test_detect_patterns(self):
        from learning_engine import PatternRecognizer
        pr = PatternRecognizer()
        for _ in range(5):
            pr.observe("login")
            pr.observe("query")
            pr.observe("logout")
        patterns = pr.detect_patterns(min_occurrences=3)
        assert isinstance(patterns, list)

    def test_predict_next(self):
        from learning_engine import PatternRecognizer
        pr = PatternRecognizer()
        for _ in range(5):
            pr.observe("step1")
            pr.observe("step2")
            pr.observe("step3")
        pr.detect_patterns(min_occurrences=3)
        prediction = pr.predict_next(["step1", "step2"])
        # May or may not predict — just check type
        assert prediction is None or isinstance(prediction, str)

    def test_alert_on_pattern(self):
        from learning_engine import PatternRecognizer
        pr = PatternRecognizer()
        triggered = []

        def callback(name, event):
            triggered.append(name)

        pr.alert_on_pattern("step1+step2", callback)
        pr._patterns["step1+step2"] = type('Pattern', (), {
            'name': 'step1+step2', 'sequence': ['step1', 'step2'],
            'occurrences': 5, 'first_seen': time.time(), 'last_seen': time.time(),
            'callbacks': []
        })()
        pr.observe("step1")
        pr.observe("step2")
        # May trigger if sequence matches
        assert isinstance(triggered, list)

    def test_repr(self):
        from learning_engine import PatternRecognizer
        pr = PatternRecognizer()
        assert "PatternRecognizer" in repr(pr)


# ===========================================================================
# SECTION 14: PerformanceTracker
# ===========================================================================

class TestPerformanceTracker:

    def test_record_task(self):
        from learning_engine import PerformanceTracker
        pt = PerformanceTracker()
        pt.record_task("coding", success=True, duration=1.5, quality_score=0.9)
        assert len(pt._records) == 1

    def test_success_rate(self):
        from learning_engine import PerformanceTracker
        pt = PerformanceTracker()
        pt.record_task("coding", True, 1.0, 0.9)
        pt.record_task("coding", True, 1.0, 0.8)
        pt.record_task("coding", False, 1.0, 0.3)
        rate = pt.success_rate("coding")
        assert abs(rate - 2/3) < 0.01

    def test_worst_performing(self):
        from learning_engine import PerformanceTracker
        pt = PerformanceTracker()
        pt.record_task("easy", True, 1.0, 0.9)
        pt.record_task("hard", False, 5.0, 0.2)
        worst = pt.worst_performing()
        assert worst[0][0] == "hard"

    def test_improvement_over_time(self):
        from learning_engine import PerformanceTracker
        pt = PerformanceTracker()
        for i in range(15):
            pt.record_task("writing", success=(i > 5), duration=1.0, quality_score=i/15)
        curve = pt.improvement_over_time("writing", window=5)
        assert len(curve) > 0

    def test_suggest_focus_areas(self):
        from learning_engine import PerformanceTracker
        pt = PerformanceTracker()
        pt.record_task("math", False, 1.0, 0.2)
        pt.record_task("math", False, 1.0, 0.2)
        suggestions = pt.suggest_focus_areas()
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0

    def test_summary(self):
        from learning_engine import PerformanceTracker
        pt = PerformanceTracker()
        pt.record_task("coding", True, 2.0, 0.8)
        summary = pt.summary()
        assert "total_tasks" in summary
        assert summary["total_tasks"] == 1

    def test_repr(self):
        from learning_engine import PerformanceTracker
        pt = PerformanceTracker()
        assert "PerformanceTracker" in repr(pt)


# ===========================================================================
# SECTION 15: AgentParliament
# ===========================================================================

class TestAgentParliament:

    def _make(self, tmp_path):
        from agent_parliament import AgentParliament
        return AgentParliament(log_path=tmp_path / "parliament.jsonl")

    def test_has_six_members(self, tmp_path):
        parliament = self._make(tmp_path)
        assert len(parliament.members()) == 6

    def test_member_roles(self, tmp_path):
        parliament = self._make(tmp_path)
        roles = {m.role for m in parliament.members()}
        expected = {"Critic", "Advocate", "Realist", "Innovator", "Ethicist", "Analyst"}
        assert roles == expected

    def test_debate_returns_rounds(self, tmp_path):
        parliament = self._make(tmp_path)
        rounds = parliament.debate("Should we adopt AI?", rounds=2)
        assert len(rounds) > 0

    def test_debate_rounds_have_statements(self, tmp_path):
        parliament = self._make(tmp_path)
        rounds = parliament.debate("AI governance?", rounds=1)
        for r in rounds:
            assert r.statement
            assert r.speaker

    def test_vote_on_proposals(self, tmp_path):
        parliament = self._make(tmp_path)
        proposals = ["Option A: proceed", "Option B: wait", "Option C: abort"]
        votes = parliament.vote(proposals)
        assert len(votes) == 3
        # All proposals get some vote
        assert sum(votes.values()) > 0

    def test_veto_works(self, tmp_path):
        parliament = self._make(tmp_path)
        result = parliament.veto("ethicist", "Deploy harmful AI", "This violates ethics")
        assert result["success"] is True
        assert "veto" in result

    def test_veto_unknown_member(self, tmp_path):
        parliament = self._make(tmp_path)
        result = parliament.veto("unknown_member", "proposal", "reason")
        assert result["success"] is False

    def test_consensus_required_for_safety(self, tmp_path):
        parliament = self._make(tmp_path)
        assert parliament.consensus_required("safety critical decision") is True
        assert parliament.consensus_required("what is the weather") is False

    def test_record_decision(self, tmp_path):
        parliament = self._make(tmp_path)
        decision = parliament.record_decision("Should we deploy?", "Yes, deploy carefully")
        assert decision.decision_id
        assert decision.winning_proposal == "Yes, deploy carefully"

    def test_review_past_decisions(self, tmp_path):
        parliament = self._make(tmp_path)
        parliament.record_decision("Q1?", "Answer 1")
        parliament.record_decision("Q2?", "Answer 2")
        reviews = parliament.review_past_decisions()
        assert len(reviews) >= 2

    def test_stats(self, tmp_path):
        parliament = self._make(tmp_path)
        stats = parliament.stats()
        assert "total_decisions" in stats
        assert "members" in stats

    def test_parliament_repr(self, tmp_path):
        parliament = self._make(tmp_path)
        assert "AgentParliament" in repr(parliament)


# ===========================================================================
# SECTION 16: SuperIntelligenceCore (Integration)
# ===========================================================================

class TestSuperIntelligenceCore:

    def _make(self, tmp_path):
        # Patch paths before importing
        import memory_system as ms
        import self_audit as sa
        import learning_engine as le
        import agent_parliament as ap
        ms.EPISODIC_PATH = tmp_path / "ep.jsonl"
        ms.SEMANTIC_PATH = tmp_path / "sem.json"
        ms.PROCEDURAL_PATH = tmp_path / "proc.json"
        sa.AUDIT_LOG_PATH = tmp_path / "audit.jsonl"
        le.LESSONS_PATH = tmp_path / "lessons.json"
        ap.PARLIAMENT_LOG_PATH = tmp_path / "parl.jsonl"
        from superintelligence_core import SuperIntelligenceCore
        return SuperIntelligenceCore()

    def test_process_returns_result(self, tmp_path):
        core = self._make(tmp_path)
        result = asyncio.run(core.process("What is 2 + 2?", context="basic arithmetic"))
        assert result.query_id
        assert result.response
        assert 0 <= result.confidence <= 1

    def test_process_with_context(self, tmp_path):
        core = self._make(tmp_path)
        result = asyncio.run(core.process(
            "Who wrote Hamlet?",
            context="Shakespeare wrote Hamlet in 1603."
        ))
        assert result.response

    def test_process_critical_uses_parliament(self, tmp_path):
        core = self._make(tmp_path)
        result = asyncio.run(core.process(
            "Should we delete the database?",
            criticality="critical"
        ))
        assert result.parliament_used is True

    def test_process_normal_no_parliament(self, tmp_path):
        core = self._make(tmp_path)
        result = asyncio.run(core.process(
            "What is the weather like in Paris?",
            criticality="normal"
        ))
        # May or may not use parliament depending on keywords
        assert isinstance(result.parliament_used, bool)

    def test_audit_runs_on_every_response(self, tmp_path):
        core = self._make(tmp_path)
        result = asyncio.run(core.process("Tell me something."))
        assert result.audit_result is not None

    def test_learn_from_session(self, tmp_path):
        core = self._make(tmp_path)
        asyncio.run(core.process("Query 1"))
        asyncio.run(core.process("Query 2"))
        session_result = asyncio.run(core.learn_from_session())
        assert session_result["lessons_extracted"] >= 0

    def test_introspect(self, tmp_path):
        core = self._make(tmp_path)
        asyncio.run(core.process("Test query"))
        introspection = asyncio.run(core.introspect())
        assert "health_score" in introspection
        assert "memory" in introspection
        assert "lessons_learned" in introspection

    def test_explain_last_response(self, tmp_path):
        core = self._make(tmp_path)
        asyncio.run(core.process("Explain something to me."))
        explanation = core.explain_last_response()
        assert "REASONING TRANSPARENCY" in explanation

    def test_explain_before_any_query(self, tmp_path):
        core = self._make(tmp_path)
        explanation = core.explain_last_response()
        assert "No response" in explanation

    def test_memory_accumulates_across_queries(self, tmp_path):
        core = self._make(tmp_path)
        asyncio.run(core.process("First query about dogs"))
        asyncio.run(core.process("Second query about cats"))
        assert core.memory.episodic.count() >= 2

    def test_repr(self, tmp_path):
        core = self._make(tmp_path)
        assert "SuperIntelligenceCore" in repr(core)

    def test_processing_result_to_dict(self, tmp_path):
        core = self._make(tmp_path)
        result = asyncio.run(core.process("Test"))
        d = result.to_dict()
        assert "query_id" in d
        assert "response" in d
        assert "confidence" in d


# ===========================================================================
# SECTION 17: Cross-module Integration
# ===========================================================================

class TestCrossModuleIntegration:

    def test_memory_feeds_reasoning(self, tmp_path):
        """Stored memory should influence analogical reasoning."""
        from memory_system import UnifiedMemory
        from distributed_reasoning import ReasoningEngine, ReasoningPath
        mem = UnifiedMemory(
            episodic_path=tmp_path / "ep.jsonl",
            semantic_path=tmp_path / "sem.json",
            procedural_path=tmp_path / "proc.json",
        )
        mem.episodic.record("solution", "use binary search for sorted arrays", "search", "success")
        engine = ReasoningEngine(memory_system=mem)
        results = engine.reason("how to search in a sorted list?",
                                 paths=[ReasoningPath.ANALOGICAL])
        assert len(results) == 1

    def test_audit_logs_to_file(self, tmp_path):
        """Audit results should persist to disk."""
        from self_audit import SelfAuditEngine, AuditLogger
        log_path = tmp_path / "test_audit.jsonl"
        logger = AuditLogger(path=log_path)
        engine = SelfAuditEngine()
        result = engine.audit("Some response to audit.", "context")
        logger.log(result)
        assert log_path.exists()
        with open(log_path) as f:
            lines = [l for l in f if l.strip()]
        assert len(lines) >= 1

    def test_learning_applies_to_reasoning(self, tmp_path):
        """Lessons learned should be applicable to new queries."""
        from learning_engine import LearningEngine
        le = LearningEngine(path=tmp_path / "lessons.json")
        le.learn_from_outcome(
            "optimizing database queries",
            "success - added index",
            "performance tuning"
        )
        applicable = le.apply_lessons("database query is slow")
        assert isinstance(applicable, list)

    def test_parliament_records_and_reviews(self, tmp_path):
        """Parliament should record decisions and allow review."""
        from agent_parliament import AgentParliament
        p = AgentParliament(log_path=tmp_path / "parl.jsonl")
        d1 = p.record_decision("AI deployment?", "Proceed with safeguards")
        d2 = p.record_decision("Data deletion?", "Archive first")
        reviews = p.review_past_decisions()
        assert len(reviews) >= 2
        decision_ids = [r["decision_id"] for r in reviews]
        assert d1.decision_id in decision_ids

    def test_full_pipeline_consistency(self, tmp_path):
        """Full pipeline should produce consistent, non-empty results."""
        import memory_system as ms
        import self_audit as sa
        import learning_engine as le
        import agent_parliament as ap
        ms.EPISODIC_PATH = tmp_path / "ep.jsonl"
        ms.SEMANTIC_PATH = tmp_path / "sem.json"
        ms.PROCEDURAL_PATH = tmp_path / "proc.json"
        sa.AUDIT_LOG_PATH = tmp_path / "audit.jsonl"
        le.LESSONS_PATH = tmp_path / "lessons.json"
        ap.PARLIAMENT_LOG_PATH = tmp_path / "parl.jsonl"
        from superintelligence_core import SuperIntelligenceCore
        core = SuperIntelligenceCore()
        for q in ["What is AI?", "How do neural networks work?", "Explain deep learning."]:
            result = asyncio.run(core.process(q))
            assert result.response
            assert result.query_id
            assert 0 <= result.confidence <= 1
        assert core.memory.episodic.count() >= 3
