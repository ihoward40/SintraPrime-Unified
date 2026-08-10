export type AuthorityLevel = 'autonomous' | 'supervisor' | 'principal' | 'prohibited';
export type ActionClass =
  | 'reasoning'
  | 'research'
  | 'computer_use'
  | 'communication'
  | 'financial'
  | 'human_delegation'
  | 'legal'
  | 'physical';

export interface MissionBudget {
  currency: string;
  totalCap: number;
  autonomousTransactionCap: number;
  approvalThreshold: number;
}

export interface MissionAuthorityPolicy {
  byActionClass: Record<ActionClass, AuthorityLevel>;
  principalId: string;
}

export interface MissionSpec {
  id: string;
  objective: string;
  successCriteria: string[];
  stopConditions: string[];
  budget: MissionBudget;
  authority: MissionAuthorityPolicy;
  allowedModels: string[];
  allowedTools: string[];
  maxIterations: number;
  metadata?: Record<string, unknown>;
}

export interface ProposedAction {
  id: string;
  missionId: string;
  agentId: string;
  modelId: string;
  tool: string;
  actionClass: ActionClass;
  args: unknown;
  estimatedCost?: number;
  rationale: string;
}

export interface AuthorityDecision {
  decision: 'allow' | 'require_approval' | 'block';
  reason: string;
  requiredLevel?: AuthorityLevel;
}

export interface MissionState {
  missionId: string;
  status: 'ready' | 'running' | 'waiting_approval' | 'paused' | 'completed' | 'failed' | 'stopped';
  spent: number;
  iteration: number;
  lastActionId?: string;
  evidenceIds: string[];
}

export interface ModelProposal {
  modelId: string;
  summary: string;
  confidence?: number;
  action?: Omit<ProposedAction, 'id' | 'missionId'>;
  stop?: boolean;
}

export interface ModelAdapter {
  id: string;
  propose(spec: MissionSpec, state: MissionState, context?: unknown): Promise<ModelProposal>;
}
