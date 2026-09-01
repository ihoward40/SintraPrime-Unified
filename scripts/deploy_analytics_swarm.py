import asyncio
import json
import logging

from portal.services.build_swarm import build_swarm
from portal.services.memory_vault import MemoryType, memory_vault

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AnalyticsSwarm")

async def deploy_analytics_plugin():
    logger.info("🐝 DEPLOYING BUILD SWARM: CROSS-TENANT ANALYTICS PLUGIN 🐝")

    project_id = "analytics-plugin-v1"
    requirement = """
    Architect and implement a cross-tenant analytics plugin that:
    1. Aggregates anonymized performance metrics across all tenants.
    2. Respects strict zero-trust isolation boundaries.
    3. Provides real-time visual projections to the Principal Command dashboard.
    """

    # 1. Execute full build workflow
    result = await build_swarm.execute_build_workflow(project_id, requirement)

    # 2. Store the build audit trail in OmniBrain
    tenant_id = "principal-tenant"
    await memory_vault.store_memory(
        tenant_id,
        content=result,
        memory_type=MemoryType.PROVEN_PROCEDURE,
        metadata={"category": "BUILD", "project": project_id}
    )

    # 3. Output results
    print(json.dumps(result, indent=2))
    return result

if __name__ == "__main__":
    asyncio.run(deploy_analytics_plugin())
