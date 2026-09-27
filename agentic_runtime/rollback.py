"""Approval-gated checkpoint and rollback execution."""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from .controls import ChangedFileManifest, Checkpoint


@dataclass(frozen=True)
class RollbackResult:
    checkpoint_id: str
    restored_ref: str
    restored_files: tuple[str, ...]
    ok: bool


class GovernedRollbackExecutor:
    """Concrete rollback orchestration with injected repository primitives.

    The executor has no ambient git/shell authority. It can only snapshot,
    restore and inspect through injected functions after authorization.
    """
    def __init__(
        self,
        *,
        authorize: Callable[[str, dict], bool],
        current_ref: Callable[[], str],
        changed_files: Callable[[str, str], Sequence[str]],
        restore_ref: Callable[[str], bool],
        record: Callable[[str, dict], None],
    ):
        self.authorize = authorize
        self.current_ref = current_ref
        self.changed_files = changed_files
        self.restore_ref = restore_ref
        self.record = record

    def checkpoint(self, checkpoint_id: str, base_ref: str) -> tuple[Checkpoint, ChangedFileManifest]:
        head = self.current_ref()
        files = tuple(sorted(set(self.changed_files(base_ref, head))))
        cp = Checkpoint(checkpoint_id=checkpoint_id, ref=head, changed_files=files)
        manifest = ChangedFileManifest(before_ref=base_ref, after_ref=head, files=list(files))
        self.record("checkpoint_created", {"checkpoint_id": checkpoint_id, "ref": head, "files": list(files)})
        return cp, manifest

    def rollback(self, checkpoint: Checkpoint, *, reason: str) -> RollbackResult:
        context = {"checkpoint_id": checkpoint.checkpoint_id, "ref": checkpoint.ref, "reason": reason}
        if not self.authorize("ROLLBACK_TO_CHECKPOINT", context):
            self.record("rollback_denied", context)
            return RollbackResult(checkpoint.checkpoint_id, checkpoint.ref, (), False)
        before = self.current_ref()
        impacted = tuple(sorted(set(self.changed_files(before, checkpoint.ref))))
        ok = bool(self.restore_ref(checkpoint.ref))
        after = self.current_ref()
        verified = ok and after == checkpoint.ref
        self.record("rollback_executed", {**context, "from_ref": before, "after_ref": after, "files": list(impacted), "ok": verified})
        return RollbackResult(checkpoint.checkpoint_id, after, impacted, verified)
