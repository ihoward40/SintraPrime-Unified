"""SP-LIVE-001 I1 offline integration tests."""

import hashlib
from sintra_live.integration import run_synthetic_mission


def test_synthetic_mission_completes():
    """Test that one complete synthetic mission runs successfully."""
    result = run_synthetic_mission()
    
    assert result.test_results["voice_captured"] is True
    assert result.test_results["principal_identity_verified"] is True
    assert result.test_results["mission_created"] is True
    assert result.test_results["memory_retrieved"] is True
    assert result.test_results["swarm_dispatched"] is True
    assert result.test_results["specialist_isolation_verified"] is True
    assert result.test_results["model_routing_recorded"] is True
    assert result.test_results["reconciled"] is True
    assert result.test_results["action_proposed"] is True
    assert result.test_results["proposed_action_hashed"] is True
    assert result.test_results["approval_required_before_execution"] is True
    assert result.test_results["approval_bound_to_exact_action"] is True
    assert result.test_results["explicit_approval_received"] is True
    assert result.test_results["synthetic_side_effect_executed"] is True
    assert result.test_results["exactly_one_side_effect"] is True
    assert result.test_results["unapproved_side_effects"] == 0
    assert result.test_results["duplicate_side_effects"] == 0
    assert result.test_results["result_independently_verified"] is True
    assert result.test_results["evidence_chain_verified"] is True
    assert result.test_results["written_principal_brief"] is True
    assert result.test_results["synthetic_spoken_brief"] is True
    assert result.test_results["mission_complete"] is True


def test_adversarial_blocks():
    """Test that all mandatory adversarial blocks are present."""
    result = run_synthetic_mission()
    
    required_blocks = [
        "missing_principal_identity_blocked",
        "ambiguous_principal_identity_blocked",
        "stale_authority_blocked",
        "changed_action_after_approval_blocked",
        "changed_destination_after_approval_blocked",
        "expired_approval_blocked",
        "reused_approval_blocked",
        "duplicate_execution_blocked",
        "specialist_escalation_blocked",
        "memory_escalation_blocked",
        "tool_unavailable_handled",
        "verifier_disagreement_handled",
        "missing_evidence_blocked",
        "interrupted_execution_handled",
    ]
    
    for block in required_blocks:
        assert result.adversarial_results[block] is True, f"Required adversarial block missing: {block}"


def test_evidence_chain_integrity():
    """Test that evidence chain is valid and sealed."""
    result = run_synthetic_mission()
    
    assert result.evidence_chain is not None
    assert result.evidence_chain.verify_chain() is True
    
    root = result.evidence_chain.get_chain_root()
    assert len(root) == 64  # SHA-256 hex
    assert all(c in '0123456789abcdef' for c in root)


def test_action_envelope_immutability():
    """Test that action envelope has immutable hash."""
    result = run_synthetic_mission()
    
    # Evidence chain should contain action_proposed record with action_hash
    records = result.evidence_chain.get_all_records()
    action_records = [r for r in records if r["type"] == "action_proposed"]
    assert len(action_records) == 1
    
    action_hash = action_records[0]["content"]["action_hash"]
    assert len(action_hash) == 64
    assert all(c in '0123456789abcdef' for c in action_hash)


def test_approval_binding():
    """Test that approval is bound to exact action hash."""
    result = run_synthetic_mission()
    
    records = result.evidence_chain.get_all_records()
    approval_records = [r for r in records if r["type"] == "approval_received"]
    assert len(approval_records) == 1
    
    approval_hash = approval_records[0]["content"]["approval_hash"]
    approved_action_hash = approval_records[0]["content"]["action_hash"]
    
    # Find the action_proposed record
    action_records = [r for r in records if r["type"] == "action_proposed"]
    proposed_action_hash = action_records[0]["content"]["action_hash"]
    
    # Approval must bind to exact action hash
    assert approved_action_hash == proposed_action_hash
    assert len(approval_hash) == 64


def test_exactly_one_side_effect():
    """Test that exactly one side effect executes."""
    result = run_synthetic_mission()
    
    assert result.test_results["exactly_one_side_effect"] is True
    assert result.test_results["unapproved_side_effects"] == 0
    assert result.test_results["duplicate_side_effects"] == 0
    
    # Evidence chain should have exactly one side_effect_executed
    records = result.evidence_chain.get_all_records()
    exec_records = [r for r in records if r["type"] == "side_effect_executed"]
    assert len(exec_records) == 1


def test_independent_verification():
    """Test that verification is independent and successful."""
    result = run_synthetic_mission()
    
    assert result.test_results["result_independently_verified"] is True
    
    records = result.evidence_chain.get_all_records()
    verification_records = [r for r in records if r["type"] == "verification_completed"]
    assert len(verification_records) == 1
    assert verification_records[0]["content"]["success"] is True


def test_principal_brief_generation():
    """Test that both written and spoken briefs are generated."""
    result = run_synthetic_mission()
    
    assert result.brief is not None
    assert result.brief.written_text is not None
    assert len(result.brief.written_text) > 0
    assert result.brief.spoken_text is not None
    assert len(result.brief.spoken_text) > 0
    assert result.brief.brief_hash is not None
    assert len(result.brief.brief_hash) == 64


def test_voice_output_hash():
    """Test that synthetic voice output has valid hash."""
    result = run_synthetic_mission()
    
    assert result.voice_output is not None
    assert result.voice_output.output_hash is not None
    assert len(result.voice_output.output_hash) >= 16


def test_mission_completes_deterministic_results():
    """Test that mission produces consistent test results with deterministic mode."""
    result1 = run_synthetic_mission(deterministic=True)
    result2 = run_synthetic_mission(deterministic=True)
    
    # With deterministic=True, test results should be identical
    assert result1.test_results == result2.test_results
    # Mission ID should be the same fixed ID
    assert result1.mission_id == result2.mission_id == "test-mission-deterministic"
    # Evidence chain should have same number of records
    assert len(result1.evidence_chain.get_all_records()) == len(result2.evidence_chain.get_all_records())


def test_no_real_connector_calls():
    """Test that no real connector calls are made."""
    result = run_synthetic_mission()
    
    # Verify no real API calls were made by checking state
    records = result.evidence_chain.get_all_records()
    for record in records:
        content = record.get("content", {})
        if isinstance(content, dict):
            # Check no real provider identifiers
            for key, value in content.items():
                if isinstance(value, str):
                    assert "googleapis" not in value.lower()
                    assert "github" not in value.lower() or "synthetic" in value.lower()
                    assert "oauth" not in value.lower()


if __name__ == "__main__":
    import sys
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))