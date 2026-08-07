import asyncio
import logging
import json
from portal.services.council_mode import council_mode
from portal.services.memory_vault import memory_vault
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from portal.database import Base

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("IsolationDebate")

DATABASE_URL = "sqlite+aiosqlite:///:memory:"

async def run_isolation_debate():
    logger.info("🏛️ INITIATING COUNCIL MODE: CRYPTOGRAPHIC ISOLATION ARCHITECTURE 🏛️")
    
    # Setup mock session
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    intent_id = "isolation-proof-architecture"
    context = {
        "proposal": "HMAC-SHA256 per-tenant isolation proofs",
        "benefits": ["Cryptographic proof of data sovereignty", "Auditable cross-tenant sharing"],
        "concerns": ["Key management overhead", "Performance impact on high-throughput ingestion"]
    }
    
    # 1. Initiate multi-model debate
    decision = await council_mode.initiate_debate(intent_id, context)
    
    # 2. Store the strategic decision in OmniBrain
    async with session_factory() as session:
        tenant_id = "principal-tenant"
        await memory_vault.store_memory(
            session,
            tenant_id,
            content={
                "strategic_intent": intent_id,
                "consensus": decision.consensus_reached,
                "recommendation": decision.recommendation,
                "votes": decision.votes,
                "rationale": decision.rationale
            },
            memory_type="INSTITUTIONAL_KNOWLEDGE",
            metadata={"category": "ARCHITECTURE", "focus": "SECURITY"}
        )
        await session.commit()
    
    # 3. Output results
    print(json.dumps(decision.model_dump(), indent=2))
    await engine.dispose()
    return decision

if __name__ == "__main__":
    asyncio.run(run_isolation_debate())
