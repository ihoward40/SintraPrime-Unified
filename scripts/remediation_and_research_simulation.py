import asyncio
import logging
import json
from portal.services.remediation_service import remediation
from portal.services.research_swarm import research_swarm
from portal.services.principal_brief import brief_service
from portal.services.memory_vault import memory_vault, MemoryType

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("RemediationSimulation")

async def run_remediation_simulation():
    logger.info("🛠️ STARTING REMEDIATION & RESEARCH SIMULATION 🛠️")
    tenant_id = "principal-tenant"
    principal_id = "principal-god-mode"
    attacker_id = "unauthorized-actor"

    # 1. Test Actor Validation (Remediation)
    logger.info("\n[TEST] Verifying Actor Validation...")
    if not remediation.validate_principal(attacker_id):
        logger.info("Status: UNAUTHORIZED ACTOR BLOCKED (REMEDIATION PASS)")
    else:
        logger.error("Status: UNAUTHORIZED ACTOR BYPASS (REMEDIATION FAIL)")
        return False

    # 2. Test Sensitive Data Masking (Remediation)
    logger.info("\n[TEST] Verifying Sensitive Data Masking...")
    raw_data = {"reason": "Approval with oauth_token=secret_123", "secret": "api_key=456"}
    masked = remediation.mask_sensitive_data(raw_data)
    logger.info(f"Masked Data: {masked}")
    if "secret_123" not in str(masked) and "[MASKED]" in str(masked):
        logger.info("Status: SENSITIVE DATA MASKED (REMEDIATION PASS)")
    else:
        logger.error("Status: DATA LEAKAGE DETECTED (REMEDIATION FAIL)")
        return False

    # 3. Test Lifecycle Timestamps & Linkage (Remediation)
    logger.info("\n[TEST] Verifying Timestamps & Linkage...")
    node = remediation.inject_lifecycle_metadata({"type": "EXECUTION_NODE"})
    linkage = remediation.link_event_to_node("evt-123", node["node_id"])
    if "created_at" in node and linkage["node_id"] == node["node_id"]:
        logger.info(f"Node: {node['node_id']} created at {node['created_at']}")
        logger.info("Status: LIFECYCLE & LINKAGE PERSISTED (REMEDIATION PASS)")
    else:
        logger.error("Status: METADATA PERSISTENCE FAILURE (REMEDIATION FAIL)")
        return False

    # 4. Deploy Research Swarm (Regulatory Investigation)
    logger.info("\n[TEST] Deploying Research Swarm...")
    topic = "Q3 Emerging Regulatory Frameworks for Cross-Tenant AI"
    investigation = await research_swarm.investigate(topic, tenant_id)
    await memory_vault.store_memory(
        tenant_id, 
        content=investigation, 
        memory_type=MemoryType.INSTITUTIONAL_KNOWLEDGE,
        metadata={"category": "REGULATORY"}
    )
    logger.info(f"Status: RESEARCH SWARM COMPLETED (Investigation ID: {investigation['investigation_id']})")

    # 5. Generate Updated Principal Brief (Phase 10 Remediation)
    logger.info("\n[TEST] Generating Updated Principal Brief...")
    try:
        report = await brief_service.create_brief(tenant_id, principal_id)
        logger.info(f"Report Generated: {report['timestamp']}")
        logger.info(f"Memory Knowledge Count: {report['sections']['memory_summary']['total_knowledge']}")
        if report['sections']['memory_summary']['total_knowledge'] > 0:
            logger.info("Status: PHASE 10 REMEDIATION VERIFIED (OmniBrain Retrieval Pass)")
        else:
            logger.error("Status: PHASE 10 REMEDIATION FAIL (Empty Retrieval)")
            return False
    except Exception as e:
        logger.error(f"Status: BRIEF GENERATION ERROR: {e}")
        return False

    logger.info("\n✨ REMEDIATION & RESEARCH SIMULATION SUCCESSFUL ✨")
    return True

if __name__ == "__main__":
    asyncio.run(run_remediation_simulation())
