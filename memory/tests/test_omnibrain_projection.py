from memory.context_packages import ContextItem, ContextPackage, ContextScope
from memory.knowledge_graph import KnowledgeGraphStore
from memory.obsidian_projection import ObsidianProjector


def package():
    return ContextPackage(
        query="review project",
        scope=ContextScope(agent_id="hermes", user_id="u1", project_id="p1"),
        items=[
            ContextItem(
                memory_id="m1",
                content="API_KEY=supersecret important project fact",
                relevance_score=0.9,
                importance=0.8,
                tags=["project"],
                provenance={"source": "github", "source_id": "sha-1", "source_uri": "repo://x"},
                scope={
                    "user_id": "u1",
                    "project_id": "p1",
                    "matter_id": None,
                    "tenant_id": None,
                    "agent_ids": ["hermes"],
                    "legacy_unscoped": False,
                },
            )
        ],
    )


def test_graph_records_provenance_edges(tmp_path):
    store = KnowledgeGraphStore(str(tmp_path / "graph.db"))
    store.record_context_package(package())
    stats = store.stats()
    assert stats["nodes"] >= 4
    assert stats["edges"] >= 3


def test_obsidian_projection_is_one_way_and_redacts_secrets(tmp_path):
    projector = ObsidianProjector(str(tmp_path / "vault"))
    paths = projector.project_package(package())
    text = "\n".join(path.read_text(encoding="utf-8") for path in paths)
    assert "projection: one-way" in text
    assert "supersecret" not in text
    assert "[REDACTED]" in text
    assert "[[Memory/m1]]" in text
