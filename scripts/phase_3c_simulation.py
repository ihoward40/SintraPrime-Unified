import asyncio
import random
import time
import uuid

from portal.services.cancellation_bus import CancellationBus, CancellationScope, CancellationSignal
from portal.services.parliament_scaling import ParliamentScalingService


async def run_scaling_simulation():
    print("=== PHASE 3C: PARLIAMENT SCALING SIMULATION ===")
    scaling_service = ParliamentScalingService()

    # Simulate high intent volume
    intent_volume = 250
    print(f"Incoming intent volume: {intent_volume}")

    start_time = time.perf_counter()
    await scaling_service.run_simulation(intent_volume)
    duration = time.perf_counter() - start_time

    status = scaling_service.get_parliament_status()
    print(f"\nFinal Parliament Status:")
    print(f"   Total Instances: {status['total_instances']}")
    print(f"   Agent Types:     {status['agent_types']}")
    print(f"   System Load:     {status['system_load']:.2%}")
    print(f"   Simulation Duration: {duration:.2f}s")

    if status['total_instances'] > 0:
        print("   Status: SCALING VERIFIED")
    else:
        print("   Status: SCALING FAILURE")

async def run_cancellation_load_test():
    print("\n=== PHASE 3C: CANCELLATION BUS LOAD TEST ===")
    bus = CancellationBus()

    # 1. Publish signals of different scopes
    print("Publishing 50 cancellation signals...")
    for i in range(50):
        scope = random.choice([CancellationScope.EXECUTION, CancellationScope.TENANT, CancellationScope.PLATFORM])
        signal = CancellationSignal(
            scope=scope,
            target_id=f"target-{i}",
            reason="Load test cancellation",
            principal_id="user-001"
        )
        await bus.publish(signal)

    # 2. Verify priority ordering
    print("\nVerifying priority delivery...")
    signal_gen = bus.subscribe()

    priorities_received = []
    for _ in range(10):
        signal = await signal_gen.__anext__()
        priorities_received.append(signal.priority)

    print(f"   First 10 priorities received: {priorities_received}")

    # Check if they are non-decreasing (0 is highest priority)
    is_ordered = all(priorities_received[i] <= priorities_received[i+1] for i in range(len(priorities_received)-1))

    if is_ordered:
        print("   Status: PRIORITY DELIVERY VERIFIED")
    else:
        print("   Status: PRIORITY DELIVERY FAILURE")

async def main():
    await run_scaling_simulation()
    await run_cancellation_load_test()
    print("\n=== PHASE 3C SIMULATION COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(main())
