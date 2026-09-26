"""Persistence boundaries for governed A2A state.

JSONL remains the default local adapter. PostgreSQL is explicit opt-in; this
module never changes external-action policy or enables an executor.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


class ShadowMismatchError(RuntimeError):
    """Raised when mirrored local and PostgreSQL state diverges."""


@runtime_checkable
class AuditStore(Protocol):
    def append(self, record: Any) -> Any: ...
    def read(self, **filters: Any) -> list[dict[str, Any]]: ...
    def integrity_check(self, **filters: Any) -> dict[str, Any]: ...


@runtime_checkable
class ApprovalStore(Protocol):
    def issue(self, receipt: Any) -> Any: ...
    def get(self, receipt_id: str, **scope: Any) -> dict[str, Any] | None: ...
    def verify_and_consume(self, receipt: Any, **scope: Any) -> None: ...
    def revoke(self, receipt_id: str, **scope: Any) -> None: ...
    def expire(self, **scope: Any) -> int: ...


@runtime_checkable
class OutboxStore(Protocol):
    def enqueue(self, **fields: Any) -> str: ...
    def get(self, outbox_id: str, **scope: Any) -> dict[str, Any] | None: ...
    def revalidate(self, outbox_id: str, **fields: Any) -> dict[str, Any]: ...
    def integrity_check(self, **scope: Any) -> dict[str, Any]: ...


@dataclass(frozen=True)
class PersistenceConfig:
    backend: str = "jsonl"
    shadow: bool = False

    @classmethod
    def from_env(cls) -> "PersistenceConfig":
        backend = os.getenv("A2A_PERSISTENCE_BACKEND", "jsonl").strip().lower()
        shadow = os.getenv("A2A_PERSISTENCE_SHADOW", "false").strip().lower() in {"1", "true", "yes", "on"}
        if backend not in {"jsonl", "postgres"}:
            raise ValueError("A2A_PERSISTENCE_BACKEND must be jsonl or postgres")
        if shadow and backend != "postgres":
            raise ValueError("A2A_PERSISTENCE_SHADOW requires A2A_PERSISTENCE_BACKEND=postgres")
        return cls(backend=backend, shadow=shadow)


def select_backend() -> PersistenceConfig:
    """Load explicit backend configuration; never silently fall back."""
    return PersistenceConfig.from_env()


class ShadowComparator:
    """Compare mirrored lifecycle projections and fail closed on mismatch."""

    def __init__(self, mismatch_sink: Any | None = None):
        self.mismatch_sink = mismatch_sink

    @staticmethod
    def _canonical(value: Any) -> Any:
        if isinstance(value, dict):
            ignored = {"sequence", "timestamp", "created_at", "updated_at"}
            return {k: ShadowComparator._canonical(v) for k, v in sorted(value.items()) if k not in ignored}
        if isinstance(value, (list, tuple)):
            return [ShadowComparator._canonical(v) for v in value]
        return value

    def compare(self, *, entity: str, local: Any, postgres: Any) -> None:
        left = self._canonical(local)
        right = self._canonical(postgres)
        if left == right:
            return
        detail = {"entity": entity, "local": left, "postgres": right}
        if self.mismatch_sink is not None:
            self.mismatch_sink(detail)
        raise ShadowMismatchError(f"shadow persistence mismatch for {entity}")
