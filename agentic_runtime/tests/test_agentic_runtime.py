from agentic_runtime.capabilities import CapabilityProfile, ModelCapabilityRegistry
from agentic_runtime.controls import CircuitBreaker
from agentic_runtime.execution_loop import ExecutionMode, GovernedExecutionLoop, StepResult
from agentic_runtime.media_workflows import MediaJob, MediaKind, MediaWorkflowPolicy


def test_registry_filters_unverified_by_default():
    registry = ModelCapabilityRegistry()
    registry.register(CapabilityProfile("long-model", "local", 262144, frozenset({"reasoning"}), True, evidence_status="UNVERIFIED"))
    assert registry.candidates({"reasoning"}, 100000) == []
    assert len(registry.candidates({"reasoning"}, 100000, verified_only=False)) == 1


def test_autoheal_is_bounded_and_reverifies():
    events, verifies = [], iter([False, True])

    def authorize(*_args): return True

    def execute(action): return StepResult(action, True, changed_files=["x.py"])

    def verify(): return StepResult("verify", next(verifies), "test")

    def repair(*_args): return "fix tests"

    def record(event, *_args): events.append(event)

    loop = GovernedExecutionLoop(authorize=authorize, execute=execute, verify=verify, repair=repair, record=record, max_heal_attempts=2)
    results = loop.run(["build feature"], ExecutionMode.BUILD)
    assert results[-1].ok is True
    assert events.count("repair_executed") == 1


def test_denied_action_stops_execution():
    executed = []
    loop = GovernedExecutionLoop(
        authorize=lambda *_args: False,
        execute=lambda action: executed.append(action) or StepResult(action, True),
        verify=lambda: StepResult("verify", True),
        repair=lambda *_args: None,
        record=lambda *_args: None,
    )
    result = loop.run(["dangerous"])
    assert result[0].output == "DENIED_BY_POLICY"
    assert executed == []


def test_autoheal_allows_first_repair_when_breaker_limit_is_one():
    verifies = iter([False, True])
    loop = GovernedExecutionLoop(
        authorize=lambda *_args: True,
        execute=lambda action: StepResult(action, True),
        verify=lambda: StepResult("verify", next(verifies), "test"),
        repair=lambda *_args: "fix tests",
        record=lambda *_args: None,
        max_heal_attempts=1,
        circuit_breaker=CircuitBreaker(1),
    )

    results = loop.run(["build feature"], ExecutionMode.BUILD)

    assert [result.action for result in results] == ["build feature", "verify", "fix tests", "verify"]
    assert results[-1].ok is True


def test_autoheal_records_unavailable_and_denied_terminal_states():
    unavailable = GovernedExecutionLoop(
        authorize=lambda *_args: True,
        execute=lambda action: StepResult(action, True),
        verify=lambda: StepResult("verify", False, "test"),
        repair=lambda *_args: None,
        record=lambda *_args: None,
        max_heal_attempts=1,
    )
    denied = GovernedExecutionLoop(
        authorize=lambda _action, context: context["mode"] == ExecutionMode.BUILD,
        execute=lambda action: StepResult(action, True),
        verify=lambda: StepResult("verify", False, "test"),
        repair=lambda *_args: "fix tests",
        record=lambda *_args: None,
        max_heal_attempts=1,
    )

    unavailable_results = unavailable.run(["build feature"], ExecutionMode.BUILD)
    denied_results = denied.run(["build feature"], ExecutionMode.BUILD)

    assert unavailable_results[-1].output == "REPAIR_UNAVAILABLE"
    assert denied_results[-1].output == "REPAIR_DENIED_BY_POLICY"


def test_media_external_provider_fails_closed():
    policy = MediaWorkflowPolicy()
    job = MediaJob(MediaKind.VIDEO, "wf-1", {"prompt": "x"}, local_only=False, external_provider="cloud")
    assert policy.admit(job)[0] is False
