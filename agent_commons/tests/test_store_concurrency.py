from concurrent.futures import ThreadPoolExecutor

from agent_commons.models import LifecycleStatus, MessageRecord, SupervisorRun
from agent_commons.store import AgentCommonsStore


def test_store_serializes_concurrent_reads_and_writes(tmp_path):
    store = AgentCommonsStore(str(tmp_path / "agent_commons.sqlite3"))
    run = SupervisorRun(
        tenant_id="tenant-a",
        workspace_id="workspace-a",
        channel_id="channel-a",
        thread_id="thread-a",
        objective="exercise concurrent access",
        owner_agent="owner",
        builder_agent="builder",
        reviewer_agent="reviewer",
        acceptance_criteria=["no sqlite race errors"],
    )
    store.save_run(run, idempotency_key="concurrency-test")

    def append(index: int) -> None:
        store.append_message(
            MessageRecord(
                tenant_id="tenant-a",
                workspace_id="workspace-a",
                channel_id="channel-a",
                thread_id="thread-a",
                task_id=run.task_id,
                from_agent=f"worker-{index}",
                to_agents=["supervisor"],
                status=LifecycleStatus.RESULT,
                payload={"index": index},
            )
        )

    def read(_: int) -> tuple[str, int]:
        stored = store.get_run("tenant-a", run.run_id)
        messages = store.get_thread(
            "tenant-a",
            "workspace-a",
            "channel-a",
            "thread-a",
        )
        return stored.run_id, len(messages)

    with ThreadPoolExecutor(max_workers=12) as executor:
        append_futures = [executor.submit(append, index) for index in range(100)]
        read_futures = [executor.submit(read, index) for index in range(100)]
        for future in append_futures:
            future.result()
        read_results = [future.result() for future in read_futures]

    assert all(run_id == run.run_id for run_id, _ in read_results)
    assert len(
        store.get_thread(
            "tenant-a",
            "workspace-a",
            "channel-a",
            "thread-a",
        )
    ) == 100
