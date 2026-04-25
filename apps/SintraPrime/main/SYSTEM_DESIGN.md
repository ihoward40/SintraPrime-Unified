# SintraPrime Autonomous Agent System Design

This document outlines the system architecture and data models for the enhanced SintraPrime autonomous agent.

## System Architecture

The following diagram illustrates the high-level architecture of the system, which is designed to be modular, scalable, and secure.

```text
+--------------------------------------------------------------------------+
|                                  User Interface                          |
|                               (Web UI, CLI, API)                         |
+--------------------------------------------------------------------------+
|                                                                          |
|    +-----------------------+      +--------------------------+           |
|    |   Orchestrator/Planner  |----->| Policy Gate / Approval UI  |           |
|    +-----------------------+      +--------------------------+           |
|               |                                                          |
|               |                                                          |
|    +----------v-----------+      +--------------------------+           |
|    |      Job Queue &        |----->|   Always-On Runner       |           |
|    |       Scheduler         |      | (Cloud Hosted)           |           |
|    +-----------------------+      +--------------------------+           |
|               |                                                          |
|               |                                                          |
|    +----------v-----------+      +--------------------------+           |
|    |      Executor           |----->| Browser Automation Runner|           |
|    | (Tools & Connectors)  |      | (Playwright)             |           |
|    +-----------------------+      +--------------------------+           |
|               |                                                          |
|               |                                                          |
|    +----------v-----------+      +--------------------------+           |
|    |     Receipt Ledger      |----->|       Observability        |           |
|    | (Immutable Audit Trail) |      | (Logs, Metrics, Tracing) |           |
|    +-----------------------+      +--------------------------+           |
|                                                                          |
|    +-----------------------+                                             |
|    |     Secrets Vault       |                                             |
|    | (Credential Broker)     |                                             |
|    +-----------------------+                                             |
|                                                                          |
+--------------------------------------------------------------------------+
```

### Architecture Layers

1.  **User Interface:** The entry point for users to interact with the system, whether through a web interface, a command-line interface (CLI), or a programmatic API.

2.  **Orchestrator/Planner:** The brain of the system. It receives user requests, breaks them down into a sequence of steps (a plan), and coordinates the execution of that plan.

3.  **Policy Gate / Approval UI:** A critical governance component that intercepts high-risk actions and requires human approval before they can be executed. This includes actions like spending money, launching ad campaigns, or making destructive changes.

4.  **Job Queue & Scheduler:** Manages the execution of tasks, especially long-running background jobs. It allows tasks to be scheduled, queued, and executed reliably, even if the user disconnects.

5.  **Always-On Runner:** A cloud-hosted environment where jobs are executed. This ensures that tasks can run to completion without being tied to a user's local machine.

6.  **Executor:** The component responsible for executing individual steps in a plan. It uses a variety of tools and connectors to interact with external systems.

7.  **Browser Automation Runner:** A specialized executor that uses tools like Playwright to perform tasks that require web browser interaction, such as scraping websites or filling out forms.

8.  **Receipt Ledger:** An immutable ledger that records every action taken by the system. This provides a complete audit trail for governance, security, and debugging purposes.

9.  **Observability:** A suite of tools for monitoring the health and performance of the system. This includes logging, metrics, and tracing to provide insights into system behavior and help diagnose issues.

10. **Secrets Vault:** A secure repository for storing sensitive information like API keys, passwords, and other credentials. It ensures that secrets are never stored in plaintext and are accessed in a controlled manner.

## Data Models

The following TypeScript interfaces define the core data models for the system.

### TaskRequest

Represents a request from a user to perform a task.

```typescript
interface TaskRequest {
  id: string; // Unique identifier for the request
  prompt: string; // The user's natural language request
  context?: any; // Any additional context provided by the user
  priority: 'low' | 'medium' | 'high';
  requester: string; // Identifier for the user who made the request
  timestamp: string; // ISO 8601 timestamp of the request
}
```

### Plan

Represents the sequence of steps the agent will take to complete a task.

```typescript
interface Plan {
  id: string; // Unique identifier for the plan
  taskId: string; // The ID of the TaskRequest this plan is for
  steps: PlanStep[];
  constraints: any; // Any constraints on the execution of the plan
}

interface PlanStep {
  id: string; // Unique identifier for the step
  description: string; // A human-readable description of the step
  tool: string; // The tool to be used for this step
  args: any; // The arguments to be passed to the tool
  dependencies: string[]; // The IDs of any steps that must be completed before this one
}
```

### ToolCall

Represents a single call to a tool.

```typescript
interface ToolCall {
  id: string; // Unique identifier for the tool call
  idempotencyKey: string; // A key to prevent duplicate executions
  planStepId: string; // The ID of the plan step this call is for
  tool: string; // The tool being called
  args: any; // The arguments passed to the tool
  timestamp: string; // ISO 8601 timestamp of the call
}
```

### ActionReceipt

Represents a record of an action taken by the system.

```typescript
interface ActionReceipt {
  id: string; // Unique identifier for the receipt
  toolCallId: string; // The ID of the tool call that generated this receipt
  actor: string; // Who or what performed the action (e.g., 'agent', 'user')
  action: string; // A description of the action taken
  timestamp: string; // ISO 8601 timestamp of the action
  result: any; // The result of the action
  hash: string; // A hash of the receipt data to ensure integrity
}
```

### PolicyDecision

Represents a decision made by the policy gate.

```typescript
interface PolicyDecision {
  id: string; // Unique identifier for the decision
  toolCallId: string; // The ID of the tool call being evaluated
  decision: 'allow' | 'block' | 'modify';
  reason: string; // The reason for the decision
  timestamp: string; // ISO 8601 timestamp of the decision
}
```

### CredentialReference

Represents a reference to a credential stored in the secrets vault.

```typescript
interface CredentialReference {
  id: string; // Unique identifier for the reference
  credentialName: string; // The name of the credential
  tokenHandle: string; // A handle to the token in the secrets vault
}
```

### JobState

Represents the state of a job being executed by the system.

```typescript
interface JobState {
  id: string; // Unique identifier for the job
  planId: string; // The ID of the plan being executed
  status: 'running' | 'paused' | 'waiting-human' | 'completed' | 'failed';
  currentStepId?: string; // The ID of the current step being executed
  history: any[]; // A history of the job's execution
}
```

### BudgetPolicy

Represents a policy for controlling spending.

```typescript
interface BudgetPolicy {
  id: string; // Unique identifier for the policy
  name: string; // A human-readable name for the policy
  spendCaps: {
    daily: number;
    weekly: number;
    monthly: number;
  };
  thresholds: {
    requiresApproval: number;
  };
  perToolLimits: {
    [toolName: string]: number;
  };
}
```

### ReportArtifact

Represents a report generated by the system.

```typescript
interface ReportArtifact {
  id: string; // Unique identifier for the artifact
  name: string; // A human-readable name for the report
  timestamp: string; // ISO 8601 timestamp of the report generation
  format: 'pdf' | 'csv' | 'markdown';
  content: any; // The content of the report
}
```
