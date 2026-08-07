import asyncio
import logging
import json
from datetime import datetime, UTC
from portal.services.principal_brief import brief_service
from portal.services.memory_vault import memory_vault, MemoryType
from portal.services.autonomous_plane import autonomous_plane
from portal.services.platform_hardening import hardening_service, god_mode_service

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("FirstBrief")

async def generate_production_brief():
    logger.info("🎬 GENERATING FIRST PRODUCTION PRINCIPAL BRIEF 🎬")
    tenant_id = "principal-tenant"
    
    # 1. Seed Production Milestone Memory
    logger.info("Recording production deployment milestone...")
    await memory_vault.store_memory(
        tenant_id,
        content="Full platform production deployment successful. All 10 strategic phases verified.",
        memory_type=MemoryType.INSTITUTIONAL_KNOWLEDGE,
        metadata={"milestone": "PRODUCTION_LAUNCH", "status": "CERTIFIED"}
    )
    
    await memory_vault.store_memory(
        tenant_id,
        content="Governed Identity Protocol (GIP) is now the authoritative identity standard for all agents.",
        memory_type=MemoryType.PROVEN_PROCEDURE,
        metadata={"scope": "SECURITY"}
    )

    # 2. Generate the Brief
    logger.info("Synthesizing first daily report...")
    report = await brief_service.create_brief(tenant_id)
    
    # 3. Output as formatted JSON for delivery
    print(json.dumps(report, indent=2))
    
    return report

if __name__ == "__main__":
    asyncio.run(generate_production_brief())
