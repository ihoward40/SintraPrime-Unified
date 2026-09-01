import asyncio
import statistics
import time
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from portal.database import Base
from portal.models.mission_control_command import (
    MissionControlCommand,
    MissionControlCommandEvent,
    MissionControlCommandReceipt,
)
from portal.models.mission_control_outbox import MissionControlOutbox
from portal.models.mission_control_run_control import MissionControlRunControl
from portal.services.memory_service import MemoryService, MemorySourceClass
from portal.services.mythos_brain import MythosBrainCoordinator


async def setup_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                sync_conn,
                tables=[
                    MissionControlCommand.__table__,
                    MissionControlCommandEvent.__table__,
                    MissionControlCommandReceipt.__table__,
                    MissionControlRunControl.__table__,
                    MissionControlOutbox.__table__,
                ],
            )
        )
    return engine

async def run_ingestion_load(memory_service, count=100):
    latencies = []
    tenant_id = "load-test-tenant"
    principal_id = "user-001"

    start_total = time.perf_counter()
    for i in range(count):
        start = time.perf_counter()
        await memory_service.ingest(
            tenant_id=tenant_id,
            source_class=MemorySourceClass.REPOSITORY,
            content=f"Load test content item {i}",
            metadata={"project": "load-test", "index": i},
            principal_id=principal_id
        )
        latencies.append(time.perf_counter() - start)
    total_time = time.perf_counter() - start_total

    return {
        "avg": statistics.mean(latencies),
        "p95": statistics.quantiles(latencies, n=20)[18],
        "throughput": count / total_time,
        "total_time": total_time
    }

async def run_coordinator_load(coordinator, engine, count=100):
    latencies = []
    tenant_id = "load-test-tenant"
    actor_id = "principal"

    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    start_total = time.perf_counter()
    async with session_maker() as session:
        for i in range(count):
            start = time.perf_counter()
            await coordinator.ingest_intent(
                session,
                tenant_id=tenant_id,
                actor_id=actor_id,
                command_type="NOVA_RESEARCH_TASK",
                payload={"query": f"test query {i}", "idempotency_key": str(uuid.uuid4())}
            )
            latencies.append(time.perf_counter() - start)
        await session.commit()
    total_time = time.perf_counter() - start_total

    return {
        "avg": statistics.mean(latencies),
        "p95": statistics.quantiles(latencies, n=20)[18],
        "throughput": count / total_time,
        "total_time": total_time
    }

async def main():
    print("=== SINTRAPRIME PHASE 3B PERFORMANCE DIAGNOSTIC ===")
    engine = await setup_db()
    memory_service = MemoryService()
    coordinator = MythosBrainCoordinator()

    print("\n1. Running Ingestion Pipeline Load (100 items)...")
    ingestion_results = await run_ingestion_load(memory_service, 100)
    print(f"   Avg Latency: {ingestion_results['avg']*1000:.2f}ms")
    print(f"   P95 Latency: {ingestion_results['p95']*1000:.2f}ms")
    print(f"   Throughput:  {ingestion_results['throughput']:.2f} req/s")

    print("\n2. Running Coordinator Intent Load (100 items)...")
    coordinator_results = await run_coordinator_load(coordinator, engine, 100)
    print(f"   Avg Latency: {coordinator_results['avg']*1000:.2f}ms")
    print(f"   P95 Latency: {coordinator_results['p95']*1000:.2f}ms")
    print(f"   Throughput:  {coordinator_results['throughput']:.2f} req/s")

    print("\n3. Integrity Check...")
    async_session = async_sessionmaker(engine, class_=AsyncSession)
    async with async_session() as session:
        from sqlalchemy import func

        from portal.models.mission_control_command import MissionControlCommand
        from portal.models.mission_control_outbox import MissionControlOutbox

        cmd_count = await session.scalar(select(func.count()).select_from(MissionControlCommand))
        outbox_count = await session.scalar(select(func.count()).select_from(MissionControlOutbox))

        print(f"   Commands recorded: {cmd_count}")
        print(f"   Outbox records:    {outbox_count}")

        if cmd_count == 100 and outbox_count == 100:
            print("   Status: INTEGRITY VERIFIED")
        else:
            print("   Status: INTEGRITY FAILURE")

    await engine.dispose()
    print("\n=== DIAGNOSTIC COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(main())
