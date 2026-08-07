import asyncio
import logging
import json
from portal.services.inter_agent_comm import comm_service
from portal.services.remediation_service import remediation

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Phase7BVerification")

async def run_phase_7b_verification():
    logger.info("🎬 STARTING PHASE 7B: ZERO-TRUST INTER-AGENT COMMUNICATION VERIFICATION 🎬")
    
    tenant_id = "principal-tenant"
    sender_id = "agent-architect"
    receiver_id = "agent-implementer"
    attacker_id = "agent-malicious"
    
    # 1. Test Secure Sending
    logger.info("\n[TEST 1] Secure Message Sending")
    payload = {"instruction": "Implement outbox", "secret_key": "api_key=789"}
    msg_id = await comm_service.send_secure_message(sender_id, receiver_id, tenant_id, payload)
    
    if msg_id:
        logger.info(f"Status: MESSAGE {msg_id} SENT (PASS)")
    else:
        logger.error("Status: MESSAGE SEND FAILURE (FAIL)")
        return False

    # 2. Test Secure Receiving & Verification
    logger.info("\n[TEST 2] Secure Message Receiving & Verification")
    received_msg = await comm_service.receive_secure_message(msg_id, receiver_id)
    
    if received_msg and "[MASKED]" in str(received_msg.payload):
        logger.info("Status: MESSAGE RECEIVED & REDACTED (PASS)")
    else:
        logger.error("Status: MESSAGE RECEIVE FAILURE (FAIL)")
        return False

    # 3. Test Unauthorized Access
    logger.info("\n[TEST 3] Unauthorized Receiver Access")
    unauthorized_msg = await comm_service.receive_secure_message(msg_id, attacker_id)
    
    if unauthorized_msg is None:
        logger.info("Status: UNAUTHORIZED ACCESS BLOCKED (PASS)")
    else:
        logger.error("Status: UNAUTHORIZED ACCESS BYPASS (FAIL)")
        return False

    logger.info("\n✨ PHASE 7B VERIFICATION SUCCESSFUL ✨")
    return True

if __name__ == "__main__":
    asyncio.run(run_phase_7b_verification())
