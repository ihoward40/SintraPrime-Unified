from types import SimpleNamespace

import pytest

from portal.routers import agent_commons


@pytest.fixture(autouse=True)
def development_runtime(monkeypatch):
    monkeypatch.setattr(
        agent_commons,
        "get_settings",
        lambda: SimpleNamespace(ENVIRONMENT="development"),
    )
    monkeypatch.setenv("WEB_CONCURRENCY", "1")
    monkeypatch.setenv("AGENT_COMMONS_STORAGE_MODE", "sqlite")
    monkeypatch.setenv("AGENT_COMMONS_EVENT_BACKEND", "in_process")
    agent_commons.get_store.cache_clear()
    agent_commons.get_event_bus.cache_clear()
    agent_commons.get_supervisor.cache_clear()
    yield
    agent_commons.get_store.cache_clear()
    agent_commons.get_event_bus.cache_clear()
    agent_commons.get_supervisor.cache_clear()


def test_adapter_mode_defaults_to_disabled(monkeypatch):
    monkeypatch.delenv("AGENT_COMMONS_ADAPTER_MODE", raising=False)

    assert agent_commons.get_adapter_mode() == agent_commons.ADAPTER_MODE_DISABLED
    assert agent_commons.get_supervisor().adapters == {}


def test_mock_adapters_require_explicit_configuration(monkeypatch):
    monkeypatch.setenv("AGENT_COMMONS_ADAPTER_MODE", "mock")
    agent_commons.get_supervisor.cache_clear()

    supervisor = agent_commons.get_supervisor()

    assert agent_commons.get_adapter_mode() == agent_commons.ADAPTER_MODE_MOCK
    assert set(supervisor.adapters) == {"hermes", "codex", "claude-code", "manus"}


def test_invalid_adapter_mode_fails_closed(monkeypatch):
    monkeypatch.setenv("AGENT_COMMONS_ADAPTER_MODE", "production-mock")

    with pytest.raises(RuntimeError, match="AGENT_COMMONS_ADAPTER_MODE"):
        agent_commons.get_adapter_mode()


def test_sse_frame_declares_id_event_retry_and_json_data():
    frame = agent_commons._encode_sse(
        {"type": "supervisor.run.updated", "data": {"run_id": "run-1"}},
        event_id=7,
    )

    assert frame.startswith("id: 7\n")
    assert "event: supervisor.run.updated\n" in frame
    assert f"retry: {agent_commons.SSE_RETRY_MILLISECONDS}\n" in frame
    assert 'data: {"type": "supervisor.run.updated", "data": {"run_id": "run-1"}}\n\n' in frame
