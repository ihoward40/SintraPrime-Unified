# SintraPrime-Unified Integration Guide v2

This document outlines the Phase 18 architecture for integrating SintraPrime agents with the IkeOS ToolGateway, the security hardening measures implemented, and the test verification framework.

## 1. IkeOS Receipt Pattern Integration

SintraPrime agents (Zero, Sigma, Nova, Chat) now route all tool executions through the IkeOS ToolGateway using the **Receipt Pattern**. This ensures asynchronous execution, centralized policy enforcement, and a comprehensive audit trail.

### Architecture

The integration is handled by the `AgentToolGatewayWrapper` in `phase18/ikeos_integration/receipt_bridge.py`.

1.  **Submission:** The agent submits a `ToolRequest` to the gateway.
2.  **Policy Check:** The request is evaluated against the `PolicyMapper` (R0-R3 risk levels).
3.  **Receipt:** The gateway immediately returns a `Receipt` with a `pending` status.
4.  **Polling:** The wrapper polls the gateway until the receipt reaches a terminal state (`completed`, `failed`, `rejected`).
5.  **Audit:** Every step (submission, polling, completion) is recorded in the `AuditTrail`.

### Usage Example

```python
from phase18.ikeos_integration.receipt_bridge import ToolGatewayClient, make_zero_wrapper

# Initialize the gateway client
gateway = ToolGatewayClient(base_url="http://localhost:3000", api_key="your-api-key")

# Create the agent wrapper
zero_agent = make_zero_wrapper(gateway)

# Execute a tool (blocks until terminal state)
receipt = zero_agent.execute_tool(
    tool_name="search_case_law",
    payload={"query": "contract breach"}
)

if receipt.status == "completed":
    print("Result:", receipt.result)
else:
    print("Error:", receipt.error)
```

## 2. Security Hardening

Phase 18 introduced a comprehensive security layer (`phase18/security/security_hardening.py`) to address 32 identified vulnerabilities.

### Key Components

*   **RateLimiter:** Token-bucket algorithm to prevent API abuse.
*   **IdempotencyStore:** Ensures safe retries for mutating operations.
*   **ApiKeyStore:** Manages hashed API keys and revocation.
*   **AuthMiddleware:** Enforces `X-Api-Key` and Bearer token authentication.
*   **Sanitizers:** Protects against path traversal (`sanitize_project_name`) and prompt injection (`sanitize_legal_input`).

### SecurityLayer Wrapper

The `SecurityLayer` composite class wraps these components for easy integration into FastAPI or Flask routes.

```python
from phase18.security.security_hardening import SecurityLayer

security = SecurityLayer(redis_host="localhost")

# In a route handler:
def handle_request(request):
    # 1. Authenticate
    security.auth.require_api_key(request.headers.get("X-Api-Key"))
    
    # 2. Rate limit
    security.rate_limiter.consume(request.client_ip)
    
    # 3. Idempotency check
    if security.idempotency.is_processed(request.idempotency_key):
        return security.idempotency.get_result(request.idempotency_key)
        
    # ... process request ...
```

## 3. Test Verification Framework

To ensure ongoing compliance with security and reliability standards, the `IssueVerifier` (`phase18/verification/issue_verifier.py`) provides static analysis and runtime health checks.

### Static Analysis

The `StaticAnalyzer` scans Python source files for known anti-patterns, including:
*   `shell=True` in subprocess calls (SEC-001)
*   Hardcoded secrets (SEC-002)
*   `eval()` or `exec()` usage (SEC-003)
*   Bare `except:` clauses (REL-002)
*   Mutable default arguments (QUA-002)

### Runtime Health Probes

The `HealthChecker` verifies the operational status of critical dependencies:
*   IkeOS Gateway (`/health` endpoint)
*   Redis connection (`PING`)
*   PARL Orchestrator initialization

### Running the Verifier

```python
from phase18.verification.issue_verifier import IssueVerifier, HealthChecker

health = HealthChecker(gateway_url="http://localhost:3000")
verifier = IssueVerifier(root_dir=".", health_checker=health)

report = verifier.verify()
print(report.summary())

if not report.passed:
    for finding in report.findings:
        if finding.is_blocking():
            print(f"BLOCKING: {finding.issue_id} - {finding.description} at {finding.file_path}:{finding.line_number}")
```

## 4. Parallel Agent Reinforcement Learning (PARL)

The PARL framework continues to orchestrate multi-agent workflows. The integration with IkeOS ensures that all parallel tasks dispatched by the PARL Orchestrator are executed securely and asynchronously via the ToolGateway.

*   **Primary Agent:** Handles task decomposition and orchestration.
*   **Tasklet AI:** Specialized agents for specific subtasks (e.g., error remediation).
*   **Manus.ai:** Integrated for complex, multi-step implementations.

This architecture ensures that SintraPrime remains scalable, secure, and highly autonomous.
