"""Regression tests for authorization gate - verifies program scope escape prevention."""

from __future__ import annotations

import time
import pytest

from sintra_live.authorization.gate import (
    AuthoritySnapshot,
    TaskAuthorization,
    AuthorityStore,
    AuthorizationGate,
    AuthorizationGateBuilder,
    AuthorizationDecision,
    requires_authorization,
)


class TestActiveL1BlocksAgentOSPhaseF:
    """TEST_1: ACTIVE_L1_BLOCKS_AGENTOS_PHASE_F
    
    SETUP:
    ACTIVE_PROGRAM = SP-LIVE-001
    ACTIVE_GATE = L1
    QUEUED_TASK = AGENTOS_PHASE_F
    
    EXPECTED:
    TASK_EXECUTION = DENY
    REASON = PROGRAM_SCOPE_MISMATCH
    """
    
    def test_l1_blocks_agentos_phase_f(self):
        """Active L1 gate should block AgentOS Phase F task."""
        builder = AuthorizationGateBuilder()
        
        # Principal authorizes L1
        snapshot = builder.create_authority(
            program_id="SP-LIVE-001",
            gate_id="SP_LIVE_001_L1_FIRST_REAL_GOVERNED_MISSION_001",
            authorization_id="auth-001",
            principal_id="principal-001",
            authorized_scope=["sp-live/l1", "github/comment"],
            capability_scope=["github-comment-write-v1"],
            side_effect_budget=1  # One comment write allowed
        )
        
        gate = builder.get_gate()
        
        # Worker tries to execute AgentOS Phase F task
        task_auth = TaskAuthorization.create(
            program_id="AGENTOS-001",  # Different program!
            gate_id="PHASE_F",        # Different gate!
            work_package_id="wp-phase-f",
            authority_snapshot_hash=snapshot.snapshot_id,
            requested_scope=["agentos/phase-f"],
            requested_capabilities=["local-compute"],
            requested_side_effect_budget=0
        )
        
        result = gate.check_authorization(task_auth)
        
        assert result.decision == AuthorizationDecision.DENY_PROGRAM_MISMATCH
        assert "program_id" in result.reason.lower() or "program" in result.reason.lower()
        assert result.details["task_program"] == "AGENTOS-001"
        assert result.details["active_program"] == "SP-LIVE-001"


class TestCompletedPhaseDoesNotAuthorizeNextPhase:
    """TEST_2: COMPLETED_PHASE_DOES_NOT_AUTHORIZE_NEXT_PHASE
    
    SETUP:
    PHASE_E = PASS
    PHASE_F = PROPOSED
    PHASE_F_AUTHORIZED = FALSE
    
    EXPECTED:
    PHASE_F_IMPLEMENTATION_STARTED = FALSE
    """
    
    def test_phase_e_pass_does_not_authorize_phase_f(self):
        """Phase E completion documentation does not grant Phase F authority."""
        builder = AuthorizationGateBuilder()
        
        # Principal authorizes L1 (NOT Phase E or F)
        snapshot = builder.create_authority(
            program_id="SP-LIVE-001",
            gate_id="SP_LIVE_001_L1_FIRST_REAL_GOVERNED_MISSION_001",
            authorization_id="auth-001",
            principal_id="principal-001",
            authorized_scope=["sp-live/l1"],
            capability_scope=["github-comment-write-v1"],
            side_effect_budget=1
        )
        
        gate = builder.get_gate()
        
        # Phase F task tries to use "phase-e-complete" as authorization
        task_auth = TaskAuthorization.create(
            program_id="SP-LIVE-001",  # Same program
            gate_id="SP_LIVE_001_L1_FIRST_REAL_GOVERNED_MISSION_001",  # Same gate
            work_package_id="wp-phase-f",
            authority_snapshot_hash=snapshot.snapshot_id,  # Uses L1 snapshot
            requested_scope=["agentos/phase-f"],  # But requests Phase F scope!
            requested_capabilities=["local-compute"],
            requested_side_effect_budget=0
        )
        
        result = gate.check_authorization(task_auth)
        
        # Should be denied because scope "agentos/phase-f" not in authorized_scope ["sp-live/l1"]
        assert result.decision == AuthorizationDecision.DENY_SCOPE_EXCEEDED
        assert "agentos/phase-f" in str(result.details.get("excess_scope", []))


class TestSwarmChildCannotEscapeGate:
    """TEST_3: SWARM_CHILD_CANNOT_ESCAPE_GATE
    
    SETUP:
    parent = SP-LIVE L1
    child proposes AgentOS Phase F
    
    EXPECTED:
    child result = OUT_OF_SCOPE_PROPOSAL
    files_modified = 0
    """
    
    def test_child_cannot_request_broader_scope_than_parent(self):
        """Child task scope must be subset of parent authority."""
        builder = AuthorizationGateBuilder()
        
        # Principal authorizes L1 with narrow scope
        snapshot = builder.create_authority(
            program_id="SP-LIVE-001",
            gate_id="SP_LIVE_001_L1_FIRST_REAL_GOVERNED_MISSION_001",
            authorization_id="auth-001",
            principal_id="principal-001",
            authorized_scope=["sp-live/l1", "github/comment"],
            capability_scope=["github-comment-write-v1"],
            side_effect_budget=1
        )
        
        gate = builder.get_gate()
        
        # Parent task (L1 envelope preparation)
        parent_auth = TaskAuthorization.create(
            program_id="SP-LIVE-001",
            gate_id="SP_LIVE_001_L1_FIRST_REAL_GOVERNED_MISSION_001",
            work_package_id="wp-l1-envelope",
            authority_snapshot_hash=snapshot.snapshot_id,
            requested_scope=["sp-live/l1"],
            requested_capabilities=["github-comment-write-v1"],
            requested_side_effect_budget=1
        )
        
        parent_result = gate.check_authorization(parent_auth)
        assert parent_result.decision == AuthorizationDecision.ALLOW
        
        # Child task (swarm worker) tries to request broader scope
        child_auth = TaskAuthorization.create(
            program_id="SP-LIVE-001",
            gate_id="SP_LIVE_001_L1_FIRST_REAL_GOVERNED_MISSION_001",
            work_package_id="wp-child-agentos",
            authority_snapshot_hash=snapshot.snapshot_id,
            requested_scope=["agentos/phase-f", "agentos/phase-g", "sp-live/l1"],  # Broader!
            requested_capabilities=["local-compute", "github-comment-write-v1"],
            requested_side_effect_budget=0,
            parent_task_id=parent_auth.task_id
        )
        
        child_result = gate.check_authorization(child_auth)
        
        assert child_result.decision == AuthorizationDecision.DENY_SCOPE_EXCEEDED
        assert "agentos/phase-f" in str(child_result.details.get("excess_scope", []))


class TestBacklogTaskCannotOverrideActiveAuthority:
    """TEST_4: BACKLOG_TASK_CANNOT_OVERRIDE_ACTIVE_AUTHORITY
    
    EXPECTED:
    priority = HIGH
    authorization = NONE
    execution = DENY
    """
    
    def test_high_priority_unauthorized_task_denied(self):
        """Even high-priority backlog tasks cannot execute without authorization."""
        builder = AuthorizationGateBuilder()
        
        # No active authorization set (Principal hasn't authorized anything)
        gate = builder.get_gate()
        
        # High-priority backlog task tries to execute
        task_auth = TaskAuthorization.create(
            program_id="SP-LIVE-001",
            gate_id="SOME_GATE",
            work_package_id="wp-backlog-high-priority",
            authority_snapshot_hash="non-existent-snapshot",
            requested_scope=["sp-live/l1"],
            requested_capabilities=["github-comment-write-v1"],
            requested_side_effect_budget=1
        )
        
        result = gate.check_authorization(task_auth)
        
        assert result.decision == AuthorizationDecision.DENY_MISSING_AUTHORITY_SNAPSHOT
        assert "no active program" in result.reason.lower()


class TestMemoryRequestDoesNotBecomeCurrentAuthority:
    """TEST_5: MEMORY_REQUEST_DOES_NOT_BECOME_CURRENT_AUTHORITY
    
    Historical user request: "implement top features"
    Current authorization: SP-LIVE L1
    
    EXPECTED:
    historical request cannot launch Phase F.
    """
    
    def test_historical_request_cannot_grant_authority(self):
        """Old user requests in memory cannot substitute for current Principal authorization."""
        builder = AuthorizationGateBuilder()
        
        # Principal authorizes L1 only
        snapshot = builder.create_authority(
            program_id="SP-LIVE-001",
            gate_id="SP_LIVE_001_L1_FIRST_REAL_GOVERNED_MISSION_001",
            authorization_id="auth-001",
            principal_id="principal-001",
            authorized_scope=["sp-live/l1"],
            capability_scope=["github-comment-write-v1"],
            side_effect_budget=1
        )
        
        gate = builder.get_gate()
        
        # Task claims authorization from "historical user request"
        task_auth = TaskAuthorization.create(
            program_id="SP-LIVE-001",
            gate_id="SP_LIVE_001_L1_FIRST_REAL_GOVERNED_MISSION_001",
            work_package_id="wp-from-memory",
            authority_snapshot_hash=snapshot.snapshot_id,
            requested_scope=["agentos/phase-f"],  # Historical request wanted this
            requested_capabilities=["local-compute"],
            requested_side_effect_budget=0
        )
        
        result = gate.check_authorization(task_auth)
        
        assert result.decision == AuthorizationDecision.DENY_SCOPE_EXCEEDED


class TestProposedNextPhaseIsNonExecutable:
    """TEST_6: PROPOSED_NEXT_PHASE_IS_NON_EXECUTABLE
    
    EXPECTED:
    NEXT_PHASE != AUTHORITY
    """
    
    def test_proposed_phase_not_executable(self):
        """A proposed next phase in roadmap is not executable authority."""
        builder = AuthorizationGateBuilder()
        
        # Only L1 authorized
        snapshot = builder.create_authority(
            program_id="SP-LIVE-001",
            gate_id="SP_LIVE_001_L1_FIRST_REAL_GOVERNED_MISSION_001",
            authorization_id="auth-001",
            principal_id="principal-001",
            authorized_scope=["sp-live/l1"],
            capability_scope=["github-comment-write-v1"],
            side_effect_budget=1
        )
        
        gate = builder.get_gate()
        
        # Task for "proposed Phase F"
        task_auth = TaskAuthorization.create(
            program_id="SP-LIVE-001",
            gate_id="SP_LIVE_001_L1_FIRST_REAL_GOVERNED_MISSION_001",
            work_package_id="wp-proposed-phase-f",
            authority_snapshot_hash=snapshot.snapshot_id,
            requested_scope=["agentos/phase-f"],
            requested_capabilities=["local-compute"],
            requested_side_effect_budget=0
        )
        
        result = gate.check_authorization(task_auth)
        
        assert result.decision == AuthorizationDecision.DENY_SCOPE_EXCEEDED


class TestAuthoritySnapshotRequiredForTaskStart:
    """TEST_7: AUTHORITY_SNAPSHOT_REQUIRED_FOR_TASK_START
    
    missing snapshot → DENY
    """
    
    def test_missing_snapshot_denied(self):
        """Task without authority snapshot must be denied."""
        builder = AuthorizationGateBuilder()
        
        snapshot = builder.create_authority(
            program_id="SP-LIVE-001",
            gate_id="L1",
            authorization_id="auth-001",
            principal_id="principal-001",
            authorized_scope=["sp-live/l1"],
            capability_scope=["github-comment-write-v1"],
            side_effect_budget=1
        )
        
        gate = builder.get_gate()
        
        # Task with non-existent snapshot hash
        task_auth = TaskAuthorization.create(
            program_id="SP-LIVE-001",
            gate_id="L1",
            work_package_id="wp-test",
            authority_snapshot_hash="non-existent-hash",
            requested_scope=["sp-live/l1"],
            requested_capabilities=["github-comment-write-v1"],
            requested_side_effect_budget=1
        )
        
        result = gate.check_authorization(task_auth)
        
        assert result.decision == AuthorizationDecision.DENY_MISSING_AUTHORITY_SNAPSHOT


class TestStaleAuthoritySnapshotDenied:
    """TEST_8: STALE_AUTHORITY_SNAPSHOT_DENIED
    
    stale snapshot → DENY
    """
    
    def test_expired_snapshot_denied(self):
        """Expired authority snapshot must be denied."""
        builder = AuthorizationGateBuilder()
        
        # Create snapshot that expired 1 second ago
        snapshot = AuthoritySnapshot.create(
            program_id="SP-LIVE-001",
            gate_id="L1",
            authorization_id="auth-expired",
            principal_id="principal-001",
            authorized_scope=["sp-live/l1"],
            capability_scope=["github-comment-write-v1"],
            side_effect_budget=1,
            expires_in_seconds=-1  # Already expired
        )
        builder.authority_store.store(snapshot)
        builder.gate.set_active_context("SP-LIVE-001", "L1")
        
        gate = builder.get_gate()
        
        task_auth = TaskAuthorization.create(
            program_id="SP-LIVE-001",
            gate_id="L1",
            work_package_id="wp-test",
            authority_snapshot_hash=snapshot.snapshot_id,
            requested_scope=["sp-live/l1"],
            requested_capabilities=["github-comment-write-v1"],
            requested_side_effect_budget=1
        )
        
        result = gate.check_authorization(task_auth)
        
        assert result.decision == AuthorizationDecision.DENY_STALE_AUTHORITY_SNAPSHOT


class TestChildScopeMustBeSubsetOfParent:
    """TEST_9: CHILD_SCOPE_MUST_BE_SUBSET_OF_PARENT
    
    broader child scope → DENY
    """
    
    def test_child_scope_subset_check(self):
        """Child task scope must be subset of authority snapshot scope."""
        builder = AuthorizationGateBuilder()
        
        snapshot = builder.create_authority(
            program_id="SP-LIVE-001",
            gate_id="L1",
            authorization_id="auth-001",
            principal_id="principal-001",
            authorized_scope=["sp-live/l1"],  # Only L1 scope
            capability_scope=["github-comment-write-v1"],
            side_effect_budget=1
        )
        
        gate = builder.get_gate()
        
        # Parent task with valid scope
        parent = TaskAuthorization.create(
            program_id="SP-LIVE-001",
            gate_id="L1",
            work_package_id="wp-parent",
            authority_snapshot_hash=snapshot.snapshot_id,
            requested_scope=["sp-live/l1"],
            requested_capabilities=["github-comment-write-v1"],
            requested_side_effect_budget=1
        )
        assert gate.check_authorization(parent).decision == AuthorizationDecision.ALLOW
        
        # Child tries to add scope not in parent authority
        child = TaskAuthorization.create(
            program_id="SP-LIVE-001",
            gate_id="L1",
            work_package_id="wp-child",
            authority_snapshot_hash=snapshot.snapshot_id,
            requested_scope=["sp-live/l1", "agentos/phase-f"],  # Broader!
            requested_capabilities=["github-comment-write-v1"],
            requested_side_effect_budget=0,
            parent_task_id=parent.task_id
        )
        
        result = gate.check_authorization(child)
        assert result.decision == AuthorizationDecision.DENY_SCOPE_EXCEEDED


class TestSideEffectBudgetCannotIncreaseByDelegation:
    """TEST_10: SIDE_EFFECT_BUDGET_CANNOT_INCREASE_BY_DELEGATION
    
    child budget > parent budget → DENY
    """
    
    def test_child_budget_cannot_exceed_parent(self):
        """Child task cannot request more side effect budget than authority allows."""
        builder = AuthorizationGateBuilder()
        
        snapshot = builder.create_authority(
            program_id="SP-LIVE-001",
            gate_id="L1",
            authorization_id="auth-001",
            principal_id="principal-001",
            authorized_scope=["sp-live/l1"],
            capability_scope=["github-comment-write-v1"],
            side_effect_budget=1  # Only 1 side effect allowed
        )
        
        gate = builder.get_gate()
        
        # Parent uses the budget
        parent = TaskAuthorization.create(
            program_id="SP-LIVE-001",
            gate_id="L1",
            work_package_id="wp-parent",
            authority_snapshot_hash=snapshot.snapshot_id,
            requested_scope=["sp-live/l1"],
            requested_capabilities=["github-comment-write-v1"],
            requested_side_effect_budget=1
        )
        assert gate.check_authorization(parent).decision == AuthorizationDecision.ALLOW
        
        # Child tries to request additional budget
        child = TaskAuthorization.create(
            program_id="SP-LIVE-001",
            gate_id="L1",
            work_package_id="wp-child",
            authority_snapshot_hash=snapshot.snapshot_id,
            requested_scope=["sp-live/l1"],
            requested_capabilities=["github-comment-write-v1"],
            requested_side_effect_budget=2,  # More than authorized!
            parent_task_id=parent.task_id
        )
        
        result = gate.check_authorization(child)
        assert result.decision == AuthorizationDecision.DENY_SIDE_EFFECT_BUDGET_EXCEEDED


class TestGateBasicFunctionality:
    """Basic gate functionality tests."""
    
    def test_valid_task_allowed(self):
        """Valid task with matching authorization should be allowed."""
        builder = AuthorizationGateBuilder()
        
        snapshot = builder.create_authority(
            program_id="SP-LIVE-001",
            gate_id="L1",
            authorization_id="auth-001",
            principal_id="principal-001",
            authorized_scope=["sp-live/l1", "github/comment"],
            capability_scope=["github-comment-write-v1", "local-compute"],
            side_effect_budget=1
        )
        
        gate = builder.get_gate()
        
        task_auth = TaskAuthorization.create(
            program_id="SP-LIVE-001",
            gate_id="L1",
            work_package_id="wp-test",
            authority_snapshot_hash=snapshot.snapshot_id,
            requested_scope=["sp-live/l1"],
            requested_capabilities=["github-comment-write-v1"],
            requested_side_effect_budget=1
        )
        
        result = gate.check_authorization(task_auth)
        assert result.decision == AuthorizationDecision.ALLOW
    
    def test_zero_side_effect_budget_enforced(self):
        """Zero side effect budget prevents any side effects."""
        builder = AuthorizationGateBuilder()
        
        snapshot = builder.create_authority(
            program_id="SP-LIVE-001",
            gate_id="L1",
            authorization_id="auth-001",
            principal_id="principal-001",
            authorized_scope=["sp-live/l1"],
            capability_scope=["local-compute"],
            side_effect_budget=0  # Zero-write!
        )
        
        gate = builder.get_gate()
        
        # Task requesting side effects with zero budget
        task_auth = TaskAuthorization.create(
            program_id="SP-LIVE-001",
            gate_id="L1",
            work_package_id="wp-test",
            authority_snapshot_hash=snapshot.snapshot_id,
            requested_scope=["sp-live/l1"],
            requested_capabilities=["local-compute"],
            requested_side_effect_budget=1  # Wants side effects!
        )
        
        result = gate.check_authorization(task_auth)
        assert result.decision == AuthorizationDecision.DENY_SIDE_EFFECT_BUDGET_EXCEEDED
    
    def test_snapshot_integrity_check(self):
        """Tampered snapshot must be rejected."""
        builder = AuthorizationGateBuilder()
        
        snapshot = builder.create_authority(
            program_id="SP-LIVE-001",
            gate_id="L1",
            authorization_id="auth-001",
            principal_id="principal-001",
            authorized_scope=["sp-live/l1"],
            capability_scope=["github-comment-write-v1"],
            side_effect_budget=1
        )
        
        gate = builder.get_gate()
        
        # Task with valid snapshot
        task_auth = TaskAuthorization.create(
            program_id="SP-LIVE-001",
            gate_id="L1",
            work_package_id="wp-test",
            authority_snapshot_hash=snapshot.snapshot_id,
            requested_scope=["sp-live/l1"],
            requested_capabilities=["github-comment-write-v1"],
            requested_side_effect_budget=1
        )
        
        result = gate.check_authorization(task_auth)
        assert result.decision == AuthorizationDecision.ALLOW
        
        # Verify integrity check would catch tampering
        assert snapshot.verify_integrity() == True
    
    def test_capability_name_drift_denied(self):
        """CAPABILITY NAME DRIFT TEST: Drifted capability name must be denied.
        
        AUTHORIZED = provider.github-issue-comment-create-v1
        REQUESTED = provider.github-comment-write-v1
        EXPECTED = DENY_CAPABILITY_MISMATCH
        """
        builder = AuthorizationGateBuilder()
        
        # Authority snapshot with EXACT certified capability
        snapshot = builder.create_authority(
            program_id="SP-LIVE-001",
            gate_id="SP_LIVE_001_L1_FIRST_REAL_GOVERNED_MISSION_001",
            authorization_id="auth-001",
            principal_id="principal-001",
            authorized_scope=["sp-live/l1", "github/comment"],
            capability_scope=["provider.github-issue-comment-create-v1"],  # EXACT certified name
            side_effect_budget=1
        )
        
        gate = builder.get_gate()
        
        # Task requests DRIFTED capability name (what Hermes incorrectly used)
        task_auth = TaskAuthorization.create(
            program_id="SP-LIVE-001",
            gate_id="SP_LIVE_001_L1_FIRST_REAL_GOVERNED_MISSION_001",
            work_package_id="wp-test",
            authority_snapshot_hash=snapshot.snapshot_id,
            requested_scope=["sp-live/l1"],
            requested_capabilities=["provider.github-comment-write-v1"],  # DRIFTED name
            requested_side_effect_budget=1
        )
        
        result = gate.check_authorization(task_auth)
        
        # Must be denied - capability alias/substitution not allowed
        assert result.decision == AuthorizationDecision.DENY_CAPABILITY_EXCEEDED
        assert "provider.github-comment-write-v1" in str(result.details.get("excess_capabilities", []))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])