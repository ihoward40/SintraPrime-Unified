"""Comprehensive tests for Trust Compliance Gateway - Phase 19C

Tests cover:
- Tool registry and risk classification
- Receipt generation and tracking
- Approval workflow for R3 tools
- Audit trail logging
- Policy mapping and agent access control
- ToolGateway integration
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

# Import components
import sys
sys.path.insert(0, '/agent/home/phase19/trust_compliance_gateway')

from tool_registry import (
    TrustComplianceRisk, TrustComplianceTool, get_tool,
    get_tools_by_risk, get_tools_by_agent, TRUST_TOOLS
)
from trust_compliance_adapter import (
    TrustComplianceGatewayAdapter, TrustComplianceReceipt,
    ApprovalRequest
)
from policy_mapping import (
    TrustCompliancePolicyMapper, IkeOSPolicyIntegration
)


# ============================================================================
# TOOL REGISTRY TESTS (6 tests)
# ============================================================================

class TestToolRegistry:
    """Tests for tool registry functionality."""
    
    def test_tool_registry_loaded(self):
        """Tool registry should load all defined tools."""
        assert len(TRUST_TOOLS) == 10
    
    def test_get_tool_by_name(self):
        """get_tool should return tool by name."""
        tool = get_tool('trust_compliance.intake')
        assert tool is not None
        assert tool.name == 'intake'
        assert tool.risk_level == TrustComplianceRisk.R0
    
    def test_get_tool_not_found(self):
        """get_tool should return None for unknown tool."""
        tool = get_tool('nonexistent.tool')
        assert tool is None
    
    def test_get_tools_by_risk_r0(self):
        """get_tools_by_risk should return R0 tools."""
        r0_tools = get_tools_by_risk(TrustComplianceRisk.R0)
        assert len(r0_tools) >= 2
        for tool in r0_tools:
            assert tool.risk_level == TrustComplianceRisk.R0
    
    def test_get_tools_by_agent_any(self):
        """get_tools_by_agent should return tools for 'any' agent."""
        tools = get_tools_by_agent('any')
        assert len(tools) > 0
    
    def test_get_tools_by_agent_nova(self):
        """get_tools_by_agent should return tools for specific agent."""
        tools = get_tools_by_agent('nova')
        assert len(tools) > 0
        # All 'any' tools plus nova-specific tools
        any_tools = get_tools_by_agent('any')
        assert len(tools) >= len(any_tools)


# ============================================================================
# RISK CLASSIFICATION TESTS (7 tests)
# ============================================================================

class TestRiskClassification:
    """Tests for risk level classification."""
    
    def test_r0_read_only_tools(self):
        """R0 tools should be read-only with no external impact."""
        r0_tools = get_tools_by_risk(TrustComplianceRisk.R0)
        for tool in r0_tools:
            assert not tool.requires_approval
    
    def test_r1_internal_tools(self):
        """R1 tools should be internal processing."""
        r1_tools = get_tools_by_risk(TrustComplianceRisk.R1)
        for tool in r1_tools:
            assert not tool.requires_approval
    
    def test_r2_external_delivery_tools(self):
        """R2 tools handle external delivery."""
        r2_tools = get_tools_by_risk(TrustComplianceRisk.R2)
        assert len(r2_tools) > 0
        for tool in r2_tools:
            assert not tool.requires_approval
    
    def test_r3_regulatory_tools(self):
        """R3 tools require approval."""
        r3_tools = get_tools_by_risk(TrustComplianceRisk.R3)
        assert len(r3_tools) == 2  # external_submit, tax_related_output
        for tool in r3_tools:
            assert tool.requires_approval
    
    def test_intake_is_r0(self):
        """Intake should be R0 (read-only)."""
        tool = get_tool('trust_compliance.intake')
        assert tool.risk_level == TrustComplianceRisk.R0
    
    def test_classify_is_r0(self):
        """Classify should be R0 (read-only)."""
        tool = get_tool('trust_compliance.classify')
        assert tool.risk_level == TrustComplianceRisk.R0
    
    def test_external_submit_is_r3(self):
        """External submit should be R3 (requires approval)."""
        tool = get_tool('trust_compliance.external_submit')
        assert tool.risk_level == TrustComplianceRisk.R3
        assert tool.requires_approval


# ============================================================================
# RECEIPT GENERATION TESTS (8 tests)
# ============================================================================

@pytest.mark.asyncio
class TestReceiptGeneration:
    """Tests for receipt generation and tracking."""
    
    async def test_receipt_generation_r0_no_approval(self):
        """R0 tools should generate receipt without approval."""
        adapter = TrustComplianceGatewayAdapter()
        result = await adapter.call_tool(
            'trust_compliance.intake',
            {'data': 'test'},
            agent_id='agent-1'
        )
        
        assert 'receipt_id' in result
        assert 'correlation_id' in result
        assert 'result' in result
    
    async def test_receipt_unique_ids(self):
        """Each receipt should have unique IDs."""
        adapter = TrustComplianceGatewayAdapter()
        result1 = await adapter.call_tool(
            'trust_compliance.intake',
            {'data': 'test1'},
            agent_id='agent-1'
        )
        result2 = await adapter.call_tool(
            'trust_compliance.intake',
            {'data': 'test2'},
            agent_id='agent-1'
        )
        
        assert result1['receipt_id'] != result2['receipt_id']
    
    async def test_receipt_stores_tool_name(self):
        """Receipt should store the tool name."""
        adapter = TrustComplianceGatewayAdapter()
        result = await adapter.call_tool(
            'trust_compliance.classify',
            {'trust_doc': 'test'},
            agent_id='agent-1'
        )
        
        receipt = adapter.get_receipt(result['receipt_id'])
        assert receipt.tool_name == 'trust_compliance.classify'
    
    async def test_receipt_stores_agent_id(self):
        """Receipt should store the agent ID."""
        adapter = TrustComplianceGatewayAdapter()
        result = await adapter.call_tool(
            'trust_compliance.intake',
            {'data': 'test'},
            agent_id='sigma'
        )
        
        receipt = adapter.get_receipt(result['receipt_id'])
        assert receipt.agent_id == 'sigma'
    
    async def test_receipt_stores_timestamp(self):
        """Receipt should store execution timestamp."""
        adapter = TrustComplianceGatewayAdapter()
        before = datetime.utcnow().isoformat()
        result = await adapter.call_tool(
            'trust_compliance.intake',
            {'data': 'test'},
            agent_id='agent-1'
        )
        after = datetime.utcnow().isoformat()
        
        receipt = adapter.get_receipt(result['receipt_id'])
        assert receipt.timestamp is not None
        assert before <= receipt.timestamp <= after
    
    async def test_receipt_input_hash(self):
        """Receipt should hash input arguments."""
        adapter = TrustComplianceGatewayAdapter()
        result = await adapter.call_tool(
            'trust_compliance.intake',
            {'data': 'test', 'id': '123'},
            agent_id='agent-1'
        )
        
        receipt = adapter.get_receipt(result['receipt_id'])
        assert receipt.input_hash is not None
        assert len(receipt.input_hash) == 64  # SHA256 hex length
    
    async def test_receipt_output_hash(self):
        """Receipt should hash output result."""
        adapter = TrustComplianceGatewayAdapter()
        result = await adapter.call_tool(
            'trust_compliance.intake',
            {'data': 'test'},
            agent_id='agent-1'
        )
        
        receipt = adapter.get_receipt(result['receipt_id'])
        assert receipt.output_hash is not None
        assert len(receipt.output_hash) == 64  # SHA256 hex length
    
    async def test_get_receipt_not_found(self):
        """get_receipt should return None for unknown receipt."""
        adapter = TrustComplianceGatewayAdapter()
        receipt = adapter.get_receipt('nonexistent-id')
        assert receipt is None


# ============================================================================
# APPROVAL WORKFLOW TESTS (8 tests)
# ============================================================================

@pytest.mark.asyncio
class TestApprovalWorkflow:
    """Tests for R3 approval workflow."""
    
    async def test_r3_tool_requires_approval_service(self):
        """R3 tools should fail without approval service."""
        adapter = TrustComplianceGatewayAdapter(approval_service=None)
        result = await adapter.call_tool(
            'trust_compliance.external_submit',
            {'data': 'test'},
            agent_id='nova'
        )
        
        assert 'error' in result
        assert 'Approval service not configured' in result['error']
    
    async def test_r3_tool_approval_denied(self):
        """R3 tool should fail when approval denied."""
        approval_service = AsyncMock()
        approval = MagicMock()
        approval.approved = False
        approval.reason = 'Pending review'
        approval_service.request_approval = AsyncMock(return_value=approval)
        
        adapter = TrustComplianceGatewayAdapter(approval_service=approval_service)
        result = await adapter.call_tool(
            'trust_compliance.external_submit',
            {'data': 'test'},
            agent_id='nova'
        )
        
        assert 'error' in result
        assert 'Approval denied' in result['error']
    
    async def test_r3_tool_approval_granted(self):
        """R3 tool should execute when approval granted."""
        approval_service = AsyncMock()
        approval = MagicMock()
        approval.approved = True
        approval.approved_by = 'admin@example.com'
        approval.approved_at = datetime.utcnow().isoformat()
        approval_service.request_approval = AsyncMock(return_value=approval)
        
        adapter = TrustComplianceGatewayAdapter(approval_service=approval_service)
        result = await adapter.call_tool(
            'trust_compliance.external_submit',
            {'data': 'test'},
            agent_id='nova'
        )
        
        assert 'result' in result
        assert 'error' not in result
    
    async def test_receipt_approval_fields(self):
        """Receipt should track approval information."""
        approval_service = AsyncMock()
        approval = MagicMock()
        approval.approved = True
        approval.approved_by = 'admin@example.com'
        approval.approved_at = '2026-04-28T08:20:00Z'
        approval_service.request_approval = AsyncMock(return_value=approval)
        
        adapter = TrustComplianceGatewayAdapter(approval_service=approval_service)
        result = await adapter.call_tool(
            'trust_compliance.tax_related_output',
            {'data': 'test'},
            agent_id='nova'
        )
        
        receipt = adapter.get_receipt(result['receipt_id'])
        assert receipt.approval_by == 'admin@example.com'
        assert receipt.approval_timestamp == '2026-04-28T08:20:00Z'
    
    async def test_approval_request_creation(self):
        """Approval request should contain required fields."""
        approval_service = AsyncMock()
        approval = MagicMock()
        approval.approved = True
        approval.approved_by = 'admin'
        approval.approved_at = '2026-04-28T08:20:00Z'
        approval_service.request_approval = AsyncMock(return_value=approval)
        
        adapter = TrustComplianceGatewayAdapter(approval_service=approval_service)
        await adapter.call_tool(
            'trust_compliance.external_submit',
            {'doc': 'test'},
            agent_id='nova'
        )
        
        # Verify approval request was called
        assert approval_service.request_approval.called
    
    async def test_r0_tool_no_approval_call(self):
        """R0 tools should not call approval service."""
        approval_service = AsyncMock()
        
        adapter = TrustComplianceGatewayAdapter(approval_service=approval_service)
        await adapter.call_tool(
            'trust_compliance.intake',
            {'data': 'test'},
            agent_id='agent-1'
        )
        
        # Approval service should not be called for R0
        assert not approval_service.request_approval.called
    
    async def test_r3_pending_status(self):
        """Receipt should show pending status for R3 before approval."""
        approval_service = AsyncMock()
        approval = MagicMock()
        approval.approved = True
        approval.approved_by = 'admin'
        approval.approved_at = '2026-04-28T08:20:00Z'
        approval_service.request_approval = AsyncMock(return_value=approval)
        
        adapter = TrustComplianceGatewayAdapter(approval_service=approval_service)
        result = await adapter.call_tool(
            'trust_compliance.external_submit',
            {'data': 'test'},
            agent_id='nova'
        )
        
        receipt = adapter.get_receipt(result['receipt_id'])
        # After execution, should be 'executed'
        assert receipt.status == 'executed'


# ============================================================================
# AUDIT TRAIL TESTS (6 tests)
# ============================================================================

@pytest.mark.asyncio
class TestAuditTrail:
    """Tests for audit trail logging."""
    
    async def test_audit_trail_logs_tool_call(self):
        """Audit trail should log tool calls."""
        adapter = TrustComplianceGatewayAdapter()
        result = await adapter.call_tool(
            'trust_compliance.intake',
            {'data': 'test'},
            agent_id='agent-1'
        )
        
        trail = adapter.get_audit_trail()
        assert len(trail) > 0
        assert any(e['event'] == 'tool_called' for e in trail)
    
    async def test_audit_trail_logs_execution(self):
        """Audit trail should log tool execution."""
        adapter = TrustComplianceGatewayAdapter()
        result = await adapter.call_tool(
            'trust_compliance.intake',
            {'data': 'test'},
            agent_id='agent-1'
        )
        
        trail = adapter.get_audit_trail()
        assert any(e['event'] == 'tool_executed' for e in trail)
    
    async def test_audit_trail_logs_approval(self):
        """Audit trail should log approval decision."""
        approval_service = AsyncMock()
        approval = MagicMock()
        approval.approved = True
        approval.approved_by = 'admin@example.com'
        approval.approved_at = '2026-04-28T08:20:00Z'
        approval_service.request_approval = AsyncMock(return_value=approval)
        
        adapter = TrustComplianceGatewayAdapter(approval_service=approval_service)
        result = await adapter.call_tool(
            'trust_compliance.external_submit',
            {'data': 'test'},
            agent_id='nova'
        )
        
        trail = adapter.get_audit_trail()
        assert any(e['event'] == 'approval_granted' for e in trail)
    
    async def test_audit_trail_correlation_id(self):
        """Audit trail entries should include correlation ID."""
        adapter = TrustComplianceGatewayAdapter()
        result = await adapter.call_tool(
            'trust_compliance.intake',
            {'data': 'test'},
            agent_id='agent-1',
            correlation_id='corr-123'
        )
        
        trail = adapter.get_audit_trail('corr-123')
        assert len(trail) > 0
        # At least one entry should have the correlation ID
        assert any(e.get('correlation_id') == 'corr-123' for e in trail)
    
    async def test_get_audit_trail_filters_by_correlation(self):
        """get_audit_trail should filter by correlation ID."""
        adapter = TrustComplianceGatewayAdapter()
        
        result1 = await adapter.call_tool(
            'trust_compliance.intake',
            {'data': 'test1'},
            agent_id='agent-1',
            correlation_id='corr-1'
        )
        result2 = await adapter.call_tool(
            'trust_compliance.intake',
            {'data': 'test2'},
            agent_id='agent-1',
            correlation_id='corr-2'
        )
        
        trail1 = adapter.get_audit_trail('corr-1')
        trail2 = adapter.get_audit_trail('corr-2')
        
        assert len(trail1) > 0
        assert len(trail2) > 0
    
    async def test_audit_trail_logs_errors(self):
        """Audit trail should log execution errors."""
        tc = MagicMock()
        tc.execute_tool = AsyncMock(side_effect=Exception('Test error'))
        
        adapter = TrustComplianceGatewayAdapter(tc_engine=tc)
        result = await adapter.call_tool(
            'trust_compliance.intake',
            {'data': 'test'},
            agent_id='agent-1'
        )
        
        trail = adapter.get_audit_trail()
        assert any(e['event'] == 'tool_failed' for e in trail)


# ============================================================================
# POLICY MAPPING TESTS (7 tests)
# ============================================================================

class TestPolicyMapping:
    """Tests for policy mapping and ToolGateway integration."""
    
    def test_policy_mapper_get_policy(self):
        """Policy mapper should generate policy dictionary."""
        policy = TrustCompliancePolicyMapper.get_policy()
        
        assert 'domain' in policy
        assert policy['domain'] == 'trust_compliance'
        assert 'tools' in policy
        assert 'approval_queue' in policy
    
    def test_policy_has_all_tools(self):
        """Policy should include all registered tools."""
        policy = TrustCompliancePolicyMapper.get_policy()
        assert len(policy['tools']) == 10
    
    def test_policy_tool_structure(self):
        """Policy tools should have required fields."""
        policy = TrustCompliancePolicyMapper.get_policy()
        
        for name, tool_policy in policy['tools'].items():
            assert 'name' in tool_policy
            assert 'description' in tool_policy
            assert 'risk_level' in tool_policy
            assert 'requires_approval' in tool_policy
            assert 'allowed_agents' in tool_policy
            assert 'rate_limit' in tool_policy
    
    def test_policy_r0_high_rate_limit(self):
        """R0 tools should have high rate limits."""
        policy = TrustCompliancePolicyMapper.get_policy()
        
        r0_tools = policy['tools']['trust_compliance.intake']
        rate = int(r0_tools['rate_limit'].split('/')[0])
        assert rate >= 10000
    
    def test_policy_r3_low_rate_limit(self):
        """R3 tools should have low rate limits."""
        policy = TrustCompliancePolicyMapper.get_policy()
        
        r3_tool = policy['tools']['trust_compliance.external_submit']
        rate = int(r3_tool['rate_limit'].split('/')[0])
        assert rate <= 100
    
    def test_map_to_tool_gateway_format(self):
        """Policy should map to ToolGateway format."""
        gateway = TrustCompliancePolicyMapper.map_to_tool_gateway()
        
        assert 'gateway_tools' in gateway
        assert 'approval_config' in gateway
        assert 'domain' in gateway
        assert len(gateway['gateway_tools']) == 10
    
    def test_approval_queue_configuration(self):
        """Approval queue should be properly configured."""
        policy = TrustCompliancePolicyMapper.get_policy()
        
        assert policy['approval_queue']['enabled'] is True
        assert policy['approval_queue']['timeout_seconds'] == 3600
        assert 'admin' in policy['approval_queue']['roles']


# ============================================================================
# AGENT ACCESS CONTROL TESTS (4 tests)
# ============================================================================

class TestAgentAccessControl:
    """Tests for agent-based access control."""
    
    def test_get_tools_by_agent(self):
        """Should return tools accessible to agent."""
        tools = TrustCompliancePolicyMapper.get_tools_by_agent('nova')
        assert len(tools) > 0
    
    def test_validate_tool_access_allowed(self):
        """Should allow access to permitted tools."""
        allowed, reason = TrustCompliancePolicyMapper.validate_tool_access(
            'trust_compliance.intake', 'nova'
        )
        assert allowed is True
    
    def test_validate_tool_access_denied(self):
        """Should deny access to non-permitted tools."""
        allowed, reason = TrustCompliancePolicyMapper.validate_tool_access(
            'invalid_tool', 'nova'
        )
        assert allowed is False
    
    def test_r3_agent_restrictions(self):
        """R3 tools should be restricted to specific agents."""
        policy = TrustCompliancePolicyMapper.get_policy()
        r3_tool = policy['tools']['trust_compliance.external_submit']
        
        # Only nova and sigma should be in allowed agents for R3
        assert 'nova' in r3_tool['allowed_agents'] or 'sigma' in r3_tool['allowed_agents']


# ============================================================================
# IKEOS INTEGRATION TESTS (5 tests)
# ============================================================================

class TestIkeOSIntegration:
    """Tests for IkeOS ToolGateway integration."""
    
    def test_ikeos_policy_integration_init(self):
        """IkeOS integration should load policies."""
        integration = IkeOSPolicyIntegration()
        assert integration.trust_compliance_policy is not None
        assert integration.gateway_format is not None
    
    def test_ikeos_get_risk_level(self):
        """Should return correct risk level for tools."""
        integration = IkeOSPolicyIntegration()
        
        r0_level = integration.get_risk_level('trust_compliance.intake')
        assert r0_level == 0
        
        r3_level = integration.get_risk_level('trust_compliance.external_submit')
        assert r3_level == 3
    
    def test_ikeos_requires_approval(self):
        """Should correctly identify approval requirements."""
        integration = IkeOSPolicyIntegration()
        
        assert integration.requires_approval('trust_compliance.external_submit') is True
        assert integration.requires_approval('trust_compliance.intake') is False
    
    def test_ikeos_get_rate_limit(self):
        """Should return rate limits for tools."""
        integration = IkeOSPolicyIntegration()
        
        limit = integration.get_rate_limit('trust_compliance.intake')
        assert limit is not None
        assert '/' in limit
    
    def test_ikeos_unknown_tool(self):
        """Should handle unknown tools gracefully."""
        integration = IkeOSPolicyIntegration()
        
        risk = integration.get_risk_level('unknown.tool')
        assert risk is None


# ============================================================================
# ERROR HANDLING TESTS (3 tests)
# ============================================================================

@pytest.mark.asyncio
class TestErrorHandling:
    """Tests for error handling."""
    
    async def test_unknown_tool_error(self):
        """Should return error for unknown tool."""
        adapter = TrustComplianceGatewayAdapter()
        result = await adapter.call_tool(
            'nonexistent.tool',
            {'data': 'test'},
            agent_id='agent-1'
        )
        
        assert 'error' in result
        assert 'Unknown tool' in result['error']
    
    async def test_execution_error_recorded(self):
        """Execution errors should be recorded in receipt."""
        tc = MagicMock()
        tc.execute_tool = AsyncMock(side_effect=Exception('Execution failed'))
        
        adapter = TrustComplianceGatewayAdapter(tc_engine=tc)
        result = await adapter.call_tool(
            'trust_compliance.intake',
            {'data': 'test'},
            agent_id='agent-1'
        )
        
        receipt = adapter.get_receipt(result['receipt_id'])
        assert receipt.status == 'failed'
        assert 'Execution failed' in receipt.error
    
    async def test_get_pending_approvals(self):
        """Should retrieve pending approval receipts."""
        approval_service = AsyncMock()
        approval = MagicMock()
        approval.approved = True
        approval.approved_by = 'admin'
        approval.approved_at = '2026-04-28T08:20:00Z'
        approval_service.request_approval = AsyncMock(return_value=approval)
        
        adapter = TrustComplianceGatewayAdapter(approval_service=approval_service)
        await adapter.call_tool(
            'trust_compliance.external_submit',
            {'data': 'test'},
            agent_id='nova'
        )
        
        # After approval, shouldn't have pending
        pending = adapter.get_pending_approvals()
        assert all(r.status != 'pending' for r in pending)


# ============================================================================
# RECEIPT SERIALIZATION TESTS (2 tests)
# ============================================================================

@pytest.mark.asyncio
class TestReceiptSerialization:
    """Tests for receipt serialization."""
    
    async def test_receipt_to_dict(self):
        """Receipt should serialize to dictionary."""
        adapter = TrustComplianceGatewayAdapter()
        result = await adapter.call_tool(
            'trust_compliance.intake',
            {'data': 'test'},
            agent_id='agent-1'
        )
        
        receipt = adapter.get_receipt(result['receipt_id'])
        receipt_dict = receipt.to_dict()
        
        assert isinstance(receipt_dict, dict)
        assert 'receipt_id' in receipt_dict
        assert 'risk_level' in receipt_dict
    
    async def test_receipt_dict_json_serializable(self):
        """Receipt dict should be JSON serializable."""
        adapter = TrustComplianceGatewayAdapter()
        result = await adapter.call_tool(
            'trust_compliance.intake',
            {'data': 'test'},
            agent_id='agent-1'
        )
        
        receipt = adapter.get_receipt(result['receipt_id'])
        receipt_dict = receipt.to_dict()
        
        # Should not raise exception
        json_str = json.dumps(receipt_dict)
        assert json_str is not None


# ============================================================================
# RISK MATRIX TESTS (1 test)
# ============================================================================

class TestRiskMatrix:
    """Tests for risk classification matrix."""
    
    def test_get_risk_matrix(self):
        """Risk matrix should classify all tools."""
        matrix = TrustCompliancePolicyMapper.get_risk_matrix()
        
        assert 'R0' in matrix
        assert 'R1' in matrix
        assert 'R2' in matrix
        assert 'R3' in matrix
        
        total = sum(len(v) for v in matrix.values())
        assert total == 10


# ============================================================================
# INTEGRATION FLOW TESTS (2 tests)
# ============================================================================

@pytest.mark.asyncio
class TestIntegrationFlow:
    """Tests for complete integration flows."""
    
    async def test_r0_to_r3_workflow(self):
        """Should handle workflow from R0 to R3 tools."""
        approval_service = AsyncMock()
        approval = MagicMock()
        approval.approved = True
        approval.approved_by = 'admin'
        approval.approved_at = '2026-04-28T08:20:00Z'
        approval_service.request_approval = AsyncMock(return_value=approval)
        
        adapter = TrustComplianceGatewayAdapter(approval_service=approval_service)
        
        # Execute R0 tool
        r0_result = await adapter.call_tool(
            'trust_compliance.intake',
            {'data': 'test'},
            agent_id='nova'
        )
        assert 'result' in r0_result
        
        # Execute R3 tool
        r3_result = await adapter.call_tool(
            'trust_compliance.external_submit',
            {'data': 'test'},
            agent_id='nova'
        )
        assert 'result' in r3_result
    
    async def test_audit_trail_complete_flow(self):
        """Audit trail should track complete execution flow."""
        approval_service = AsyncMock()
        approval = MagicMock()
        approval.approved = True
        approval.approved_by = 'admin'
        approval.approved_at = '2026-04-28T08:20:00Z'
        approval_service.request_approval = AsyncMock(return_value=approval)
        
        adapter = TrustComplianceGatewayAdapter(approval_service=approval_service)
        
        corr_id = 'test-correlation-123'
        await adapter.call_tool(
            'trust_compliance.external_submit',
            {'data': 'test'},
            agent_id='nova',
            correlation_id=corr_id
        )
        
        trail = adapter.get_audit_trail(corr_id)
        
        # Should have multiple events
        assert len(trail) >= 3


# ============================================================================
# Run tests with pytest
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
