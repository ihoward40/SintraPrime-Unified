"""Trust Compliance Adapter - Phase 19C

Bridges Trust Compliance Engine with ToolGateway, providing receipt generation,
approval workflow, and audit trail tracking for all tool invocations.
"""

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from tool_registry import get_tool, TrustComplianceRisk


@dataclass
class TrustComplianceReceipt:
    """Receipt generated for each Trust Compliance tool invocation."""
    receipt_id: str
    correlation_id: str
    tool_name: str
    risk_level: TrustComplianceRisk
    status: str  # pending, approved, executed, failed, rejected
    agent_id: str
    timestamp: str
    input_hash: str
    output_hash: Optional[str] = None
    approval_by: Optional[str] = None
    approval_timestamp: Optional[str] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert receipt to dictionary for serialization."""
        return {
            'receipt_id': self.receipt_id,
            'correlation_id': self.correlation_id,
            'tool_name': self.tool_name,
            'risk_level': f'R{self.risk_level.value}',
            'status': self.status,
            'agent_id': self.agent_id,
            'timestamp': self.timestamp,
            'input_hash': self.input_hash,
            'output_hash': self.output_hash,
            'approval_by': self.approval_by,
            'approval_timestamp': self.approval_timestamp,
            'error': self.error,
        }


class ApprovalRequest:
    """Represents a request for approval of an R3 action."""
    def __init__(self, receipt_id: str, tool_name: str, risk_level: TrustComplianceRisk,
                 args: Dict[str, Any]):
        self.receipt_id = receipt_id
        self.tool_name = tool_name
        self.risk_level = risk_level
        self.args = args
        self.created_at = datetime.utcnow().isoformat()
        self.approved = False
        self.approved_by = None
        self.approved_at = None
        self.reason = None


class TrustComplianceGatewayAdapter:
    """Gateway adapter for Trust Compliance tool execution with governance.
    
    Features:
    - Receipt generation for all tool calls
    - Risk-based approval workflow
    - Audit trail tracking
    - Integration with ToolGateway policy
    """
    
    def __init__(self, tc_engine=None, approval_service=None):
        """Initialize the adapter.
        
        Args:
            tc_engine: Trust Compliance Engine instance
            approval_service: Service for handling R3 approvals
        """
        self.tc = tc_engine
        self.approval_service = approval_service
        self.receipts: Dict[str, TrustComplianceReceipt] = {}
        self.audit_trail: list = []
    
    def _hash_input(self, args: Dict[str, Any]) -> str:
        """Generate hash of input arguments.
        
        Args:
            args: Input arguments dictionary
        
        Returns:
            SHA256 hash of JSON representation
        """
        try:
            json_str = json.dumps(args, sort_keys=True, default=str)
            return hashlib.sha256(json_str.encode()).hexdigest()
        except Exception:
            return hashlib.sha256(str(args).encode()).hexdigest()
    
    def _hash_output(self, result: Any) -> str:
        """Generate hash of output result.
        
        Args:
            result: Output result
        
        Returns:
            SHA256 hash of JSON representation
        """
        try:
            json_str = json.dumps(result, sort_keys=True, default=str)
            return hashlib.sha256(json_str.encode()).hexdigest()
        except Exception:
            return hashlib.sha256(str(result).encode()).hexdigest()
    
    async def call_tool(self,
                       tool_name: str,
                       args: Dict[str, Any],
                       agent_id: str,
                       **kwargs) -> Dict[str, Any]:
        """Call a trust compliance tool with governance checks.
        
        Args:
            tool_name: Name of the tool to call
            args: Arguments to pass to the tool
            agent_id: ID of the agent calling the tool
            **kwargs: Additional options (e.g., correlation_id)
        
        Returns:
            Dictionary with result, receipt_id, and correlation_id,
            or error information
        """
        
        # Get tool metadata
        tool = get_tool(tool_name)
        if not tool:
            return {'error': f'Unknown tool: {tool_name}'}
        
        # Generate receipt
        receipt_id = str(uuid.uuid4())
        correlation_id = kwargs.get('correlation_id', str(uuid.uuid4()))
        input_hash = self._hash_input(args)
        
        receipt = TrustComplianceReceipt(
            receipt_id=receipt_id,
            correlation_id=correlation_id,
            tool_name=tool_name,
            risk_level=tool.risk_level,
            status='pending',
            agent_id=agent_id,
            timestamp=datetime.utcnow().isoformat(),
            input_hash=input_hash
        )
        
        self.receipts[receipt_id] = receipt
        self.audit_trail.append({
            'event': 'tool_called',
            'receipt_id': receipt_id,
            'correlation_id': correlation_id,
            'tool_name': tool_name,
            'risk_level': f'R{tool.risk_level.value}',
            'agent_id': agent_id,
            'timestamp': receipt.timestamp
        })
        
        # Check if approval needed
        if tool.requires_approval:
            if not self.approval_service:
                receipt.status = 'failed'
                receipt.error = 'Approval service not configured for R3 action'
                self.audit_trail.append({
                    'event': 'tool_failed',
                    'receipt_id': receipt_id,
                    'reason': 'No approval service configured'
                })
                return {
                    'error': receipt.error,
                    'receipt_id': receipt_id,
                    'correlation_id': correlation_id
                }
            
            approval_request = ApprovalRequest(
                receipt_id=receipt_id,
                tool_name=tool_name,
                risk_level=tool.risk_level,
                args=args
            )
            
            # Request approval from service
            approval = await self.approval_service.request_approval(approval_request)
            
            if not approval.approved:
                receipt.status = 'rejected'
                self.audit_trail.append({
                    'event': 'approval_rejected',
                    'receipt_id': receipt_id,
                    'reason': approval.reason
                })
                return {
                    'error': 'Approval denied',
                    'receipt_id': receipt_id,
                    'correlation_id': correlation_id
                }
            
            receipt.approval_by = approval.approved_by
            receipt.approval_timestamp = approval.approved_at
            
            self.audit_trail.append({
                'event': 'approval_granted',
                'receipt_id': receipt_id,
                'approved_by': approval.approved_by,
                'timestamp': approval.approved_at
            })
        
        # Execute tool
        try:
            if self.tc is None:
                # Mock execution for testing
                result = {'status': 'success', 'tool': tool_name}
            else:
                result = await self.tc.execute_tool(tool_name, **args)
            
            receipt.status = 'executed'
            receipt.output_hash = self._hash_output(result)
            
            self.audit_trail.append({
                'event': 'tool_executed',
                'receipt_id': receipt_id,
                'tool_name': tool_name,
                'status': 'success',
                'timestamp': datetime.utcnow().isoformat()
            })
            
            return {
                'result': result,
                'receipt_id': receipt_id,
                'correlation_id': correlation_id
            }
        
        except Exception as e:
            receipt.status = 'failed'
            receipt.error = str(e)
            
            self.audit_trail.append({
                'event': 'tool_failed',
                'receipt_id': receipt_id,
                'tool_name': tool_name,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            })
            
            return {
                'error': str(e),
                'receipt_id': receipt_id,
                'correlation_id': correlation_id
            }
    
    def get_receipt(self, receipt_id: str) -> Optional[TrustComplianceReceipt]:
        """Retrieve receipt by ID.
        
        Args:
            receipt_id: Receipt ID to lookup
        
        Returns:
            TrustComplianceReceipt if found, None otherwise
        """
        return self.receipts.get(receipt_id)
    
    def get_audit_trail(self, correlation_id: str = None) -> list:
        """Get audit trail, optionally filtered by correlation ID.
        
        Args:
            correlation_id: Optional correlation ID to filter
        
        Returns:
            List of audit trail entries
        """
        if correlation_id:
            return [
                e for e in self.audit_trail
                if e.get('correlation_id') == correlation_id or e.get('receipt_id') in [
                    r.receipt_id for r in self.receipts.values()
                    if r.correlation_id == correlation_id
                ]
            ]
        return self.audit_trail.copy()
    
    def get_receipts_by_status(self, status: str) -> list:
        """Get all receipts with a specific status.
        
        Args:
            status: Status to filter (pending, approved, executed, failed, rejected)
        
        Returns:
            List of receipts with matching status
        """
        return [r for r in self.receipts.values() if r.status == status]
    
    def get_pending_approvals(self) -> list:
        """Get all receipts pending approval.
        
        Returns:
            List of pending approval receipts
        """
        return self.get_receipts_by_status('pending')
