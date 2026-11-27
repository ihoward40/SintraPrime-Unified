# Inspired by vectorize-io/hindsight (MIT License) — https://github.com/vectorize-io/hindsight
"""
Tests for the learning memory layer (retain / recall / reflect,
memory banks, and knowledge pages / mental models).
"""

from __future__ import annotations

import os
import tempfile
import unittest


def _make_temp_dir() -> str:
    return tempfile.mkdtemp()


def _make_learning(tmp_dir: str):
    from memory.learning import LearningMemory
    from memory.memory_engine import MemoryEngine
    engine = MemoryEngine(
        semantic_db_path=os.path.join(tmp_dir, "semantic.db"),
        episodic_db_path=os.path.join(tmp_dir, "episodic.db"),
        profiles_dir=os.path.join(tmp_dir, "profiles"),
    )
    return LearningMemory(engine)


# ===========================================================================
# 1. Memory banks
# ===========================================================================

class TestMemoryBanks(unittest.TestCase):
    """Tests for the MemoryBank abstraction."""

    def test_create_bank_slugifies_name(self):
        from memory.learning import LearningMemory
        lm = _make_learning(_make_temp_dir())
        bank = lm.create_bank("Project Apollo", description="A project bank", purpose="testing")
        self.assertEqual(bank.bank_id, "project_apollo")
        self.assertEqual(bank.name, "Project Apollo")
        self.assertEqual(bank.description, "A project bank")

    def test_create_bank_idempotent(self):
        lm = _make_learning(_make_temp_dir())
        first = lm.create_bank("Shared")
        second = lm.create_bank("Shared")
        self.assertEqual(first.bank_id, second.bank_id)
        self.assertEqual(len(lm.list_banks()), 1)

    def test_get_bank_lookup(self):
        lm = _make_learning(_make_temp_dir())
        lm.create_bank("Legal")
        self.assertIsNotNone(lm.get_bank("legal"))
        self.assertIsNone(lm.get_bank("does-not-exist"))


# ===========================================================================
# 2. Retain / recall operations
# ===========================================================================

class TestRetainRecall(unittest.TestCase):
    """Tests for the retain and recall operations over the engine."""

    def test_retain_stores_entry_in_bank(self):
        lm = _make_learning(_make_temp_dir())
        lm.create_bank("Legal")
        entry = lm.retain(
            "The annual report deadline is important and critical.",
            bank_id="legal",
            user_id="u1",
        )
        self.assertIsNotNone(entry.id)
        self.assertIn("bank:legal", entry.tags)
        self.assertEqual(entry.metadata.get("bank_id"), "legal")

    def test_retain_without_bank(self):
        lm = _make_learning(_make_temp_dir())
        entry = lm.retain("A free-floating fact about the world.")
        self.assertIsNotNone(entry.id)
        self.assertNotIn("bank_id", entry.metadata)

    def test_retain_unknown_bank_raises(self):
        lm = _make_learning(_make_temp_dir())
        with self.assertRaises(ValueError):
            lm.retain("Something", bank_id="nope")

    def test_recall_scoped_to_bank(self):
        lm = _make_learning(_make_temp_dir())
        lm.create_bank("Legal")
        lm.create_bank("Kitchen")
        lm.retain("The court filing deadline is critical for the legal matter.", bank_id="legal")
        lm.retain("The stove gets hot, so use oven mitts.", bank_id="kitchen")

        legal = lm.recall("deadline", bank_id="legal")
        self.assertGreater(len(legal), 0)
        for r in legal:
            self.assertEqual(r.entry.metadata.get("bank_id"), "legal")

    def test_recall_unknown_bank_raises(self):
        lm = _make_learning(_make_temp_dir())
        with self.assertRaises(ValueError):
            lm.recall("anything", bank_id="nope")


# ===========================================================================
# 3. Reflect + knowledge pages (mental models)
# ===========================================================================

class TestReflectAndPages(unittest.TestCase):
    """Tests for reflection and durable knowledge pages."""

    def _seed(self, lm, bank_id="legal"):
        from memory.learning import LearningMemory  # noqa: F401
        lm.create_bank(bank_id)
        lm.retain("The court filing deadline is critical.", bank_id=bank_id, tags=["deadline"])
        lm.retain("The annual report fee is required by Sep 30.", bank_id=bank_id, tags=["deadline"])
        lm.retain("Compliance review must happen quarterly.", bank_id=bank_id, tags=["deadline"])
        return lm

    def test_reflect_returns_reflection(self):
        from memory.learning import Reflection
        lm = _make_learning(_make_temp_dir())
        self._seed(lm)
        reflection = lm.reflect("What deadlines matter?", bank_id="legal")
        self.assertIsInstance(reflection, Reflection)
        self.assertEqual(reflection.bank_id, "legal")
        self.assertGreater(reflection.memory_count, 0)
        self.assertTrue(reflection.key_themes)
        self.assertIn("deadline", reflection.summary.lower())

    def test_reflect_distills_knowledge_pages(self):
        from memory.learning import KnowledgePage
        lm = _make_learning(_make_temp_dir())
        self._seed(lm)
        reflection = lm.reflect("deadlines", bank_id="legal")
        self.assertGreater(len(reflection.knowledge_pages), 0)
        page = reflection.knowledge_pages[0]
        self.assertIsInstance(page, KnowledgePage)
        self.assertTrue(page.supporting_entry_ids)
        self.assertGreaterEqual(page.confidence, 0.6)

    def test_reflect_merges_pages_on_repeat(self):
        lm = _make_learning(_make_temp_dir())
        self._seed(lm)
        first = lm.reflect("deadlines", bank_id="legal")
        second = lm.reflect("deadlines", bank_id="legal")
        first_ids = {p.page_id for p in first.knowledge_pages}
        second_ids = {p.page_id for p in second.knowledge_pages}
        # Same pages should be merged, not duplicated
        self.assertEqual(first_ids, second_ids)
        pages = lm.get_knowledge_pages(bank_id="legal")
        self.assertEqual(len(pages), len(first_ids))

    def test_reflect_empty_memory(self):
        lm = _make_learning(_make_temp_dir())
        lm.create_bank("empty")
        reflection = lm.reflect("nothing here matches xyzzy", bank_id="empty")
        self.assertEqual(reflection.memory_count, 0)
        self.assertEqual(reflection.knowledge_pages, [])

    def test_get_knowledge_pages_and_single_page(self):
        lm = _make_learning(_make_temp_dir())
        self._seed(lm)
        lm.reflect("deadlines", bank_id="legal")
        pages = lm.get_knowledge_pages(bank_id="legal")
        self.assertGreater(len(pages), 0)
        fetched = lm.get_knowledge_page(pages[0].page_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.title, pages[0].title)

    def test_knowledge_pages_persist_in_semantic_store(self):
        lm = _make_learning(_make_temp_dir())
        self._seed(lm)
        lm.reflect("deadlines", bank_id="legal")
        # A second LearningMemory over the same engine dir recovers pages
        from memory.learning import LearningMemory
        from memory.memory_engine import MemoryEngine
        engine = lm._engine  # same engine: pages are in its semantic store
        lm2 = LearningMemory(engine)
        pages = lm2.get_knowledge_pages(bank_id="legal")
        self.assertGreater(len(pages), 0)

    def test_run_learning_cycle(self):
        lm = _make_learning(_make_temp_dir())
        self._seed(lm)
        pages = lm.run_learning_cycle(bank_id="legal")
        self.assertGreater(len(pages), 0)
        self.assertEqual(len(lm.get_knowledge_pages(bank_id="legal")), len(pages))

    def test_reflection_to_dict(self):
        lm = _make_learning(_make_temp_dir())
        self._seed(lm)
        reflection = lm.reflect("deadlines", bank_id="legal")
        d = reflection.to_dict()
        self.assertEqual(d["query"], "deadlines")
        self.assertEqual(d["bank_id"], "legal")
        self.assertIn("knowledge_pages", d)
        self.assertIn("key_themes", d)


# ===========================================================================
# 4. Package exports
# ===========================================================================

class TestLearningExports(unittest.TestCase):
    """The learning layer should be importable from the package root."""

    def test_package_exports(self):
        import memory
        for name in ("LearningMemory", "MemoryBank", "KnowledgePage", "Reflection"):
            self.assertIn(name, memory.__all__)
            self.assertTrue(hasattr(memory, name))


if __name__ == "__main__":
    unittest.main()
