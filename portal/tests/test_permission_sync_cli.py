"""CLI tests for Mission Control permission synchronization."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from portal.scripts import sync_mission_control_permissions as sync_script


@dataclass
class _FakeReport:
    mode: str


class _FakeSession:
    def __init__(self) -> None:
        self.commit_calls = 0
        self.rollback_calls = 0

    async def commit(self) -> None:
        self.commit_calls += 1

    async def rollback(self) -> None:
        self.rollback_calls += 1


class _FakeSessionContext:
    def __init__(self, session: _FakeSession) -> None:
        self.session = session

    async def __aenter__(self) -> _FakeSession:
        return self.session

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["verify", "dry-run", "apply"])
async def test_permission_sync_cli_commits_only_for_apply(monkeypatch, mode: str):
    session = _FakeSession()
    monkeypatch.setattr(sync_script, "AsyncSessionLocal", lambda: _FakeSessionContext(session))

    async def _verify(_session):
        return _FakeReport(mode="VERIFY")

    async def _plan(_session):
        return _FakeReport(mode="DRY_RUN")

    async def _apply(_session):
        return _FakeReport(mode="RECONCILE")

    monkeypatch.setattr(sync_script, "inspect_permission_manifest", _verify)
    monkeypatch.setattr(sync_script, "plan_permission_manifest", _plan)
    monkeypatch.setattr(sync_script, "sync_permission_manifest", _apply)

    await sync_script._run(mode)

    if mode == "apply":
        assert session.commit_calls == 1
        assert session.rollback_calls == 0
    else:
        assert session.commit_calls == 0
        assert session.rollback_calls == 0
