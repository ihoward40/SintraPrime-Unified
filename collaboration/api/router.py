"""Collaboration API router — CF-1E.

Backend foundation only. Frontend is Phase CF-2 (directive §XLIV:
"Do not let frontend scope explode this PR").
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from collaboration.models import EventEnvelope
from collaboration.models.enums import EventType
from collaboration.policies import KillSwitch
from collaboration.services.activation_service import ActivationService
from collaboration.services.binding_service import BindingService
from collaboration.services.channel_service import ChannelService
from collaboration.services.handoff_service import HandoffService
from collaboration.services.membership_service import MembershipService
from collaboration.services.presence_service import PresenceService
from collaboration.services.shutdown_service import ShutdownService
from collaboration.services.store import CollaborationStore

from .schemas import (
    BindingCreate,
    ChannelCreate,
    EventEnvelopeIn,
    HandoffCreate,
    MembershipJoin,
    StopAgentRequest,
)

router = APIRouter(prefix="/api/collaboration", tags=["collaboration"])


class CollaborationAPI:
    """Binds services to the router. Caller owns persistence lifecycle."""

    def __init__(self, base_dir: str):
        self.store = CollaborationStore(base_dir + "/store")
        self.channels = ChannelService(self.store)
        self.memberships = MembershipService(self.store)
        self.bindings = BindingService(self.store)
        self.handoffs = HandoffService(self.store)
        self.presence = PresenceService()
        self.kill_switch = KillSwitch()
        self.activations = ActivationService(
            store=self.store,
            concurrency=__import__(
                "collaboration.policies", fromlist=["ConcurrencyPolicy"]
            ).ConcurrencyPolicy(),
        )
        self.shutdown = ShutdownService(self.activations, self.bindings)
        self._wire()

    def _wire(self) -> None:
        api = self

        @router.post("/channels", status_code=201)
        def create_channel(body: ChannelCreate) -> dict:
            ch = api.channels.create(
                tenant_id=body.tenant_id,
                name=body.name,
                slug=body.slug,
                channel_type=body.channel_type,
                visibility=body.visibility,
                description=body.description,
                created_by=body.created_by,
            )
            return {"id": ch.id}

        @router.get("/channels")
        def list_channels(tenant_id: str) -> list[dict]:
            return [
                {"id": c.id, "name": c.name, "slug": c.slug, "channel_type": c.channel_type.value}
                for c in api.channels.list_by_tenant(tenant_id)
            ]

        @router.get("/channels/{channel_id}")
        def get_channel(channel_id: str) -> dict:
            ch = api.channels.get(channel_id)
            if ch is None:
                raise HTTPException(status_code=404, detail="channel not found")
            return {
                "id": ch.id,
                "name": ch.name,
                "slug": ch.slug,
                "channel_type": ch.channel_type.value,
                "visibility": ch.visibility.value,
                "status": ch.status.value,
            }

        @router.post("/channels/{channel_id}/members", status_code=201)
        def join_channel(channel_id: str, body: MembershipJoin) -> dict:
            m = api.memberships.join(
                channel_id=channel_id,
                tenant_id=channel_id,
                principal_id=body.principal_id,
                principal_type=body.principal_type,
                role=body.role,
            )
            return {"id": m.id, "status": "joined"}

        @router.get("/channels/{channel_id}/members")
        def list_members(channel_id: str) -> list[dict]:
            return [
                {"principal_id": m.principal_id, "role": m.role.value, "status": m.status.value}
                for m in api.memberships.get_active(channel_id)
            ]

        @router.post("/channels/{channel_id}/bindings", status_code=201)
        def create_binding(channel_id: str, body: BindingCreate) -> dict:
            b = api.bindings.bind(
                tenant_id=channel_id,
                channel_id=channel_id,
                agent_id=body.agent_id,
                allowed_event_types=body.allowed_event_types,
                max_parallelism=body.max_parallelism,
                memory_mode=body.memory_mode,
                provider_profile=body.provider_profile,
                model_profile=body.model_profile,
                actor_allowlist=body.actor_allowlist,
                shadow_mode=body.shadow_mode,
            )
            return {"id": b.id, "status": "bound"}

        @router.get("/channels/{channel_id}/bindings")
        def list_bindings(channel_id: str) -> list[dict]:
            return [
                {
                    "id": b.id,
                    "agent_id": b.agent_id,
                    "response_mode": b.response_mode.value,
                    "stopped": b.stopped,
                    "shadow_mode": b.shadow_mode,
                }
                for b in api.bindings.list_for_channel(channel_id)
            ]

        @router.post("/channels/{channel_id}/bindings/{binding_id}/stop")
        def stop_binding(_channel_id: str, binding_id: str) -> dict:
            b = api.bindings.stop(binding_id)
            if b is None:
                raise HTTPException(status_code=404, detail="binding not found")
            return {"id": b.id, "status": "stopped"}

        @router.post("/channels/{channel_id}/events")
        def dispatch_event(channel_id: str, body: EventEnvelopeIn) -> dict:
            evt = EventEnvelope(
                event_id=body.event_id,
                event_type=EventType(body.event_type),
                tenant_id=body.tenant_id,
                channel_id=body.channel_id,
                actor_type=body.actor_type,
                actor_id=body.actor_id,
                correlation_id=body.correlation_id,
                payload=body.payload,
                hop_count=body.hop_count,
                origin_type=body.origin_type,
                origin_id=body.origin_id,
            )
            from collaboration.events.dispatcher import EventDispatcher
            from collaboration.policies import DeduplicationPolicy, EventPolicyEngine, LoopGuard

            dispatcher = EventDispatcher(
                event_policy=EventPolicyEngine(loop_guard=LoopGuard(), dedup=DeduplicationPolicy()),
            )
            bindings = api.bindings.list_for_channel(channel_id)
            outcomes = dispatcher.dispatch(evt, bindings)
            return {
                "event_id": body.event_id,
                "outcomes": [
                    {"agent_id": o.target_agent, "status": o.status.value} for o in outcomes
                ],
            }

        @router.post("/handoffs", status_code=201)
        def create_handoff(body: HandoffCreate) -> dict:
            h = api.handoffs.create(
                handoff_id=body.handoff_id,
                source_agent=body.source_agent,
                target_agent=body.target_agent,
                channel_id="ch_handoff",
                tenant_id="t_handoff",
                task=body.task,
                input_artifacts=body.input_artifacts,
                expected_output_schema=body.expected_output_schema,
                correlation_id=body.correlation_id,
            )
            return {"id": h.handoff_id, "status": h.status.value}

        @router.get("/channels/{channel_id}/activity")
        def channel_activity(channel_id: str) -> dict:
            bindings = api.bindings.list_for_channel(channel_id)
            return {
                "channel_id": channel_id,
                "agents": api.presence.channel_status(bindings),
                "activations": [
                    {
                        "activation_id": a.activation_id,
                        "agent_id": a.agent_id,
                        "status": a.status.value,
                    }
                    for a in api.activations.list_by_channel(channel_id)
                ],
            }

        @router.post("/agents/stop")
        def stop_agent(body: StopAgentRequest) -> dict:
            return api.shutdown.stop_agent(body.agent_id, "all")


api = None


def get_router(base_dir: str) -> APIRouter:
    global api
    api = CollaborationAPI(base_dir)
    return router
