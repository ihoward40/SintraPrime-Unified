from portal.services.orchestration.budget_policy import (
    BudgetLimits,
    check_budget,
    consume_budget,
    initial_budget_usage,
)
from portal.services.orchestration.model_router import route_provider
from portal.services.orchestration.provider_registry import mock_provider_registry
from portal.services.orchestration.schemas import Role, TaskType
from portal.services.orchestration.task_classifier import classify_task


def test_routes_coding_work_to_declared_coding_provider():
    classification = classify_task("Implement backend API code with tests")
    decision = route_provider(
        role=Role.WORKER,
        classification=classification,
        budget=initial_budget_usage(),
        providers=mock_provider_registry(),
    )

    assert decision.selected_provider == "coding_model"
    assert "benchmark_only_routing" in decision.policy_applied
    assert decision.estimated_cost == 0.0


def test_rejects_provider_when_sensitivity_not_allowed():
    classification = classify_task("Research privileged legal strategy", {"sensitivity": "PRIVILEGED"})
    decision = route_provider(
        role=Role.RESEARCHER,
        classification=classification,
        budget=initial_budget_usage(),
        providers=mock_provider_registry(),
    )

    assert decision.selected_provider in {"reasoning_model", "checker_model"}
    assert any(rejection["reason"] == "sensitivity_not_allowed" for rejection in decision.rejected_providers)


def test_high_assurance_can_exclude_worker_provider_for_checker_independence():
    classification = classify_task("Implement secure code")
    decision = route_provider(
        role=Role.CHECKER,
        classification=classification,
        budget=initial_budget_usage(),
        providers=mock_provider_registry(),
        exclude_provider_ids={"coding_model"},
    )

    assert decision.selected_provider == "checker_model"
    assert any(rejection["reason"] == "excluded_for_independence" for rejection in decision.rejected_providers)


def test_budget_allowlist_rejects_unapproved_provider():
    usage = initial_budget_usage(BudgetLimits(approved_providers=["checker_model"]))
    classification = classify_task("Implement backend API code")
    decision = route_provider(
        role=Role.WORKER,
        classification=classification,
        budget=usage,
        providers=mock_provider_registry(),
    )

    assert decision.selected_provider == "checker_model"
    assert any(rejection["reason"] == "provider_not_approved" for rejection in decision.rejected_providers)


def test_budget_hard_limit_blocks_node_expansion():
    usage = initial_budget_usage(BudgetLimits(maximum_nodes=1))
    assert check_budget(usage, nodes=1).allowed is True

    usage = consume_budget(usage, nodes=1)
    blocked = check_budget(usage, nodes=1, task_type=TaskType.CODING)

    assert blocked.allowed is False
    assert blocked.reason == "maximum_nodes"
