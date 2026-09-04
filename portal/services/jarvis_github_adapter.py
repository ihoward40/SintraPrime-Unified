"""JARVIS-001-B1 GitHub label adapter (B1-4) + fake provider.

The adapter is executor-owned: it is the only component that may hold a
mutation credential, and only at the execution boundary. It supports exactly
one operation: add a label to one designated test issue. No arbitrary repo,
no delete/merge/close/branch/release/workflow/secret/deployment surfaces.
"""
from __future__ import annotations

from typing import Any

from .jarvis_action_taxonomy import ActionFailure

ALLOWED_LABEL = "jarvis-b1-acceptance"
ALLOWED_OPERATIONS = frozenset({"add_label"})


class GitHubProvider:
    """Structural protocol for B1 providers (real or fake)."""

    def get_issue_labels(self, repo: str, issue_number: int) -> list: ...

    def add_label(self, repo: str, issue_number: int, label: str, token: str | None = None) -> dict: ...


class GitHubLabelAdapter:
    """The only B1 mutation surface. One operation, canonical verification."""

    def __init__(self, provider: GitHubProvider | None = None, credential: str | None = None) -> None:
        self._provider = provider
        self._credential = credential

    def read_issue_state(self, repo: str, issue_number: int) -> dict:
        return self._require_provider().get_issue_labels(repo, issue_number)

    def mutate(self, repo: str, issue_number: int, label: str, token: str | None = None) -> dict:
        return self._require_provider().add_label(repo, issue_number, label, token=token)

    def _require_provider(self) -> GitHubProvider:
        if self._provider is None:
            raise ActionFailure("EXECUTOR_UNAVAILABLE")
        return self._provider


class FakeGitHubProvider:
    """Deterministic in-memory GitHub stand-in. Counts mutation calls."""

    def __init__(self) -> None:
        self._labels: dict[str, list[str]] = {}
        self.mutation_calls = 0
        self._token_seen: str | None = None

    def get_issue_labels(self, repo: str, issue_number: int) -> list:
        return list(self._labels.get((repo, issue_number), []))

    def add_label(self, repo: str, issue_number: int, label: str, token: str | None = None) -> dict:
        self.mutation_calls += 1
        self._token_seen = token
        labels = self._labels.setdefault((repo, issue_number), [])
        if label not in labels:
            labels.append(label)
        return {"ok": True, "label": label}

    @property
    def token_seen(self):
        return self._token_seen

    def prime_label(self, issue_number: int, label: str, repo: str = "ihoward40/SintraPrime-Unified") -> None:
        self._labels[(repo, issue_number)] = [label]
