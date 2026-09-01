import asyncio
import logging

from portal.services.build_swarm import build_swarm
from portal.services.council_mode import council_mode

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Phase8Simulation")

async def run_council_mode_simulation():
    logger.info("=== PHASE 8: COUNCIL MODE SIMULATION ===")

    intent_id = "strategic-intent-001"
    context = {"target": "cross-tenant-consolidation"}

    decision = await council_mode.initiate_debate(intent_id, context)

    logger.info(f"Consensus: {decision.consensus_reached}")
    logger.info(f"Recommendation: {decision.recommendation}")

    if decision.consensus_reached and len(decision.votes) == 3:
        logger.info("Status: COUNCIL MODE VERIFIED")
        return True
    logger.error("Status: COUNCIL MODE FAILURE")
    return False

async def run_build_swarm_simulation():
    logger.info("\n=== PHASE 8: BUILD SWARM SIMULATION ===")

    project_id = "project-delta"
    requirement = "Implement secure multi-tenant outbox"

    result = await build_swarm.execute_build_workflow(project_id, requirement)

    logger.info(f"Project Status: {result['status']}")
    logger.info(f"Audit Trail Depth: {len(result['audit_trail'])}")

    if result['status'] == "CERTIFIED" and len(result['audit_trail']) == 5:
        logger.info("Status: BUILD SWARM VERIFIED")
        return True
    logger.error("Status: BUILD SWARM FAILURE")
    return False

async def main():
    council_success = await run_council_mode_simulation()
    build_success = await run_build_swarm_simulation()

    if council_success and build_success:
        logger.info("\n=== PHASE 8 ARCHITECTURE VERIFIED ===")
    else:
        logger.error("\n=== PHASE 8 ARCHITECTURE VERIFICATION FAILED ===")

if __name__ == "__main__":
    asyncio.run(main())
