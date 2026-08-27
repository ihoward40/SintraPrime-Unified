"""Principal Brief generation for offline integration."""

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class BriefFormat(Enum):
    """Brief output formats."""
    WRITTEN = "WRITTEN"
    SPOKEN = "SPOKEN"
    BOTH = "BOTH"


@dataclass(frozen=True)
class PrincipalBrief:
    """Immutable Principal Brief."""
    mission_id: str
    mission_purpose: str
    principal_id: str
    session_id: str
    completed_at: float
    evidence_chain_root: str
    verification_result: Dict[str, Any]
    side_effect_summary: Dict[str, Any]
    informational_summary: Dict[str, Any]
    approval_summary: Dict[str, Any]
    brief_hash: str = ""
    written_text: str = ""
    spoken_text: str = ""

    def __post_init__(self):
        if not self.brief_hash:
            content = f"{self.mission_id}|{self.evidence_chain_root}|{self.completed_at}"
            object.__setattr__(self, 'brief_hash', hashlib.sha256(content.encode()).hexdigest())
        if not self.written_text:
            object.__setattr__(self, 'written_text', self._generate_written())
        if not self.spoken_text:
            object.__setattr__(self, 'spoken_text', self._generate_spoken())

    def _generate_written(self) -> str:
        parts = [
            f"=== PRINCIPAL BRIEF ===",
            f"Mission: {self.mission_id}",
            f"Purpose: {self.mission_purpose}",
            f"Principal: {self.principal_id}",
            f"Session: {self.session_id}",
            f"Completed: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime(self.completed_at))}",
            f"Evidence Chain: {self.evidence_chain_root[:16]}...",
            f"",
            f"=== VERIFICATION ===",
            f"Result: {'VERIFIED' if self.verification_result.get('success') else 'FAILED'}",
            f"Verifier: {self.verification_result.get('verifier_id')}",
            f"Discrepancies: {len(self.verification_result.get('discrepancies', []))}",
            f"",
            f"=== SIDE EFFECT ===",
            f"Executed: {self.side_effect_summary.get('executed', False)}",
            f"Action Hash: {self.side_effect_summary.get('action_hash', 'N/A')[:16]}...",
            f"Receipt: {self.side_effect_summary.get('receipt_hash', 'N/A')[:16]}...",
            f"State After: {json.dumps(self.side_effect_summary.get('state_after', {}), indent=2)}",
            f"",
            f"=== INFORMATIONAL ===",
            f"Active Matters: {self.informational_summary.get('active_matters', 0)}",
            f"Informational: {self.informational_summary.get('informational', 0)}",
            f"Requires Approval: {self.informational_summary.get('requires_approval', 0)}",
            f"",
            f"=== APPROVAL ===",
            f"Approval Hash: {self.approval_summary.get('approval_hash', 'N/A')[:16]}...",
            f"Approved At: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime(self.approval_summary.get('approved_at', 0)))}",
            f"Approval Phrase: {self.approval_summary.get('approval_phrase', 'N/A')}",
            f"",
            f"Brief Hash: {self.brief_hash[:16]}..."
        ]
        return "\n".join(parts)

    def _generate_spoken(self) -> str:
        verified = "verified" if self.verification_result.get('success') else "failed"
        matters = self.informational_summary.get('active_matters', 0)
        info = self.informational_summary.get('informational', 0)
        approval_needed = self.informational_summary.get('requires_approval', 0)
        side_effect = "executed" if self.side_effect_summary.get('executed') else "not executed"
        
        return (
            f"Good evening. Mission {self.mission_id[:8]} complete. "
            f"I found {matters} active matters: {info} informational and {approval_needed} requiring approval. "
            f"The external action has been {side_effect} and independently {verified}. "
            f"Evidence chain sealed. Brief hash {self.brief_hash[:8]}. "
            f"Would you like the detailed written brief?"
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "mission_purpose": self.mission_purpose,
            "principal_id": self.principal_id,
            "session_id": self.session_id,
            "completed_at": self.completed_at,
            "evidence_chain_root": self.evidence_chain_root,
            "verification_result": self.verification_result,
            "side_effect_summary": self.side_effect_summary,
            "informational_summary": self.informational_summary,
            "approval_summary": self.approval_summary,
            "brief_hash": self.brief_hash,
            "written_text": self.written_text,
            "spoken_text": self.spoken_text
        }


class PrincipalBriefGenerator:
    """Generates Principal Brief from sealed evidence."""

    def __init__(self, mission_id: str, principal_identity, mission_purpose: str):
        self.mission_id = mission_id
        self.principal_identity = principal_identity
        self.mission_purpose = mission_purpose

    def generate(self, evidence_chain, verification_result, side_effect_receipt, approval_record, informational_items: List[Dict[str, Any]]) -> PrincipalBrief:
        """Generate both written and spoken Principal Brief."""
        principal_id = self.principal_identity.principal_id if hasattr(self.principal_identity, 'principal_id') else self.principal_identity.get('principal_id', 'unknown')
        session_id = self.principal_identity.session_id if hasattr(self.principal_identity, 'session_id') else self.principal_identity.get('session_id', 'unknown')
        
        # Build summaries
        verification_dict = verification_result.to_dict() if hasattr(verification_result, 'to_dict') else (verification_result.__dict__ if hasattr(verification_result, '__dict__') else verification_result)
        
        side_effect_summary = {
            "executed": side_effect_receipt.success if side_effect_receipt else False,
            "action_hash": side_effect_receipt.action_hash if side_effect_receipt else "",
            "receipt_hash": side_effect_receipt.receipt_hash if side_effect_receipt else "",
            "state_after": side_effect_receipt.state_after if side_effect_receipt else {}
        }
        
        active_matters = 0
        informational = 0
        requires_approval = 0
        for item in informational_items:
            if item.get("type") == "status_summary":
                active_matters = item.get("active_matters", 0)
                informational = item.get("informational", 0)
                requires_approval = item.get("requires_approval", 0)
        
        informational_summary = {
            "active_matters": active_matters,
            "informational": informational,
            "requires_approval": requires_approval
        }
        
        approval_summary = {}
        if approval_record:
            approval_summary = {
                "approval_hash": approval_record.approval_hash,
                "approved_at": approval_record.approved_at,
                "approval_phrase": approval_record.approval_phrase
            }
        
        brief = PrincipalBrief(
            mission_id=self.mission_id,
            mission_purpose=self.mission_purpose,
            principal_id=principal_id,
            session_id=session_id,
            completed_at=time.time(),
            evidence_chain_root=evidence_chain.get_chain_root(),
            verification_result=verification_dict,
            side_effect_summary=side_effect_summary,
            informational_summary=informational_summary,
            approval_summary=approval_summary
        )
        
        return brief