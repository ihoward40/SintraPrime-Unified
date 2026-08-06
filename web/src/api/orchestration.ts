export type OrchestrationRun = {
  run_id: string;
  objective: string;
  status: string;
  execution_mode: string;
  classification: {
    task_type: string;
    sensitivity: string;
    required_roles: string[];
    approval_requirement: boolean;
  };
  nodes: Array<{
    node_id: string;
    role: string;
    status: string;
    assigned_provider?: string | null;
    confidence?: number | null;
    dependencies: string[];
  }>;
  routing_decisions: Array<{
    selected_provider: string | null;
    candidate_providers: string[];
    rejected_providers: Array<{ provider_id: string; reason: string }>;
    selection_reason: string;
  }>;
  budget: {
    input_tokens_used: number;
    output_tokens_used: number;
    provider_cost_used: number;
    nodes_used: number;
    retries_used: number;
    hard_limit_reached: boolean;
    limit_reason?: string | null;
  };
  verification: Array<{
    verification_result: string;
    confidence_score: number;
    evidence_quality: string;
    contradictions: string[];
    unresolved_uncertainty: string[];
  }>;
  reconciliation?: {
    verified_result: { claims: string[] };
    supported_inference: string[];
    unresolved_issue: string[];
    principal_decision_required: string[];
    disputed_claims: Array<{ claim: string; resolution: string }>;
    final_confidence: number;
  } | null;
  approvals: Array<{
    approval_id: string;
    requested_action: string;
    reason: string;
    status: string;
  }>;
  events: Array<{
    sequence: number;
    event_type: string;
    actor_role?: string | null;
    created_at: string;
  }>;
};

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem('sintraprime_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function executeOrchestration(payload: {
  objective: string;
  constraints: Record<string, unknown>;
  execution_mode: string;
  budget_limits: Record<string, unknown>;
}): Promise<OrchestrationRun> {
  const response = await fetch('/api/orchestration/execute', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(`Orchestration request failed: ${response.status}`);
  }
  return response.json();
}
