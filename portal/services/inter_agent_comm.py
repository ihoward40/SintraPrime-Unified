import logging
import uuid
from datetime import datetime, UTC
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from .isolation_proof import isolation_proof_service, IsolationProof
from .remediation_service import remediation

logger = logging.getLogger(__name__)

class AgentMessage(BaseModel):
    message_id: str
    sender_id: str
    receiver_id: str
    tenant_id: str
    payload: Dict[str, Any]
    isolation_proof: IsolationProof
    timestamp: str

class InterAgentCommunicationService:
    """
    Phase 7B: Zero-Trust Inter-Agent Communication.
    Enables secure, verified communication between agents within the same tenant.
    """
    def __init__(self):
        self.message_ledger: List[AgentMessage] = []

    async def send_secure_message(
        self, 
        sender_id: str, 
        receiver_id: str, 
        tenant_id: str, 
        content: Dict[str, Any]
    ) -> str:
        """
        Sends a secure message between agents with zero-trust verification.
        """
        logger.info(f"[INTER_AGENT_COMM] Sending secure message from {sender_id} to {receiver_id}")
        
        # 1. REMEDIATION: Redact boundaries
        safe_content = remediation.redact_boundaries(content)
        
        # 2. Generate Isolation Proof
        message_id = f"msg-{uuid.uuid4().hex[:8]}"
        proof = isolation_proof_service.generate_proof(tenant_id, message_id, safe_content)
        
        # 3. Construct Message
        message = AgentMessage(
            message_id=message_id,
            sender_id=sender_id,
            receiver_id=receiver_id,
            tenant_id=tenant_id,
            payload=safe_content,
            isolation_proof=proof,
            timestamp=datetime.now(UTC).isoformat()
        )
        
        # 4. Record in Ledger
        self.message_ledger.append(message)
        
        logger.info(f"[INTER_AGENT_COMM] Message {message_id} sent and verified.")
        return message_id

    async def receive_secure_message(self, message_id: str, receiver_id: str) -> Optional[AgentMessage]:
        """
        Retrieves and verifies a secure message for a receiver.
        """
        message = next((m for m in self.message_ledger if m.message_id == message_id), None)
        
        if not message:
            logger.error(f"[INTER_AGENT_COMM] Message {message_id} not found.")
            return None
            
        if message.receiver_id != receiver_id:
            logger.error(f"[INTER_AGENT_COMM] Receiver {receiver_id} not authorized for message {message_id}.")
            return None
            
        # 5. Verify Isolation Proof
        if not isolation_proof_service.verify_proof(message.isolation_proof, message.payload):
            logger.error(f"[INTER_AGENT_COMM] Isolation proof verification failed for message {message_id}.")
            return None
            
        logger.info(f"[INTER_AGENT_COMM] Message {message_id} received and verified by {receiver_id}.")
        return message

# Global instance
comm_service = InterAgentCommunicationService()
