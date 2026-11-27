"""ChannelBrief — persistent channel-level operating document (§XXVI)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ChannelBrief:
    channel_id: str
    mission: str = ""
    current_objective: str = ""
    rules: list[str] = field(default_factory=list)
    important_artifacts: list[str] = field(default_factory=list)
    definitions: dict = field(default_factory=dict)
    active_decisions: list[dict] = field(default_factory=list)
    do_not_do_list: list[str] = field(default_factory=list)
    version: str = "1"
    last_updated: str = ""
    updated_by: str = ""
