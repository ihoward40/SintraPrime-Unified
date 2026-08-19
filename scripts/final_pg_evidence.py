import asyncio
import json
import logging
import uuid
from datetime import UTC, datetime

import asyncpg
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from portal.database import Base
from portal.models.orchestration import (
    ApprovalRequest,
    MemoryEntry,
    OrchestrationEvent,
    OrchestrationLinkage,
    OrchestrationNode,
    OrchestrationRun,
    PrincipalAuthority,
)
from portal.services.memory_vault import memory_vault
from portal.services.mythos_brain import MythosBrainCoordinator
from portal.services.principal_brief import brief_service
from portal.services.remediation_service import remediation

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("PGEvidence")

# PostgreSQL connection string (local sandbox)
PG_URL = "postgresql+asyncpg://sintra_app:sintra_app@localhost/sintraprime_test"

async def run_pg_evidence():
    logger.info("🎬 GENERATING AUTHORITATIVE POSTGRESQL/RLS EVIDENCE 🎬")

    # Superuser engine for seeding
    ROOT_URL = "postgresql+asyncpg://postgres:postgres@localhost/sintraprime_test"
    root_engine = create_async_engine(ROOT_URL)
    root_session_factory = async_sessionmaker(root_engine, expire_on_commit=False, class_=AsyncSession)

    # App engine for testing
    engine = create_async_engine(PG_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    evidence = {
        "timestamp": datetime.now(UTC).isoformat(),
        "environment": "PostgreSQL 16 / Ubuntu 24.04",
        "results": []
    }

    tenant_a_id = "00000000-0000-0000-0000-00000000000a"
    tenant_b_id = "00000000-0000-0000-0000-00000000000b"
    principal_id = "00000000-0000-0000-0000-000000000001"

    async with root_session_factory() as session:
        # CLEAN STATE
        await session.execute(text("TRUNCATE tenants, roles, users, orchestration_runs, orchestration_nodes, orchestration_events, orchestration_approval_requests, orchestration_linkages, orchestration_principal_authorities, memory_vault CASCADE"))
        await session.commit()

        # 0. SEED AUTHORITIES (Finding 5)
        logger.info("[STEP 0] Seeding Principal Authority")
        # Seed base tables for FKs
        await session.execute(text(f"INSERT INTO tenants (id, name, slug) VALUES ('{tenant_a_id}', 'Tenant A', 'tenant-a')"))
        await session.execute(text(f"INSERT INTO tenants (id, name, slug) VALUES ('{tenant_b_id}', 'Tenant B', 'tenant-b')"))
        role_id = str(uuid.uuid4())
        await session.execute(text(f"INSERT INTO roles (id, name) VALUES ('{role_id}', 'PRINCIPAL')"))
        await session.execute(text(f"INSERT INTO users (id, tenant_id, role_id, email) VALUES ('{principal_id}', '{tenant_a_id}', '{role_id}', 'principal@tenant-a.com')"))

        auth = PrincipalAuthority(
            id=str(uuid.uuid4()),
            tenant_id=tenant_a_id,
            user_id=principal_id,
            scope="GOD_MODE",
            is_active=True
        )
        session.add(auth)
        await session.commit()

    await root_engine.dispose()

    async with session_factory() as session:

        # 1. TEST RLS ISOLATION (Finding 2)
        logger.info("[TEST 1] RLS Tenant Isolation")
        run_a_id = str(uuid.uuid4())
        # Set tenant context
        await session.execute(text(f"SET app.current_tenant_id = '{tenant_a_id}'"))
        run_a = OrchestrationRun(
            id=run_a_id, tenant_id=tenant_a_id, objective="Tenant A Task",
            task_type="mixed", sensitivity="INTERNAL", execution_mode="SINGLE"
        )
        session.add(run_a)
        await session.commit()

        # Try to read from Tenant B context
        await session.execute(text(f"SET app.current_tenant_id = '{tenant_b_id}'"))
        res = await session.execute(select(OrchestrationRun).where(OrchestrationRun.id == run_a_id))
        rls_status = "PASS" if res.scalar_one_or_none() is None else "FAIL"
        evidence["results"].append({"gate": "PostgreSQL RLS Isolation", "status": rls_status})
        await session.commit()

        # 2. TEST APPEND-ONLY AUDIT (Finding 1)
        logger.info("[TEST 2] Append-Only Audit Integrity")
        # Save run first time
        from portal.services.orchestration.persistence import save_run
        run_dict = {
            "run_id": run_a_id, "tenant_id": tenant_a_id, "objective": "Audit Test",
            "events": [{"id": str(uuid.uuid4()), "event_type": "INIT", "event_hash": "h1"}]
        }
        await session.execute(text(f"SET app.current_tenant_id = '{tenant_a_id}'"))
        await save_run(session, run_dict)
        await session.commit()

        # Save run second time with new event
        event_2_id = str(uuid.uuid4())
        run_dict["events"].append({"id": event_2_id, "event_type": "WORK", "event_hash": "h2"})
        await session.execute(text(f"SET app.current_tenant_id = '{tenant_a_id}'"))
        await save_run(session, run_dict)
        await session.commit()

        # Verify both events exist (no deletion)
        await session.execute(text(f"SET app.current_tenant_id = '{tenant_a_id}'"))
        res = await session.execute(select(OrchestrationEvent).where(OrchestrationEvent.run_id == run_a_id))
        events = res.scalars().all()
        audit_status = "PASS" if len(events) == 2 else "FAIL"
        evidence["results"].append({"gate": "Append-Only Audit (No Deletion)", "status": audit_status})
        await session.commit()

        # 3. TEST REDACTION (Finding 4)
        logger.info("[TEST 3] Boundary Redaction (Keys & Values)")
        payload = {"api_key": "secret-123", "nested": {"oauth_token": "secret-456"}}
        redacted = remediation.redact_boundaries(payload)
        redact_status = "PASS" if "[MASKED_KEY_api_key]" in redacted and "[MASKED_VALUE]" in redacted["[MASKED_KEY_api_key]"] else "FAIL"
        evidence["results"].append({"gate": "Boundary Redaction (Keys/Values)", "status": redact_status})

        # 4. TEST CONCURRENT APPROVAL (Finding 6)
        logger.info("[TEST 4] Concurrent Approval Safety")
        app_id = str(uuid.uuid4())
        await session.execute(text(f"SET app.current_tenant_id = '{tenant_a_id}'"))
        approval = ApprovalRequest(
            id=app_id, run_id=run_a_id, requested_action="Test", reason="Test",
            risk_level="high", status="REQUESTED", requested_by_role="WORKER", version=1
        )
        session.add(approval)
        await session.commit()

        # Simulate two concurrent updates
        await session.execute(text(f"SET app.current_tenant_id = '{tenant_a_id}'"))
        success_1 = await remediation.record_approval_with_concurrency_safety(
            session, app_id, principal_id, "APPROVED", "First", 1
        )
        success_2 = await remediation.record_approval_with_concurrency_safety(
            session, app_id, principal_id, "DENIED", "Second", 1
        )
        await session.commit()

        concurrency_status = "PASS" if success_1 and not success_2 else "FAIL"
        evidence["results"].append({"gate": "Concurrent Approval Safety", "status": concurrency_status})

        # 5. TEST DURABLE LINKAGE (Finding 7)
        logger.info("[TEST 5] Durable Event-to-Node Linkage")
        node_id = "node-1"
        run_dict["nodes"] = [{"node_id": node_id, "role": "WORKER", "objective": "Work"}]
        run_dict["events"].append({"id": str(uuid.uuid4()), "event_type": "NODE_START", "event_hash": "h3", "node_id": node_id})
        await session.execute(text(f"SET app.current_tenant_id = '{tenant_a_id}'"))
        await save_run(session, run_dict)
        await session.commit()

        await session.execute(text(f"SET app.current_tenant_id = '{tenant_a_id}'"))
        res = await session.execute(select(OrchestrationLinkage).where(OrchestrationLinkage.tenant_id == tenant_a_id))
        linkage = res.scalars().first()
        linkage_status = "PASS" if linkage is not None else "FAIL"
        evidence["results"].append({"gate": "Durable Event-Node Linkage", "status": linkage_status})
        await session.commit()

    # Output evidence to repo
    report_path = "artifacts/remediation_evidence_report.json"
    with open(f"/home/ubuntu/SintraPrime-Unified/{report_path}", "w") as f:
        json.dump(evidence, f, indent=2)

    logger.info(f"✨ EVIDENCE COMMITTED TO {report_path} ✨")
    await engine.dispose()
    return evidence

if __name__ == "__main__":
    asyncio.run(run_pg_evidence())
