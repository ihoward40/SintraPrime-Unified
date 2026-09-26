"""Fail-closed shadow dual-write and reconciliation primitives for C10-R5."""
from __future__ import annotations

import inspect
import os
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from .jsonl_store import append_jsonl, integrity_check, read_jsonl
from .persistence import ShadowComparator, ShadowMismatchError


@dataclass(frozen=True)
class ShadowMismatch:
    mismatch_id: str
    tenant_id: str
    store_pair: str
    lifecycle_area: str
    expected_state: Any
    actual_state: Any
    severity: str = "critical"
    detected_at: float = 0.0
    certification_blocked: bool = True

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class ShadowMismatchStore:
    """Append-only durable mismatch ledger; every record blocks certification."""

    def __init__(self, path: str | None = None):
        self.path = Path(path or os.getenv("A2A_SHADOW_MISMATCH_STORE", "var/a2a_shadow_mismatches.jsonl"))

    def record(self, *, tenant_id: str, store_pair: str, lifecycle_area: str, expected_state: Any, actual_state: Any, severity: str = "critical") -> dict[str, Any]:
        mismatch = ShadowMismatch(uuid.uuid4().hex, tenant_id, store_pair, lifecycle_area, expected_state, actual_state, severity, time.time(), True)
        return append_jsonl(self.path, mismatch.as_dict())

    def read(self) -> list[dict[str, Any]]:
        return read_jsonl(self.path)

    def integrity_check(self) -> dict[str, Any]:
        return integrity_check(self.path)


class ShadowMirror:
    """Mirror one lifecycle write to two stores and compare normalized results."""

    def __init__(self, mismatch_store: ShadowMismatchStore, *, comparator: ShadowComparator | None = None):
        self.mismatch_store = mismatch_store
        self.comparator = comparator or ShadowComparator()

    def _mismatch(self, *, tenant_id: str, area: str, expected: Any, actual: Any, reason: str | None = None) -> None:
        self.mismatch_store.record(tenant_id=tenant_id, store_pair="jsonl:postgres", lifecycle_area=area, expected_state=expected, actual_state=actual, severity="critical")
        detail = f"shadow mismatch for {area}"
        if reason:
            detail += f": {reason}"
        raise ShadowMismatchError(detail)

    def mirror(self, *, tenant_id: str, lifecycle_area: str, local_write: Callable[[], Any], postgres_write: Callable[[], Any]) -> Any:
        try:
            expected = local_write()
            actual = postgres_write()
            self.comparator.compare(entity=lifecycle_area, local=expected, postgres=actual)
            return expected
        except ShadowMismatchError as exc:
            self._mismatch(tenant_id=tenant_id, area=lifecycle_area, expected=locals().get("expected"), actual=locals().get("actual"), reason=str(exc))
        except Exception as exc:
            self._mismatch(tenant_id=tenant_id, area=lifecycle_area, expected=locals().get("expected"), actual={"error": type(exc).__name__, "detail": str(exc)}, reason="mirror write failed")
        raise AssertionError("unreachable")

    async def mirror_async(self, *, tenant_id: str, lifecycle_area: str, local_write: Callable[[], Any], postgres_write: Callable[[], Any]) -> Any:
        async def invoke(fn: Callable[[], Any]) -> Any:
            value = fn()
            return await value if inspect.isawaitable(value) else value
        try:
            expected = await invoke(local_write)
            actual = await invoke(postgres_write)
            self.comparator.compare(entity=lifecycle_area, local=expected, postgres=actual)
            return expected
        except ShadowMismatchError as exc:
            self._mismatch(tenant_id=tenant_id, area=lifecycle_area, expected=locals().get("expected"), actual=locals().get("actual"), reason=str(exc))
        except Exception as exc:
            self._mismatch(tenant_id=tenant_id, area=lifecycle_area, expected=locals().get("expected"), actual={"error": type(exc).__name__, "detail": str(exc)}, reason="mirror write failed")
        raise AssertionError("unreachable")


def reconcile_records(*, local: Iterable[dict[str, Any]], postgres: Iterable[dict[str, Any]], key: str = "idempotency_key") -> dict[str, Any]:
    left = {str(row.get(key)): row for row in local if row.get(key) is not None}
    right = {str(row.get(key)): row for row in postgres if row.get(key) is not None}
    missing_in_postgres = sorted(set(left) - set(right))
    missing_in_jsonl = sorted(set(right) - set(left))
    divergent = sorted(k for k in set(left) & set(right) if ShadowComparator._canonical(left[k]) != ShadowComparator._canonical(right[k]))
    return {"jsonl_count": len(left), "postgres_count": len(right), "missing_in_postgres": missing_in_postgres, "missing_in_jsonl": missing_in_jsonl, "divergent": divergent, "mismatch_count": len(missing_in_postgres) + len(missing_in_jsonl) + len(divergent), "certification_blocked": bool(missing_in_postgres or missing_in_jsonl or divergent)}
