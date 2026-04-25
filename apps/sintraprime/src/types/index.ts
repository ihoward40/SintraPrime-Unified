/**
 * Core type definitions for the SintraPrime autonomous agent system
 */

export interface TaskRequest {
  id: string;
  prompt: string;
  context?: any;
  priority: 'low' | 'medium' | 'high';
  requester: string;
  timestamp: string;
}

export interface Plan {
  id: string;
  taskId: string;
  steps: PlanStep[];
  constraints: any;
}

export interface PlanStep {
  id: string;
  description: string;
  tool: string;
  args: any;
  dependencies: string[];
}

export interface ToolCall {
  id: string;
  idempotencyKey: string;
  planStepId: string;
  tool: string;
  args: any;
  timestamp: string;
}

export interface ActionReceipt {
  id: string;
  toolCallId: string;
  actor: string;
  action: string;
  timestamp: string;
  result: any;
  hash: string;
}

export interface PolicyDecision {
  id: string;
  toolCallId: string;
  decision: 'allow' | 'block' | 'modify';
  reason: string;
  timestamp: string;
  modifiedArgs?: any;
}

export interface CredentialReference {
  id: string;
  credentialName: string;
  tokenHandle: string;
}

export interface JobState {
  id: string;
  planId: string;
  status: 'running' | 'paused' | 'waiting-human' | 'completed' | 'failed';
  currentStepId?: string;
  history: JobHistoryEntry[];
}

export interface JobHistoryEntry {
  stepId: string;
  status: 'completed' | 'failed';
  result?: any;
  error?: string;
  timestamp: string;
}

export interface BudgetPolicy {
  id: string;
  name: string;
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

export interface ReportArtifact {
  id: string;
  name: string;
  timestamp: string;
  format: 'pdf' | 'csv' | 'markdown';
  content: any;
}

export interface Tool {
  name: string;
  description: string;
  execute(args: any): Promise<any>;
}

export interface Connector {
  name: string;
  type: string;
  authenticate(): Promise<void>;
  call(method: string, endpointOrArgs: any, args?: any): Promise<any>;
}

/**
 * Execution context for agent tasks
 */
export interface ExecutionContext {
  userId?: string;
  agentId?: string;
  sessionId?: string;
  environment?: 'production' | 'staging' | 'development';
  [key: string]: any;
}

/**
 * Task to be executed by an agent
 */
export interface Task {
  id: string;
  type: string;
  description: string;
  params?: any;
  priority?: 'low' | 'medium' | 'high';
}

/**
 * Result of a task execution
 */
export interface TaskResult {
  success: boolean;
  output?: any;
  error?: string;
  metadata?: {
    duration?: number;
    timestamp?: string;
    [key: string]: any;
  };
}
