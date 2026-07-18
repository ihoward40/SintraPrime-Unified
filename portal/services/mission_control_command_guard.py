"""Server-side guard for Mission Control command execution."""

from __future__ import annotations

from enum import StrEnum


class RefusalReason(StrEnum):
    COMMAND_EXECUTION_NOT_ENABLED = "COMMAND_EXECUTION_NOT_ENABLED"


def refuse_increment_one_execution() -> RefusalReason:
    """Increment One authorizes command recording only, never execution."""
    return RefusalReason.COMMAND_EXECUTION_NOT_ENABLED
