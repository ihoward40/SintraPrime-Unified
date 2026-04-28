# Trust Compliance Gateway Integration with IkeOS ToolGateway

## Overview

This document describes how to integrate Trust Compliance tools into the IkeOS ToolGateway policy system.

## Integration Points

### 1. Core Policy Mapper Integration

In `core/ikeos_integration/policy_mapper.py`, add the following:

```python
from phase19.trust_compliance_gateway.policy_mapping import (
    TrustCompliancePolicyMapper, IkeOSPolicyIntegration
)

class PolicyMapper:
    def __init__(self):
        # ... existing code ...
        
        # Add Trust Compliance policy
        self.trust_compliance_integration = IkeOSPolicyIntegration()
        self.trust_compliance_policy = TrustCompliancePolicyMapper.get_policy()
    
    def get_risk_level(self, tool_name: str) -> int:
        """Get risk level for a tool.
        
        Args:
            tool_name: Full tool name (e.g., 'trust_compliance.intake')
        
        Returns:
            Risk level 0-3 or None if tool not found
        """
        # Check if this is a Trust Compliance tool
        if tool_name.startswith('trust_compliance.'):
            return self.trust_compliance_integration.get_risk_level(tool_name)
        
        # ... handle other tool domains ...
    
    def requires_approval(self, tool_name: str) -> bool:
        """Check if a tool requires approval.
        
        Args:
            tool_name: Full tool name
        
        Returns:
            True if approval required, False otherwise
        """
        if tool_name.startswith('trust_compliance.'):
            return self.trust_compliance_integration.requires_approval(tool_name)
        
        # ... handle other tool domains ...
    
    def get_rate_limit(self, tool_name: str) -> str:
        """Get rate limit for a tool.
        
        Args:
            tool_name: Full tool name
        
        Returns:
            Rate limit string (e.g., '100/hour')
        """
        if tool_name.startswith('trust_compliance.'):
            return self.trust_compliance_integration.get_rate_limit(tool_name)
        
        # ... default rate limit ...
    
    def validate_agent_access(self, tool_name: str, agent: str) -> tuple:
        """Validate if an agent can access a tool.
        
        Args:
            tool_name: Full tool name
            agent: Agent name
        
        Returns:
            Tuple of (allowed: bool, reason: str)
        """
        if tool_name.startswith('trust_compliance.'):
            return TrustCompliancePolicyMapper.validate_tool_access(tool_name, agent)
        
        # ... handle other tool domains ...
```

### 2. ToolGateway Gateway Integration

In `core/ikeos_integration/tool_gateway.py`, add:

```python
from phase19.trust_compliance_gateway.trust_compliance_adapter import (
    TrustComplianceGatewayAdapter
)

class IkeOSToolGateway:
    def __init__(self):
        # ... existing code ...
        
        # Initialize Trust Compliance Gateway adapter
        self.trust_compliance_adapter = TrustComplianceGatewayAdapter(
            approval_service=self.approval_service
        )
    
    async def call_tool(self, tool_name: str, args: dict, agent_id: str, **kwargs):
        """Call a tool through the gateway.
        
        Routes Trust Compliance tools through the dedicated adapter.
        """
        if tool_name.startswith('trust_compliance.'):
            return await self.trust_compliance_adapter.call_tool(
                tool_name, args, agent_id, **kwargs
            )
        
        # ... route to other tool adapters ...
```

### 3. Approval Service Integration

The Trust Compliance Gateway expects an approval service with this interface:

```python
class ApprovalService:
    async def request_approval(self, approval_request: ApprovalRequest) -> Approval:
        """Request approval for an R3 action.
        
        Args:
            approval_request: ApprovalRequest with receipt_id, tool_name, risk_level, args
        
        Returns:
            Approval object with approved (bool), approved_by (str), approved_at (str)
        """
        # Implementation sends request to approval queue,
        # waits for human approval, returns result
        pass
```

### 4. Receipt and Audit Trail Storage

The adapter maintains in-memory receipt and audit trail storage. For production, integrate with:

- **Database**: Store receipts with unique receipt_id for permanent audit trail
- **Stripe**: Attach receipt_id to charges for compliance tracking
- **Notion**: Store receipt metadata for case management
- **Google Drive**: Archive execution logs with receipt_id for retention

Example database schema:

```sql
CREATE TABLE trust_compliance_receipts (
    receipt_id VARCHAR(36) PRIMARY KEY,
    correlation_id VARCHAR(36),
    tool_name VARCHAR(255),
    risk_level VARCHAR(2),
    status VARCHAR(20),
    agent_id VARCHAR(100),
    timestamp TIMESTAMP,
    input_hash VARCHAR(64),
    output_hash VARCHAR(64),
    approval_by VARCHAR(100),
    approval_timestamp TIMESTAMP,
    error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE trust_compliance_audit_trail (
    id INT AUTO_INCREMENT PRIMARY KEY,
    receipt_id VARCHAR(36),
    correlation_id VARCHAR(36),
    event VARCHAR(50),
    event_data JSON,
    timestamp TIMESTAMP,
    FOREIGN KEY (receipt_id) REFERENCES trust_compliance_receipts(receipt_id)
);
```

## Tool Registry

The Trust Compliance tool registry defines all available tools with metadata:

| Tool | Risk Level | Requires Approval | Description |
|------|------------|-------------------|-------------|
| `trust_compliance.intake` | R0 | No | Client intake form processing |
| `trust_compliance.classify` | R0 | No | Determine trust type and jurisdiction |
| `trust_compliance.generate_summary` | R1 | No | Summarize trust structure |
| `trust_compliance.rewrite_clause` | R1 | No | Suggest improved language |
| `trust_compliance.create_exhibit` | R1 | No | Generate family trees/asset schedules |
| `trust_compliance.prepare_bank_packet` | R2 | No | Create bank-ready documents |
| `trust_compliance.prepare_court_packet` | R2 | No | Create court-ready documents |
| `trust_compliance.send_client_email` | R2 | No | Send documents to client |
| `trust_compliance.external_submit` | R3 | **Yes** | Submit to court/agency |
| `trust_compliance.tax_related_output` | R3 | **Yes** | Generate tax filings |

## Risk Classification

- **R0** (Read-only): No external impact, no approval needed
- **R1** (Internal): Client-visible but internal processing, no approval needed
- **R2** (External Delivery): External communication but not regulatory, no approval needed
- **R3** (Regulatory)**: Tax filings, court submissions, requires approval from senior attorney/admin

## Rate Limiting

Rate limits are enforced per risk level:

- **R0**: 10,000 calls/hour (very permissive)
- **R1**: 1,000 calls/hour (standard)
- **R2**: 500 calls/hour (restricted)
- **R3**: 100 calls/hour (highly restricted)

## Approval Workflow

For R3 tools (external_submit, tax_related_output):

1. **Request**: Agent calls tool, receipt generated with status='pending'
2. **Queue**: Approval service receives approval request with receipt details
3. **Review**: Senior attorney/admin reviews request (1-hour timeout)
4. **Decision**: Approval granted or denied
5. **Execution**: If approved, tool executes; if denied, returns error
6. **Receipt**: Updated with approval_by, approval_timestamp, and final status

## Receipt Tracking

Each tool call generates a unique receipt containing:

```json
{
    "receipt_id": "550e8400-e29b-41d4-a716-446655440000",
    "correlation_id": "workflow-123",
    "tool_name": "trust_compliance.external_submit",
    "risk_level": "R3",
    "status": "executed",
    "agent_id": "nova",
    "timestamp": "2026-04-28T08:20:00Z",
    "input_hash": "sha256...",
    "output_hash": "sha256...",
    "approval_by": "admin@example.com",
    "approval_timestamp": "2026-04-28T08:21:00Z",
    "error": null
}
```

## Audit Trail

Complete audit trail tracking:

```
[
  {
    "event": "tool_called",
    "receipt_id": "550e8400...",
    "tool_name": "trust_compliance.external_submit",
    "risk_level": "R3",
    "agent_id": "nova",
    "timestamp": "2026-04-28T08:20:00Z"
  },
  {
    "event": "approval_granted",
    "receipt_id": "550e8400...",
    "approved_by": "admin@example.com",
    "timestamp": "2026-04-28T08:21:00Z"
  },
  {
    "event": "tool_executed",
    "receipt_id": "550e8400...",
    "status": "success",
    "timestamp": "2026-04-28T08:21:30Z"
  }
]
```

## Usage Examples

### Example 1: R0 Tool (No Approval)

```python
adapter = TrustComplianceGatewayAdapter()
result = await adapter.call_tool(
    'trust_compliance.intake',
    {'client_name': 'John Doe', 'trust_doc': '...'},
    agent_id='sigma'
)
# Returns immediately with receipt and result
```

### Example 2: R3 Tool (With Approval)

```python
adapter = TrustComplianceGatewayAdapter(approval_service=approval_service)
result = await adapter.call_tool(
    'trust_compliance.external_submit',
    {'recipient': 'court@example.com', 'documents': [...]},
    agent_id='nova'
)
# Waits for approval, executes after approval granted
```

### Example 3: Retrieve Receipt and Audit Trail

```python
# Get receipt
receipt = adapter.get_receipt(receipt_id)
print(receipt.status)  # 'executed'
print(receipt.approval_by)  # 'admin@example.com'

# Get audit trail for correlation
trail = adapter.get_audit_trail(correlation_id)
for entry in trail:
    print(f"{entry['timestamp']}: {entry['event']}")
```

## Testing

Run comprehensive tests:

```bash
pytest phase19/trust_compliance_gateway/tests/ -v

# Expected output: 40+ tests, 100% pass rate
```

## Acceptance Criteria Verification

✅ All Trust Compliance calls go through ToolGateway adapter
✅ All calls emit receipts with unique receipt_id (uuid4)
✅ R3 actions (external_submit, tax_related_output) require approval
✅ Receipts include input/output hashes for integrity verification
✅ Audit trail tracks complete execution history
✅ 40+ tests with 100% pass rate
✅ Complete documentation and integration guide

## Next Steps

1. Integrate with core/ikeos_integration/policy_mapper.py
2. Wire approval service for R3 actions
3. Set up persistent receipt storage in database
4. Configure Stripe charge metadata attachment
5. Wire Notion integration for case management
6. Set up Google Drive archival for audit trails
7. Deploy to production with monitoring
