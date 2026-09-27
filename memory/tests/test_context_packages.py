from datetime import datetime

from memory.context_packages import ContextPackageBuilder, ContextScope
from memory.memory_types import MemoryEntry, MemorySearchResult, MemoryType


class FakeSemantic:
    def __init__(self, results):
        self.results = results

    def recall(self, **kwargs):
        return list(self.results)


class FakeEngine:
    def __init__(self, results):
        self.semantic = FakeSemantic(results)


def result(*, user_id=None, metadata=None, content="memory", score=0.9):
    entry = MemoryEntry(
        content=content,
        memory_type=MemoryType.SEMANTIC,
        user_id=user_id,
        metadata=metadata or {},
        created_at=datetime.utcnow(),
    )
    return MemorySearchResult(entry=entry, relevance_score=score)


def test_legacy_memory_requires_matching_user():
    builder = ContextPackageBuilder(FakeEngine([result(user_id="u1")]))
    allowed = builder.build("q", ContextScope(agent_id="hermes", user_id="u1"))
    denied = builder.build("q", ContextScope(agent_id="hermes", user_id="u2"))
    assert len(allowed.items) == 1
    assert allowed.items[0].scope["legacy_unscoped"] is True
    assert denied.items == []


def test_anonymous_unscoped_memory_is_not_global():
    builder = ContextPackageBuilder(FakeEngine([result(user_id=None)]))
    package = builder.build("q", ContextScope(agent_id="hermes"))
    assert package.items == []


def test_explicit_agent_and_project_scope_is_enforced():
    memory = result(
        user_id=None,
        metadata={"agent_ids": ["hermes"], "project_id": "p1", "source_id": "src-1"},
    )
    builder = ContextPackageBuilder(FakeEngine([memory]))
    ok = builder.build("q", ContextScope(agent_id="hermes", project_id="p1"))
    wrong_agent = builder.build("q", ContextScope(agent_id="sigma", project_id="p1"))
    wrong_project = builder.build("q", ContextScope(agent_id="hermes", project_id="p2"))
    assert len(ok.items) == 1
    assert ok.items[0].provenance["source_id"] == "src-1"
    assert wrong_agent.items == []
    assert wrong_project.items == []
