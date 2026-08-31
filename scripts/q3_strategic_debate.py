import asyncio
import logging
import json
from portal.services.council_mode import council_mode
from portal.services.memory_vault import memory_vault, MemoryType

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Q3StrategicDebate")

async def run_q3_debate():
    logger.info("🏛️ INITIATING COUNCIL MODE: Q3 AUTONOMOUS EXPANSION PRIORITIES 🏛️")
    
    intent_id = "q3-expansion-strategy"
    context = {
        "priorities": [
            "Cross-tenant knowledge sharing",
            "Predictive resource allocation",
            "Autonomous legal filing automation",
            "VLM-driven document forensic auditing"
        ],
        "constraints": ["Zero-trust isolation", "Minimal platform overhead"]
    }
    
    # 1. Initiate multi-model debate
    decision = await council_mode.initiate_debate(intent_id, context)
    
    # 2. Store the strategic decision in OmniBrain
    tenant_id = "principal-tenant"
    await memory_vault.store_memory(
        tenant_id,
        content={
            "strategic_intent": intent_id,
            "consensus": decision.consensus_reached,
            "recommendation": decision.recommendation,
            "votes": decision.votes,
            "rationale": decision.rationale
        },
        memory_type=MemoryType.INSTITUTIONAL_KNOWLEDGE,
        metadata={"category": "STRATEGY", "quarter": "2026-Q3"}
    )
    
    # 3. Output results
    print(json.dumps(decision.model_dump(), indent=2))
    return decision

if __name__ == "__main__":
    asyncio.run(run_q3_debate())
