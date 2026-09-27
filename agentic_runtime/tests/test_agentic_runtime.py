from agentic_runtime.capabilities import CapabilityProfile, ModelCapabilityRegistry
from agentic_runtime.execution_loop import ExecutionMode, GovernedExecutionLoop, StepResult
from agentic_runtime.media_workflows import MediaJob, MediaKind, MediaWorkflowPolicy


def test_registry_filters_unverified_by_default():
    registry = ModelCapabilityRegistry()
    registry.register(CapabilityProfile("long-model", "local", 262144, frozenset({"reasoning"}), True, evidence_status="UNVERIFIED"))
    assert registry.candidates({"reasoning"}, 100000) == []
    assert len(registry.candidates({"reasoning"}, 100000, verified_only=False)) == 1


def test_autoheal_is_bounded_and_reverifies():
    events, verifies = [], iter([False, True])
    def authorize(action, context): return True
    def execute(action): return StepResult(action, True, changed_files=["x.py"])
    def verify(): return StepResult("verify", next(verifies), "test")
    def repair(failure, attempt): return "fix tests"
    def record(event, payload): events.append(event)
    loop = GovernedExecutionLoop(authorize=authorize, execute=execute, verify=verify, repair=repair, record=record, max_heal_attempts=2)
    results = loop.run(["build feature"], ExecutionMode.BUILD)
    assert results[-1].ok is True
    assert events.count("repair_executed") == 1


def test_denied_action_stops_execution():
    executed = []
    loop = GovernedExecutionLoop(
        authorize=lambda action, context: False,
        execute=lambda action: executed.append(action) or StepResult(action, True),
        verify=lambda: StepResult("verify", True),
        repair=lambda failure, attempt: None,
        record=lambda event, payload: None,
    )
    result = loop.run(["dangerous"])
    assert result[0].output == "DENIED_BY_POLICY"
    assert executed == []


def test_media_external_provider_fails_closed():
    policy = MediaWorkflowPolicy()
    job = MediaJob(MediaKind.VIDEO, "wf-1", {"prompt": "x"}, local_only=False, external_provider="cloud")
    assert policy.admit(job)[0] is False
