import uuid
from datetime import datetime, UTC
from typing import Any, Protocol, runtime_checkable
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models.mission_control_command import MissionControlCommand, MissionControlCommandEvent
from ..models.mission_control_outbox import MissionControlOutbox
from ..models.mission_control_run_control import MissionControlRunControl

@runtime_checkable
class IntentExecutor(Protocol):
    """Protocol for all stateless executors managed by the Mythos Brain."""
    async def execute(self, command: MissionControlCommand) -> Any:
        ...
    async def cancel(self, command: MissionControlCommand) -> Any:
        ...

class PolicyEnforcementPoint:
    """
    Centralized governance policy enforcement for the Mythos Brain.
    Validates intents against security and operational boundaries.
    """
    async def authorize_intent(self, tenant_id: str, actor_id: str, intent_type: str, payload: dict) -> bool:
        # Placeholder for real policy evaluation (e.g., OPA/Rego)
        # In God Mode, the Principal has elevated authority.
        if actor_id == "principal":
            return True
        
        # Default refusal-only policy for sensitive operations
        if intent_type in ["DESTRUCTIVE_RESEARCH", "EXTERNAL_FILING"]:
            return False
            
        return True

class MythosBrainCoordinator:
    """
    The central Execution Coordinator for the SintraPrime platform.
    Owns the lifecycle of intent and ensures durable dispatch via the transactional outbox.
    """
    def __init__(self, pep: PolicyEnforcementPoint = None):
        self.pep = pep or PolicyEnforcementPoint()

    async def ingest_intent(
        self, 
        db: AsyncSession, 
        tenant_id: str, 
        actor_id: str, 
        command_type: str, 
        payload: dict,
        correlation_id: str | None = None
    ) -> MissionControlCommand:
        """
        Ingests a new intent, validates it, and prepares it for dispatch.
        Ensures atomicity between ledger recording and outbox creation.
        """
        # 1. Authorize via PEP
        authorized = await self.pep.authorize_intent(tenant_id, actor_id, command_type, payload)
        if not authorized:
            raise PermissionError(f"Intent {command_type} unauthorized for actor {actor_id}")

        correlation_id = correlation_id or str(uuid.uuid4())
        
        # 2. Record in Intent Ledger
        command = MissionControlCommand(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            actor_id=actor_id,
            command_type=command_type,
            payload=payload,
            state="AUTHORIZED",
            correlation_id=correlation_id,
            idempotency_key=payload.get("idempotency_key", str(uuid.uuid4()))
        )
        db.add(command)
        
        # 3. Add Initial Event
        event = MissionControlCommandEvent(
            command_id=command.id,
            event_type="INTENT_INGESTED",
            payload={"authorized": True},
            event_hash=str(uuid.uuid4()) # Placeholder for real hash chain
        )
        db.add(event)

        # 4. Create Transactional Outbox entry for dispatch
        outbox_entry = MissionControlOutbox(
            tenant_id=tenant_id,
            command_id=command.id,
            executor_type=self._resolve_executor(command_type),
            message_type="EXECUTE_INTENT",
            payload=payload,
            correlation_id=correlation_id,
            state="PENDING",
            next_attempt_at=datetime.now(UTC)
        )
        db.add(outbox_entry)
        
        return command

    def _resolve_executor(self, command_type: str) -> str:
        """Maps command types to specific executor engines."""
        if command_type.startswith("NOVA_"):
            return "nova"
        if command_type.startswith("WORKFLOW_"):
            return "workflow"
        return "default_marshal"

    async def cancel_intent(self, db: AsyncSession, tenant_id: str, command_id: str, reason: str) -> bool:
        """Initiates prioritized cancellation for an active intent."""
        command = await db.get(MissionControlCommand, command_id)
        if not command or command.tenant_id != tenant_id:
            return False
            
        if command.state in ["COMPLETED", "FAILED", "CANCELLED"]:
            return False

        # 1. Update Command State
        command.state = "CANCELLING"
        
        # 2. Add Cancellation Event
        event = MissionControlCommandEvent(
            command_id=command.id,
            event_type="CANCELLATION_REQUESTED",
            payload={"reason": reason},
            event_hash=str(uuid.uuid4())
        )
        db.add(event)
        
        # 3. Create High-Priority Outbox entry for cancellation
        outbox_entry = MissionControlOutbox(
            tenant_id=tenant_id,
            command_id=command.id,
            executor_type=self._resolve_executor(command.command_type),
            message_type="CANCEL_INTENT",
            payload={"reason": reason},
            correlation_id=command.correlation_id,
            state="PENDING",
            next_attempt_at=datetime.now(UTC)
        )
        db.add(outbox_entry)
        
        return True
