import asyncio
import logging
import json
import uuid
from datetime import datetime, UTC
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from portal.database import Base
from portal.services.remediation_service import remediation
from portal.services.memory_vault import memory_vault
from portal.services.mythos_brain import MythosBrainCoordinator
from portal.services.principal_brief import brief_service
from portal.services.isolation_proof import isolation_proof_service
from portal.services.council_mode import council_mode
from portal.models.mission_control_outbox import MissionControlOutbox, EventNodeLinkage, MemoryEntry
from sqlalchemy import select

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("FinalEvidence")

DATABASE_URL = "sqlite+aiosqlite:///:memory:"

async def run_final_evidence():
    logger.info("🎬 GENERATING FINAL MACHINE-READABLE EVIDENCE 🎬")
    
    # 1. Setup DB
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    evidence = {"timestamp": datetime.now(UTC).isoformat(), "results": []}
    tenant_id = "principal-tenant"
    principal_id = "principal-god-mode"

    async with session_factory() as session:
        # --- TEST 1: ACTOR VALIDATION ---
        logger.info("[TEST 1] Actor Validation")
        coordinator = MythosBrainCoordinator(session)
        try:
            await coordinator.ingest_intent(tenant_id, "attacker", "PRINCIPAL_COMMAND", {})
            val_status = "FAIL"
        except PermissionError:
            val_status = "PASS"
        evidence["results"].append({"gate": "Actor Validation", "status": val_status})

        # --- TEST 2: REDACTION ---
        logger.info("[TEST 2] Boundary Redaction")
        intent_id = await coordinator.ingest_intent(
            tenant_id, principal_id, "STANDARD", {"secret": "oauth_token=123"}
        )
        await session.commit()
        
        # Verify redaction
        res = await session.execute(select(MissionControlOutbox).where(MissionControlOutbox.intent_id == intent_id))
        entry = res.scalar_one()
        redact_status = "PASS" if "123" not in str(entry.payload) and "[MASKED]" in str(entry.payload) else "FAIL"
        evidence["results"].append({"gate": "Boundary Redaction", "status": redact_status})

        # --- TEST 3: LINKAGE & TIMESTAMPS ---
        logger.info("[TEST 3] Linkage & Timestamps")
        link_res = await session.execute(select(EventNodeLinkage).where(EventNodeLinkage.tenant_id == tenant_id))
        linkage = link_res.scalar_one()
        link_status = "PASS" if linkage.node_id == entry.payload["node_id"] else "FAIL"
        evidence["results"].append({"gate": "Durable Linkage", "status": link_status})

        # --- TEST 4: PHASE 7A ISOLATION PROOF ---
        logger.info("[TEST 4] Cryptographic Isolation Proof")
        proof = isolation_proof_service.generate_proof(tenant_id, "res-1", "sensitive-content")
        is_valid = isolation_proof_service.verify_proof(proof, "sensitive-content")
        proof_status = "PASS" if is_valid else "FAIL"
        evidence["results"].append({"gate": "Isolation Proof", "status": proof_status})

        # --- TEST 5: PHASE 10 OMNIBRAIN TO BRIEF ---
        logger.info("[TEST 5] Phase 10 Pipeline")
        await memory_vault.store_memory(session, tenant_id, "Production Milestone", "INSTITUTIONAL_KNOWLEDGE")
        await session.commit()
        report = await brief_service.create_brief(session, tenant_id, principal_id)
        brief_status = "PASS" if report["sections"]["memory_summary"]["total_knowledge"] > 0 else "FAIL"
        evidence["results"].append({"gate": "Phase 10 Pipeline", "status": brief_status})

    # Output evidence
    with open("/home/ubuntu/final_evidence_report.json", "w") as f:
        json.dump(evidence, f, indent=2)
    
    logger.info("✨ FINAL EVIDENCE GENERATED ✨")
    await engine.dispose()
    return evidence

if __name__ == "__main__":
    asyncio.run(run_final_evidence())
