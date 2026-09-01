import asyncio
import json
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from portal.models.orchestration import OrchestrationEvent, OrchestrationRun
from portal.services.auditable_trails import auditable_trails
from portal.services.orchestration.persistence import save_run

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Phase7C")

PG_URL = "postgresql+asyncpg://sintra_app:sintra_app@localhost/sintraprime_test"

async def run_phase_7c_verification():
    logger.info("🎬 INITIALIZING PHASE 7C VERIFICATION: AUDITABLE EXECUTION TRAILS 🎬")

    engine = create_async_engine(PG_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    tenant_id = "00000000-0000-0000-0000-00000000000a"
    run_id = str(uuid.uuid4())

    async with session_factory() as session:
        # 1. SETUP: Create a run with events
        async with session.begin():
            await session.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant_id}'"))
            run_dict = {
                "run_id": run_id,
                "tenant_id": tenant_id,
                "objective": "Audit Trail Test",
                "task_type": "mixed",
                "sensitivity": "INTERNAL",
                "events": [
                    {"id": str(uuid.uuid4()), "event_type": "START", "event_hash": "h1", "payload": {"api_key": "secret-1"}},
                    {"id": str(uuid.uuid4()), "event_type": "WORK", "event_hash": "h2", "payload": {"status": "processing"}},
                    {"id": str(uuid.uuid4()), "event_type": "END", "event_hash": "h3", "payload": {"result": "success"}}
                ]
            }
            await save_run(session, run_dict)

        # 2. TEST: Generate Trail
        async with session.begin():
            await session.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant_id}'"))
            trail = await auditable_trails.generate_execution_trail(session, run_id, tenant_id)

            logger.info(f"[TEST] Trail Generated: {json.dumps(trail, indent=2)}")

            # Verify redaction in trail
            first_event = trail["events"][0]
            # Check if any key contains MASKED_KEY
            if any("MASKED_KEY" in k for k in first_event["payload"]):
                logger.info("✅ REDACTION IN TRAIL VERIFIED")
            else:
                logger.error("❌ REDACTION IN TRAIL FAILED")

            # 3. TEST: Verify Integrity
            is_valid = await auditable_trails.verify_trail_integrity(trail)
            if is_valid:
                logger.info("✅ TRAIL INTEGRITY VERIFIED")
            else:
                logger.error("❌ TRAIL INTEGRITY FAILED")

            # 4. TEST: Tamper Proofing
            trail["events"][1]["payload"]["status"] = "TAMPERED"
            is_valid_tampered = await auditable_trails.verify_trail_integrity(trail)
            if not is_valid_tampered:
                logger.info("✅ TAMPER DETECTION VERIFIED")
            else:
                logger.error("❌ TAMPER DETECTION FAILED")

    await engine.dispose()
    logger.info("✨ PHASE 7C VERIFICATION COMPLETE ✨")

if __name__ == "__main__":
    asyncio.run(run_phase_7c_verification())
