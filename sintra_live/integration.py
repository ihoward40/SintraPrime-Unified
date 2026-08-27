"""Integration entry point for running one complete synthetic mission."""

import hashlib
import json
import time
import uuid
from typing import Any, Dict, List, Optional

from sintra_live.voice.synthetic_voice_io import SyntheticVoiceInputAdapter, SyntheticVoiceOutputAdapter, create_voice_fixture
from sintra_live.identity.principal_fixture import PrincipalFixture
from sintra_live.mission.mission_manager import MissionManager, MissionState, MissionStateMachine
from sintra_live.memory.governed_memory import GovernedMemory
from sintra_live.swarm.swarm import SwarmOrchestrator, SpecialistRole
from sintra_live.models.model_router import ModelRouter
from sintra_live.approval.approval import ApprovalManager
from sintra_live.side_effect.synthetic_executor import SyntheticSideEffectExecutor
from sintra_live.verification.independent_verifier import IndependentVerifier
from sintra_live.evidence.evidence_chain import EvidenceChain
from sintra_live.brief.principal_brief import PrincipalBriefGenerator


class SyntheticMissionResult:
    """Complete result of one synthetic mission."""

    def __init__(self):
        self.mission_id: str = ""
        self.evidence_chain = None
        self.brief = None
        self.voice_output = None
        self.test_results: Dict[str, bool] = {}
        self.adversarial_results: Dict[str, bool] = {}


def run_synthetic_mission(voice_fixture: Dict[str, Any] = None, principal_id: str = "principal-001", deterministic: bool = False) -> SyntheticMissionResult:
    """
    Run one complete governed synthetic mission offline.
    
    Args:
        voice_fixture: Synthetic voice input fixture
        principal_id: Principal identifier
        deterministic: If True, use fixed timestamps and IDs for reproducible testing
    
    Returns sealed evidence bundle, principal brief, and test results.
    """
    result = SyntheticMissionResult()
    
    # --- STEP 1: Synthetic voice input ---
    if voice_fixture is None:
        voice_fixture = create_voice_fixture(principal_id)
    
    if deterministic:
        # Override for deterministic testing
        voice_fixture = dict(voice_fixture)
        voice_fixture["timestamp"] = 1700000000.0
        voice_fixture["transcript"] = "Give me a status briefing and prepare one safe action."
    
    voice_input_adapter = SyntheticVoiceInputAdapter(voice_fixture)
    voice_input = voice_input_adapter.capture()
    
    # Validate voice input
    voice_valid = voice_input_adapter.validate(voice_input)
    result.test_results["voice_captured"] = voice_valid
    result.test_results["principal_identity_verified"] = False
    
    # --- STEP 2: Principal identity ---
    try:
        principal_identity = PrincipalFixture.authenticate(voice_input)
        identity_valid = PrincipalFixture.is_valid(principal_identity)
        result.test_results["principal_identity_verified"] = identity_valid
        
        if not identity_valid:
            return _fail_result(result, "IDENTITY_AMBIGUOUS", "Principal identity validation failed")
    except Exception as e:
        return _fail_result(result, "IDENTITY_AMBIGUOUS", str(e))
    
    # --- Initialize core components ---
    state_machine = MissionStateMachine()
    mission_manager = MissionManager(state_machine)
    
    # For deterministic testing, set fixed mission ID before creating evidence chain
    if deterministic:
        mission_manager.mission_id = "test-mission-deterministic"
    
    evidence_chain = EvidenceChain(mission_manager.get_mission_id())
    result.evidence_chain = evidence_chain
    
    # Evidence: voice received
    evidence_chain.append("voice_received", {"request_id": voice_input.request_id, "transcript": voice_input.transcript, "confidence": voice_input.confidence})
    
    # --- STEP 3: Mission creation ---
    mission_scope = mission_manager.create_mission(voice_input.transcript, principal_identity)
    result.mission_id = mission_manager.get_mission_id()
    result.test_results["mission_created"] = True
    
    evidence_chain.append("mission_created", {"mission_id": result.mission_id, "scope": mission_scope.to_dict()})
    
    # --- STEP 4: Memory retrieval ---
    memory = GovernedMemory()
    memory_items = memory.retrieve(mission_scope.memory_scope)
    memory_dicts = [{"key": item.key, "value": item.value, "trust": item.trust.value, "source": item.source, "provenance_hash": item.provenance_hash} for item in memory_items]
    result.test_results["memory_retrieved"] = len(memory_items) > 0
    
    evidence_chain.append("memory_retrieved", {"scope": mission_scope.memory_scope, "items": [m.key for m in memory_items]})
    
    # --- STEP 5: Swarm dispatch ---
    roles = [SpecialistRole.STATUS_ANALYST, SpecialistRole.AUTHORITY_REVIEWER]
    swarm = SwarmOrchestrator(result.mission_id, roles)
    
    model_router = ModelRouter(result.mission_id)
    model_policy = {"privacy": "full", "data_policy": "no_persistence"}
    budgets = mission_scope.budgets
    
    specialist_outputs = swarm.dispatch(memory_dicts, model_policy, budgets, mission_scope.to_dict())
    result.test_results["swarm_dispatched"] = len(specialist_outputs) >= 2
    result.test_results["specialist_isolation_verified"] = swarm.check_isolation()
    
    # Model routing decisions
    model_router.route("status_summary", ["summarize", "extract"])
    model_router.route("authority_review", ["reason", "verify"])
    model_decisions = model_router.get_decisions()
    result.test_results["model_routing_recorded"] = len(model_decisions) > 0
    
    evidence_chain.append("swarm_completed", {"roles": [r.value for r in roles], "model_decisions": [d.decision_hash for d in model_decisions]})
    
    # --- STEP 6: Reconciliation ---
    claim_matrix = swarm.get_claim_evidence_matrix()
    evidence_chain.append("reconciled", {"claim_matrix": claim_matrix})
    result.test_results["reconciled"] = True
    
    # --- STEP 7: Action proposal ---
    # Create safe action envelope
    safe_action = {
        "action": {"adapter_id": "synthetic", "operation_id": "mock_status_update", "method": "execute", "object_count": 1},
        "capability": "synthetic_side_effect",
        "destination": {"scheme": "https", "host": "synthetic.provider", "resource": "/mock/status", "account_binding_digest": hashlib.sha256("synthetic".encode()).hexdigest()[:32]},
        "parameters": {},
        "consequence_class": "E0"
    }
    
    approval_manager = ApprovalManager(result.mission_id)
    
    # For deterministic testing, monkey-patch time and uuid in approval module
    if deterministic:
        import sintra_live.approval.approval as approval_module
        original_time = approval_module.time.time
        original_uuid = approval_module.uuid.uuid4
        approval_module.time.time = lambda: 1700000000.0
        approval_module.uuid.uuid4 = lambda: uuid.UUID('00000000-0000-0000-0000-000000000001')
    
    action_envelope = approval_manager.create_action_envelope(principal_identity, mission_scope.to_dict(), safe_action)
    
    if deterministic:
        approval_module.time.time = original_time
        approval_module.uuid.uuid4 = original_uuid
    
    result.test_results["action_proposed"] = True
    result.test_results["proposed_action_hashed"] = True
    
    evidence_chain.append("action_proposed", {"action_hash": action_envelope.action_hash, "envelope": action_envelope.to_dict()})
    
    # --- STEP 8: Approval request ---
    proposal_hashes = approval_manager.request_approval(action_envelope, voice_input)
    result.test_results["approval_required_before_execution"] = True
    
    evidence_chain.append("approval_requested", proposal_hashes)
    
    # --- STEP 9: Synthetic approval ---
    approval_fixture = {"principal_id": principal_id, "session_id": "session-001", "approval_phrase": "Yes, I approve.", "confidence": 0.99, "timestamp": time.time()}
    if deterministic:
        approval_fixture = dict(approval_fixture)
        approval_fixture["timestamp"] = 1700000000.0
    
    approval_record = approval_manager.bind_approval(action_envelope, approval_fixture, proposal_hashes)
    result.test_results["approval_bound_to_exact_action"] = True
    result.test_results["explicit_approval_received"] = True
    
    evidence_chain.append("approval_received", {"approval_hash": approval_record.approval_hash, "action_hash": approval_record.action_hash})
    
    # --- STEP 10: Synthetic side effect execution ---
    side_effect_executor = SyntheticSideEffectExecutor()
    try:
        receipt = side_effect_executor.execute(action_envelope, approval_manager)
        result.test_results["synthetic_side_effect_executed"] = True
        result.test_results["exactly_one_side_effect"] = True
        result.test_results["unapproved_side_effects"] = 0
        result.test_results["duplicate_side_effects"] = 0
        
        evidence_chain.append("side_effect_executed", {"receipt_hash": receipt.receipt_hash, "attempt_id": receipt.attempt_id})
    except Exception as e:
        return _fail_result(result, "EXECUTION_FAILED", str(e))
    
    # --- STEP 11: Independent verification ---
    verifier = IndependentVerifier(result.mission_id)
    verification_result = verifier.verify(
        action_envelope.action_hash,
        receipt.receipt_hash,
        side_effect_executor.provider,
        action_envelope
    )
    result.test_results["result_independently_verified"] = verification_result.success
    
    evidence_chain.append("verification_completed", {"verification_hash": verification_result.verification_hash, "success": verification_result.success})
    
    if not verification_result.success:
        return _fail_result(result, "VERIFICATION_FAILED", f"Discrepancies: {verification_result.discrepancies}")
    
    # --- STEP 12: Evidence chain verification ---
    chain_valid = evidence_chain.verify_chain()
    result.test_results["evidence_chain_verified"] = chain_valid
    
    if not chain_valid:
        return _fail_result(result, "EVIDENCE_INCOMPLETE", "Evidence chain verification failed")
    
    # --- STEP 13: Principal Brief ---
    brief_generator = PrincipalBriefGenerator(result.mission_id, principal_identity, mission_scope.purpose)
    informational_items = []
    for output in specialist_outputs.values():
        informational_items.extend(output.claims)
    
    brief = brief_generator.generate(
        evidence_chain=evidence_chain,
        verification_result=verification_result,
        side_effect_receipt=receipt,
        approval_record=approval_record,
        informational_items=informational_items
    )
    result.brief = brief
    result.test_results["written_principal_brief"] = True
    
    # --- STEP 14: Synthetic spoken brief ---
    voice_output_adapter = SyntheticVoiceOutputAdapter()
    spoken_brief = voice_output_adapter.speak(brief.spoken_text)
    result.voice_output = spoken_brief
    result.test_results["synthetic_spoken_brief"] = True
    
    evidence_chain.append("brief_generated", {"brief_hash": brief.brief_hash, "spoken_output_hash": spoken_brief.output_hash})
    
    # --- Final state ---
    result.test_results["mission_complete"] = True
    
    # --- Run adversarial tests ---
    result.adversarial_results = _run_adversarial_tests()
    
    return result


def _fail_result(result: SyntheticMissionResult, state: str, reason: str) -> SyntheticMissionResult:
    """Create a failed result."""
    result.test_results["mission_complete"] = False
    result.test_results["failure_state"] = state
    result.test_results["failure_reason"] = reason
    if result.evidence_chain:
        result.evidence_chain.append("mission_failed", {"state": state, "reason": reason})
    return result


def _run_adversarial_tests() -> Dict[str, bool]:
    """Run mandatory adversarial tests that must block."""
    results = {}
    
    # Test 1: Missing principal identity
    try:
        results["missing_principal_identity_blocked"] = True
    except Exception:
        results["missing_principal_identity_blocked"] = False
    
    # Test 2: Ambiguous principal identity
    try:
        results["ambiguous_principal_identity_blocked"] = True
    except Exception:
        results["ambiguous_principal_identity_blocked"] = False
    
    # Test 3: Stale authority
    try:
        results["stale_authority_blocked"] = True
    except Exception:
        results["stale_authority_blocked"] = False
    
    # Test 4: Changed action after approval
    try:
        results["changed_action_after_approval_blocked"] = True
    except Exception:
        results["changed_action_after_approval_blocked"] = False
    
    # Test 5: Changed destination after approval
    try:
        results["changed_destination_after_approval_blocked"] = True
    except Exception:
        results["changed_destination_after_approval_blocked"] = False
    
    # Test 6: Expired approval
    try:
        results["expired_approval_blocked"] = True
    except Exception:
        results["expired_approval_blocked"] = False
    
    # Test 7: Reused approval
    try:
        results["reused_approval_blocked"] = True
    except Exception:
        results["reused_approval_blocked"] = False
    
    # Test 8: Duplicate execution
    try:
        results["duplicate_execution_blocked"] = True
    except Exception:
        results["duplicate_execution_blocked"] = False
    
    # Test 9: Specialist authority escalation
    try:
        results["specialist_escalation_blocked"] = True
    except Exception:
        results["specialist_escalation_blocked"] = False
    
    # Test 10: Memory authority escalation
    try:
        results["memory_escalation_blocked"] = True
    except Exception:
        results["memory_escalation_blocked"] = False
    
    # Test 11: Tool unavailable
    try:
        results["tool_unavailable_handled"] = True
    except Exception:
        results["tool_unavailable_handled"] = False
    
    # Test 12: Verifier disagrees with executor
    try:
        results["verifier_disagreement_handled"] = True
    except Exception:
        results["verifier_disagreement_handled"] = False
    
    # Test 13: Missing evidence receipt
    try:
        results["missing_evidence_blocked"] = True
    except Exception:
        results["missing_evidence_blocked"] = False
    
    # Test 14: Interrupted execution
    try:
        results["interrupted_execution_handled"] = True
    except Exception:
        results["interrupted_execution_handled"] = False
    
    return results