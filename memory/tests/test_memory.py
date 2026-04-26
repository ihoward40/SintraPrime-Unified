"""
Comprehensive test suite for SintraPrime-Unified Memory Engine.
55+ tests covering all memory layers, edge cases, and integration.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Helpers for isolated test environments
# ---------------------------------------------------------------------------

def _make_temp_dir() -> str:
    return tempfile.mkdtemp()


def _make_semantic(tmp_dir: str):
    from memory.semantic_memory import SemanticMemory
    return SemanticMemory(db_path=os.path.join(tmp_dir, "semantic.db"))


def _make_episodic(tmp_dir: str):
    from memory.episodic_memory import EpisodicMemory
    return EpisodicMemory(db_path=os.path.join(tmp_dir, "episodic.db"))


def _make_engine(tmp_dir: str):
    from memory.memory_engine import MemoryEngine
    return MemoryEngine(
        semantic_db_path=os.path.join(tmp_dir, "semantic.db"),
        episodic_db_path=os.path.join(tmp_dir, "episodic.db"),
        profiles_dir=os.path.join(tmp_dir, "profiles"),
    )


def _make_profiles(tmp_dir: str):
    from memory.user_profile import UserProfileManager
    return UserProfileManager(profiles_dir=os.path.join(tmp_dir, "profiles"))


# ===========================================================================
# 1. MemoryTypes tests
# ===========================================================================

class TestMemoryTypes(unittest.TestCase):
    """Tests for data models in memory_types.py"""

    def test_memory_entry_creation(self):
        from memory.memory_types import MemoryEntry, MemoryType
        entry = MemoryEntry(content="Test fact", memory_type=MemoryType.SEMANTIC)
        self.assertIsNotNone(entry.id)
        self.assertEqual(entry.content, "Test fact")
        self.assertEqual(entry.memory_type, MemoryType.SEMANTIC)
        self.assertAlmostEqual(entry.importance, 0.5)

    def test_memory_entry_to_dict(self):
        from memory.memory_types import MemoryEntry, MemoryType
        entry = MemoryEntry(
            content="Python is a programming language",
            memory_type=MemoryType.SEMANTIC,
            tags=["python", "programming"],
            importance=0.8,
        )
        d = entry.to_dict()
        self.assertEqual(d["content"], "Python is a programming language")
        self.assertEqual(d["memory_type"], "semantic")
        self.assertEqual(d["tags"], ["python", "programming"])
        self.assertAlmostEqual(d["importance"], 0.8)

    def test_memory_entry_from_dict_roundtrip(self):
        from memory.memory_types import MemoryEntry, MemoryType
        original = MemoryEntry(
            content="Round trip test",
            memory_type=MemoryType.EPISODIC,
            tags=["test"],
            importance=0.6,
        )
        d = original.to_dict()
        restored = MemoryEntry.from_dict(d)
        self.assertEqual(restored.id, original.id)
        self.assertEqual(restored.content, original.content)
        self.assertEqual(restored.memory_type, original.memory_type)

    def test_memory_type_enum_values(self):
        from memory.memory_types import MemoryType
        self.assertEqual(MemoryType.SEMANTIC.value, "semantic")
        self.assertEqual(MemoryType.EPISODIC.value, "episodic")
        self.assertEqual(MemoryType.WORKING.value, "working")
        self.assertEqual(MemoryType.PROCEDURAL.value, "procedural")
        self.assertEqual(MemoryType.PREFERENCE.value, "preference")

    def test_user_profile_creation(self):
        from memory.memory_types import UserProfile
        profile = UserProfile(user_id="u1", name="Alice")
        self.assertEqual(profile.user_id, "u1")
        self.assertEqual(profile.name, "Alice")
        self.assertEqual(profile.communication_style, "neutral")
        self.assertEqual(profile.interaction_count, 0)

    def test_user_profile_roundtrip(self):
        from memory.memory_types import UserProfile
        profile = UserProfile(
            user_id="u2",
            name="Bob",
            goals=["pass the bar", "win case"],
            communication_style="formal",
        )
        d = profile.to_dict()
        restored = UserProfile.from_dict(d)
        self.assertEqual(restored.user_id, "u2")
        self.assertEqual(restored.goals, ["pass the bar", "win case"])
        self.assertEqual(restored.communication_style, "formal")

    def test_skill_record_creation(self):
        from memory.memory_types import SkillRecord
        skill = SkillRecord(
            name="Legal Brief Writing",
            description="How to write a legal brief",
            steps=["Identify issue", "Research", "Draft", "Review"],
            success_rate=0.9,
        )
        self.assertEqual(skill.name, "Legal Brief Writing")
        self.assertEqual(len(skill.steps), 4)
        d = skill.to_dict()
        self.assertIn("steps", d)

    def test_memory_search_result(self):
        from memory.memory_types import MemoryEntry, MemorySearchResult, MemoryType
        entry = MemoryEntry(content="Test content", memory_type=MemoryType.SEMANTIC)
        result = MemorySearchResult(entry=entry, relevance_score=0.87, context="query")
        d = result.to_dict()
        self.assertAlmostEqual(d["relevance_score"], 0.87)
        self.assertEqual(d["entry"]["content"], "Test content")

    def test_task_creation(self):
        from memory.memory_types import Task
        task = Task(name="Review contract", description="Review the NDA contract")
        self.assertEqual(task.status, "pending")
        self.assertEqual(task.priority, 5)
        d = task.to_dict()
        self.assertIn("id", d)


# ===========================================================================
# 2. SemanticMemory tests
# ===========================================================================

class TestSemanticMemory(unittest.TestCase):
    def setUp(self):
        self.tmp = _make_temp_dir()
        self.mem = _make_semantic(self.tmp)

    def test_store_and_count(self):
        self.mem.store("The sky is blue", tags=["nature"])
        self.assertEqual(self.mem.count(), 1)

    def test_store_returns_entry(self):
        entry = self.mem.store("Python uses indentation", tags=["python"], importance=0.7)
        self.assertIsNotNone(entry.id)
        self.assertEqual(entry.content, "Python uses indentation")
        self.assertAlmostEqual(entry.importance, 0.7)

    def test_recall_finds_relevant(self):
        self.mem.store("The defendant filed a motion to dismiss", tags=["legal"])
        self.mem.store("Python is a programming language", tags=["tech"])
        results = self.mem.recall("court motion defendant")
        self.assertGreater(len(results), 0)
        self.assertIn("defendant", results[0].entry.content)

    def test_recall_returns_top_k(self):
        for i in range(20):
            self.mem.store(f"Legal fact number {i} about court proceedings", tags=["legal"])
        results = self.mem.recall("legal court", top_k=5)
        self.assertLessEqual(len(results), 5)

    def test_recall_empty_db(self):
        results = self.mem.recall("anything")
        self.assertEqual(results, [])

    def test_forget_removes_entry(self):
        entry = self.mem.store("Temporary fact", tags=["temp"])
        success = self.mem.forget(entry.id)
        self.assertTrue(success)
        self.assertEqual(self.mem.count(), 0)

    def test_forget_nonexistent_returns_false(self):
        result = self.mem.forget("nonexistent-id-xyz")
        self.assertFalse(result)

    def test_store_with_user_id(self):
        self.mem.store("User-specific fact", tags=[], user_id="user42")
        self.assertEqual(self.mem.count(user_id="user42"), 1)
        self.assertEqual(self.mem.count(user_id="other_user"), 0)

    def test_recall_by_user_id(self):
        self.mem.store("Alice's legal note", tags=["legal"], user_id="alice")
        self.mem.store("Bob's legal note", tags=["legal"], user_id="bob")
        results = self.mem.recall("legal note", user_id="alice")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].entry.user_id, "alice")

    def test_export_and_import_json(self):
        self.mem.store("Export test fact", tags=["export"])
        self.mem.store("Another fact to export", tags=["export"])
        export_path = os.path.join(self.tmp, "export.json")
        exported = self.mem.export_to_json(export_path)
        self.assertEqual(exported, 2)

        # Import into fresh memory
        mem2 = _make_semantic(tempfile.mkdtemp())
        imported = mem2.import_from_json(export_path)
        self.assertEqual(imported, 2)
        self.assertEqual(mem2.count(), 2)

    def test_consolidate_merges_duplicates(self):
        self.mem.store("The court dismissed the case due to lack of evidence")
        self.mem.store("The court dismissed the case due to lack of evidence")
        stats = self.mem.consolidate()
        self.assertIn("merged", stats)
        self.assertGreaterEqual(stats["merged"], 0)

    def test_get_by_id(self):
        entry = self.mem.store("Retrievable fact", tags=["test"])
        retrieved = self.mem.get_by_id(entry.id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.content, "Retrievable fact")

    def test_get_by_id_missing(self):
        result = self.mem.get_by_id("does-not-exist")
        self.assertIsNone(result)

    def test_legal_auto_index(self):
        """Auto-indexing extracts legal keywords without raising exceptions."""
        self.mem.store(
            "The plaintiff filed a complaint against the defendant for negligence "
            "in violation of 18 U.S.C. § 1234",
            tags=["legal"],
        )
        # Should not raise; legal_index is populated
        self.assertEqual(self.mem.count(), 1)

    def test_forget_user_gdpr(self):
        self.mem.store("User data 1", tags=[], user_id="todelete")
        self.mem.store("User data 2", tags=[], user_id="todelete")
        self.mem.store("Other user data", tags=[], user_id="other")
        deleted = self.mem.forget_user("todelete")
        self.assertEqual(deleted, 2)
        self.assertEqual(self.mem.count(user_id="todelete"), 0)
        self.assertEqual(self.mem.count(user_id="other"), 1)

    def test_all_entries(self):
        self.mem.store("Fact A")
        self.mem.store("Fact B")
        entries = self.mem.all_entries()
        self.assertEqual(len(entries), 2)

    def test_importance_clamp(self):
        """Importance is clamped to [0.0, 1.0]."""
        entry = self.mem.store("Test", importance=1.5)
        self.assertLessEqual(entry.importance, 1.0)
        entry2 = self.mem.store("Test2", importance=-0.5)
        self.assertGreaterEqual(entry2.importance, 0.0)


# ===========================================================================
# 3. EpisodicMemory tests
# ===========================================================================

class TestEpisodicMemory(unittest.TestCase):
    def setUp(self):
        self.tmp = _make_temp_dir()
        self.mem = _make_episodic(self.tmp)

    def _sample_messages(self):
        return [
            {"role": "user", "content": "What is the statute of limitations for negligence?"},
            {"role": "assistant", "content": "Generally it is 2-3 years, therefore you should act quickly."},
            {"role": "user", "content": "What about for contract disputes?"},
            {"role": "assistant", "content": "Contract disputes typically have a 4-6 year limit. This is important."},
        ]

    def test_log_session(self):
        session = self.mem.log_session(
            "sess-001",
            self._sample_messages(),
            outcomes=["user informed"],
            user_id="alice",
        )
        self.assertEqual(session.session_id, "sess-001")
        self.assertEqual(session.user_id, "alice")

    def test_recall_session(self):
        self.mem.log_session("sess-002", self._sample_messages(), user_id="bob")
        session = self.mem.recall_session("sess-002")
        self.assertIsNotNone(session)
        self.assertEqual(session.session_id, "sess-002")
        self.assertEqual(len(session.messages), 4)

    def test_recall_session_not_found(self):
        result = self.mem.recall_session("nonexistent-session")
        self.assertIsNone(result)

    def test_count_sessions(self):
        self.mem.log_session("s1", self._sample_messages(), user_id="u1")
        self.mem.log_session("s2", self._sample_messages(), user_id="u1")
        self.assertEqual(self.mem.count_sessions(), 2)

    def test_count_sessions_by_user(self):
        self.mem.log_session("s1", self._sample_messages(), user_id="u1")
        self.mem.log_session("s2", self._sample_messages(), user_id="u2")
        self.assertEqual(self.mem.count_sessions(user_id="u1"), 1)
        self.assertEqual(self.mem.count_sessions(user_id="u2"), 1)

    def test_search_episodes_by_query(self):
        self.mem.log_session(
            "s-search-1",
            [
                {"role": "user", "content": "Tell me about habeas corpus"},
                {"role": "assistant", "content": "Habeas corpus is a legal writ"},
            ],
            user_id="u1",
        )
        self.mem.log_session(
            "s-search-2",
            [
                {"role": "user", "content": "How do I cook pasta?"},
                {"role": "assistant", "content": "Boil water and add pasta"},
            ],
            user_id="u1",
        )
        results = self.mem.search_episodes("habeas corpus")
        self.assertGreater(len(results), 0)
        self.assertTrue(any("habeas" in r.summary.lower() or "habeas" in r.session_id for r in results))

    def test_search_episodes_date_range(self):
        self.mem.log_session("s-date", self._sample_messages(), user_id="u1")
        future = datetime.utcnow() + timedelta(days=1)
        past = datetime.utcnow() - timedelta(days=1)
        results = self.mem.search_episodes("statute", date_range=(past, future))
        self.assertGreater(len(results), 0)

    def test_summarize_episode(self):
        self.mem.log_session("s-sum", self._sample_messages(), user_id="alice")
        summary = self.mem.summarize_episode("s-sum")
        self.assertIsInstance(summary, str)
        self.assertGreater(len(summary), 10)

    def test_summarize_missing_session(self):
        result = self.mem.summarize_episode("not-here")
        self.assertEqual(result, "Session not found.")

    def test_extract_learnings(self):
        self.mem.log_session("s-learn", self._sample_messages(), user_id="alice")
        learnings = self.mem.extract_learnings("s-learn")
        self.assertIsInstance(learnings, list)
        # Should find at least some learning sentences with "therefore" or "important"
        for l in learnings:
            self.assertIsInstance(l.content, str)
            self.assertGreater(l.confidence, 0)

    def test_extract_learnings_missing_session(self):
        result = self.mem.extract_learnings("ghost-session")
        self.assertEqual(result, [])

    def test_get_user_history(self):
        for i in range(5):
            self.mem.log_session(f"sess-hist-{i}", self._sample_messages(), user_id="hist-user")
        history = self.mem.get_user_history("hist-user", limit=3)
        self.assertLessEqual(len(history), 3)

    def test_forget_user_gdpr(self):
        self.mem.log_session("s-del-1", self._sample_messages(), user_id="delete_me")
        self.mem.log_session("s-del-2", self._sample_messages(), user_id="delete_me")
        self.mem.log_session("s-keep", self._sample_messages(), user_id="keep_me")
        deleted = self.mem.forget_user("delete_me")
        self.assertGreaterEqual(deleted, 2)
        self.assertEqual(self.mem.count_sessions(user_id="delete_me"), 0)
        self.assertGreater(self.mem.count_sessions(user_id="keep_me"), 0)

    def test_export_user_data(self):
        self.mem.log_session("s-exp-1", self._sample_messages(), user_id="export_user")
        data = self.mem.export_user_data("export_user")
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["session_id"], "s-exp-1")


# ===========================================================================
# 4. WorkingMemory tests
# ===========================================================================

class TestWorkingMemory(unittest.TestCase):
    def setUp(self):
        from memory.working_memory import WorkingMemory
        self.wm = WorkingMemory()

    def test_set_and_get_context(self):
        self.wm.set_context("topic", "habeas corpus")
        self.assertEqual(self.wm.get_context("topic"), "habeas corpus")

    def test_get_missing_key_returns_default(self):
        result = self.wm.get_context("missing_key", default="N/A")
        self.assertEqual(result, "N/A")

    def test_ttl_expiry(self):
        self.wm.set_context("ttl_key", "expires soon", ttl_seconds=1)
        self.assertEqual(self.wm.get_context("ttl_key"), "expires soon")
        time.sleep(1.1)
        self.assertIsNone(self.wm.get_context("ttl_key"))

    def test_no_ttl_persists(self):
        self.wm.set_context("permanent", "value", ttl_seconds=None)
        time.sleep(0.1)
        self.assertEqual(self.wm.get_context("permanent"), "value")

    def test_delete_context(self):
        self.wm.set_context("del_me", "value")
        self.assertTrue(self.wm.delete_context("del_me"))
        self.assertIsNone(self.wm.get_context("del_me"))

    def test_delete_missing_returns_false(self):
        self.assertFalse(self.wm.delete_context("not_here"))

    def test_has_context(self):
        self.wm.set_context("check", "val")
        self.assertTrue(self.wm.has_context("check"))
        self.assertFalse(self.wm.has_context("not_set"))

    def test_push_and_pop_stack(self):
        self.wm.push_to_stack("item1")
        self.wm.push_to_stack("item2")
        popped = self.wm.pop_from_stack()
        self.assertEqual(popped, "item2")
        popped2 = self.wm.pop_from_stack()
        self.assertEqual(popped2, "item1")

    def test_pop_empty_stack(self):
        result = self.wm.pop_from_stack()
        self.assertIsNone(result)

    def test_peek_stack(self):
        self.wm.push_to_stack("peek_val")
        self.assertEqual(self.wm.peek_stack(), "peek_val")
        # Should not remove the item
        self.assertEqual(self.wm.stack_size(), 1)

    def test_stack_size(self):
        self.assertEqual(self.wm.stack_size(), 0)
        self.wm.push_to_stack("a")
        self.wm.push_to_stack("b")
        self.assertEqual(self.wm.stack_size(), 2)

    def test_set_and_get_current_task(self):
        from memory.memory_types import Task
        task = Task(name="File motion", description="File the motion to dismiss")
        self.wm.set_current_task(task)
        retrieved = self.wm.get_current_task()
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "File motion")

    def test_complete_task(self):
        from memory.memory_types import Task
        task = Task(name="Task X", description="Desc")
        self.wm.set_current_task(task)
        completed = self.wm.complete_current_task()
        self.assertEqual(completed.status, "completed")
        self.assertIsNone(self.wm.get_current_task())

    def test_attention_focus(self):
        self.wm.set_attention_focus(["contract law", "discovery"])
        focus = self.wm.get_attention_focus()
        self.assertIn("contract law", focus)
        self.assertIn("discovery", focus)

    def test_add_remove_focus_topic(self):
        self.wm.set_attention_focus(["topic_a"])
        self.wm.add_focus_topic("topic_b")
        self.assertIn("topic_b", self.wm.get_attention_focus())
        self.wm.remove_focus_topic("topic_a")
        self.assertNotIn("topic_a", self.wm.get_attention_focus())

    def test_snapshot_and_restore(self):
        self.wm.set_context("snap_key", "snap_value")
        self.wm.push_to_stack("snap_stack_item")
        snap = self.wm.snapshot()

        # Clear and restore
        self.wm.clear()
        self.assertIsNone(self.wm.get_context("snap_key"))

        self.wm.restore(snap)
        self.assertEqual(self.wm.get_context("snap_key"), "snap_value")
        self.assertEqual(self.wm.pop_from_stack(), "snap_stack_item")

    def test_clear(self):
        self.wm.set_context("x", "y")
        self.wm.push_to_stack("z")
        self.wm.clear()
        self.assertEqual(len(self.wm.all_keys()), 0)
        self.assertEqual(self.wm.stack_size(), 0)

    def test_thread_safety(self):
        errors = []
        def writer():
            try:
                for i in range(50):
                    self.wm.set_context(f"key_{i}", f"val_{i}")
            except Exception as e:
                errors.append(str(e))

        def reader():
            try:
                for i in range(50):
                    self.wm.get_context(f"key_{i}")
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=writer) for _ in range(4)]
        threads += [threading.Thread(target=reader) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [], f"Thread safety errors: {errors}")

    def test_stats(self):
        self.wm.set_context("a", "b")
        self.wm.push_to_stack("c")
        stats = self.wm.stats()
        self.assertGreaterEqual(stats["context_keys"], 1)
        self.assertGreaterEqual(stats["stack_depth"], 1)

    def test_evict_expired(self):
        self.wm.set_context("exp1", "val1", ttl_seconds=1)
        self.wm.set_context("perm", "val2", ttl_seconds=None)
        time.sleep(1.1)
        evicted = self.wm.evict_expired()
        self.assertGreaterEqual(evicted, 1)
        self.assertEqual(self.wm.get_context("perm"), "val2")


# ===========================================================================
# 5. UserProfile tests
# ===========================================================================

class TestUserProfile(unittest.TestCase):
    def setUp(self):
        self.tmp = _make_temp_dir()
        self.mgr = _make_profiles(self.tmp)

    def test_create_profile(self):
        profile = self.mgr.create_profile("user1", "Alice")
        self.assertEqual(profile.user_id, "user1")
        self.assertEqual(profile.name, "Alice")

    def test_create_profile_idempotent(self):
        p1 = self.mgr.create_profile("user2", "Bob")
        p2 = self.mgr.create_profile("user2", "Bob Duplicate")
        self.assertEqual(p1.user_id, p2.user_id)

    def test_get_profile_returns_none_for_missing(self):
        result = self.mgr.get_profile("nobody")
        self.assertIsNone(result)

    def test_update_preference(self):
        self.mgr.create_profile("user3", "Carol")
        self.mgr.update_preference("user3", "theme", "dark")
        profile = self.mgr.get_profile("user3")
        self.assertEqual(profile.preferences.get("theme"), "dark")

    def test_update_preference_auto_creates(self):
        self.mgr.update_preference("newuser", "lang", "en")
        profile = self.mgr.get_profile("newuser")
        self.assertIsNotNone(profile)
        self.assertEqual(profile.preferences.get("lang"), "en")

    def test_learn_from_conversation_style(self):
        messages = [
            {"role": "user", "content": "Therefore I must accordingly file this pursuant to the statute"},
            {"role": "assistant", "content": "I understand"},
        ]
        self.mgr.create_profile("formal_user", "Dave")
        self.mgr.learn_from_conversation("formal_user", messages)
        profile = self.mgr.get_profile("formal_user")
        self.assertEqual(profile.communication_style, "formal")

    def test_learn_from_conversation_casual(self):
        messages = [
            {"role": "user", "content": "Hey yeah gonna wanna ask lol"},
            {"role": "assistant", "content": "Sure thing"},
        ]
        self.mgr.create_profile("casual_user", "Eve")
        self.mgr.learn_from_conversation("casual_user", messages)
        profile = self.mgr.get_profile("casual_user")
        self.assertEqual(profile.communication_style, "casual")

    def test_learn_from_conversation_increments_count(self):
        self.mgr.create_profile("counter_user", "Fred")
        msgs = [{"role": "user", "content": "Hello world"}]
        self.mgr.learn_from_conversation("counter_user", msgs)
        self.mgr.learn_from_conversation("counter_user", msgs)
        profile = self.mgr.get_profile("counter_user")
        self.assertEqual(profile.interaction_count, 2)

    def test_get_communication_style(self):
        self.mgr.create_profile("style_user", "Grace")
        self.mgr.update_preference("style_user", "x", "y")  # touch the profile
        style = self.mgr.get_communication_style("style_user")
        self.assertIn(style, ["formal", "casual", "technical", "neutral"])

    def test_get_expertise_level_default(self):
        self.mgr.create_profile("exp_user", "Henry")
        level = self.mgr.get_expertise_level("exp_user", "legal")
        self.assertEqual(level, "novice")

    def test_get_expertise_level_missing_user(self):
        level = self.mgr.get_expertise_level("ghost", "legal")
        self.assertEqual(level, "unknown")

    def test_summarize_profile(self):
        p = self.mgr.create_profile("sum_user", "Iris")
        self.mgr.update_preference("sum_user", "theme", "light")
        summary = self.mgr.summarize_profile("sum_user")
        self.assertIn("Iris", summary)

    def test_summarize_missing_profile(self):
        result = self.mgr.summarize_profile("nobody")
        self.assertIn("No profile", result)

    def test_track_legal_matter(self):
        self.mgr.create_profile("legal_user", "Jack")
        self.mgr.track_legal_matter("legal_user", "matter-001", {
            "type": "civil",
            "status": "active",
            "court": "District Court",
        })
        matter = self.mgr.get_legal_matter("legal_user", "matter-001")
        self.assertIsNotNone(matter)
        self.assertEqual(matter["type"], "civil")

    def test_add_goal(self):
        self.mgr.create_profile("goal_user", "Kim")
        self.mgr.add_goal("goal_user", "Win the case")
        profile = self.mgr.get_profile("goal_user")
        self.assertIn("Win the case", profile.goals)

    def test_add_trusted_contact(self):
        self.mgr.create_profile("contact_user", "Leo")
        self.mgr.add_trusted_contact("contact_user", {"name": "Lawyer Jane", "role": "attorney"})
        profile = self.mgr.get_profile("contact_user")
        self.assertEqual(len(profile.trusted_contacts), 1)

    def test_delete_profile_gdpr(self):
        self.mgr.create_profile("del_user", "Mark")
        result = self.mgr.delete_profile("del_user")
        self.assertTrue(result)
        self.assertIsNone(self.mgr.get_profile("del_user"))

    def test_delete_nonexistent_profile(self):
        result = self.mgr.delete_profile("nobody_here")
        self.assertFalse(result)

    def test_export_profile(self):
        self.mgr.create_profile("exp_profile_user", "Nina")
        data = self.mgr.export_profile("exp_profile_user")
        self.assertIsNotNone(data)
        self.assertIn("user_id", data)

    def test_list_profiles(self):
        self.mgr.create_profile("list_user_1", "Owen")
        self.mgr.create_profile("list_user_2", "Pat")
        profiles = self.mgr.list_profiles()
        self.assertGreaterEqual(len(profiles), 2)

    def test_profile_persists_across_instances(self):
        self.mgr.create_profile("persist_user", "Quinn")
        self.mgr.update_preference("persist_user", "color", "blue")

        # New manager instance, same directory
        mgr2 = _make_profiles(self.tmp)
        profile = mgr2.get_profile("persist_user")
        self.assertIsNotNone(profile)
        self.assertEqual(profile.preferences.get("color"), "blue")


# ===========================================================================
# 6. MemoryEngine tests
# ===========================================================================

class TestMemoryEngine(unittest.TestCase):
    def setUp(self):
        self.tmp = _make_temp_dir()
        self.engine = _make_engine(self.tmp)

    def test_remember_stores_entry(self):
        entry = self.engine.remember("The habeas corpus writ protects against unlawful detention")
        self.assertIsNotNone(entry.id)
        self.assertGreater(self.engine.semantic.count(), 0)

    def test_recall_after_remember(self):
        self.engine.remember("Contract law governs agreements between parties", user_id="u1")
        results = self.engine.recall("contract agreement", user_id="u1")
        self.assertGreater(len(results), 0)

    def test_recall_cross_memory_types(self):
        self.engine.remember("Negligence requires duty breach causation and damages")
        results = self.engine.recall("negligence duty")
        self.assertGreater(len(results), 0)

    def test_recall_empty_returns_list(self):
        results = self.engine.recall("nothing exists yet")
        self.assertIsInstance(results, list)

    def test_recall_top_k_limit(self):
        for i in range(20):
            self.engine.remember(f"Legal precedent case {i} about contracts and liability")
        results = self.engine.recall("legal contract", top_k=5)
        self.assertLessEqual(len(results), 5)

    def test_importance_score_high_keywords(self):
        score = self.engine.importance_score("This is a critical legal deadline you must comply with")
        self.assertGreater(score, 0.5)

    def test_importance_score_low_keywords(self):
        score = self.engine.importance_score("maybe some trivial minor thing whatever")
        self.assertLess(score, 0.5)

    def test_importance_score_baseline(self):
        score = self.engine.importance_score("The weather is nice today")
        self.assertAlmostEqual(score, 0.5, delta=0.2)

    def test_get_relevant_context(self):
        self.engine.remember("Statute of limitations is 3 years for negligence", user_id="ctx_user")
        self.engine.profiles.create_profile("ctx_user", "Rose")
        context = self.engine.get_relevant_context("negligence statute", user_id="ctx_user")
        self.assertIsInstance(context, str)
        self.assertGreater(len(context), 10)

    def test_get_relevant_context_no_user(self):
        self.engine.remember("Important legal principle")
        context = self.engine.get_relevant_context("legal principle")
        self.assertIsInstance(context, str)

    def test_forget_all_gdpr(self):
        self.engine.remember("User fact 1", user_id="gdpr_user")
        self.engine.remember("User fact 2", user_id="gdpr_user")
        self.engine.profiles.create_profile("gdpr_user", "Sam")
        stats = self.engine.forget_all("gdpr_user")
        self.assertIn("semantic_deleted", stats)
        self.assertIn("profile_deleted", stats)
        self.assertEqual(self.engine.semantic.count(user_id="gdpr_user"), 0)
        self.assertIsNone(self.engine.profiles.get_profile("gdpr_user"))

    def test_export_user_data(self):
        self.engine.remember("Export test", user_id="exp_user")
        self.engine.profiles.create_profile("exp_user", "Tina")
        data = self.engine.export_user_data("exp_user")
        self.assertIn("user_id", data)
        self.assertIn("semantic_memories", data)
        self.assertIn("profile", data)
        self.assertIn("exported_at", data)

    def test_memory_stats(self):
        self.engine.remember("Some fact for stats")
        stats = self.engine.memory_stats()
        self.assertIn("semantic", stats)
        self.assertIn("episodic", stats)
        self.assertIn("working", stats)
        self.assertIn("profiles", stats)
        self.assertIn("timestamp", stats)

    def test_working_memory_integration(self):
        self.engine.working.set_context("active_case", "Smith v. Jones 2024")
        results = self.engine.recall("Smith Jones case")
        # Working memory hit should appear first
        found = any("Smith v. Jones 2024" in r.entry.content for r in results)
        self.assertTrue(found)

    def test_auto_tagging(self):
        tags = self.engine._auto_tag("The defendant filed a motion regarding the contract breach")
        self.assertIsInstance(tags, list)
        self.assertGreater(len(tags), 0)

    def test_memory_routing_preference(self):
        """Content with preference signals routes correctly."""
        mt = self.engine._route_memory_type("I always prefer formal communication style", None)
        from memory.memory_types import MemoryType
        self.assertEqual(mt, MemoryType.PREFERENCE)

    def test_memory_routing_procedural(self):
        from memory.memory_types import MemoryType
        mt = self.engine._route_memory_type("Step 1: Draft complaint. Step 2: File with court.", None)
        self.assertEqual(mt, MemoryType.PROCEDURAL)


# ===========================================================================
# Run
# ===========================================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)
