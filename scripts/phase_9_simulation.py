import asyncio
import logging
from portal.services.memory_vault import memory_vault, MemoryType
from portal.services.principal_brief import brief_service
from portal.services.autonomous_plane import autonomous_plane

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Phase9Simulation")

async def run_omnibrain_simulation():
    logger.info("=== PHASE 9: OMNIBRAIN MEMORY VAULT SIMULATION ===")
    
    tenant_id = "tenant-alpha"
    
    # 1. Store Learned Lesson
    logger.info("Storing learned lesson...")
    lesson_id = await memory_vault.store_memory(
        tenant_id,
        content="Always verify Pydantic enums before cross-PR handoff.",
        memory_type=MemoryType.LESSON_LEARNED,
        metadata={"source": "PR-255-FIX", "priority": "HIGH"}
    )
    
    # 2. Store Proven Procedure
    logger.info("Storing proven procedure...")
    proc_id = await memory_vault.store_memory(
        tenant_id,
        content="Unified Execution Protocol: Validate -> Ingest -> Dispatch -> Audit.",
        memory_type=MemoryType.PROVEN_PROCEDURE,
        metadata={"author": "Mythos-Brain"}
    )
    
    # 3. Retrieve Memory
    memories = await memory_vault.retrieve_tenant_memory(tenant_id)
    logger.info(f"Retrieved {len(memories)} memory entries for {tenant_id}")
    
    if len(memories) == 2 and lesson_id and proc_id:
        logger.info("Status: OMNIBRAIN MEMORY VAULT VERIFIED")
        return True
    else:
        logger.error("Status: OMNIBRAIN MEMORY VAULT FAILURE")
        return False

async def run_principal_brief_simulation():
    logger.info("\n=== PHASE 9: PRINCIPAL BRIEF SIMULATION ===")
    
    tenant_id = "tenant-alpha"
    
    # 1. Trigger some activity for the report
    await autonomous_plane.coordinate_cross_tenant_intent(
        [{"tenant_id": tenant_id, "idempotency_key": "sim-123", "type": "BRIEF_GEN"}],
        "SIM-CONTEXT"
    )
    
    # 2. Generate Brief
    logger.info(f"Generating Principal Brief for {tenant_id}...")
    report = await brief_service.create_brief(tenant_id)
    
    logger.info(f"Report Timestamp: {report['timestamp']}")
    logger.info(f"Total Lessons: {report['sections']['memory_summary']['total_lessons']}")
    logger.info(f"Active Orchestrations: {report['sections']['operations']['active_orchestrations']}")
    
    if report['sections']['memory_summary']['total_lessons'] > 0 and report['sections']['operations']['active_orchestrations'] > 0:
        logger.info("Status: PRINCIPAL BRIEF VERIFIED")
        return True
    else:
        logger.error("Status: PRINCIPAL BRIEF FAILURE")
        return False

async def main():
    vault_success = await run_omnibrain_simulation()
    brief_success = await run_principal_brief_simulation()
    
    if vault_success and brief_success:
        logger.info("\n=== PHASE 9 ARCHITECTURE VERIFIED ===")
    else:
        logger.error("\n=== PHASE 9 ARCHITECTURE VERIFICATION FAILED ===")

if __name__ == "__main__":
    asyncio.run(main())
