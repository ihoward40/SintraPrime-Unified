import asyncio
import time
import uuid
import logging
from portal.services.autonomous_plane import autonomous_plane
from portal.services.parliament_scaling import scaling_service
from portal.services.cancellation_bus import bus

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Phase4Simulation")

async def run_cross_tenant_simulation():
    logger.info("=== PHASE 4: CROSS-TENANT PARLIAMENT SIMULATION ===")
    
    # 1. Define multi-tenant intents
    shared_context = "PROJECT-X-CONSOLIDATION"
    intents = [
        {"tenant_id": "tenant-a", "idempotency_key": str(uuid.uuid4()), "type": "RESEARCH"},
        {"tenant_id": "tenant-b", "idempotency_key": str(uuid.uuid4()), "type": "ANALYSIS"},
        {"tenant_id": "tenant-c", "idempotency_key": str(uuid.uuid4()), "type": "FILING"},
        {"tenant_id": "tenant-a", "idempotency_key": str(uuid.uuid4()), "type": "AUDIT"},
    ]
    
    logger.info(f"Coordinating {len(intents)} intents across 3 tenants...")
    
    # 2. Execute orchestration
    orchestration_id = await autonomous_plane.coordinate_cross_tenant_intent(intents, shared_context)
    logger.info(f"Orchestration started: {orchestration_id}")
    
    # 3. Verify status
    status = autonomous_plane.get_plane_status()
    logger.info(f"Plane State: {status['state']}")
    logger.info(f"Parliament Instances: {status['parliament_status']['total_instances']}")
    
    if status['active_orchestrations_count'] == 1 and status['parliament_status']['total_instances'] > 0:
        logger.info("Status: CROSS-TENANT COORDINATION VERIFIED")
    else:
        logger.error("Status: CROSS-TENANT COORDINATION FAILURE")
        return False
    return True

async def run_global_stop_simulation():
    logger.info("\n=== PHASE 4: GLOBAL EMERGENCY STOP SIMULATION ===")
    
    # 1. Trigger global stop
    await autonomous_plane.global_emergency_stop(
        reason="Simulated Platform Breach",
        principal_id="principal-god-mode"
    )
    
    # 2. Verify cancellation bus signal
    # Note: Since we're in the same process, we check the bus state
    if len(bus._active_cancellations) > 0:
        logger.info("Status: GLOBAL STOP SIGNAL VERIFIED")
    else:
        logger.error("Status: GLOBAL STOP SIGNAL FAILURE")
        return False
    return True

async def main():
    start = time.perf_counter()
    
    coord_success = await run_cross_tenant_simulation()
    stop_success = await run_global_stop_simulation()
    
    duration = time.perf_counter() - start
    logger.info(f"\nPhase 4 Simulation Duration: {duration:.2f}s")
    
    if coord_success and stop_success:
        logger.info("\n=== PHASE 4 ARCHITECTURE VERIFIED ===")
    else:
        logger.error("\n=== PHASE 4 ARCHITECTURE VERIFICATION FAILED ===")

if __name__ == "__main__":
    asyncio.run(main())
