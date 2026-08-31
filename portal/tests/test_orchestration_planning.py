from portal.services.orchestration.execution_graph import topological_node_ids, validate_dag
from portal.services.orchestration.role_assignment import assign_roles
from portal.services.orchestration.schemas import ExecutionMode, Role, Sensitivity, TaskType
from portal.services.orchestration.task_classifier import classify_task
from portal.services.orchestration.task_decomposer import decompose_task


def test_classifies_mixed_confidential_task_with_governance_roles():
    classification = classify_task(
        "Implement code for trust-law research with citation checking for a confidential client"
    )

    assert classification.task_type == TaskType.MIXED
    assert classification.sensitivity == Sensitivity.CONFIDENTIAL
    assert Role.RESEARCHER in classification.required_roles
    assert Role.GOVERNANCE_REVIEWER in classification.required_roles
    assert classification.expected_cost == 0.0


def test_classification_requires_approval_for_gated_actions():
    classification = classify_task("Prepare to deploy and send external communications")

    assert classification.approval_requirement is True
    assert "deploy" in classification.prohibited_actions
    assert "send external communications" in classification.prohibited_actions


def test_high_assurance_assigns_principal_without_replacing_checker():
    roles = assign_roles(ExecutionMode.HIGH_ASSURANCE, [Role.RESEARCHER])

    assert Role.PRINCIPAL in roles
    assert Role.CHECKER in roles
    assert Role.SECURITY_REVIEWER in roles
    assert roles.index(Role.CHECKER) < roles.index(Role.PRINCIPAL)


def test_decomposition_creates_focused_instructions_and_valid_dag():
    classification = classify_task("Code a secure API endpoint with tests")
    nodes = decompose_task(
        objective="Code a secure API endpoint with tests",
        classification=classification,
        execution_mode=ExecutionMode.THINK_WORK_CHECK,
    )

    validate_dag(nodes)
    assert len(nodes) >= 5
    assert nodes[0].instructions.permitted_inputs[0] == "objective"
    assert all("Do not execute external actions." in node.instructions.constraints for node in nodes)
    root_ids = {node.node_id for node in nodes if not node.dependencies}
    assert {"planner-1", "thinker-1"}.issubset(root_ids)
    assert set(topological_node_ids(nodes)) == {node.node_id for node in nodes}


def test_dag_validation_rejects_missing_dependency():
    classification = classify_task("Draft operations runbook")
    nodes = decompose_task(
        objective="Draft operations runbook",
        classification=classification,
        execution_mode=ExecutionMode.PLAN_AND_EXECUTE,
    )
    nodes[-1].dependencies.append("missing-node")

    try:
        validate_dag(nodes)
    except ValueError as exc:
        assert "missing dependencies" in str(exc)
    else:
        raise AssertionError("Expected missing dependency validation error")
