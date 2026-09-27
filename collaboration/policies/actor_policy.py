"""ActorPolicyEngine — who may trigger which agent (§XII)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from collaboration.models import AgentChannelBinding, EventEnvelope
from collaboration.models.enums import MembershipRole


class ActorTriggerPolicy(str, Enum):
    ANY_AUTHENTICATED_MEMBER = "any_authenticated_member"
    CHANNEL_OWNER = "channel_owner"
    CHANNEL_ADMINS = "channel_admins"
    ALLOWLIST = "allowlist"
    SYSTEM_ONLY = "system_only"
    PRINCIPAL_ONLY = "principal_only"


@dataclass
class ActorPolicyDecision:
    allow: bool = False
    reason: str = ""


class ActorPolicyEngine:
    """Deterministic actor gate. Default for sensitive agents: ALLOWLIST."""

    def __init__(self):
        self._policies: dict[str, ActorTriggerPolicy] = {}

    def set_policy(self, agent_id: str, policy: ActorTriggerPolicy) -> None:
        self._policies[agent_id] = policy

    def get_policy(self, agent_id: str) -> ActorTriggerPolicy:
        return self._policies.get(agent_id, ActorTriggerPolicy.ALLOWLIST)

    def evaluate(
        self,
        event: EventEnvelope,
        binding: AgentChannelBinding,
        *,
        actor_role: MembershipRole | None = None,
        principal_ids: set[str] | None = None,
    ) -> ActorPolicyDecision:
        policy = self.get_policy(binding.agent_id)

        if event.actor_type == "system":
            return ActorPolicyDecision(True, "system actor")

        # SYSTEM_ONLY: only system/service actors
        if policy == ActorTriggerPolicy.SYSTEM_ONLY:
            allow = event.actor_type == "service"
            return ActorPolicyDecision(allow, "allowed" if allow else "system_only_policy")

        # PRINCIPAL_ONLY
        if policy == ActorTriggerPolicy.PRINCIPAL_ONLY:
            allow = (
                event.actor_type == "human"
                and principal_ids is not None
                and event.actor_id in principal_ids
            )
            return ActorPolicyDecision(allow, "allowed" if allow else "principal_only_policy")

        # ALLOWLIST
        if policy == ActorTriggerPolicy.ALLOWLIST:
            allow = event.actor_id in binding.actor_allowlist
            return ActorPolicyDecision(allow, "allowed" if allow else "actor_not_in_allowlist")

        # CHANNEL_OWNER
        if policy == ActorTriggerPolicy.CHANNEL_OWNER:
            allow = actor_role == MembershipRole.OWNER
            return ActorPolicyDecision(allow, "allowed" if allow else "requires_channel_owner")

        # CHANNEL_ADMINS
        if policy == ActorTriggerPolicy.CHANNEL_ADMINS:
            allow = actor_role in (MembershipRole.OWNER, MembershipRole.ADMIN)
            return ActorPolicyDecision(allow, "allowed" if allow else "requires_channel_admin")

        # ANY_AUTHENTICATED_MEMBER (default permissive)
        return ActorPolicyDecision(True, "allowed")
